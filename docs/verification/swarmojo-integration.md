# Swarmojo integration verification

Local verification on October 22, 2026, from base `83c66c454d376b2f98d248bc3fd1cd9e0b6e163d` with the integration
changes in this commit. Python 3.12.14, CPU model runtime, Mojo 1.1.0 (8189361e),
headless Chromium 1234. Raw evidence is stored outside the shipped repository in
`~/.codex/benchmarks/swarmojo-upgrade/`.

## Changes checked

- ROMS 1.4 knowledge stack, with source hashes and local adaptations recorded in
  `config/roms-upstream.json`; Swarmojo project and approval behavior retained.
- Portable task briefs from explicitly selected, current project references.
- Pinned standalone Row Witness and Path Carry downloads with source licenses.
- Removed unused MiniLM loading/cache, duplicate MCP search tools, and separate
  Mojo retrieval implementation. Mojo now delegates to the shared retrieval path.
- Native import restores the interpreter environment used by child processes.

## Results

| Check | Result | Evidence |
| --- | --- | --- |
| Full `python -m pytest -q`, real native search and broker binaries, cached model, offline | 1,686 passed; 81 skipped; 145 subtests passed | `full-3.log` |
| Final desktop, release, integration, engines and Swarmojo tests after browser fix | 104 passed | `final-desktop.log` |
| Final native loader, MCP policy, task skill and desktop release tests | 85 passed | `final-boundaries.log` |
| Portable workflow commands in clean source snapshot and base-only environment, no native search module or ML dependencies | 920 passed; 14 skipped across five batches; both first-run demos passed | `portable.log`, `portable-commands.json` |
| Real cached Q8 CPU inference, normalized vectors, three semantic rankings, Unicode splitting, ingestion/idempotence and hybrid/vector search | Passed | `real-embedding.log` |
| Compile native search extension and MCP executable | Passed | `build-search.log`, `mojo-mcp-build.log` |
| Real compiled MCP protocol: search, memory, tickets, context limits, resources/prompts and rejected invalid input | Passed | `mojo-protocol-3.log` |
| Browser: select ROMS reference, preview/download brief, invalidate edited preview, download both tools, mobile layout | Passed | `browser-3.log`, screenshots |
| Downloaded HTML tools: sample CSV comparison and JSON export; filename issue detection; zero HTTP requests | Passed | `browser-result.json`, `csv-report.json` |
| Wheel installation and desktop/utility/CLI checks outside checkout without ML packages | Passed | `package-acceptance.log` |
| Row Witness locked dependency build and upstream tests | 56 passed, typecheck/build passed | Upstream checkout logs |
| Path Carry locked dependency build and upstream tests | 69 passed, typecheck/build passed | Upstream checkout logs |
| Dependency manifests and regenerated uv/Pixi lockfiles | Parsed; uv freshness check passed; retired embedding/CUDA dependencies removed | `uv-lock.log`, `pixi-lock.log` |
| PathCarry audit and `git diff --check` | No errors or warnings | Local final audit |

The full suite preceded the final sidebar wiring and native bridge registration
changes; the affected desktop, native loader, MCP and protocol checks were rerun
after those changes. Earlier failed attempts remain in the evidence directory.
Fixture updates use the new embedding dimension, model revision cache namespace,
and source registry contract; they do not enable the retired backend.

## Limits

This is local Linux verification. New GitHub Actions coverage is configured but
has not run remotely. Windows and other optional/hardware integrations represented
by skipped tests are not certified. Task-authoring contracts were tested; no new
live generation-model quality benchmark or performance improvement is claimed.
The portable wheel intentionally excludes platform-specific native binaries.
Full knowledge indexing requires the documented source build and model setup.
