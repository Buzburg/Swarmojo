"""Real desktop HTTP contracts, project isolation and preserved specialist behavior."""
import json
from pathlib import Path
import threading
import uuid

import pytest
from starlette.testclient import TestClient

from app.desktop import create_app, specialist_manifest, ROLE_TEMPLATES, Problem
from app.meta.models import ModelClient, ModelConfig
from app.meta.premade import get_premade_agents_dict

HEADERS = {'X-Swarmojo-Client': 'desktop'}


@pytest.fixture
def desktop(tmp_path):
    calls = []
    provider = ModelClient()
    def generate(config, messages, tools):
        calls.append(messages)
        if 'failure-fixture' in messages[-1]['content']:
            raise RuntimeError('provider unavailable: secret-key')
        content = json.dumps({'reply': 'Proposed a working greeting.', 'files': [{'path': 'hello.py', 'content': 'print("hello")\n'}]})
        return {'content': content, 'usage': {'total_tokens': 40}}
    provider.register_adapter('openai_compatible', generate)
    app = create_app(tmp_path/'desktop', provider)
    with TestClient(app, headers=HEADERS) as client:
        yield client, app.state.desktop, calls


def configure(client):
    r = client.put('/api/settings', json={'main_name':'Main agent', 'base_url':'http://127.0.0.1:8769/v1', 'model_id':'test-model'})
    assert r.status_code == 200, r.text


def project(client, name='Demo project'):
    r = client.post('/api/projects', json={'name':name, 'brief':'Build a tiny greeting script.'})
    assert r.status_code == 200, r.text
    return r.json()['id']


def chat(client, scope, text='Build a greeting script', **kwargs):
    return client.post(f'/api/conversations/{scope}/messages', json={'text':text, 'request_id':uuid.uuid4().hex, **kwargs})


def test_empty_projects_and_no_implicit_agents_or_model(desktop):
    client, service, _ = desktop
    state = client.get('/api/state').json()
    assert state['projects'] == [] and not state['model_configured']
    id = project(client)
    assert client.get('/api/state').json()['projects'][0]['agents'] == []
    result = chat(client, id)
    assert result.status_code == 503
    assert service.conversation(id)['messages'] == []


@pytest.mark.parametrize('role', list(ROLE_TEMPLATES))
def test_generic_names_preserve_specialist_capabilities(role):
    config = ModelConfig(model_id='fixture', max_call_cost_usd=0)
    original = get_premade_agents_dict()[ROLE_TEMPLATES[role]]
    custom = specialist_manifest(role, 'project-agent', 'My chosen name', config)
    assert custom.name == 'My chosen name'
    for attribute in ('role', 'description', 'tools', 'skills', 'memory_policy', 'temperature', 'division'):
        assert getattr(custom, attribute) == getattr(original, attribute)
    assert original.system_prompt in custom.system_prompt
    custom.tools.append('fixture')
    assert 'fixture' not in original.tools


def test_project_agent_rename_remove_and_restart(desktop):
    client, service, _ = desktop
    first, second = project(client), project(client,'Other')
    result = client.post(f'/api/projects/{first}/agents', json={'role':'designer'}).json()
    agent = next(p for p in result['projects'] if p['id']==first)['agents'][0]
    assert agent['name'] == 'Designer'
    r = client.patch(f'/api/projects/{first}/agents/{agent["id"]}', json={'role':'designer','name':'Visual lead'})
    assert r.status_code == 200
    assert service.agents(second) == []
    assert client.request('DELETE',f'/api/projects/{second}/agents/{agent["id"]}',json={}).status_code == 404
    reopened = create_app(service.directory).state.desktop
    assert reopened.agents(first)[0]['name'] == 'Visual lead'
    assert client.request('DELETE',f'/api/projects/{first}/agents/{agent["id"]}',json={}).status_code == 200
    assert service.agents(first) == []


