"""Acceptance checks for provider-neutral, durable meta-harness execution."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.control_store import ControlStore
from app.engines.governance import HarnessGovernanceEngine
from app.meta.agent import MetaAgentInstance
from app.meta.dedup_cache import DeduplicatedExecutionCache
from app.meta.environment import ExecutionEnvironment
from app.meta.manifest import AgentManifest, EnvironmentConfig
from app.meta.models import ModelClient, ModelConfig, ModelError, ModelRegistry
from app.meta.parallel_dispatcher import ParallelToolDispatcher


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    root = tmp_path / 'workspace'
    root.mkdir()
    state = tmp_path / 'operator'
    monkeypatch.setenv('SWARMOJO_CONTROL_DIR', str(state))
    return root, state


def environment(runtime, scope='run:coder'):
    root, state = runtime
    return ExecutionEnvironment(EnvironmentConfig(id='test', name='test', root_path=str(root),
        snapshot_on_action=False, circuit_breaker_enabled=False), state_dir=state, scope=scope)


def approve(env, proposal):
    env.store.approve(proposal['request_id'], proposal['fingerprint'])
    return proposal['request_id']


def test_write_requires_exact_approval_and_replays_after_restart(runtime):
    env = environment(runtime)
    proposed = env.write_file('file.txt', 'one')
    assert proposed['approval_required'] and not (env.root_path / 'file.txt').exists()
    with pytest.raises(ValueError): env.store.approve(proposed['request_id'], 'incorrect')
    request = approve(env, proposed)
    assert not env.write_file('file.txt', 'different', request_id=request)['success']
    assert env.write_file('file.txt', 'one', request_id=request)['success']
    (env.root_path / 'file.txt').write_text('user edit')
    retried = environment(runtime).write_file('file.txt', 'one', request_id=request)
    assert retried['replayed'] and retried['success']
    assert (env.root_path / 'file.txt').read_text() == 'user edit'
    assert not environment(runtime, 'another:coder').write_file('file.txt', 'one', request_id=request)['success']


def test_stale_write_and_path_escape_are_rejected(runtime):
    env = environment(runtime)
    target = env.root_path / 'existing.txt'
    target.write_text('original')
    proposed = env.write_file(target.name, 'replacement')
    request = approve(env, proposed)
    target.write_text('edited by user')
    assert not env.write_file(target.name, 'replacement', request_id=request)['success']
    assert target.read_text() == 'edited by user'
    for path in ('../workspace-sibling/escape', '.git/config', '.env'):
        assert not env.write_file(path, 'forbidden')['success']
    outside = env.root_path.parent / 'outside.txt'
    outside.write_text('private')
    try: (env.root_path / 'linked.txt').symlink_to(outside)
    except OSError: return  # Windows runners may not grant symlink creation.
    assert not env.write_file('linked.txt', 'forbidden')['success']
    assert outside.read_text() == 'private'


def test_concurrent_retries_dispatch_once_and_crash_stays_uncertain(runtime):
    env = environment(runtime)
    action = {'test': 'effect'}
    proposed = env.store.propose(action, {}, env.scope)
    request = approve(env, proposed)
    effects = []
    def operation():
        effects.append('effect')
        time.sleep(.05)
        return {'ok': True}
    def attempt(_):
        store = ControlStore(*runtime)
        return store.execute(request, action, {}, env.scope, operation)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    assert effects == ['effect']
    assert any(r.get('ok') for r in results)
    assert attempt(0)['replayed']
    next_request = approve(env, env.store.propose(action, {}, env.scope))
    def interrupted(): raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        env.store.execute(next_request, action, {}, env.scope, interrupted)
    assert ControlStore(*runtime).execute(next_request, action, {}, env.scope, operation)['status'] == 'uncertain'
    assert effects == ['effect']


def test_control_state_cannot_live_in_workspace(runtime):
    with pytest.raises(ValueError): ControlStore(runtime[0], runtime[0] / 'state')


def test_budget_reservations_are_atomic_persistent_and_tasks_enforce_dependencies(runtime):
    gov = HarnessGovernanceEngine(str(runtime[0]))
    assert gov.get_org_chart()['nodes'] == []
    assert all(not tasks for tasks in gov.list_tasks().values())
    gov.hire_agent('coder', 'Coder', 'engineering', budget_cap_usd=2)
    gov.update_settings({'cost_hard_cap_usd': 1})
    def reserve(index):
        try:
            HarnessGovernanceEngine(str(runtime[0])).reserve('coder', 100, .6, str(index))
            return str(index)
        except ValueError: return None
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        accepted = [v for v in pool.map(reserve, range(8)) if v is not None]
    assert len(accepted) == 1
    resumed = HarnessGovernanceEngine(str(runtime[0]))
    assert resumed.get_budget_summary()['reserved_cost_usd'] == .6
    resumed.settle(accepted[0])
    assert gov.get_budget_summary()['total_spend_usd'] == .6
    with pytest.raises(ValueError): gov.hire_agent('coder', 'Reset', 'engineering')
    gov.create_task('first', 'Implement', '', assignee_id='coder')
    gov.create_task('second', 'Review', '', assignee_id='coder', blocked_by=['first'])
    with pytest.raises(ValueError): resumed.update_task_status('second', 'in_progress')
    with pytest.raises(ValueError): resumed.update_task_status('first', 'done')
    for status in ('in_progress', 'review', 'done'): resumed.update_task_status('first', status)
    assert gov.update_task_status('second', 'in_progress')['status'] == 'updated'


def agent(runtime, profile='mock', run='run', policy='compact_kv', client=None, registry=None):
    return MetaAgentInstance(AgentManifest(id='coder', name='Coder', role='coding', description='code',
        model_profile=profile, memory_policy=policy), workspace_root=str(runtime[0]), run_id=run,
        state_dir=runtime[1], model_client=client, model_registry=registry)


@pytest.mark.parametrize('policy', ['compact_kv', 'titans', 'none'])
def test_memory_requires_real_receipts_and_survives_resume(runtime, policy):
    worker = agent(runtime, policy=policy)
    worker.execute_turn('unverified: all tests passed')
    assert worker.store.facts(worker.scope) == []
    with pytest.raises(ValueError): worker.remember_receipt('made-up')
    env = environment(runtime, worker.scope)
    request = approve(env, env.write_file('evidence.txt', 'actual bytes'))
    env.write_file('evidence.txt', 'actual bytes', request_id=request)
    assert worker.remember_receipt(request)['verified']
    restored = agent(runtime, policy=policy)
    assert len(restored.store.facts(restored.scope)) == 1
    if policy == 'compact_kv': assert 'actual bytes' in restored.build_system_prompt()
    if policy == 'titans': assert restored.titans_mem.read('actual bytes', top_k=3)
    other = agent(runtime, run='different', policy=policy)
    assert other.store.facts(other.scope) == []
    with pytest.raises(ValueError): other.remember_receipt(request)
    bad = env.store.propose({'test': 'failed'}, {}, worker.scope)
    env.store.approve(bad['request_id'], bad['fingerprint'])
    env.store.execute(bad['request_id'], bad['action'], {}, worker.scope, lambda: {'ok': False})
    with pytest.raises(ValueError): worker.remember_receipt(bad['request_id'])


def test_two_provider_adapters_share_budget_and_errors_never_become_mock(runtime):
    registry = ModelRegistry()
    client = ModelClient(registry)
    seen = []
    for backend in ('provider-a', 'provider-b'):
        registry.register(backend, ModelConfig(model_id='arbitrary-' + backend, backend=backend,
                                              max_call_cost_usd=.1))
        def adapter(config, messages, tools):
            seen.append(config.model_id)
            return {'content': 'provider response', 'usage': {'total_tokens': 12}}
        client.register_adapter(backend, adapter)
        result = agent(runtime, backend, client=client, registry=registry).execute_turn('code')
        assert not result['simulated'] and result['model'] == 'arbitrary-' + backend
    worker = agent(runtime, 'provider-a', client=client, registry=registry)
    worker.governance.update_settings({'cost_hard_cap_usd': .2})
    with pytest.raises(ValueError, match='Budget exhausted'): worker.execute_turn('more')
    assert len(seen) == 2
    def broken(*args): raise ConnectionError('secret credential')
    client.register_adapter('provider-a', broken)
    with pytest.raises(ModelError, match='Provider request failed') as exc:
        client.generate(registry.get('provider-a'), [])
    assert 'secret credential' not in str(exc.value)
    with pytest.raises(ValueError): registry.get('typo-profile')
    with pytest.raises(ValueError): ModelConfig('x', extra_params={'max_tokens': 10**10})
    registry.register('secret', ModelConfig('id', api_key='private', headers={'X-Key': 'private'}))
    assert 'private' not in json.dumps(registry.list_profiles())


def test_openai_compatible_http_adapter_uses_selected_model():
    received = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append((self.path, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
            body = json.dumps({'choices': [{'message': {'content': 'hello'}, 'finish_reason': 'stop'}],
                               'usage': {'total_tokens': 9}}).encode()
            self.send_response(200); self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        def log_message(self, *args): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        result = ModelClient().generate(ModelConfig('users-choice', backend='openai_compatible',
                base_url=f'http://127.0.0.1:{server.server_port}/v1'), [{'role': 'user', 'content': 'hello'}])
        assert result['content'] == 'hello' and not result['simulated']
        assert received[0][0] == '/v1/chat/completions'
        assert received[0][1]['model'] == 'users-choice'
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_mcp_mutations_are_reviewable_and_workspace_is_fixed(runtime, monkeypatch):
    monkeypatch.chdir(runtime[0])
    from app.meta.meta_tools import register_meta_tools
    class Server:
        def __init__(self): self.tools = {}
        def tool(self, **kwargs):
            def register(fn): self.tools[fn.__name__] = fn; return fn
            return register
    server = Server(); register_meta_tools(server)
    tools = server.tools
    p = json.loads(tools['coding_write_atomic']('from-mcp.txt', 'review me'))
    assert p['approval_required'] and not (runtime[0] / 'from-mcp.txt').exists()
    assert not any('approve' in name and name != 'meta_execute_approved' for name in tools)
    env = environment(runtime, 'mcp'); approve(env, p)
    assert json.loads(tools['meta_execute_approved'](p['request_id']))['success']
    one = json.loads(tools['meta_dedup_run']('echo test'))
    other_server = Server(); register_meta_tools(other_server)
    two = json.loads(other_server.tools['meta_dedup_run']('echo test'))
    assert one['request_id'] == two['request_id'] and two['approval_required']
    with pytest.raises(ValueError): tools['meta_create_environment']('outside', 'outside', str(runtime[1]))
    with pytest.raises(ValueError): tools['coding_repo_codemap'](str(runtime[1]))
    with pytest.raises(ValueError): tools['meta_desktop_action']('type', text='x', dry_run=False)


def test_command_sandbox_fails_closed_without_backend(runtime, monkeypatch):
    env = environment(runtime)
    cmd = [sys.executable, '-c', "open('should-not-exist', 'w').write('x')"]
    request = approve(env, env.execute_command(cmd))
    monkeypatch.setattr('app.meta.environment.shutil.which', lambda _: None)
    result = env.execute_command(cmd, request_id=request)
    assert not result['success'] and not (runtime[0] / 'should-not-exist').exists()


@pytest.fixture
def linux_sandbox(runtime):
    if sys.platform != 'linux' or not shutil.which('bwrap'):
        pytest.skip('Real command sandbox acceptance requires Linux bubblewrap')
    env = environment(runtime)
    probe = subprocess.run(env._sandbox([sys.executable, '-c', 'pass']), capture_output=True, timeout=10)
    if probe.returncode:
        if os.environ.get('SWARMOJO_REQUIRE_SANDBOX') == '1': pytest.fail(probe.stderr.decode())
        pytest.skip('Host forbids bubblewrap user namespaces: ' + probe.stderr.decode()[:200])
    return env


def test_actual_sandbox_hides_host_secrets_and_dedup_survives_restart(runtime, linux_sandbox, monkeypatch):
    env = linux_sandbox
    secret = runtime[0].parent / 'private.txt'; secret.write_text('private')
    monkeypatch.setenv('SWARMOJO_TEST_SECRET', 'never pass')
    code = ("import os; from pathlib import Path; "
            f"assert not Path({str(secret)!r}).exists(); "
            f"assert not Path({str(env.store.directory)!r}).exists(); "
            "assert 'SWARMOJO_TEST_SECRET' not in os.environ; "
            "p=Path('count'); p.write_text(p.read_text()+'x' if p.exists() else 'x'); print('done')")
    cmd = [sys.executable, '-c', code]
    cache = DeduplicatedExecutionCache(workspace_root=runtime[0], state_dir=runtime[1])
    proposed = cache.get_or_run(cmd, tenant_id=env.scope)
    request = approve(env, proposed)
    result = cache.get_or_run(cmd, tenant_id=env.scope, request_id=request)
    assert result['success'], result
    again = DeduplicatedExecutionCache(workspace_root=runtime[0], state_dir=runtime[1])
    assert again.get_or_run(cmd, tenant_id=env.scope, request_id=request)['from_cache']
    assert (runtime[0] / 'count').read_text() == 'x'
    (runtime[0] / 'input.txt').write_text('one')
    pending = cache.get_or_run(cmd, input_paths=['input.txt'])
    (runtime[0] / 'input.txt').write_text('two')
    with pytest.raises(ValueError, match='inputs changed'):
        cache.get_or_run(cmd, input_paths=['input.txt'], request_id=pending['request_id'])


def test_actual_sandbox_timeout_and_output_bound(runtime, linux_sandbox):
    env = linux_sandbox
    cmd = [sys.executable, '-c', 'import time; time.sleep(10)']
    request = approve(env, env.execute_command(cmd, timeout=.2))
    result = env.execute_command(cmd, timeout=.2, request_id=request)
    assert result['status'] == 'timeout' and not result['success']
    cmd = [sys.executable, '-c', "print('x'*100000)"]
    request = approve(env, env.execute_command(cmd))
    result = env.execute_command(cmd, request_id=request)
    assert result['status'] == 'output_limit' and len(result['output']) <= 65536


@pytest.mark.parametrize('cancel', [False, True])
def test_dispatcher_stops_worker_and_descendant_before_late_effect(runtime, cancel):
    root, _ = runtime
    ready, late = root / 'ready', root / 'late'
    def work():
        import subprocess, sys, time
        from pathlib import Path
        child = subprocess.Popen([sys.executable, '-c',
            f"import time; from pathlib import Path; time.sleep(6); Path({str(late)!r}).write_text('escaped')"])
        ready.write_text(str(child.pid))
        time.sleep(10)
    event = threading.Event()
    def cancel_when_ready():
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline: time.sleep(.01)
        event.set()
    watcher = threading.Thread(target=cancel_when_ready, daemon=True)
    if cancel: watcher.start()
    result = ParallelToolDispatcher().execute_batch([('owned', work)], timeout_s=15 if cancel else 5,
                                                    cancelled=event if cancel else None)
    assert ready.exists(), 'Worker must actually start before testing cancellation'
    assert result['results']['owned']['status'] == ('cancelled' if cancel else 'timeout')
    if cancel: watcher.join(timeout=1)
    time.sleep(6.1)
    assert not late.exists(), 'Descendant survived the stopped worker'


def test_dispatcher_rejects_duplicate_ids_before_effect(runtime):
    target = runtime[0] / 'effect'
    with pytest.raises(ValueError):
        ParallelToolDispatcher().execute_batch([('same', lambda: target.write_text('x')), ('same', lambda: 2)])
    assert not target.exists()


def test_bound_command_inputs_cannot_be_bypassed_by_generic_retry(runtime):
    env = environment(runtime)
    source = runtime[0] / 'input.py'; source.write_text('one')
    cmd = [sys.executable, '-c', 'pass']
    cache = DeduplicatedExecutionCache(workspace_root=runtime[0], state_dir=runtime[1])
    proposal = cache.get_or_run(cmd, tenant_id=env.scope, input_paths=['input.py'])
    approve(env, proposal)
    source.write_text('two')
    record = env.store.inspect(proposal['request_id'])
    with pytest.raises(ValueError, match='inputs changed'):
        env.submit(record['action']['action'], request_id=proposal['request_id'])
    assert env.store.inspect(proposal['request_id'])['status'] == 'approved'


def test_recursive_agent_uses_provider_and_reserves_budget(runtime):
    from app.meta.coding_agent import PrimeRecursionEngine
    registry = ModelRegistry(); client = ModelClient(registry)
    registry.register('default', ModelConfig('chosen', backend='custom', max_call_cost_usd=.1))
    calls = []
    def adapter(config, messages, tools):
        calls.append(config.model_id)
        return {'content': 'real adapter result', 'usage': {'total_tokens': 10}}
    client.register_adapter('custom', adapter)
    recursive = PrimeRecursionEngine(workspace_root=str(runtime[0]), model_client=client, model_registry=registry)
    result = recursive.invoke_subagent('reviewer', 'Review code', 'Review code')
    assert result.content == 'real adapter result' and not result.metadata['simulated']
    gov = HarnessGovernanceEngine(str(runtime[0]))
    assert gov.get_budget_summary()['total_spend_usd'] == .1
    gov.update_settings({'cost_hard_cap_usd': .1})
    with pytest.raises(ValueError, match='Budget exhausted'):
        recursive.invoke_subagent('reviewer', 'Review code', 'Review code')
    assert calls == ['chosen']


def test_default_configuration_does_not_silently_choose_mock(runtime, monkeypatch):
    from app.meta.builder import AgentBuilder
    for key in ('SWARMOJO_MODEL_URL', 'SWARMOJO_MODEL_ID', 'SWARMMOJO_LOCAL_LLM_URL', 'SWARMMOJO_LOCAL_MODEL'):
        monkeypatch.delenv(key, raising=False)
    assert ModelConfig('chosen').backend == 'openai_compatible'
    manifest = AgentBuilder('custom').name('Custom').role('research').build()
    assert manifest.model_profile == 'default'
    with pytest.raises(ValueError, match='Unknown model profile'):
        MetaAgentInstance(manifest, workspace_root=str(runtime[0]))


def test_approval_expiry_and_provider_failure_preserve_conservative_accounting(runtime):
    env = environment(runtime)
    p = env.store.propose({'action': 'example'}, {}, env.scope, lifetime=-1)
    with pytest.raises(ValueError): env.store.approve(p['request_id'], p['fingerprint'])
    registry = ModelRegistry(); client = ModelClient(registry)
    registry.register('broken', ModelConfig('broken', backend='custom', max_call_cost_usd=.25))
    def broken(*args): raise TimeoutError('no response')
    client.register_adapter('custom', broken)
    worker = agent(runtime, 'broken', client=client, registry=registry)
    with pytest.raises(ModelError): worker.execute_turn('code')
    assert worker.governance.get_budget_summary()['total_spend_usd'] == .25
    assert worker.store.facts(worker.scope) == []


def test_titans_recall_keeps_persisted_candidate_at_negative_cosine_boundary(tmp_path):
    from app.engines.titans import TitansMemory
    memory = TitansMemory(root=str(tmp_path))
    memory.init()
    memory.write('actual bytes', key='2')
    restored = TitansMemory(root=str(tmp_path))
    assert restored.read('actual bytes') == [{'key':'2', 'value':'actual bytes'}]
    assert restored.recall('actual bytes')['confidence'] == 0
