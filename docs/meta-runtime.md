# Swarmojo's model-agnostic meta runtime

Swarmojo is a standalone harness for coding, review, research, coordination, and custom
specialists. Its core does not require RWKV, Qwen, FlashMojo, Omarchy, or a particular
model vendor. Model quality still determines reasoning quality; these controls make
execution and its evidence more dependable. No cross-model benchmark establishes a
“best agent” claim.

## Choose a provider

Install the distribution with `pip install .` from the repository. The existing
`swarmmojo` launcher retains its spelling for compatibility. For any server implementing
OpenAI-compatible chat completions, configure its `/v1` endpoint and exact model ID:

```sh
export SWARMOJO_MODEL_URL=http://127.0.0.1:8000/v1
export SWARMOJO_MODEL_ID=your-model-id
export SWARMOJO_MODEL_API_KEY=local
export SWARMOJO_MAX_CALL_COST_USD=0
swarmmojo meta run --team fullstack_team --task 'Review the proposed module design' --json
```

Zero cost is appropriate for a free local endpoint. For a paid provider, set a conservative
maximum cost per request based on your provider's prices and output limit. Swarmojo
reserves and charges this configured bound; it does not discover pricing or control the
provider's billing. Remote providers receive the prompts and context you send them.
Keep real API keys in the operator's environment, outside project files.

Premade agents use the configured `default` profile. Missing profiles, unavailable
providers, and malformed responses produce errors rather than simulated success.
Explicit offline demonstration:

```sh
swarmmojo meta run --team fullstack_team --model mock --task 'Plan a small parser' --json
```

Mock results carry `simulated: true`. A team's output is a proposal, not proof that code
was changed or tests passed. Structured `tool_calls` and parsed JSON actions are returned
for integration; reasoning turns do not automatically execute them.

Use the Python API to mix models across specialists or connect other protocols:

```python
from app.meta.harness import MetaHarness
from app.meta.models import ModelConfig

harness = MetaHarness(workspace_root=".")
harness.model_registry.register("my-provider", ModelConfig(
    model_id="any-model", backend="my-protocol", max_call_cost_usd=0,
    max_tokens=2048, timeout_seconds=30,
))

def adapter(config, messages, tools):
    # Call your provider's SDK here, honoring config's limits and deadline.
    # Normalize its response; never manufacture a successful result after failure.
    response = my_provider.complete(model=config.model_id, messages=messages,
                                   max_tokens=config.max_tokens,
                                   timeout=config.timeout_seconds)
    return {"content": response.text, "usage": {"total_tokens": response.total_tokens}}

harness.model_client.register_adapter("my-protocol", adapter)
report = harness.run_task("Review a design", model_overrides={"all": "my-provider"})
```

The adapter example assumes your own `my_provider` SDK client. Adapters are trusted
operator code and must enforce their SDK's timeout. `model_overrides` also accepts agent
IDs; an explicit override takes precedence over saved inline model settings. Provider
profiles can declare `supports_tools=False`. Protocol compatibility does not guarantee
that every model supports tools, vision, or other features.

## Review and execute an exact action

The model-facing coding mutations and deduplicated commands share `ExecutionEnvironment`.
They return a pending request before changing files or starting a command. For example:

```python
from app.meta.environment import ExecutionEnvironment
from app.meta.manifest import EnvironmentConfig

env = ExecutionEnvironment(EnvironmentConfig(id="work", name="Work", root_path="."))
proposal = env.write_file("example.txt", "review these exact bytes\n")
print(proposal["request_id"], proposal["fingerprint"])
```

Inspect the complete action, target preimage, workspace, scope, and expiration locally:

```sh
python -m app.meta.control --workspace . inspect REQUEST_ID
python -m app.meta.control --workspace . approve REQUEST_ID --fingerprint REVIEWED_FINGERPRINT
```