def test_separate_main_chat_and_exact_approval_replay(desktop):
    client, service, calls = desktop
    configure(client)
    id = project(client)
    assert chat(client,'main','Hello Main').status_code == 200
    assert service.conversation(id)['messages'] == []
    request_id = uuid.uuid4().hex
    body = {'text':'Build a greeting','request_id':request_id}
    result = client.post(f'/api/conversations/{id}/messages',json=body)
    assert result.status_code == 200, result.text
    data = result.json()
    assert not (service.workspace(id)/'hello.py').exists()
    approval = data['approvals'][0]
    replay = client.post(f'/api/conversations/{id}/messages',json=body)
    assert replay.status_code == 200 and len(calls)==2
    assert all('Hello Main' not in m['content'] for m in calls[-1])
    url=f'/api/conversations/{id}/approvals/{approval["request_id"]}'
    assert client.post(url,json={'fingerprint':'0'*64,'decision':'approve'}).status_code==409
    accepted={'fingerprint':approval['fingerprint'],'decision':'approve'}
    assert client.post(url,json=accepted).status_code==200
    assert (service.workspace(id)/'hello.py').read_text()=='print("hello")\n'
    assert client.post(url,json=accepted).status_code==200
    assert service.conversation('main')['approvals']==[]
    assert len(service.conversation(id)['messages'])==2


def test_stale_write_and_foreign_approval_fail_closed(desktop):
    client, service, _ = desktop
    configure(client); first, second=project(client),project(client,'Other')
    approval=chat(client,first).json()['approvals'][0]
    body={'fingerprint':approval['fingerprint'],'decision':'approve'}
    assert client.post(f'/api/conversations/{second}/approvals/{approval["request_id"]}',json=body).status_code==404
    (service.workspace(first)/'hello.py').write_text('User changes')
    assert client.post(f'/api/conversations/{first}/approvals/{approval["request_id"]}',json=body).status_code==400
    assert (service.workspace(first)/'hello.py').read_text()=='User changes'


def test_rejected_action_never_applies(desktop):
    client, service, _ = desktop
    configure(client); id=project(client)
    a=chat(client,id).json()['approvals'][0]
    url=f'/api/conversations/{id}/approvals/{a["request_id"]}'
    assert client.post(url,json={'fingerprint':a['fingerprint'],'decision':'reject'}).status_code==200
    assert client.post(url,json={'fingerprint':a['fingerprint'],'decision':'approve'}).status_code==409
    assert not (service.workspace(id)/'hello.py').exists()


def test_selected_team_only_and_preserved_specialist_prompt(desktop):
    client, service, calls=desktop
    configure(client); first, second=project(client),project(client,'Other')
    client.post(f'/api/projects/{first}/agents',json={'role':'writer','name':'Editor'})
    client.post(f'/api/projects/{second}/agents',json={'role':'studio'})
    assert chat(client,first,team=True).status_code==200
    assert len(calls)==2
    system=calls[0][0]['content']
    source=get_premade_agents_dict()['author_scribe']
    assert source.system_prompt in system and 'Editor' in system
    assert all(tool in system for tool in source.tools)
    assert service.conversation(second)['messages']==[]


def test_provider_failure_is_explicit_not_simulated(desktop):
    client, service, calls=desktop
    configure(client)
    result=chat(client,'main','failure-fixture')
    assert result.status_code==502 and 'secret-key' not in result.text
    data=service.conversation('main')
    assert data['messages'][-1]['role']=='error' and not data['busy']
    assert data['approvals']==[]


def test_model_keys_never_persist_or_return(desktop):
    client,service,_=desktop
    secret='fixture-api-key-never-save'
    body={'main_name':'Assistant','display_name':'Sam','base_url':'https://example.com/v1','model_id':'demo','api_key':secret}
    assert client.put('/api/settings',json=body).status_code==200
    assert service.api_key==secret
    assert secret not in client.get('/api/state').text
    assert secret.encode() not in service.db_path.read_bytes()


@pytest.mark.parametrize('path', ['../escape','/tmp/escape','secrets/key','CON'])
def test_generated_unsafe_paths_never_write(desktop,path):
    client,service,_=desktop
    id=project(client)
    with pytest.raises((ValueError, Problem)):
        service.stage(id,json.dumps({'reply':'bad','files':[{'path':path,'content':'bad'}]}))
    assert service.conversation(id)['files']==[]


