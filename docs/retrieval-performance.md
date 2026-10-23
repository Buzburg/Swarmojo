# Retrieval correctness and performance

The ROMS 1.4 integration replaces the previous retrieval implementations. Python,
MCP, and the Mojo entry point use one local search path with native typo expansion
and rank fusion, source identifiers, document/type/topic filters, and database
freshness checks. Query vectors and persistent cache records require 768 finite
float32 values; cache identity includes the pinned model revision. Invalid cache
records are recomputed. The old remote-embedding and MiniLM paths are removed.

Tests exercise literal identifiers and Unicode, typo matches, duplicate chunks,
filtered vector candidates, local and external database writes, rollback, invalid
vectors, revision changes, and compiled Mojo/Python parity. Native import must also
preserve the interpreter environment used by subprocesses.

No end-to-end speed improvement is claimed from the older synthetic fusion
measurements. See [ROMS setup](roms-integration.md) for runtime and reindexing
requirements. Selected evidence still requires review; retrieval does not verify
source claims or grant action permissions.
