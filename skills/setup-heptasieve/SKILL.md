---
name: setup-heptasieve
description: Set up HeptaSieve from one request. Creates config.json, chooses which Heptabase whiteboards to export, previews the plan, runs the first sync, and optionally installs the launchd auto-sync. Use when a user wants to install or configure HeptaSieve.
---

# Set up HeptaSieve

Walk the user through a safe, fail-closed setup. The guiding principle: only export cards the user explicitly allows, and never read `hepta.db` for any other purpose.

## Steps

1. **Check prerequisites.** Confirm macOS, `python3 --version` is 3.9+, and the Heptabase desktop app is installed. Confirm the database exists at the `db_path` in `config.example.json` (default: `~/Library/Application Support/project-meta/hepta.db`).

2. **Create the config.** If `config.json` does not exist, run `cp config.example.json config.json`. Never overwrite an existing `config.json` without asking.

3. **Choose what to export (the important part).** Ask the user which whiteboards are safe to expose to an AI. Do not guess and do not default to "everything." Fill `whitelist_whiteboards` with `board name -> destination`:
   - empty string -> the `board_output_dir` root
   - relative path -> a subfolder under `board_output_dir`
   - absolute path -> a fixed location anywhere on disk
   Add precise title overrides to `card_map` only if the user names specific cards.

4. **Set output paths.** Confirm absolute paths for `base_output_dir` and `board_output_dir`.

5. **Preview.** Run `python3 heptabase_sync.py --dry` and show the plan. Confirm with the user that only intended cards appear. If something unexpected shows up, fix the config before any real run.

6. **First sync.** Run `python3 heptabase_sync.py`.

7. **Verify (optional but recommended).** Run `python3 selftest.py`; all checks must pass.

8. **Auto-sync (optional).** Copy `com.example.heptasieve.plist` to `~/Library/LaunchAgents/`, edit the absolute paths and the `python3` path inside it, then `launchctl load ~/Library/LaunchAgents/com.example.heptasieve.plist`.

## Guardrails

- Never read `hepta.db` to "help" the user pick cards. Ask them by name instead. The database contains confidential cards by design.
- After setup, point the user's AI agent at the exported Markdown folder only.
- The empty whitelist is the safe default. When in doubt, export less.
