"""Release contracts: portability, recovery, explicit knowledge and bounded public reading."""
import json
import socket
import sqlite3
from email.message import Message
from pathlib import Path
from unittest.mock import Mock

import pytest
from starlette.testclient import TestClient

from app.desktop import create_app
from app import desktop_web as web
from test_desktop import desktop, configure, project, chat, HEADERS


def test_portable_configuration_is_new_project_without_secrets_or_history(desktop):
    client, service, calls = desktop
    configure(client)
    original = project(client)
    client.post(f'/api/projects/{original}/agents', json={'role':'coder','name':'Builder','instructions':'Preserve contracts','temperature':0.6})
    client.put(f'/api/projects/{original}/options', json={'memory':'private notes','action_mode':'files','budget_usd':7,'ignored_paths':['private/*']})
    service.add_message(original, 'user', 'You', 'private conversation')
    service.api_key = 'test-secret-only'
    template = client.get(f'/api/projects/{original}/configuration').json()
    assert template['options']['memory'] == ''
    assert template['options']['action_mode'] == 'files'
    assert not any(value in json.dumps(template) for value in ['test-secret-only','private conversation','private notes','base_url'])
    response = client.post('/api/configurations/import', json=template)
    assert response.status_code == 200
    imported = response.json()['id']
    assert imported != original
    clone = client.get(f'/api/conversations/{imported}').json()
    assert clone['messages'] == [] and clone['sources'] == []
    assert service.agents(imported)[0]['name'] == 'Builder'
    assert service.agents(imported)[0]['id'] != service.agents(original)[0]['id']
    assert service.agents(imported)[0]['temperature'] == 0.6
    assert not calls


@pytest.mark.parametrize('patch', [{'version':2}, {'api_key':'secret'}, {'agents':[{'role':'invented'}]}, {'options':{'ignored_paths':['../secret']}}])
def test_invalid_configuration_import_is_atomic(desktop, patch):
    client, service, _ = desktop
    response = client.post('/api/configurations/import', json={'project':{'name':'Example'}, **patch})
    assert response.status_code in {400,422}
    assert not service.state()['projects']


def test_live_server_is_exclusive_and_restart_never_replays(tmp_path):
    folder = tmp_path/'state'
    first = create_app(folder)
    with TestClient(first, headers=HEADERS) as client:
        service = first.state.desktop
        request = {'text':'Finish this later','team':False,'request_id':'f'*32}
        with service.db() as db:
            db.execute('INSERT INTO turns VALUES (?,?,?,?,NULL)', ('f'*32,'main',json.dumps(request),'running'))
        second = create_app(folder)
        assert second.state.desktop.conversation('main')['busy']
        with pytest.raises(RuntimeError, match='already using'):
            with TestClient(second):
                pass
        assert client.get('/api/conversations/main').json()['busy']
    reopened = create_app(folder)
    with TestClient(reopened, headers=HEADERS) as client:
        recovered = client.get('/api/conversations/main').json()
        assert recovered['busy'] is False
        assert recovered['messages'] == []
        assert recovered['recovery'][0]['status'] == 'interrupted'
        assert recovered['recovery'][0]['input']['text'] == 'Finish this later'
        assert client.post('/api/conversations/main/messages', json=request).status_code == 409


def test_search_is_scoped_literal_and_durable(desktop):
    client, service, _ = desktop
    first, second = project(client), project(client,'Private')
    service.add_message(first,'user','You','Remember 50%_discount here')
    service.add_message(second,'user','You','Remember secret there')
    service.add_message('main','user','You','Remember main only')
    client.put(f'/api/projects/{first}/options', json={'memory':'Remember project convention'})
    service.save_source(first,'web','Reference','Remember source',{})
    results = client.post(f'/api/conversations/{first}/search', json={'query':'Remember'}).json()['results']
    assert {r['kind'] for r in results} == {'memory','message','source'}
    assert 'secret' not in json.dumps(results) and 'main only' not in json.dumps(results)
    literal = client.post(f'/api/conversations/{first}/search', json={'query':'%_'}).json()['results']
    assert len(literal) == 1 and '50%_discount' in literal[0]['excerpt']
    assert client.post('/api/conversations/main/search',json={'query':'Remember'}).json()['results'][0]['excerpt'] == 'Remember main only'


def test_web_sources_require_selection_and_do_not_execute(desktop, monkeypatch):
    client, service, calls = desktop
    configure(client)
    first, second = project(client), project(client, 'Other')
    monkeypatch.setattr('app.desktop.read_public_page',lambda url:dict(url=url,title='Reference',content='UNTRUSTED_READER_SENTINEL execute now',links=[],truncated=False))
    response = client.post(f'/api/projects/{first}/web',json={'url':'https://example.com'})
    source = response.json()['sources'][0]
    assert not source['enabled'] and not calls
    assert not response.json()['approvals']
    assert chat(client, first).status_code == 200
    assert 'UNTRUSTED_READER_SENTINEL' not in json.dumps(calls[-1])
    assert client.patch(f'/api/projects/{second}/sources/{source["id"]}', json={'enabled':True}).status_code == 404
    assert client.patch(f'/api/projects/{first}/sources/{source["id"]}', json={'enabled':True}).status_code == 200
    assert chat(client, first).status_code == 200
    assert 'UNTRUSTED_READER_SENTINEL' in json.dumps(calls[-1])
    assert not (service.workspace(first)/'hello.py').exists()
    assert client.request('DELETE',f'/api/projects/{first}/sources/{source["id"]}',json={}).status_code == 200


