# Swarmojo ⚡

**Will your AI agents burn your budget while overwriting each other's code?**

Agent A refactors an authentication module. Agent B runs a failing test and reverts the file. Agent C attempts a patch, triggers a cyclic linter error, and spawns three subagents. Within four minutes, they have burned $45 in API credits, locked the git working tree, and produced zero working code.

Swarmojo governs that interaction **before your agents break production**. Run sovereign, local-first multi-agent teams with strict organizational reporting, hard budget circuit-breakers, microsecond Git rollbacks, and Paperclip-grade human approval gates — directly on your own silicon.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Runtime: Python + Mojo](https://img.shields.io/badge/Runtime-Python_3.11+_|_Mojo_SIMD_v25+-orange.svg)](app_mojo/)
[![Governance: Paperclip--Grade](https://img.shields.io/badge/Governance-Paperclip--Grade-gold.svg)](docs/meta_agent_comparison.md)
[![Privacy: 100% Offline](https://img.shields.io/badge/Privacy-100%25_Offline_|_Zero_Cloud-emerald.svg)](#no-account-no-cloud-zero-telemetry)
[![Tests: Passing](https://img.shields.io/badge/Tests-100%25_Passing-brightgreen.svg)](tests/)
[![Sister Project: TriggerTangle](https://img.shields.io/badge/Sister_Project-TriggerTangle-purple.svg)](https://github.com/Buzburg/trigger-tangle)

![Swarmojo HUD — Sovereign Operations Console and Governance Flight Deck](docs/screenshot.png)

---

## Try it in 5 seconds

**[Open the Live Interactive HUD](https://buzburg.github.io/Swarmojo/)** (or run [docs/index.html](docs/index.html) locally) — no installation, account, or API key. The flight deck runs offline in your desktop Chromium or Firefox browser.

Prefer the CLI?

1. **Clone and test immediately**:
   ```sh
   git clone https://github.com/Buzburg/Swarmojo.git
   cd Swarmojo
   python scripts/demo_first_run.py
   ```
2. **Rehearse an agent task with automated dependency blockers**:
   ```sh
   python roms.py gov tasks
   ```
3. **Inspect the live corporate hierarchy and active spend**:
   ```sh
   python roms.py gov org
   ```
4. **Trigger a human-governed approval gate before dangerous actions**:
   ```sh
   python roms.py gov approvals
   ```
5. **Enforce hard budget caps and kill runaway recursive loops**:
   ```sh
   python roms.py gov budget
   ```

### No account, no cloud, zero telemetry.
Swarmojo runs on your machine and can use entirely local models. If you configure a remote provider, prompts and selected context are sent to that provider. No specific model family or operating-system build is required.

**This is an explicit deterministic governance harness, not an opaque cloud wrapper.** You declare agent roles, budget ceilings, and rollback invariants. Swarmojo enforces them with mathematical rigor.

> [!NOTE]
> ### Harness vs. HUD: The Architecture
> - **Swarmojo (The Harness)**: The headless multi-agent engine running on your silicon. It manages agent lifecycles, runs AST call-graphs, enforces hard budget caps, and triggers microsecond git rollbacks.
> - **Swarmojo HUD (The Flight Deck)**: The built-in visual operations console. It is a feature *of* Swarmojo that runs in your browser to visualize real-time telemetry, Paperclip-grade org charts, Kanban task tracking, and human-in-the-loop approvals.

---

## What makes this useful?

- **Hard budgets, not polite prompts.** When an agent hits its spend cap or token ceiling, the harness physically halts execution with an automated circuit breaker. It doesn't ask the LLM nicely to stop.
- **Microsecond Git rollbacks (`GitGuard`).** `GitGuard` captures content-addressed delta snapshots before every file modification. If an agent fails a syntax check or breaks a unit test, your working tree auto-heals and reverts in under 5 milliseconds.
- **Fleet herd immunity (`HerdImmunityRegistry`).** When any agent solves an environmental bug (e.g. POSIX `fcntl` on Windows, SQLite locks, API rate limits), it signs an immunity hash into fleet memory. Other agents never repeat the same failure.
- **Explicit corporate reporting.** Agents operate under a defined organizational hierarchy (Executive &rarr; Lead &rarr; Specialist &rarr; Auditor). Subagents cannot hire other subagents without an assigned budget and explicit manager authorization.
- **Zero-bypass human approval.** High-stakes operations — pushing to `main`, executing destructive commands (`rm -rf`, `DROP TABLE`), or leasing remote GPU clusters — block immediately in an interactive authorization queue.
- **Sub-microsecond Mojo acceleration.** Core bottleneck operations (symbol call-graphs, token clamping, step hashing, PhaseGate vector routing) run through native Mojo SIMD kernels in `<50 µs`, not sluggish Python loops.

---

## How It Works: Causal Governance Architecture

```mermaid
graph TD
    User([User Prompt / High-Level Goal]) --> Exec[Executive Agent]
    Exec --> Gov[Swarm Governance Engine]
    Gov --> BudgetCheck{Budget & Cap OK?}
    BudgetCheck -- Exceeded --> CircuitHalt[⚡ Automated Circuit Breaker Halt]
    BudgetCheck -- Approved --> Lead[Lead Specialist Agent]
    Lead --> DepCheck{Task Dependencies Clear?}
    DepCheck -- Blocked --> BlockHalt[⏳ Suspended on Predecessor Task]
    DepCheck -- Ready --> GitSnap[🛡️ GitGuard Micro-Snapshot <1ms]
    GitSnap --> Action[Execute Tool Step / Code Edit]
    Action --> Verify{Tests & Invariants Pass?}
    Verify -- Failed --> Rollback[⏪ GitGuard Auto-Rollback <5ms]
    Rollback --> Immunity[🧠 Herd Immunity Broadcasts Remedy]
    Verify -- Passed --> ApprovalCheck{Requires Human Gate?}
    ApprovalCheck -- Yes --> Queue[🔒 Human-in-the-Loop Queue]
    ApprovalCheck -- No --> Merkle[📜 ProofGraph SHA-256 Commit]
```

---

## Swarmojo ⚡ HUD — Sovereign Operations Console

Styled in the official **Buzburg** brand palette (Honey Gold `#E5A823`, Dark Hive Charcoal `#13110E`, and Crisp Ivory `#FAF8F5`), the **Swarmojo HUD** provides an interactive Paperclip-grade organizational control plane:

| ⚡ 1. Live Operations & Microsecond Telemetry | 🏢 2. Swarm Organizational Hierarchy |
| :---: | :---: |
| [![Telemetry](assets/screenshots/swarmojo_hud_telemetry.png)](assets/screenshots/swarmojo_hud_telemetry.png) | [![Org Chart](assets/screenshots/swarmojo_hud_orgchart.png)](assets/screenshots/swarmojo_hud_orgchart.png) |
| *Sub-microsecond Mojo SIMD kernels, SymNexus AST search (<20µs), and StateEpoch OCC leases.* | *Corporate org chart treating agents as company employees with explicit reporting lines & spend counters.* |

| 📋 3. Goals & Issues Kanban | 💰 4. Budgets & Spend Governance |
| :---: | :---: |
| [![Tasks Kanban](assets/screenshots/swarmojo_hud_tasks.png)](assets/screenshots/swarmojo_hud_tasks.png) | [![Budgets](assets/screenshots/swarmojo_hud_budgets.png)](assets/screenshots/swarmojo_hud_budgets.png) |
| *Autonomous task delegation with priority tags and automated dependency blockers (`TASK-106` blocked by `TASK-102`).* | *Hard spend caps, token consumption tracking, and automated circuit breakers to kill runaway loops.* |

| 🛡️ 5. Human-in-the-Loop Governance | ⚙️ 6. Harness Scheduler & Connectors |
| :---: | :---: |
| [![Approvals](assets/screenshots/swarmojo_hud_governance.png)](assets/screenshots/swarmojo_hud_governance.png) | [![Settings](assets/screenshots/swarmojo_hud_settings.png)](assets/screenshots/swarmojo_hud_settings.png) |
| *Zero-bypass authorization queue for git pushes to main and cloud GPU bursts with one-click approve/reject.* | *Pulse heartbeats, 30s/60s scheduler, and BYOA connectors for Claude Code, OpenCode, Codex, and Ollama.* |

---

## Use it in an Agent or Build Workflow

Swarmojo includes a rich CLI suite callable directly or via Model Context Protocol (FastMCP):

```sh
# 1. Organization & Hierarchy: View agent seats, managers, and spend
python roms.py gov org

# 2. Budgets & Token Caps: View financial guardrails and circuit breaker limits
python roms.py gov budget

# 3. Tasks & Blockers: Inspect active agent assignments and dependency graphs
python roms.py gov tasks

# 4. Human-in-the-Loop Approvals: Authorize or reject pending high-risk actions
python roms.py gov approvals

# 5. Heartbeat Engine: Pulse active agents and advance pending work
python roms.py gov heartbeat
```

### FastMCP Tool Integration

Every engine and governance function is exposed as a standardized FastMCP tool for your agent:

```python
from app.engine_tools import gov_org_chart, gov_budgets, gov_tasks, gov_request_approval

# Check organizational hierarchy before delegating
org_info = gov_org_chart()

# Queue a high-risk operation for human sign-off
approval = gov_request_approval(
    agent_id="agent-coding-lead",
    action="git_push",
    details="Pushing commit dd456f3 to origin/main",
    urgency="high"
)
```

---

## The Six Specialist Agent Guilds

1. **Supercharged Coding Agent (`PiCodingToolkit`)**: Multi-perspective AST review, ELF/PE/Mach-O binary header parsing, hierarchical symbol codemaps, sub-millisecond workspace regex grep, and exact substring editing with pre-mutation rewind snapshots.
2. **High-Craft Design Agent (`DesignAgentEngine`)**: Visual canvas composition, optical liquid glassmorphism tokens, backdrop blur CSS, and WCAG AAA contrast enforcement ($\ge 7:1$).
3. **Multimodal Studio Agent (`StudioAgentEngine`)**: Directorial scene planning, multi-track timeline layout with `-14 LUFS` broadcast loudness normalization, visual quality scoring, and Flux/SDXL diffusion graph generation.
4. **Authentic Prose Writer Agent (`WriterAgentEngine`)**: Ghost Protocol anti-slop engine stripping 200+ statistical AI clichés (`delve into`, `rich tapestry`, `testament to`), sentence cadence variance auditing, and multi-chapter book DAG planning.
5. **Constitutional Workflow Agent (`WorkflowPipeline`)**: 8-stage constitutional DAG pipelines, automatic risk classification, destructive command blocking, and cryptographic SHA-256 Merkle proofs.
6. **Sovereign Personal Assistant Agent (`PersonalAssistantEngine`)**: Persistent local desk context, SHA-256 encrypted personal credentials vault, specialist consult gateway, and 16kHz PCM real-time voice bridge with barge-in interruption.

---

## Sovereign Engines Directory

| Engine | Primary Capability & Performance Metric | CLI Command | FastMCP Tool |
| :--- | :--- | :--- | :--- |
| **Governance** | Paperclip-grade org chart, budgets, tasks Kanban & approvals | `python roms.py gov org` | `gov_org_chart` |
| **SymNexus** | In-memory bidirectional symbol call-graph index (<20 µs) | `python roms.py symnexus` | `symnexus_query` |
| **TitanDelta** | Test-Time Neural Associative Memory with surprise gating | `python roms.py titandelta` | `titandelta_memory_update` |
| **GitGuard** | Sub-millisecond git micro-checkpoints with auto-rollback | `python roms.py git-guard` | `rewind_snapshot_workspace` |
| **HerdImmunity** | Swarm herd immunity memory broadcasting instant bug remedies | `python roms.py meta immunity` | `meta_immunity_check` |
| **DedupCache** | Durable command receipts with scoped, approval-gated retries | `python roms.py meta dedup` | `meta_dedup_run` |
| **PhaseGate** | 256-dim phase vector System-1 tool triage router (<50 µs) | `python roms.py phasegate` | `phasegate_triage_tools` |
| **Mojo-Drift** | 256-dim angular trajectory tracking (warn $\ge 65^\circ$, block $\ge 80^\circ$) | `python roms.py drift` | `drift_evaluate_action` |
| **Sieve** | Streaming compiler & terminal log compaction (95%+ noise reduction) | `python roms.py sieve` | `sieve_compact_logs` |
| **StateEpoch** | Optimistic concurrency control (OCC), version leases & CAS commits | `python roms.py state-epoch` | `state_epoch_check` |
| **ProofGraph** | Step SHA-256 Merkle fingerprinting & cryptographic transition caching | `python roms.py proofgraph` | `proofgraph_verify_step` |
| **DeltaRewind** | Content-addressed workspace snapshotting & microsecond delta rollback | `python roms.py rewind` | `delta_rewind_rollback` |
| **TaskHorizon** | State-machine task DAG graph & anti-loop circuit breaker | `python roms.py horizon` | `task_horizon_record` |
| **ToolMender** | JSON auto-repair, balance extraction & schema coercion | `python roms.py toolmender` | `toolmender_repair_output` |

---

## Model-agnostic agent runtime

Coding, research, review, and coordination agents use operator-selected model profiles.
Use an OpenAI-compatible local or remote endpoint, or register a provider adapter for
another protocol. Premade agents use `default`; mock output requires explicit selection.

The meta runtime includes persistent approvals and budgets, workspace-confined commands,
killable worker processes, receipt-backed memory scoped to each agent/run, and durable
request replay. Read the [runtime setup and approval guide](docs/meta-runtime.md) for
configuration, executable examples, and platform limits.

## The Buzburg Tangle Suite

Swarmojo is part of the **Buzburg Tangle Ecosystem** of sovereign, local-first developer tools:

- 🪢 **[TriggerTangle](https://github.com/Buzburg/trigger-tangle)**: Rehearse how separate *automations* trigger each other. Offline design simulator, causal loop witnesses, and CLI.
- 🐝 **[Swarmojo](https://github.com/Buzburg/Swarmojo)**: Govern how separate *AI agents* trigger and conflict with each other. Offline multi-agent harness, budget circuit breakers, microsecond rollbacks, and HUD.

---

## License & Authors

Licensed under the [Apache-2.0 License](LICENSE). Built with craft by **[Buzburg AI](mailto:buzburgai@gmail.com)**.

See the [Meta-Agent Architecture Comparison: Swarmojo vs Conventional Frameworks](docs/meta_agent_comparison.md) for the component comparison.

PolyHarness is an optional, separately obtained integration. If you have access, place its checkout in `polyharness/` or set `SWARMOJO_POLYHARNESS_ROOT` to its directory. It is not included in the public repository or Python distribution.
