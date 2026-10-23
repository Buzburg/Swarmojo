# Buzburg repository integration review

Reviewed all 45 repositories listed by the Buzburg account on October 22, 2026.
The portfolio pass inspected repository descriptions and README scope/limitations.
Selected components received source/build/test inspection; this is not a full code audit of every repository.

| Repository | Disposition |
| --- | --- |
| [ROMS](https://github.com/Buzburg/ROMS) | Updated knowledge stack to pinned v1.4.0; preserve Swarmojo orchestration and policy. |
| [row-witness](https://github.com/Buzburg/row-witness) | Added pinned offline CSV comparer; supports column mapping, duplicate conflicts and report export. |
| [agent-rewind](https://github.com/Buzburg/agent-rewind) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [cortex](https://github.com/Buzburg/cortex) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [Swarmojo](https://github.com/Buzburg/Swarmojo) | Target repository; preserve current desktop, specialist roles and approval flow. |
| [fastgate](https://github.com/Buzburg/fastgate) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [skillcheck](https://github.com/Buzburg/skillcheck) | Defer Rust toolchain integration; generated skills remain reviewed candidates, not automatically activated. |
| [polyharness](https://github.com/Buzburg/polyharness) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [confidence-lab](https://github.com/Buzburg/confidence-lab) | Specialized forecasting calibration; no current desktop forecast evaluation dataset contract. |
| [changepoint-explorer](https://github.com/Buzburg/changepoint-explorer) | Specialized time-series analysis; useful future analyst tool, outside the general workspace workflow. |
| [workflowproof](https://github.com/Buzburg/workflowproof) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [rebalance-lab](https://github.com/Buzburg/rebalance-lab) | Portfolio simulation needs a dedicated user workflow and assumptions; no automatic financial decisions added. |
| [policy-impact-lab](https://github.com/Buzburg/policy-impact-lab) | Causal analysis needs explicit study design and data; not a general agent safety component. |
| [retryfence](https://github.com/Buzburg/retryfence) | Existing request IDs and approval receipts cover current actions; add a destination-aware adapter only with a concrete external action. |
| [statefresh](https://github.com/Buzburg/statefresh) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [unity-asset-map](https://github.com/Buzburg/unity-asset-map) | Game-asset analysis is useful only for a Unity project; defer until a project-scoped adapter is requested. |
| [envghost](https://github.com/Buzburg/envghost) | Existing credential handling and process-memory API keys remain; avoid introducing a competing secret store. |
| [traceseal](https://github.com/Buzburg/traceseal) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-memory](https://github.com/Buzburg/mojo-memory) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-goose-state](https://github.com/Buzburg/mojo-goose-state) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-agent-rewind](https://github.com/Buzburg/mojo-agent-rewind) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [localdoc-search](https://github.com/Buzburg/localdoc-search) | Keep existing bounded text chunking/keyword helpers; remove its unused MiniLM loader and separate semantic cache. ROMS owns semantic retrieval. |
| [triad-engine](https://github.com/Buzburg/triad-engine) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [ptrm-mojo](https://github.com/Buzburg/ptrm-mojo) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [roms-v1-archive](https://github.com/Buzburg/roms-v1-archive) | Superseded by current ROMS; do not import another knowledge backend. |
| [swarm-mojo](https://github.com/Buzburg/swarm-mojo) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [path-carry](https://github.com/Buzburg/path-carry) | Added current offline folder/ZIP auditor; supplements the existing Python filename checks. |
| [Buzburg](https://github.com/Buzburg/Buzburg) | Profile and brand assets; no runtime capability to integrate. |
| [watch-scheduler](https://github.com/Buzburg/watch-scheduler) | Separate staffing application with its own data model and solver; not an agent task scheduler. |
| [mojo-bitnet](https://github.com/Buzburg/mojo-bitnet) | Experimental inference/planning component; requires separate parity and runtime evaluation before replacing existing behavior. |
| [mojo-drift](https://github.com/Buzburg/mojo-drift) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-deltanet](https://github.com/Buzburg/mojo-deltanet) | Experimental inference/planning component; requires separate parity and runtime evaluation before replacing existing behavior. |
| [mojo-compact-kv](https://github.com/Buzburg/mojo-compact-kv) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-goose-tree](https://github.com/Buzburg/mojo-goose-tree) | Experimental inference/planning component; requires separate parity and runtime evaluation before replacing existing behavior. |
| [mojo-fastgate](https://github.com/Buzburg/mojo-fastgate) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [Github-Gemini](https://github.com/Buzburg/Github-Gemini) | Experimental inference/planning component; requires separate parity and runtime evaluation before replacing existing behavior. |
| [mojo-sieve](https://github.com/Buzburg/mojo-sieve) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-micro-toolcall](https://github.com/Buzburg/mojo-micro-toolcall) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-local-horizon](https://github.com/Buzburg/mojo-local-horizon) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-titans](https://github.com/Buzburg/mojo-titans) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-symdex](https://github.com/Buzburg/mojo-symdex) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [mojo-skillcheck](https://github.com/Buzburg/mojo-skillcheck) | Defer experimental counterpart; lint findings alone cannot certify model-generated instructions. |
| [ptrm-rs](https://github.com/Buzburg/ptrm-rs) | Experimental inference/planning component; requires separate parity and runtime evaluation before replacing existing behavior. |
| [mojond](https://github.com/Buzburg/mojond) | Existing engine, adapter or related implementation already present; retain its current contract rather than import a duplicate. |
| [loop-guard](https://github.com/Buzburg/loop-guard) | Workflow rehearsal already exists through the bundled TriggerTangle harness; avoid a second overlapping simulator. |

## Implemented scope

- Current ROMS indexing, search, source-derived skills, task authoring, saved candidates and portable briefs.
- Desktop export of an explicitly selected project’s current ROMS references, with stale/cross-project selection rejection.
- Pinned Row Witness and Path Carry standalone downloads, with license notices and content hashes.
- Existing Swarmojo names, specialist tools, MCP policy environment variables and explicit execution approvals remain intact.

## Source identity

`config/roms-upstream.json` records the ROMS revision and copied-file hashes.
`app/desktop_assets/utilities/PROVENANCE.json` records upstream commits and built-file hashes.
Utilities are compiled from their locked dependencies and downloaded as attachments.
They are not installed as desktop-origin scripts or automatically granted project access.
