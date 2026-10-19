# MCP access and security controls

Swarmojo's desktop and MCP server are separate interfaces. Desktop projects retain
per-agent On/Off and Team/Isolated settings and human-reviewed file/command proposals.
The MCP controls below apply to tool calls through the Python server and the shared
Mojo bridge. They do not restrict direct Python imports or privileged CLI use.

## Start with read-only access

`python swarmmojo.py mcp` starts a local stdio server, with `read_only` as its default
MCP profile. Only explicitly reviewed lookup and text-analysis tools can run. Tools
that write records, dispatch models, invoke external providers, or run arbitrary commands are
blocked before their function executes. Tools remain discoverable so clients can show
their schemas; visibility is not permission. Read operations may initialize local
indexes or caches and use local inspection utilities. Startup ingestion still follows the configured embedding provider.

A trusted local operator can enable the broader tool set before launching:

```sh
SWARMOJO_MCP_PROFILE=local python swarmmojo.py mcp
```

The `local` profile allows normal mutations and configured provider calls. Existing
exact-action approvals still apply to coding writes, command proposals and workflow
proof commands. An agent cannot approve those requests through MCP: review them with
the local control CLI. Destructive memory deletion and workspace rewind tools require
the additional operator setting `SWARMOJO_MCP_ALLOW_DESTRUCTIVE=1`. That setting is a
session capability grant, not per-call human approval; enable it only for trusted
clients when those operations are intended. Profiles cannot be changed by a tool call.

Do not expose this stdio server as an unauthenticated public HTTP service. These
controls are not user authentication, tenant separation, or an OS sandbox for all
Python tools. Resource/prompt reads are outside the tool-call profile and limits.
An MCP client can read local information within the server account's permissions;
use a dedicated OS account/workspace when stronger separation is required.

## Request limits

Tool dispatch has a rolling limit of 60 attempts per minute and four concurrent calls
per server process. Rejected attempts count toward the rate limit. Limits reject calls
without queuing or automatic retry. Configure `SWARMOJO_MCP_CALLS_PER_MINUTE` (1–600)
and `SWARMOJO_MCP_MAX_CONCURRENT` (1–16) at startup. Invalid configuration fails startup.
These limits are process-local; they are not distributed quotas or a cost estimate.

## Custom Python tools

No custom plugin executes automatically by default. Review plugin source and enable
specific module names, without `.py`, in a trusted local session:

```sh
SWARMOJO_MCP_PROFILE=local SWARMOJO_MCP_PLUGINS=code_search python swarmmojo.py mcp
```

The loader rejects path traversal and symlinked plugins. Changes to a permitted plugin
are not imported until restart unless `SWARMOJO_MCP_HOT_RELOAD=1` is also set. Hot reload
still honors the same allowlist. Permitted Python plugins have host-code privileges;
this is explicit trust, not a plugin sandbox or a defense against a malicious local
process replacing reviewed source. Bundled example tools are optional plugins too.

## Credential storage

New assistant-vault values use authenticated Fernet encryption. The private key is
stored in Swarmojo's control directory outside the project workspace, so ordinary
project snapshots do not include it. On POSIX, keys and vault files are owner-only.
Windows users must also protect the control directory with their account's ACLs.

Legacy base64 records are migrated together on first vault access. Corrupt records,
modified ciphertext, symlinks and missing keys fail without overwriting the vault.
Migration does not erase older backups or filesystem history. Back up the control key
privately with the encrypted vault; losing it makes the encrypted values unreadable.
Control storage is keyed by the workspace path. Moving a workspace also requires
restoring its key to the control directory for the new path; do not discard the old key.
This does not protect against a process that already runs as the same OS user.

## Tool metadata and external catalogues

All built-in MCP registrations include read-only, destructive, idempotence and
open-world hints. Hints are conservative capability descriptions, not authorization.
For example, memory updates are mutations even if their names sound like queries;
workflow-proof tools can propose command execution and are not read-only lookups.

The optional `calculate_refund_amount` example only subtracts a return-shipping fee
from an amount and formats the result. It has no payment integration, network call,
account access, or state change, and cannot issue a refund. Negative and non-finite
inputs are rejected. Its MCP description and hints state that explicitly.

The [PolicyLayer record](https://policylayer.com/tools/swarmojo) was checked on October
18, 2026. Its classification of that calculator as money-moving does not match the
implementation. The page also states identity is unverified and authentication has
not been probed. Publishing these fixes does not update or certify that third-party
record. Swarmojo retains consequential capabilities that need operator control;
a regression pass is not a guarantee against every vulnerability.
