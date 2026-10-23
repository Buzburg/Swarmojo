# ROMS in Swarmojo

Swarmojo incorporates the ROMS 1.4 knowledge layer at the revision recorded in
`config/roms-upstream.json`. Its project runtime, approval ledger, specialist roles,
and desktop remain Swarmojo components. There is one active embedding backend and
one MCP knowledge search entry point. Retired model loading and duplicate research
searches have been removed.

## Desktop and offline tools

The regular installation remains sufficient for the desktop. Memory searches an
existing local index without starting a model. Select references, choose **Export
selected task brief**, enter the task and constraints, and preview before downloading.
The export checks that the selected excerpts still match the index. Re-select older
references that lack a chunk identifier. A brief carries evidence, not permission to
execute commands or an automatically activated skill.

**Local utilities** downloads the CSV comparer from Row Witness or the folder/ZIP
filename checker from Path Carry. Save and open the HTML file locally. Both work
offline; neither sends selected files to the agent or changes those files. Runtime
files, pinned revisions, hashes, and licenses are in `app/desktop_assets/utilities/`.
No Node runtime, npm dependencies, or upstream source tree is included.

## Full knowledge runtime (source checkout)

Use Python 3.12 and a Mojo compiler compatible with the checked-in native sources
(verified with Mojo 1.1.0). Run from the repository root in your virtual environment:

```sh
python -m pip install 'torch>=2.5' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e '.[ml]'
python scripts/build_search_native.py --mojo /path/to/mojo
python scripts/fetch_embedding.py
python -m app.source_library menu
python swarmmojo.py knowledge
```

The embedding download needs network access once; retrieval then runs locally on
CPU. The native extension is built for this source checkout and platform. The
portable wheel does not include a machine-specific binary. PDF, Office, structured
text, and image intake use the new parsing layer; image OCR additionally needs the
local `tesseract` executable. The knowledge browser runs separately from the desktop.

The new index defaults to `data/embeddinggemma-q8.db`. The old 384-dimensional index
cannot supply vectors for the new 768-dimensional runtime. Re-import your original
sources into the new index. Point `ROMS_DB_PATH` at an existing updated ROMS index if
you already have one. Old model/provider overrides must be removed. No legacy
backend or index conversion shortcut is retained; original user documents and
existing databases are not deleted by this upgrade.

## Skills and MCP

`python swarmmojo.py skills --help` exposes source-derived skill management. The knowledge browser offers task-skill authoring workflows. Source evidence
is quoted data, not instructions to the host. Drafts require review; saving a draft
does not activate it or grant tool access. Bounded authoring can use an explicitly
configured OpenAI-compatible model endpoint. More relevant indexed evidence can
improve grounding, but does not guarantee a correct skill.

MCP keeps the Swarmojo profiles and approval rules. `search_knowledge_base` now
supports document, type, and topic filters. The former duplicate `zg_search` and `search_by_topic` tools
have been removed. Read-only profiles block intake, saving, and deletion. Evidence preparation and
unsaved drafting remain available; see [MCP access controls](mcp-security.md) before enabling local writes.
