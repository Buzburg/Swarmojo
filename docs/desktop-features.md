# Swarmojo desktop guide

The desktop brings projects, specialist teams, conversations, memory, and reviewed
changes into one local workspace. It uses Swarmojo's existing agent runtime,
governance ledger, approval store, and SQLite persistence.

## Projects and specialists

Create a project first, then add up to 16 specialists from the 21 available roles.
The role picker includes Assistant, Coder, Writer, Designer, Forecaster, Researcher,
Director, Marketer, Mathematician, Renigineer (reverse engineering), Accountant, Trader,
Lawyer, and Adjuster, alongside the existing Studio and technical roles. Names and additional
guidance are editable. Original role prompts, tool lists, skills, and memory policies
remain in use. Each specialist has an **On/Off** switch and a **Team/Isolated** mode.
Per-agent model overrides use the workspace endpoint and key.

- **On + Team:** included when you select **Work with → Team**. Main combines the
  enabled team specialists’ replies into a coordinated answer.
- **On + Isolated:** open that specialist’s isolated workspace for a direct conversation.
  It has its own history, agent memory, files, and approvals; shared project notes,
  tasks, references, and other agents’ work do not enter its context.
- **Off:** blocks new work for that specialist without deleting its configuration or
  history. Queued team members are checked again before their model call. A response
  already underway can finish; switching off is not a cancellation button.

Isolated specialists still receive the project brief and follow its controls and
shared budget. Isolation separates working context and files, not the model provider
or an operating-system security boundary. Switching back to Team never merges isolated
work. Its history and pending approvals remain accessible through **View isolated
history**; new isolated messages require On + Isolated. Specialists with isolated
turns cannot be removed while that history exists; turn them off to retain it.
Participation settings persist across restarts and travel with project templates.

Project tasks support owners, priorities, dependencies, and validated transitions.
The task board records your assessment of progress. Discuss task prepares an editable
chat draft; moving a task does not start a model or certify a deliverable.

## Settings and navigation

Settings is labeled in the top bar, including narrow windows. Ctrl+, / Cmd+, opens
model settings. Ctrl+K / Cmd+K opens quick navigation for projects and sections.
Workspace settings also provides project-template import.

No model is selected by an upgrade. Configure your endpoint, model ID, temperature,
timeout, output-token limit and maximum cost per call. API keys remain in memory for
the server session; they are not written to project templates or the database.

Project Controls sets discussion/file/command permissions, shared-file context,
relative exclusion globs, and a lifetime budget. Restrictions are checked again at
approval time. Costs consume the configured per-call bound, not a provider invoice.
Existing per-agent limits also apply. Activity records runs, task changes, settings,
and approval decisions; execution details remain in Approvals.

## Memory, search, and ROMS

Project notes persist across restarts and enter future project turns. They are context,
not permission to execute actions. Search notes & history searches that project's
notes, messages, and saved references; Main agent history has a separate search.
Search returns up to 40 bounded excerpts and never merges other projects' histories.

ROMS remains included. The Memory section can search an existing local ROMS index
using bounded read-only lexical retrieval. Missing indexes are reported without
creating a database. At most three indexed chunks are returned, with 4,000-character
review excerpts. Adding an excerpt checks its indexed content hash again. Results
are snapshots: original source files are not opened or revalidated.

Only selected sources enter a future project turn: at most four references, each
bounded to 3,000 characters. File context separately includes at most eight files
with bounded excerpts and twelve active task records. Disabling a source or excluding
a file affects future context; it does not erase previously saved chat messages.

## Public-page reader

The Web section fetches a public page only after you submit its URL. Saved text is
excluded from model context until you select Use in project context. You can remove
references and inspect their saved text, source URL, links, and retrieval time.

The reader supports HTML and plain text on public HTTP(S) ports 80/443. DNS answers
and redirect destinations are checked; the connection uses a validated address.
It does not use scripts, cookies, login sessions, or proxy environment variables.
Responses are limited to 1 MB and saved text to 20,000 characters. Compressed responses
and unsupported formats are rejected. A project stores at most 50 references.
Some sites require browser execution or block text readers and will not be readable.

Page content is untrusted reference material. It cannot approve a command or file
change. Opening a link separately in your browser follows that browser's own policies.

## Portable configurations

Project Memory offers Download template; Workspace settings offers Import template.
The versioned JSON format contains the project name/brief, specialist roles and names,
additional guidance, per-agent options, and project controls. Export omits notes,
credentials, connection settings, history, sources, tasks, receipts, and workspace files.
Review project briefs and additional guidance before sharing: user-written text can
contain private information even though credential fields are excluded.

An import validates the whole configuration and creates a separate project with fresh
IDs. Unsupported fields, versions, roles, and invalid context rules are rejected.
Importing never connects a model, changes the global connection, or executes an agent.

## Recovery and local storage

Projects, agents, messages, references, and approvals persist in the desktop state
directory. Browser local storage remembers message drafts and the last view, scoped
by the server's state directory. Use a trusted browser profile; drafts are local text,
not an encrypted secret store.

A server restart marks unfinished turns interrupted. Saved specialist replies and
proposals remain available, and Recover a previous request restores an editable draft.
Nothing is automatically resent or re-executed. One server may own a state directory
at a time; the operating system releases its lock after exit or a crash.

The GitHub Pages site is a static interface preview. Start the local server to use
persistent projects and agents. Command execution requires Linux bubblewrap; unavailable
sandbox support fails closed. Desktop use does not require a native Mojo installation.
