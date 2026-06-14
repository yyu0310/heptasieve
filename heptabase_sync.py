"""
HeptaSieve — privacy-first Heptabase to Markdown sync
=====================================================
Export only the *whitelisted* cards from your local Heptabase database into
Markdown files at the destinations you choose. Everything else stays invisible.

The whitelist is built from two fail-closed sources:
  1. whitelist_whiteboards: whiteboards you name explicitly. Only the cards on
     each board's *surface* are read (sub-whiteboards are NOT followed). To sync
     a sub-whiteboard, add its name to the list too (name every board you want).
     Each board's cards are written to that board's configured destination.
  2. card_map: a title -> exact-path override layer. These cards are always
     synced by title (regardless of which board they live on), and their path
     takes precedence.

Exclusions (safety):
  - blacklist_whiteboards: cards on these boards are subtracted *before* any
    content is read. Blacklist wins over whitelist.
  - sub-whiteboards: once a card is moved into a sub-whiteboard its
    whiteboard_id changes, so a surface scan never sees it -> excluded by design.

Titles and content of non-whitelisted cards are never returned: every query
that touches title/content is constrained to whitelisted whiteboard ids or
card_map titles.

Usage:
    python3 heptabase_sync.py          # sync (default, used by launchd)
    python3 heptabase_sync.py --dry    # preview without writing
    python3 heptabase_sync.py --force  # force re-export of everything

Version history:
    v3.3.0  Board destinations accept absolute paths: a board can sync straight
            into an isolated project subfolder. The config doubles as the
            routing index for "where each board lands".
    v3.2.0  Nested section subfolders (section_subfolders): board cards are
            split into subfolders by their nested section path; when parent and
            child overlap, the deepest section wins.
    v3.1.0  Converter covers the full Heptabase schema: table -> md table,
            bullet/todo/toggle_list_item, video; blank line inserted before
            headings.
    v3.0.0  Whiteboard-membership whitelist + blacklist boards + structural
            sub-whiteboard exclusion.
"""

import sqlite3
import json
import sys
import argparse
import re
from datetime import datetime
from pathlib import Path

VERSION = "3.3.0"

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
STATE_PATH = SCRIPT_DIR / "state.json"


# ============================================================
# Config and state
# ============================================================

def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["db_path_resolved"] = Path(cfg["db_path"]).expanduser()
    cfg["base_output_resolved"] = Path(cfg["base_output_dir"])
    cfg["board_output_resolved"] = Path(cfg.get("board_output_dir", cfg["base_output_dir"]))
    cfg.setdefault("whitelist_whiteboards", {})
    cfg.setdefault("blacklist_whiteboards", [])
    cfg.setdefault("card_map", {})
    return cfg


def save_state(state: dict):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ============================================================
# ProseMirror JSON -> Markdown converter
# Covers the Heptabase schema: table, bullet/todo/toggle_list_item, video,
# plus standard ProseMirror (bullet_list > list_item, etc.) for older cards.
# ============================================================

def marks_wrap(text: str, marks: list) -> str:
    for mark in marks:
        t = mark.get("type", "")
        if t == "bold":
            text = f"**{text}**"
        elif t == "italic":
            text = f"*{text}*"
        elif t == "code":
            text = f"`{text}`"
        elif t == "strike":
            text = f"~~{text}~~"
        elif t == "link":
            href = mark.get("attrs", {}).get("href", "")
            text = f"[{text}]({href})"
    return text


def _inline(nodes) -> str:
    """Join inline child nodes into a single line of text."""
    return "".join(node_to_md(c) for c in nodes)


def _list_item(node, indent: int, prefix: str) -> str:
    """Heptabase flat list item (bullet/todo/toggle): first paragraph is the
    item text, the rest is nested content."""
    text, rest = "", []
    for i, ch in enumerate(node.get("content", [])):
        if i == 0 and ch.get("type") == "paragraph":
            text = _inline(ch.get("content", []))
        else:
            rest.append(ch)
    line = "  " * indent + prefix + text + "\n"
    nested = "".join(node_to_md(c, indent + 1) for c in rest)
    return line + nested


def _std_list_item(node, indent: int, order=None) -> str:
    """Standard ProseMirror list_item (older cards use bullet_list > list_item)."""
    if node.get("type") != "list_item":
        return node_to_md(node, indent)
    text, rest = "", []
    for i, ch in enumerate(node.get("content", [])):
        if i == 0 and ch.get("type") == "paragraph":
            text = _inline(ch.get("content", []))
        else:
            rest.append(ch)
    prefix = f"{order}. " if order else "- "
    line = "  " * indent + prefix + text + "\n"
    nested = "".join(node_to_md(c, indent + 1) for c in rest)
    return line + nested


