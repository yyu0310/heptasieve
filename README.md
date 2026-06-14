# HeptaSieve

**Privacy-first, AI-safe, continuous local sync from Heptabase to structured Markdown.**

You decide exactly which cards an AI agent ever gets to see. Everything else stays out of reach.

English · [繁體中文](README.zh-TW.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

> Unofficial tool. Not affiliated with or endorsed by Heptabase. macOS only for now.

---

## Why this exists

It started with a simple goal: connect Heptabase to Claude Code so an AI agent could read my notes.

The official route is Heptabase's own [CLI](https://github.com/heptameta/heptabase-cli-skills), which you turn on in the app under Settings, AI Features, CLI. It is **fail-open**: once you authorize it, the agent can read your entire knowledge base. Third-party tools like the `heptabase-mcp` server work the same way. That is fine if everything in your knowledge base is safe to share. It does not work if you keep confidential cards next to the ones you want an AI to use, which most people do.

The real insight: the privacy wall is not inside Heptabase. It is at the boundary of *what the AI can read*. So the value of a tool like this is not "sync my notes." It is **keep the confidential cards somewhere the AI cannot reach, and export only the rest into AI-readable Markdown.**

That is the sieve. Only the cards you allow pass through.

## What it does

HeptaSieve reads your local Heptabase database directly and writes selected cards as Markdown files at destinations you choose. A `launchd` job runs it every 15 minutes, so the Markdown stays in step with your notes. The AI agent only ever reads the exported Markdown folder. It never touches the database.

- **Reads the live local database.** Heptabase stopped offering local backups in late 2025, so reading the live DB is now the reliable path to continuous local sync.
- **Structure-faithful conversion.** Tables, bullet / todo / toggle lists, nested sections, and videos are reverse-engineered from Heptabase's ProseMirror schema and rendered as clean Markdown.
- **Any-destination routing.** Each whiteboard can land in its own folder, including an absolute path that drops a board straight into a separate project.

## The fail-closed privacy model

A card is exported only if it matches one of two explicit allow-lists. Nothing is read by default.

| Source | Rule |
|---|---|
| **`whitelist_whiteboards`** | Whiteboards you name. Only the cards on each board's *surface* are read. Sub-whiteboards are not followed. To include one, name it too. |
| **`card_map`** | A `title -> exact path` layer. These titles are always synced, and their path wins. |
| **`blacklist_whiteboards`** | Cards on these boards are subtracted *before* any content is read. Blacklist beats whitelist, so a card placed on two boards by mistake is still blocked. |
| **Sub-whiteboards (un-named)** | Moving a card into a sub-whiteboard changes its `whiteboard_id`, so a surface scan never sees it. Excluded by structure, not by a rule you have to remember. |

The guarantee in one line: every query that touches a card's title or content is constrained to whitelisted whiteboard ids or `card_map` titles. A non-whitelisted card's title and content are never read into memory at all.

Two design principles fall out of this: **structural exclusion beats subtractive exclusion** (a card the query can't reach is safer than a card you filtered out after reading), and **the best notification is the one you never need** (the system is built so there is no "did I leak that card?" question to answer).

## How it compares

| | HeptaSieve | Official Heptabase CLI | Other export tools |
|---|---|---|---|
| Privacy model | Fail-closed allow-list | Fail-open (full knowledge base) | Full export |
| Continuous local sync | Yes (`launchd`, 15 min) | Read on request | One-shot export |
| Reads live local DB | Yes | Varies | Often needs a backup file |
| Structure-faithful Markdown | Tables, lists, sections, video | Varies | Varies |
| Per-board destination routing | Yes, incl. absolute paths | No | No |

This is not a full replacement for Heptabase, and "better than official" only holds on three axes: controllable privacy, continuous local sync, and structure fidelity. The audience is intentionally narrow: macOS users who live in Heptabase and care about what an AI can see. If that is you, this is built for exactly your case.

## Install

Requirements: macOS, Python 3.9+, the Heptabase desktop app installed.

```bash
git clone https://github.com/yyu0310/heptasieve.git
cd heptasieve
cp config.example.json config.json
```

Then edit `config.json` (every field has an inline comment explaining it):

1. Confirm `db_path` points at your local `hepta.db`.
2. Set `base_output_dir` and `board_output_dir` to where you want Markdown written.
3. List the whiteboards you want to export under `whitelist_whiteboards`.
4. Add any precise title overrides under `card_map`.

Run a preview first, which writes nothing:

```bash
python3 heptabase_sync.py --dry
```

When the plan looks right, run it for real:

```bash
python3 heptabase_sync.py
```

### Sync automatically every 15 minutes

```bash
cp com.example.heptasieve.plist ~/Library/LaunchAgents/
# edit the copied file: set the absolute paths and confirm your python3 path
launchctl load ~/Library/LaunchAgents/com.example.heptasieve.plist
```

## Using it with an AI agent

HeptaSieve ships agent-readable docs so you can set it up by talking to an AI coding agent instead of following steps by hand:

- [`AGENTS.md`](AGENTS.md) and [`CLAUDE.md`](CLAUDE.md): how an agent should reason about and configure this tool.
- [`llms.txt`](llms.txt): an index of the docs for LLMs.
- [`skills/setup-heptasieve/`](skills/setup-heptasieve/): a Claude Code skill that walks the whole setup in one request.

Point your agent at the exported Markdown folder, never at `hepta.db`. That separation is the entire point.

## How it works

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the architecture: the data flow, the fail-closed ordering inside `build_plan`, the database tables it reads, and the privacy invariants to preserve when modifying the code.

## Limitations and honest caveats

- **Schema is fragile.** This depends on Heptabase's internal database shape. A Heptabase update can break it. It is unofficial by nature.
- **Reading the live DB is not officially blessed.** It works well in practice, and it is read-only, but you should know it is not a supported integration.
- **macOS only.** The paths and `launchd` setup assume macOS today.

## License

[MIT](LICENSE).