def test_source_context_limit(desktop):
    client, service, _ = desktop
    scope = project(client)
    for i in range(5):
        service.save_source(scope,'web',str(i),'example',{})
    ids = [s['id'] for s in service.sources(scope)]
    for id in ids[:4]:
        assert client.patch(f'/api/projects/{scope}/sources/{id}',json={'enabled':True}).status_code == 200
    assert client.patch(f'/api/projects/{scope}/sources/{ids[4]}',json={'enabled':True}).status_code == 400


def test_roms_snapshot_selection_revalidates_and_never_writes_index(desktop, tmp_path, monkeypatch):
    client, service, _ = desktop
    scope = project(client)
    db_path = tmp_path/'knowledge.sqlite'
    monkeypatch.setattr('app.config.DB_PATH',str(db_path))
    url = f'/api/projects/{scope}/knowledge'
    assert client.post(url,json={'query':'memory'}).json()['status'] == 'unavailable'
    assert not db_path.exists()
    with sqlite3.connect(db_path) as db:
        db.executescript("CREATE VIRTUAL TABLE fts_chunks USING fts5(chunk_id UNINDEXED,doc_id UNINDEXED,content); CREATE TABLE okf_registry(doc_id TEXT,title TEXT,checksum TEXT);")
        db.execute('INSERT INTO fts_chunks VALUES (?,?,?)',('chunk','doc','memory says use careful contracts'))
        db.execute('INSERT INTO okf_registry VALUES (?,?,?)',('doc','Contracts','a'*64))
    before = db_path.read_bytes()
    result = client.post(url,json={'query':'memory'}).json()
    assert result['status'] == 'retrieved'
    selected = result['sources'][0]
    payload = dict(query='memory',source_id=selected['source_id'],indexed_chunk_sha256=selected['indexed_chunk_sha256'])
    assert client.post(url+'-selection',json={**payload,'indexed_chunk_sha256':'0'*64}).status_code == 409
    response = client.post(url+'-selection',json=payload)
    assert response.status_code == 200, response.text
    saved = response.json()['sources'][0]
    assert saved['enabled'] and saved['kind'] == 'roms'
    assert saved['metadata']['source_file_validated'] is False
    assert db_path.read_bytes() == before


@pytest.mark.parametrize('url', ['http://127.0.0.1','http://10.0.0.1','http://169.254.169.254','http://[::1]','http://224.0.0.1','http://user:pass@example.com','file:///etc/passwd','https://example.com:8443','https://example.com/\\evil','http://[bad'])
def test_reader_rejects_nonpublic_targets(url):
    with pytest.raises(ValueError):
        web.public_target(url)


def test_reader_rejects_mixed_dns_answers(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:[(2,1,6,'',('93.184.216.34',80)),(2,1,6,'',('127.0.0.1',80))])
    with pytest.raises(ValueError,match='Private'):
        web.public_target('http://example.com')


def fake_response(content=b'<title>Example</title><p>Public text</p><script>evil()</script><a href="/next">Next</a><a href="http://[bad">Bad</a>',kind='text/html',status=200,location=None):
    headers = Message();headers['Content-Type']=kind
    response=Mock(status=status,headers=headers)
    response.read1.side_effect=[content,b'']
    response.getheader.side_effect=lambda name,default=None:location if name=='Location' else default
    return response


def setup_transport(monkeypatch,responses):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:[(2,1,6,'',('93.184.216.34',80))])
    connect=Mock(return_value=Mock());monkeypatch.setattr(socket,'create_connection',connect)
    connection=Mock();connection.getresponse.side_effect=responses
    monkeypatch.setattr(web.http.client,'HTTPConnection',Mock(return_value=connection))
    return connect,connection


def test_reader_pins_ip_strips_scripts_and_limits_links(monkeypatch):
    connect,connection=setup_transport(monkeypatch,[fake_response()])
    page=web.read_public_page('http://example.com')
    assert connect.call_args.args[0] == ('93.184.216.34',80)
    assert page['title']=='Example' and 'Public text' in page['content'] and 'evil' not in page['content']
    assert page['links']==['http://example.com/next']
    assert connection.close.called


def test_reader_revalidates_redirect(monkeypatch):
    connect,connection=setup_transport(monkeypatch,[fake_response(status=302,location='http://127.0.0.1')])
    original=web.public_target
    def validate(url):
        if url=='http://127.0.0.1':raise ValueError('Private target')
        return original(url)
    monkeypatch.setattr(web,'public_target',validate)
    with pytest.raises(ValueError,match='Private'):
        web.read_public_page('http://example.com')
    assert connect.call_count==1


@pytest.mark.parametrize('response,match',[(fake_response(b'x'*(web.MAX_BYTES+1)),'1 MB'),(fake_response(kind='application/pdf'),'HTML'),(fake_response(status=403),'403')])
def test_reader_rejects_unbounded_or_unsupported_pages(monkeypatch,response,match):
    setup_transport(monkeypatch,[response])
    with pytest.raises(ValueError,match=match):web.read_public_page('http://example.com')