def _cell_text(cell) -> str:
    parts = []
    for ch in cell.get("content", []):
        if ch.get("type") == "paragraph":
            parts.append(_inline(ch.get("content", [])))
        else:
            parts.append(node_to_md(ch))
    txt = " ".join(p.strip() for p in parts if p.strip())
    return txt.replace("\n", " ").replace("|", "\\|")


def _table_md(node) -> str:
    rows = [r for r in node.get("content", []) if r.get("type") == "table_row"]
    if not rows:
        return ""
    def cells(r):
        return [c for c in r.get("content", []) if c.get("type") in ("table_cell", "table_header")]
    lines = ["| " + " | ".join(_cell_text(c) for c in cells(r)) + " |" for r in rows]
    ncol = len(cells(rows[0]))
    sep = "| " + " | ".join(["---"] * ncol) + " |"
    body = "\n".join(lines[1:])
    return lines[0] + "\n" + sep + ("\n" + body if body else "") + "\n\n"


def node_to_md(node: dict, indent: int = 0) -> str:
    t = node.get("type", "")
    content = node.get("content", [])
    attrs = node.get("attrs", {})

    if t == "text":
        return marks_wrap(node.get("text", ""), node.get("marks", []))
    if t == "paragraph":
        return _inline(content) + "\n\n"
    if t == "heading":
        return "#" * attrs.get("level", 1) + " " + _inline(content) + "\n\n"
    if t == "horizontal_rule":
        return "---\n\n"
    if t == "hard_break":
        return "\n"
    if t == "code_block":
        lang = attrs.get("language") or attrs.get("params") or ""
        return f"```{lang}\n" + _inline(content) + "\n```\n\n"
    if t == "blockquote":
        inner = "".join(node_to_md(c) for c in content)
        return "\n".join("> " + l for l in inner.strip().splitlines()) + "\n\n"
    # Heptabase flat lists
    if t == "bullet_list_item":
        return _list_item(node, indent, "- ")
    if t == "todo_list_item":
        return _list_item(node, indent, "- [x] " if attrs.get("checked") else "- [ ] ")
    if t == "toggle_list_item":
        return _list_item(node, indent, "- ")
    if t == "table":
        return _table_md(node)
    if t == "video":
        url = attrs.get("url")
        return f"{'  ' * indent}[🎥 video]({url})\n\n" if url else ""
    # Standard ProseMirror nested lists (fallback for older cards)
    if t == "bullet_list":
        return "".join(_std_list_item(i, indent) for i in content) + "\n"
    if t == "ordered_list":
        return "".join(_std_list_item(it, indent, order=i) for i, it in enumerate(content, 1)) + "\n"
    if t == "doc":
        return "".join(node_to_md(c) for c in content)
    # Unknown node: recurse into children
    if content:
        return "".join(node_to_md(c, indent) for c in content)
    return ""


def prosemirror_to_markdown(json_str: str) -> str:
    try:
        doc = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return json_str
    md = node_to_md(doc)
    md = re.sub(r"([^\n])\n(#{1,6} )", r"\1\n\n\2", md)  # blank line before headings
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


# ============================================================
# DB access (fail-closed)
# ============================================================

def get_whiteboard_ids(conn, names: list) -> dict:
    """Whiteboard name -> id (exact match, excludes trashed). Names not found
    simply never appear in the result."""
    result = {}
    if not names:
        return result
    cur = conn.cursor()
    for name in names:
        cur.execute("SELECT id FROM whiteboard WHERE name = ? AND is_trashed = 0", (name,))
        row = cur.fetchone()
        if row:
            result[name] = row["id"]
    return result


def get_board_card_ids(conn, whiteboard_id: str) -> set:
    """Card ids on a whiteboard's surface (returns card_id only, never touches
    title/content)."""
    cur = conn.cursor()
    cur.execute("SELECT card_id FROM card_instance WHERE whiteboard_id = ?", (whiteboard_id,))
    return {r["card_id"] for r in cur.fetchall()}


