# Swarmojo architecture

By [Buzburg AI](mailto:buzburgai@gmail.com).

Swarmojo combines a local project desktop with reusable agent, memory, retrieval,
and governance components. This page retains its historical URL for existing links.

## Desktop flow

1. The user creates a project, chooses specialist roles, and configures a model.
2. A conversation gathers the selected project context. Team mode gathers specialist
   responses before the coordinator produces its response.
3. Proposed changes are staged in the approval store. Model generation never executes them.
4. The user reviews an exact file or command proposal. The runtime checks permissions,
   fingerprints, freshness, and the execution boundary before applying an approved action.
5. Replies, activity, and receipts remain available for inspection and recovery.

## Core components

| Component | Responsibility |
| --- | --- |
| Local desktop | Project navigation, team configuration, chat, tasks, references, settings |
| Specialist runtime | Role manifests, model selection, project guidance, bounded history |
| Governance | Agent records, task transitions, token/cost reservations, budget limits |
| Approval store | Durable proposals, reviewed fingerprints, freshness checks, execution receipts |
| ROMS | Knowledge retrieval, memory, and context interfaces |
| Native Mojo modules | Optional kernels and advanced native runtime components |

Portable project templates copy configuration into a new project. Browser refreshes
restore local drafts and navigation. Server recovery identifies interrupted turns
without replaying generation or execution.

Selected model providers receive user messages and included context. Public-page
reading explicitly contacts the requested site. The desktop server binds to loopback;
it is not a multi-user hosted service. Native benchmarks and individual component
checks should not be interpreted as end-to-end model latency or correctness guarantees.

For setup and exact limits, see [the desktop guide](desktop-features.md),
[agent runtime](meta-runtime.md), and [harness interface](HARNESS.md).