Then retry the identical action with `request_id=REQUEST_ID`. MCP clients can call
`meta_execute_approved` for their request. MCP has no tool that grants approval. MCP-created agent/environment definitions are
session-local; use the operator CLI to persist definitions.
Approval expires after 15 minutes, binds exact action bytes and observed file hashes,
and cannot be reused for another scope or edited target. A completed retry returns the
original receipt without repeating the effect; that receipt describes the historical
operation, not the file's current contents.

Commands use argv, not implicit shell interpretation. On Linux they require bubblewrap
and usable user namespaces: a writable `/workspace`, read-only runtime mounts, temporary
home, no network, and no inherited credentials. Use paths relative to the workspace.
Missing sandbox support fails closed. Windows/macOS currently support approved file
operations, but this command boundary has no sandbox backend there. Legacy desktop
MCP actions remain preview-only until an operator-controlled adapter is configured.

The Python engine APIs and operator CLI are trusted interfaces, not a sandbox for
arbitrary Python code. Run the MCP server from the intended workspace. Other legacy
Swarmojo engines retain their own APIs; this is not a claim that every repository
integration uses the meta execution boundary.

## Durable state, budgets, memory, and retries

Control state defaults to `~/.local/state/swarmojo/control/<workspace-hash>/`.
`SWARMOJO_CONTROL_DIR` can select another operator-owned directory outside the workspace.
The approval CLI and runtime must use the same directory and workspace. Keep it private:
receipts contain action inputs and outputs. SQLite transactions coordinate separate
processes. Back up the control directory while the runtime is stopped.

Governance starts empty; demo organization data requires `demo=True`. Tasks, dependency
transitions, approval records, spend, and reservations survive restarts. Inference reserves
per-agent tokens and configured worst-case cost before contacting the provider. Pending
reservations count against caps. Errors conservatively consume the reservation; a crash
leaves it held. Inspect and reconcile unresolved reservations as the operator rather
than silently freeing them. Python configuration and inspection:

```python
from app.engines.governance import HarnessGovernanceEngine

gov = HarnessGovernanceEngine(".")
gov.update_settings({"cost_hard_cap_usd": 10})
print(gov.get_budget_summary())  # Includes unresolved reservation IDs.
# After determining a crashed request's actual usage:
# gov.settle(request_id, tokens=observed_tokens, cost_usd=observed_cost)
```

Each agent has a run ID and memory scope. Resume with the same run ID to recover memory;
a different run gets separate memory. Only successful execution receipts in the same
scope can enter verified memory through `agent.remember_receipt(receipt_id)`. Construct
that agent's environment with `scope=agent.scope`. Model prose, mock reviews, and
unverified notes do not become facts automatically. Receipts certify recorded operations,
not the truth of arbitrary text inside a file or command output.

`DeduplicatedExecutionCache` persists requests across instances and restarts. Supply
`input_paths=["source.py", ...]` when command results depend on workspace files; their
hashes bind the approval and invalidate reuse after changes. Without declared inputs,
a cached command result remains a historical receipt. Cache expiry or `force_refresh`
creates a new request requiring new approval. Request IDs provide at-most-once dispatch,
not an exactly-once external side-effect guarantee. Interrupted in-flight requests are
`uncertain` and never automatically dispatched again. Inspect their effects before
creating another request.

`ParallelToolDispatcher` runs trusted operator callables in separate processes, using
POSIX process groups or Windows kill-on-close jobs. Timeout, cancellation, and completion
reap owned workers and children. Callables cannot mutate parent-process Python objects;
return results explicitly. Model-generated code belongs in the confined command boundary,
not in a deserialized callable.

## Verification

```sh
python -m pytest tests/test_meta_runtime_safety.py tests/test_meta_harness.py -q
# Linux host with bubblewrap/user namespaces; fail if sandbox acceptance cannot run:
SWARMOJO_REQUIRE_SANDBOX=1 python -m pytest tests/test_meta_runtime_safety.py -q
```

Coverage includes concurrent reservations and request replay, restart recovery, stale
approvals, scoped evidence, real process-tree termination, sandbox containment, two
provider adapters, and a local HTTP protocol fixture. The provider tests establish
integration behavior, not live-model coding quality or compatibility with every service.
