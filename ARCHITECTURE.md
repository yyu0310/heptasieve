# Architecture

> The code itself lives in `heptabase_sync.py`. This document explains the design only; it does not repeat code.

## 1. Data flow

```
hepta.db (local SQLite, maintained by the Heptabase desktop app)
        │  reads only whitelisted-whiteboard surface cards and card_map titles (fail-closed)
        ▼
heptabase_sync.py  ── reads ──▶ config.json (whitelist boards / blacklist boards / card_map)
        │            ── writes ─▶ state.json (last_sync record)
        │  ProseMirror JSON -> Markdown
        ▼
.md files under base_output_dir / board_output_dir
        ▼
Your AI agent reads only these .md files, never hepta.db
```

`launchd` starts the script every 15 minutes. It is a short-lived process that runs and exits. No AI is involved in the sync itself.

## 2. Whitelist / exclusion model (the core of v3)

| Source | Rule | Why it is fail-closed |
|---|---|---|
| **whitelist_whiteboards** (board name -> folder) | Read only the cards on these boards' surface, write to the matching folder | Un-named boards are not read by default |
| **card_map** (title -> path) | These titles are always synced; their path wins | Query is `WHERE title IN` the whitelisted titles only |
| **blacklist_whiteboards** | Cards on these boards are subtracted first, before content is read; wins over whitelist | Catches a card placed on two boards by mistake |
| **Sub-whiteboards (un-named)** | Moving a card into a sub-whiteboard changes its `whiteboard_id`, so a surface scan never sees it | Structural exclusion, never enters the query at all |

To read a specific sub-whiteboard, add its name to `whitelist_whiteboards` (name every board, still fail-closed).

## 3. hepta.db tables used (read-only)

| Table | Columns | Purpose | Reads content? |
|---|---|---|---|
| `whiteboard` | `id, name, is_trashed` | Match a board name to its id | No, only the board name (which you chose) |
| `card_instance` | `whiteboard_id, card_id` | Get the card ids on a board surface | No, returns card_id only |
| `card` | `id, title, content, last_edited_time, is_trashed` | Read the cards selected for sync | Yes, but `WHERE id IN <filtered ids>` or `title IN card_map` |

## 4. The fail-closed order inside `build_plan` (most important)

```
1. Compute blacklist ids   <- card_instance of blacklist boards (ids only)
2. Compute board-surface ids <- card_instance of whitelist boards (ids only)
3. Surface ids - blacklist ids  <- subtract first, before the next step
4. Read content             <- fetch_cards_by_ids(filtered ids)  <- only here does it touch title/content
5. Read card_map by title    <- fetch_cards_by_titles, then subtract blacklist ids again
6. Build the plan: card_map path wins; everything else uses "board folder / sanitized title.md"
```

The key point: the blacklist is subtracted *before content is read*, so an excluded card's title and content are never fetched. Sub-whiteboard cards are out of range from step 2.

## 5. Function responsibilities

| Function | Responsibility |
|---|---|
| `load_config` / `save_state` | Read config, write last_sync |
| `node_to_md` / `marks_wrap` / `_inline` / `_list_item` / `_std_list_item` / `_cell_text` / `_table_md` / `prosemirror_to_markdown` | ProseMirror -> Markdown, covering the Heptabase schema (table, bullet/todo/toggle_list_item, video) plus standard ProseMirror |
| `get_whiteboard_ids` | Board name -> id (exact match, excludes trashed, skips not found) |
| `get_board_card_ids` | Set of surface card_ids for a board (ids only) |
| `get_section_paths` | card_id -> nested section path (via cardInstance -> card_id; deepest section wins on overlap). Used when `section_subfolders` is on |
| `fetch_cards_by_ids` | Read only the given ids (batched to stay under the SQL variable limit) |
| `fetch_cards_by_titles` | card_map: read only whitelisted titles |
| `sanitize_filename` | Title -> safe filename (`/` -> `!`, strip illegal chars, blank -> untitled) |
| `build_plan` | Decide which cards to sync and where each lands (fail-closed order) |
| `sync` | Compare timestamps, update only newer cards, write Markdown |
| `parse_hepta_time` | Parse ISO time |
| `main` | Parse args, dispatch, write state |

## 6. Privacy invariants (must hold when modifying the code)

1. Any query that reads title/content **must** be constrained to already-filtered ids (whitelist surface minus blacklist) or `card_map` titles. No unconditional `SELECT title/content`.
2. The blacklist **must** be subtracted before content is fetched, never read-then-discard.
3. Board membership is always computed from `card_instance` card_ids. Do not widen the read range to make output convenient.
4. Before adding a feature, confirm it cannot pull an un-named board or sub-whiteboard into the read range.

## 7. Edge cases

- Same card on multiple whitelisted boards -> the first folder in config order wins.
- A board card's title collides with a `card_map` title -> `card_map` path wins (the board copy is skipped).
- Filename collision in the same folder -> the later one gets a `_{first 6 of id}` suffix.
- Title contains `/` -> replaced with `!` in the filename; blank title -> `untitled`.

## 8. Nested section classification (`section_subfolders`)

- When `section_subfolders: true`, board cards are split into subfolders by their nested section path (e.g. `Exercise/Compound-lifts`).
- `section_object` links to a cardInstance id, which is mapped back to card_id via `card_instance`; on parent/child overlap the deepest section wins.
- Sections are used only for *classification* (a wrong guess just misfiles a card, low risk), never for the allow/block lists (those need a stable decision).
- A card framed by no section lands at the board folder root.