def test_origin_host_and_json_guards(desktop):
    client,service,_=desktop
    assert client.post('/api/projects',json={'name':'No'},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/state',headers={'Host':'evil.example'}).status_code==400
    assert client.post('/api/projects',content='name=No',headers={'Content-Type':'text/plain'}).status_code==403
    assert client.post('/api/projects',json={'name':'No'},headers={'X-Swarmojo-Client':''}).status_code==403
    assert client.post('/api/projects',content='x'*128001,headers={'Content-Type':'application/json'}).status_code==413
    assert service.state()['projects']==[]


def test_packaged_assets_and_preview_match(desktop):
    client,_,_=desktop
    root=Path(__file__).resolve().parents[1]
    for name in ('index.html','desktop.css','desktop.js'):
        assert (root/'app/desktop_assets'/name).read_bytes()==(root/'docs'/name).read_bytes()
        response=client.get('/' if name=='index.html' else '/'+name)
        assert response.status_code==200
        assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert client.get('/desktop.sqlite3').status_code==404


def test_nested_project_files_create_directories_only_after_approval(desktop):
    client, service, _ = desktop
    id = project(client)
    service.stage(id, json.dumps({'reply':'Ready for review', 'files':[
        {'path':'src/main.py','content':'print("ready")\n'},
        {'path':'src/util.py','content':'VALUE = 3\n'}]}))
    assert not (service.workspace(id)/'src').exists()
    for a in service.conversation(id)['approvals']:
        result=client.post(f'/api/conversations/{id}/approvals/{a["request_id"]}',json={
            'fingerprint':a['fingerprint'],'decision':'approve'})
        assert result.status_code==200, result.text
    assert (service.workspace(id)/'src/main.py').read_text()=='print("ready")\n'
    assert service.conversation(id)['files']==['src/main.py','src/util.py']


def test_symlink_swap_blocks_nested_write(desktop,tmp_path):
    client,service,_=desktop
    id=project(client)
    service.stage(id,json.dumps({'reply':'ready','files':[{'path':'src/main.py','content':'safe'}]}))
    a=service.conversation(id)['approvals'][0]
    outside=tmp_path/'outside';outside.mkdir()
    (service.workspace(id)/'src').symlink_to(outside,target_is_directory=True)
    result=client.post(f'/api/conversations/{id}/approvals/{a["request_id"]}',json={
        'fingerprint':a['fingerprint'],'decision':'approve'})
    assert result.status_code==400
    assert not (outside/'main.py').exists()


def test_duplicate_or_invalid_later_file_leaves_no_partial_proposals(desktop):
    client,service,_=desktop
    id=project(client)
    with pytest.raises((ValueError,Problem)):
        service.stage(id,json.dumps({'reply':'bad','files':[{'path':'a.txt','content':'a'},{'path':'b.txt','content':'\0'}]}))
    assert service.conversation(id)['approvals']==[]


def test_real_http_provider_roundtrip_and_conversation_context(tmp_path):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            payload=json.dumps({'choices':[{'message':{'content':'Hello from the configured provider'},'finish_reason':'stop'}],
                                'usage':{'total_tokens':30}}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with TestClient(create_app(tmp_path/'http-desktop'),headers=HEADERS) as client:
            assert client.put('/api/settings',json={'main_name':'Guide','model_id':'chosen-model',
                'base_url':f'http://127.0.0.1:{server.server_port}/v1'}).status_code==200
            assert chat(client,'main','My name is Jo').status_code==200
            result=chat(client,'main','What is my name?')
            assert result.status_code==200,result.text
            assert result.json()['messages'][-1]['content']=='Hello from the configured provider'
            assert result.json()['messages'][-1]['metadata']['simulated'] is False
            assert received[-1]['model']=='chosen-model'
            assert any(m['content']=='My name is Jo' for m in received[-1]['messages'])
    finally:
        server.shutdown();server.server_close();thread.join()


def test_sandbox_python_uses_the_active_mounted_runtime(desktop, monkeypatch):
    import sys
    import shutil
    client, service, _ = desktop
    if sys.platform != 'linux':
        pytest.skip('bubblewrap is Linux-only')
    original = shutil.which
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/bwrap' if name == 'bwrap' else
                        '/unmounted/host/python' if name == 'python' else original(name))
    argv = service.environment(project(client))._sandbox(['python', 'src/main.py'])
    assert argv[-2:] == [str(Path(sys.executable).resolve()), 'src/main.py']
    assert '/unmounted/host/python' not in argv


def test_project_controls_persist_and_block_old_approvals(desktop):
    client, service, _ = desktop
    configure(client); id = project(client)
    proposal = chat(client, id).json()['approvals'][0]
    data = {'action_mode':'discuss','share_files':False,'memory':'Use a warm voice.','budget_usd':5}
    result = client.put(f'/api/projects/{id}/options', json=data)
    assert result.status_code == 200, result.text
    assert result.json()['budget']['organization_hard_cap_usd'] == 5
    reopened = create_app(service.directory).state.desktop
    assert reopened.options(id)['memory'] == 'Use a warm voice.'
    assert not reopened.options(id)['share_files']
    assert client.post(f'/api/conversations/{id}/approvals/{proposal["request_id"]}', json={
        'fingerprint':proposal['fingerprint'],'decision':'approve'}).status_code == 403
    with pytest.raises(Problem, match='permissions'):
        service.stage(id,json.dumps({'reply':'Blocked','files':[{'path':'x','content':'x'}]}))
    client.put(f'/api/projects/{id}/options',json={'action_mode':'files'})
    with pytest.raises(Problem, match='permissions'):
        service.stage(id,json.dumps({'reply':'Blocked','commands':[['echo','hello']]}))
    assert not (service.workspace(id)/'hello.py').exists()


def test_project_memory_and_file_context_are_explicit_and_isolated(desktop):
    client, service, calls = desktop
    configure(client); first,second = project(client), project(client,'Separate')
    root=service.workspace(first)
    (root/'visible.txt').write_text('VISIBLE_CONTEXT')
    (root/'private.txt').write_text('EXCLUDED_CONTEXT')
    options={'memory':'PROJECT_DECISION','ignored_paths':['private.*']}
    assert client.put(f'/api/projects/{first}/options',json=options).status_code == 200
    assert chat(client,first).status_code == 200
    context=json.dumps(calls[-1])
    assert 'VISIBLE_CONTEXT' in context and 'PROJECT_DECISION' in context
    assert 'EXCLUDED_CONTEXT' not in context
    options['share_files']=False
    client.put(f'/api/projects/{first}/options',json=options)
    chat(client,first)
    # Earlier model responses do not contain fixture file contents.
    assert 'VISIBLE_CONTEXT' not in json.dumps(calls[-1])
    chat(client,second)
    assert 'PROJECT_DECISION' not in json.dumps(calls[-1])
    chat(client,'main')
    assert 'PROJECT_DECISION' not in json.dumps(calls[-1])


def test_agent_options_select_models_pause_and_preserve_role(desktop):
    client, service, _ = desktop
    configure(client); id=project(client)
    configs=[]
    def response(config,messages,tools):
        configs.append(config)
        return {'content':'A response','usage':{'total_tokens':4}}
    service.client.register_adapter('openai_compatible',response)
    client.post(f'/api/projects/{id}/agents',json={'role':'coder','name':'Builder','model_id':'coding-model','temperature':0.7})
    client.post(f'/api/projects/{id}/agents',json={'role':'writer','enabled':False})
    assert chat(client,id,team=True).status_code == 200
    assert [c.model_id for c in configs] == ['coding-model','test-model']
    assert configs[0].temperature == 0.7
    agent=service.agents(id)[0]
    r=client.patch(f'/api/projects/{id}/agents/{agent["id"]}',json={'role':'writer','name':'Renamed'})
    assert r.status_code == 400
    assert service.agents(id)[0]['role']=='coder'
    client.patch(f'/api/projects/{id}/agents/{agent["id"]}',json={'role':'coder','enabled':False})
    assert chat(client,id,team=True).status_code == 400
    assert len(configs)==2


def test_budget_is_enforced_before_provider_dispatch(desktop):
    client, service, calls = desktop
    configure(client); id=project(client)
    client.put('/api/settings',json={**service.settings(),'max_call_cost_usd':0.2})
    client.put(f'/api/projects/{id}/options',json={'budget_usd':0.3})
    assert chat(client,id).status_code == 200
    assert chat(client,id).status_code == 502
    assert len(calls)==1
    data=service.conversation(id)
    assert data['budget']['total_spend_usd']==0.2
    assert any(e['kind']=='run_failed' for e in data['activity'])
    assert not data['busy']


def test_task_dependencies_ownership_and_restart(desktop):
    client,service,_=desktop
    first,second=project(client),project(client,'Other')
    r=client.post(f'/api/projects/{first}/tasks',json={'title':'Design','description':'A reviewed layout'})
    assert r.status_code==200,r.text
    design=r.json()['tasks']['backlog'][0]['id']
    r=client.post(f'/api/projects/{first}/tasks',json={'title':'Build','blocked_by':[design]})
    build=next(t['id'] for t in r.json()['tasks']['backlog'] if t['title']=='Build')
    assert client.patch(f'/api/projects/{first}/tasks/{build}',json={'status':'in_progress'}).status_code==400
    assert client.patch(f'/api/projects/{second}/tasks/{design}',json={'status':'in_progress'}).status_code==400
    assert client.post(f'/api/projects/{second}/tasks',json={'title':'Invalid','blocked_by':[design]}).status_code==400
    assert client.post(f'/api/projects/{first}/tasks',json={'title':'Invalid','assignee_id':'foreign-agent'}).status_code==400
    for status in ['in_progress','review','done']:
        assert client.patch(f'/api/projects/{first}/tasks/{design}',json={'status':status}).status_code==200
    assert client.patch(f'/api/projects/{first}/tasks/{build}',json={'status':'in_progress'}).status_code==200
    reopened=create_app(service.directory).state.desktop
    assert reopened.conversation(first)['tasks']['done'][0]['title']=='Design'
    assert all(not rows for rows in reopened.conversation(second)['tasks'].values())
    assert any(e['kind']=='task_updated' for e in reopened.conversation(first)['activity'])


def test_agent_with_unfinished_tasks_cannot_be_removed(desktop):
    client,service,_=desktop
    id=project(client)
    client.post(f'/api/projects/{id}/agents',json={'role':'coder'})
    agent=service.agents(id)[0]['id']
    client.post(f'/api/projects/{id}/tasks',json={'title':'Build','assignee_id':agent})
    assert client.request('DELETE',f'/api/projects/{id}/agents/{agent}',json={}).status_code==409


@pytest.mark.parametrize('body',[{'ignored_paths':['../outside']},{'ignored_paths':['/absolute']},{'budget_usd':-1},{'action_mode':'automatic'}])
def test_project_options_reject_invalid_controls(desktop,body):
    client,_,_=desktop
    id=project(client)
    assert client.put(f'/api/projects/{id}/options',json=body).status_code in {400,422}


def test_task_edit_rejects_cycles_and_can_reassign(desktop):
    client,service,_=desktop
    id=project(client)
    a=client.post(f'/api/projects/{id}/tasks',json={'title':'First'}).json()['tasks']['backlog'][0]['id']
    result=client.post(f'/api/projects/{id}/tasks',json={'title':'Second','blocked_by':[a]}).json()
    b=next(t['id'] for t in result['tasks']['backlog'] if t['title']=='Second')
    r=client.put(f'/api/projects/{id}/tasks/{a}',json={'title':'Cycle','blocked_by':[b]})
    assert r.status_code==400 and 'cycle' in r.json()['error']
    client.post(f'/api/projects/{id}/agents',json={'role':'writer'})
    agent=service.agents(id)[0]['id']
    r=client.put(f'/api/projects/{id}/tasks/{b}',json={'title':'Write the brief','assignee_id':agent,'blocked_by':[a]})
    assert r.status_code==200
    task=next(t for t in r.json()['tasks']['backlog'] if t['id']==b)
    assert task['title']=='Write the brief' and task['assignee_id']==agent


def test_context_preparation_failure_does_not_stick_running(desktop,monkeypatch):
    client,service,calls=desktop
    configure(client);id=project(client)
    monkeypatch.setattr(service,'files',lambda scope: (_ for _ in ()).throw(OSError('Unreadable workspace')))
    assert chat(client,id).status_code==500
    with service.db() as db:
        assert db.execute('SELECT status FROM turns').fetchone()['status']=='failed'
    assert calls==[]