def get_section_paths(conn, whiteboard_id: str) -> dict:
    """
    Return {card_id: nested section path}, e.g. "Exercise/Compound-lifts".
    Computed using only ids and section titles; a card in no section does not
    appear in the result (-> placed at the board folder root).
    section_object links to a cardInstance id, which is mapped back to card_id
    via card_instance.
    """
    cur = conn.cursor()
    cur.execute("SELECT id, title FROM section WHERE whiteboard_id = ?", (whiteboard_id,))
    sec_title = {r["id"]: r["title"] for r in cur.fetchall()}
    if not sec_title:
        return {}

    cur.execute("SELECT id, card_id FROM card_instance WHERE whiteboard_id = ?", (whiteboard_id,))
    inst2card = {r["id"]: r["card_id"] for r in cur.fetchall()}

    parent_of = {}            # child section -> parent section
    card_secs = {}            # card_id -> {section_id, ...}
    for sid in sec_title:
        cur.execute("SELECT object_id, object_type FROM section_object WHERE section_id = ?", (sid,))
        for r in cur.fetchall():
            if r["object_type"] == "section":
                parent_of[r["object_id"]] = sid
            elif r["object_type"] == "cardInstance":
                cardid = inst2card.get(r["object_id"])
                if cardid:
                    card_secs.setdefault(cardid, set()).add(sid)

    def depth(sid):
        d = 0
        seen = set()
        while sid in parent_of and sid not in seen:
            seen.add(sid)
            sid = parent_of[sid]
            d += 1
        return d

    def path(sid):
        chain, seen = [], set()
        while sid and sid not in seen:
            seen.add(sid)
            chain.append(sanitize_filename(sec_title.get(sid, "")))
            sid = parent_of.get(sid)
        return "/".join(t for t in reversed(chain) if t)

    result = {}
    for cardid, sids in card_secs.items():
        deepest = max(sids, key=depth)   # on parent/child overlap, take the deepest (most specific) section
        result[cardid] = path(deepest)
    return result


def fetch_cards_by_ids(conn, ids: set) -> dict:
    """Read only the cards with the given ids. WHERE id IN constrains the read;
    cards not in the set are never returned."""
    if not ids:
        return {}
    ids = list(ids)
    out = {}
    cur = conn.cursor()
    # Batch to stay under the SQL variable limit
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        ph = ",".join("?" * len(chunk))
        cur.execute(
            f"SELECT id, title, content, last_edited_time FROM card "
            f"WHERE is_trashed=0 AND id IN ({ph})", chunk)
        for r in cur.fetchall():
            out[r["id"]] = dict(r)
    return out


def fetch_cards_by_titles(conn, titles: list) -> dict:
    """Read only the whitelisted titles (used by card_map). Returns {title: row}."""
    if not titles:
        return {}
    ph = ",".join("?" * len(titles))
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, title, content, last_edited_time FROM card "
        f"WHERE is_trashed=0 AND title IN ({ph})", titles)
    return {r["title"]: dict(r) for r in cur.fetchall()}


