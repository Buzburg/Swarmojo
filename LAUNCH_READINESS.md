# Launch readiness — Swarmojo

Reviewed October 17, 2026. Visibility has not been changed by this review.

**Recommendation: Already public.**

84 focused desktop/engine tests and the no-install demo passed locally. Existing current-commit hosted checks cover the broader portable harness.

## Scope and limits

No real external model/API session or full native optional stack was revalidated in this review.

## Evidence

Baseline reviewed: `9b1b05362148c1e36d8e0bc34911e698d63dcbb9`. Documentation and focused corrections may follow this baseline; check CI on the final commit before releasing.

Local checks used Linux x86-64, Python 3.12.14, Node 26.8.1, the installed Rust toolchain, and Mojo 1.1.0 where relevant. Native/Python/HTTP coverage is distinguished; a passing subset is not a full product certification.

- `desktop`: PASS — 84 passed in 2.72s.
- `demo`: PASS.
- Baseline hosted workflow [Offline release checks](https://github.com/Buzburg/Swarmojo/actions/runs/38308678029): success.
- Baseline hosted workflow [pages build and deployment](https://github.com/Buzburg/Swarmojo/actions/runs/38308677816): success.

Detailed command logs and setup diagnostics are retained in the private local launch-review workspace.

## MCP and specialist update — October 18, 2026

This update adds MCP capability restrictions, request limits, explicit plugin opt-in,
reviewed workflow-proof execution, encrypted assistant credentials, and the expanded
project specialist catalogue. It also publishes the project On/Off and Team/Isolated
controls. See [MCP access controls](docs/mcp-security.md) for upgrade behavior.

Validated locally with Python 3.12.14, FastMCP 4.1.1, and rebuilt Mojo 1.1.0 broker and
sandbox binaries:

- Full pytest suite: **1,511 passed, 83 skipped, 145 subtests passed**.
- Minimum supported FastMCP 4.1.0: **62 focused checks passed**.
- Browser acceptance: role selection and renaming, participation modes, separate
  conversations/drafts, team filtering, refresh persistence, and 1440/390/319-pixel
  layouts passed with a fixture provider and no JavaScript errors.
- Built wheel installed successfully; installed launchers and new modules worked
  outside the source tree. Dependency consistency, no-install demonstration, preview
  synchronization, JavaScript syntax, and PathCarry checks passed.

Skipped tests and fixture model responses do not establish live model quality,
external-provider compatibility, or certification of every optional native feature.
No payment or financial transaction was executed. Check the hosted workflow on the
commit containing this update for the corresponding Linux/Windows CI results.
