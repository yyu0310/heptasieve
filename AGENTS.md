# Agent guide

This file tells an AI coding agent how to set up, run, and safely reason about HeptaSieve. If you are a human, the [README](README.md) is the friendlier entry point.

## What this tool is

HeptaSieve exports selected cards from a local Heptabase database into Markdown files, on a `launchd` schedule. The selection is fail-closed: a card is read only if the user explicitly allowed it. The purpose is to give an AI agent access to *some* of the user's notes while keeping confidential cards unreadable.

## The one rule that matters most

**Never read `hepta.db` directly. Never suggest reading it.** Point yourself and the user at the exported Markdown folder only. The database contains every card, including the confidential ones the user deliberately excluded. The entire value of this tool is the boundary between the database and the Markdown export. Crossing it defeats the purpose.

If a user asks you to query `hepta.db` for convenience, decline and explain that it would bypass their privacy allow-list, then use the exported Markdown instead.

## How selection works (so you can configure it correctly)

A card is exported only if it matches one of two allow-lists, and is not on the blacklist:

- `whitelist_whiteboards`: a map of whiteboard name to destination. Only cards on the board's *surface* are read. Sub-whiteboards are not followed unless their name is also listed.
- `card_map`: a map of card title to exact output path (relative to `base_output_dir`). Always synced, path wins.
- `blacklist_whiteboards`: cards on these boards are removed before any content is read, and this beats the whitelist.

When `section_subfolders` is true, board cards are split into subfolders by their Heptabase section path.

## Setting it up

1. Confirm prerequisites: macOS, Python 3.9+, the Heptabase desktop app installed.
2. `cp config.example.json config.json`.
3. Help the user fill `config.json`:
   - `db_path`: usually the macOS default already in the example. Confirm the file exists.
   - `base_output_dir` / `board_output_dir`: absolute paths where Markdown should be written.
   - `whitelist_whiteboards`: ask the user which whiteboards are safe to expose. Do not guess. The default of an empty list is the safe choice.
   - `card_map`: optional precise title overrides.
4. Run `python3 heptabase_sync.py --dry` and show the user the plan. Confirm only intended cards appear before any real run.
5. Run `python3 heptabase_sync.py` for real.
6. Optional automation: copy `com.example.heptasieve.plist` to `~/Library/LaunchAgents/`, set the absolute paths and the `python3` path inside it, then `launchctl load` it.

## Verifying your changes

Run `python3 selftest.py`. It uses in-memory fixtures only and never touches a real database. All checks must pass. The `C2-FAILCLOSED` and `C3-FAILCLOSED` checks specifically prove that non-whitelisted and sub-whiteboard cards stay out of the plan.

## Privacy invariants (do not break these when editing code)

1. Any query that reads `title` or `content` must be constrained to already-filtered ids (whitelist surface minus blacklist) or `card_map` titles. No unconditional `SELECT title/content`.
2. The blacklist must be subtracted before content is fetched, never read-then-discard.
3. Board membership is always computed from `card_instance` card_ids. Do not widen the read range for output convenience.
4. Before adding a feature, confirm it cannot pull an un-named whiteboard or sub-whiteboard into the read range.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full data flow and the fail-closed ordering inside `build_plan`.