def parse_hepta_time(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return datetime.min


# ============================================================
# Filenames / paths
# ============================================================

def sanitize_filename(title: str) -> str:
    """Turn a card title into a safe filename (collapse newlines/extra spaces,
    strip path separators and illegal characters)."""
    name = re.sub(r"\s+", " ", title).strip()   # internal newlines / extra spaces -> single space
    name = name.replace("/", "!").replace("\\", "!")
    name = re.sub(r'[:*?"<>|]', "_", name)
    name = name.strip(". ")
    return name or "untitled"


# ============================================================
# Sync
# ============================================================

def build_plan(conn, cfg) -> tuple:
    """
    Decide which cards to sync and where each one goes. Returns (plan, stats).
    plan: {card_id: {"card": row, "path": Path}}
    fail-closed order: compute blacklist ids -> subtract them from board-surface
    ids BEFORE reading content -> read card_map by title and subtract blacklist too.
    """
    base = cfg["base_output_resolved"]
    board_base = cfg["board_output_resolved"]
    card_map = cfg["card_map"]

    # 1. Blacklist ids (computed first, always subtracted later)
    bl_ids = set()
    for wid in get_whiteboard_ids(conn, cfg["blacklist_whiteboards"]).values():
        bl_ids |= get_board_card_ids(conn, wid)

    # 2. Board-surface cards: id -> resolved output dir (Path). Subtract blacklist
    #    before reading content. A board destination (whitelist value) may be a
    #    path relative to board_base, or an absolute path (a permanent home, e.g.
    #    a board folded into a separate project). With section_subfolders on,
    #    cards are further split by their nested section path.
    board_id_to_dir = {}
    use_sections = cfg.get("section_subfolders", False)
    wl = get_whiteboard_ids(conn, list(cfg["whitelist_whiteboards"].keys()))
    name_by_id = {v: k for k, v in wl.items()}
    for name, wid in wl.items():
        dest = cfg["whitelist_whiteboards"][name]
        if dest and Path(dest).is_absolute():
            root = Path(dest)
        elif dest:
            root = board_base / dest
        else:
            root = board_base
        sec_paths = get_section_paths(conn, wid) if use_sections else {}
        for cid in get_board_card_ids(conn, wid):
            if cid in bl_ids:
                continue
            sub = sec_paths.get(cid, "")
            board_id_to_dir.setdefault(cid, root / sub if sub else root)  # same card on multiple boards -> first wins

    board_cards = fetch_cards_by_ids(conn, set(board_id_to_dir.keys()))

    # 3. card_map: read by title, subtract blacklist
    cm_cards = fetch_cards_by_titles(conn, list(card_map.keys()))
    cm_cards = {t: c for t, c in cm_cards.items() if c["id"] not in bl_ids}

    # 4. Build the plan (card_map path takes precedence)
    plan = {}
    cm_titles = set(card_map.keys())
    for title, card in cm_cards.items():
        plan[card["id"]] = {"card": card, "path": base / card_map[title]}
    used_names = {}  # detect filename collisions within the same folder
    for cid, card in board_cards.items():
        if card["title"] in cm_titles:
            continue  # already overridden by card_map
        if cid in plan:
            continue
        outdir = board_id_to_dir[cid]
        fname = sanitize_filename(card["title"])
        key = (str(outdir), fname)
        if key in used_names:
            fname = f"{fname}_{cid[:6]}"  # name collision -> append id suffix
        used_names[key] = cid
        plan[cid] = {"card": card, "path": outdir / f"{fname}.md"}

    stats = {
        "blacklist_excluded": len(bl_ids),
        "whitelist_boards_found": len(wl),
        "whitelist_boards_requested": len(cfg["whitelist_whiteboards"]),
        "board_cards": len([c for c in board_cards if board_cards[c]["title"] not in cm_titles]),
        "cardmap_cards": len(cm_cards),
        "cardmap_missing": [t for t in card_map if t not in cm_cards],
        "name_by_id": name_by_id,
    }
    return plan, stats


def sync(conn, cfg, dry_run=False, force=False) -> dict:
    print(f"{'[DRY RUN] ' if dry_run else ''}=== HeptaSieve sync v{VERSION} START ===")
    plan, stats = build_plan(conn, cfg)

    # Whiteboard delivery status
    req, found = stats["whitelist_boards_requested"], stats["whitelist_boards_found"]
    if req == 0:
        print("  ℹ️  No whitelisted whiteboards yet; syncing card_map cards only.")
    elif found < req:
        print(f"  ⚠️  {req} whitelisted whiteboards requested, only {found} found (check names).")
    else:
        print(f"  Whitelisted whiteboards: all {found} found.")
    print(f"  Blacklist-excluded cards: {stats['blacklist_excluded']}")
    print(f"  To sync: card_map {stats['cardmap_cards']} + board cards {stats['board_cards']} = {len(plan)}")

    def disp(p):
        for root, tag in ((cfg["base_output_resolved"], "base"), (cfg["board_output_resolved"], "board")):
            try:
                return f"{tag}/{p.relative_to(root)}"
            except ValueError:
                continue
        return str(p)

    updated = skipped = 0
    for cid, item in plan.items():
        card, out_path = item["card"], item["path"]
        hepta_time = parse_hepta_time(card["last_edited_time"])
        if not force and out_path.exists():
            file_mtime = datetime.fromtimestamp(out_path.stat().st_mtime).astimezone()
            if hepta_time.astimezone() <= file_mtime:
                skipped += 1
                continue
        md = prosemirror_to_markdown(card["content"])
        if dry_run:
            print(f"  📝 would update: {disp(out_path)}")
        else:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md, encoding="utf-8")
            print(f"  ✅ updated: {disp(out_path)}")
        updated += 1

    if stats["cardmap_missing"]:
        for t in stats["cardmap_missing"]:
            print(f"  ⚠️  card_map card not found: <{t}>")

    print(f"  Done: updated {updated} / skipped {skipped} (unchanged) / card_map missing {len(stats['cardmap_missing'])}")
    print(f"=== HeptaSieve sync v{VERSION} END ===")
    return {"updated": updated, "skipped": skipped, "stats": stats}


def main():
    parser = argparse.ArgumentParser(description=f"HeptaSieve sync v{VERSION}")
    parser.add_argument("--dry", action="store_true", help="preview mode, no writes")
    parser.add_argument("--force", action="store_true", help="force re-export of everything")
    args = parser.parse_args()

    cfg = load_config()
    db_path = cfg["db_path_resolved"]
    if not db_path.exists():
        print(f"❌ hepta.db not found: {db_path} (the Heptabase desktop app must be installed)")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        res = sync(conn, cfg, dry_run=args.dry, force=args.force)
        if not args.dry:
            save_state({
                "last_sync": {
                    "time": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "updated": res["updated"],
                    "skipped": res["skipped"],
                    "blacklist_excluded": res["stats"]["blacklist_excluded"],
                    "cardmap_missing": res["stats"]["cardmap_missing"],
                }
            })
    finally:
        conn.close()


if __name__ == "__main__":
    main()
