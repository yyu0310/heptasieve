# CLAUDE.md

Guidance for Claude Code (and other AI agents) working in this repository.

The full agent guide lives in [AGENTS.md](AGENTS.md). Read it first. The single most important rule, repeated here so it is never missed:

**Never read `hepta.db` directly, and never suggest it.** Work only from the exported Markdown folder. The database holds every card, including the confidential ones the user deliberately kept out of the export. The boundary between the database and the Markdown output is the entire point of this tool.

To verify any code change: `python3 selftest.py` (in-memory fixtures, never touches a real database). All checks must pass.

For the architecture and the privacy invariants you must preserve when editing code, see [ARCHITECTURE.md](ARCHITECTURE.md).
