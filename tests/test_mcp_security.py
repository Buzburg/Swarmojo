"""Real MCP dispatch and side-effect regressions for the local server boundary."""
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import MiddlewareContext

from app.mcp_policy import MCPPolicy, tool_annotations, plugin_allowed


def context(name):
    return MiddlewareContext(message=SimpleNamespace(name=name))


def test_default_policy_denies_mutation_before_function_runs():
    server = FastMCP('policy-test', middleware=[MCPPolicy(profile='read_only')])
    calls = []

    @server.tool(annotations=tool_annotations('memory_retain'))
    def memory_retain():
        calls.append('write')
        return 'unexpected'

    @server.tool(annotations=tool_annotations('memory_get'))
    def memory_get():
        return 'read result'

    async def check():
        async with Client(server) as client:
            listing = {t.name: t for t in await client.list_tools()}
            assert listing['memory_get'].annotations.model_dump(by_alias=True)['readOnlyHint']
            assert not listing['memory_retain'].annotations.model_dump(by_alias=True)['readOnlyHint']
            with pytest.raises(ToolError, match='read_only'):
                await client.call_tool('memory_retain')
            assert (await client.call_tool('memory_get')).content[0].text == 'read result'
    asyncio.run(check())
    assert calls == []


def test_operator_profile_and_destructive_opt_in_are_separate():
    async def check():
        calls = []
        async def next_call(ctx):
            calls.append(ctx.message.name)
            return 'ok'
        policy = MCPPolicy(profile='local', allow_destructive=False)
        assert await policy.on_call_tool(context('memory_retain'), next_call) == 'ok'
        with pytest.raises(ToolError, match='Destructive'):
            await policy.on_call_tool(context('memory_forget'), next_call)
        enabled = MCPPolicy(profile='local', allow_destructive=True)
        assert await enabled.on_call_tool(context('memory_forget'), next_call) == 'ok'
        assert calls == ['memory_retain', 'memory_forget']
    asyncio.run(check())


def test_limits_enforce_concurrency_recovery_and_sliding_window():
    async def check():
        now = [0.0]
        policy = MCPPolicy(profile='local', max_concurrent=1, calls_per_minute=3, clock=lambda:now[0])
        entered, release = asyncio.Event(), asyncio.Event()
        async def slow(ctx):
            entered.set()
            await release.wait()
            raise RuntimeError('fixture error')
        async def fast(ctx):return 'ok'
        running = asyncio.create_task(policy.on_call_tool(context('memory_get'), slow))
        await entered.wait()
        with pytest.raises(ToolError, match='concurrent'):
            await policy.on_call_tool(context('memory_get'), fast)
        release.set()
        with pytest.raises(RuntimeError):await running
        assert policy.inflight == 0
        assert await policy.on_call_tool(context('memory_get'), fast) == 'ok'
        with pytest.raises(ToolError, match='rate limit'):
            await policy.on_call_tool(context('memory_get'), fast)
        now[0] = 60
        assert await policy.on_call_tool(context('memory_get'), fast) == 'ok'
    asyncio.run(check())


@pytest.mark.parametrize('kwargs', [{'profile':'typo'},{'calls_per_minute':0},{'max_concurrent':0}])
def test_invalid_policy_fails_closed(kwargs):
    with pytest.raises(ValueError):MCPPolicy(**kwargs)


def test_plugin_import_and_hot_reload_need_explicit_operator_opt_ins(tmp_path, monkeypatch):
    from app import server, watcher
    root = tmp_path/'custom_tools';root.mkdir()
    marker = tmp_path/'executions.txt'
    source = f'from pathlib import Path\np=Path({str(marker)!r})\np.write_text(p.read_text()+"x" if p.exists() else "x")\n'
    (root/'approved.py').write_text(source)
    (root/'unapproved.py').write_text('raise RuntimeError("must never import")')
    monkeypatch.setattr(server, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(watcher, 'BASE_DIR', tmp_path)
    for key in ['SWARMOJO_MCP_PROFILE','SWARMOJO_MCP_PLUGINS','SWARMOJO_MCP_HOT_RELOAD']:
        monkeypatch.delenv(key,raising=False)
    server.load_custom_tools()
    watcher._reload_custom_tool(root/'approved.py')
    assert not marker.exists()
    monkeypatch.setenv('SWARMOJO_MCP_PROFILE','local')
    monkeypatch.setenv('SWARMOJO_MCP_PLUGINS','approved')
    server.load_custom_tools()
    assert marker.read_text() == 'x'
    watcher._reload_custom_tool(root/'approved.py')
    assert marker.read_text() == 'x'
    monkeypatch.setenv('SWARMOJO_MCP_HOT_RELOAD','1')
    watcher._reload_custom_tool(root/'approved.py')
    assert marker.read_text() == 'xx'
    assert not plugin_allowed(root/'unapproved.py',root)
    monkeypatch.setenv('SWARMOJO_MCP_PLUGINS','../approved')
    with pytest.raises(ValueError):plugin_allowed(root/'approved.py',root)


def test_plugin_symlinks_cannot_escape_allowlist(tmp_path, monkeypatch):
    root=tmp_path/'custom_tools';root.mkdir()
    outside=tmp_path/'outside.py';outside.write_text('raise RuntimeError()')
    try:(root/'approved.py').symlink_to(outside)
    except OSError:pytest.skip('Host does not permit symlinks')
    monkeypatch.setenv('SWARMOJO_MCP_PROFILE','local')
    monkeypatch.setenv('SWARMOJO_MCP_PLUGINS','approved')
    assert not plugin_allowed(root/'approved.py',root)


@pytest.mark.parametrize('name',['proofgraph_verify_step','workflowproof_verify_step'])
def test_mcp_proof_commands_require_review_instead_of_running_on_host(tmp_path, monkeypatch, name):
    from app.engine_tools import register_engine_tools
    root=tmp_path/'workspace';root.mkdir()
    monkeypatch.chdir(root)
    monkeypatch.setenv('SWARMOJO_CONTROL_DIR',str(tmp_path/'control'))
    (root/'unreviewed.py').write_text('from pathlib import Path\nPath("UNREVIEWED").write_text("bad")')
    server=FastMCP('proof-test',middleware=[MCPPolicy(profile='local')])
    register_engine_tools(server)
    async def check():
        async with Client(server) as client:
            response=await client.call_tool(name,{'step_id':'test','command':f'"{sys.executable}" unreviewed.py'})
            return json.loads(response.content[0].text)
    result=asyncio.run(check())
    assert result['approval_required']
    assert not (root/'UNREVIEWED').exists()
    assert result['request_id'] and result['fingerprint']


def test_refund_calculator_is_read_only_arithmetic():
    from custom_tools.example_tool import register_tools
    server=FastMCP('calculator')
    register_tools(server)
    async def check():
        async with Client(server) as client:
            tool=(await client.list_tools())[0]
            assert tool.annotations.model_dump(by_alias=True)['readOnlyHint'] and not tool.annotations.model_dump(by_alias=True)['openWorldHint']
            assert 'never issues a refund' in tool.description
            response=await client.call_tool('calculate_refund_amount',{'item_price':100,'return_shipping_fee':5})
            assert '$95.00' in response.content[0].text
            with pytest.raises(ToolError):
                await client.call_tool('calculate_refund_amount',{'item_price':-100})
    asyncio.run(check())
