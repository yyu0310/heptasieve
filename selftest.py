"""
HeptaSieve self-test
====================
Runs entirely against in-memory fixture databases and hand-built JSON. It never
reads a real hepta.db.

The focus is the fail-closed guarantee: cards from non-whitelisted whiteboards,
sub-whiteboards, and blacklisted boards must never enter the sync plan.

Run:
    python3 selftest.py
"""

import json
import sqlite3
import sys
import importlib.util
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("heptabase_sync", HERE / "heptabase_sync.py")
hs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hs)

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")


def md(doc):
    return hs.prosemirror_to_markdown(json.dumps(doc))


# ============================================================
print("\n[A] ProseMirror -> Markdown converter")
# ============================================================
doc = {"type": "doc", "content": [
    {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Title"}]},
    {"type": "paragraph", "content": [
        {"type": "text", "text": "bold", "marks": [{"type": "bold"}]},
        {"type": "text", "text": "text"}]}]}
out = md(doc)
check("A1 heading + bold", "## Title" in out and "**bold**text" in out, repr(out))

doc = {"type": "doc", "content": [{"type": "bullet_list", "content": [
    {"type": "list_item", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "outer"}]},
        {"type": "bullet_list", "content": [{"type": "list_item", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "inner"}]}]}]}]}]}]}
check("A2 nested list", "- outer" in md(doc) and "inner" in md(doc))

check("A3 bad JSON passes through", hs.prosemirror_to_markdown("bad{") == "bad{")
check("A4 empty doc -> empty string", md({"type": "doc", "content": []}) == "")

doc = {"type": "doc", "content": [{"type": "code_block", "attrs": {"language": "py"},
       "content": [{"type": "text", "text": "x=1"}]}]}
check("A5 code_block", "```py" in md(doc) and "x=1" in md(doc))


# ---- Heptabase-specific nodes ----
def cell(txt, header=False):
    return {"type": "table_header" if header else "table_cell",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": txt}]}]}

doc = {"type": "doc", "content": [{"type": "table", "content": [
    {"type": "table_row", "content": [cell("Move", True), cell("Weight", True)]},
    {"type": "table_row", "content": [cell("Lat pulldown"), cell("85")]},
    {"type": "table_row", "content": [cell("Pull-up"), cell("")]},
]}]}
out = md(doc)
check("A6 table -> md table",
      "| Move | Weight |" in out and "| --- | --- |" in out
      and "| Lat pulldown | 85 |" in out and "| Pull-up |  |" in out, repr(out))

doc = {"type": "doc", "content": [
    {"type": "bullet_list_item", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "item"}]}]}]}
check("A7 bullet_list_item", md(doc).strip() == "- item", repr(md(doc)))

doc = {"type": "doc", "content": [
    {"type": "todo_list_item", "attrs": {"checked": True},
     "content": [{"type": "paragraph", "content": [{"type": "text", "text": "done"}]}]},
    {"type": "todo_list_item", "attrs": {"checked": False},
     "content": [{"type": "paragraph", "content": [{"type": "text", "text": "todo"}]}]}]}
out = md(doc)
check("A8 todo checkbox", "- [x] done" in out and "- [ ] todo" in out, repr(out))

doc = {"type": "doc", "content": [
    {"type": "toggle_list_item", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "summary"}]},
        {"type": "video", "attrs": {"url": "https://youtu.be/x"}}]}]}
out = md(doc)
check("A9 toggle + video", "- summary" in out and "[🎥 video](https://youtu.be/x)" in out, repr(out))

# Nested: bullet under bullet
doc = {"type": "doc", "content": [
    {"type": "bullet_list_item", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "outer"}]},
        {"type": "bullet_list_item", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "inner"}]}]}]}]}
out = md(doc)
check("A10 nested bullet indent", "- outer" in out and "  - inner" in out, repr(out))

# Non-ASCII content survives the converter unchanged
doc = {"type": "doc", "content": [
    {"type": "paragraph", "content": [{"type": "text", "text": "日本語とテスト"}]}]}
check("A11 unicode preserved", "日本語とテスト" in md(doc), repr(md(doc)))


# ============================================================
print("\n[B] Filename sanitizing")
# ============================================================
check("B1 slash -> !", hs.sanitize_filename("Knowledge / Base") == "Knowledge ! Base",
      hs.sanitize_filename("Knowledge / Base"))
check("B2 blank title -> untitled", hs.sanitize_filename("   ") == "untitled")
check("B3 illegal chars", hs.sanitize_filename('a:b*c?') == "a_b_c_", hs.sanitize_filename('a:b*c?'))
check("B4 internal newline collapsed", hs.sanitize_filename("Line one\nLine two") == "Line one Line two",
      hs.sanitize_filename("Line one\nLine two"))


# ============================================================
print("\n[C] v3 sync plan (fixture, verifies fail-closed)")
# ============================================================
def make_fixture():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE card (id TEXT PRIMARY KEY, title TEXT, content TEXT,
                           last_edited_time TEXT, is_trashed INTEGER DEFAULT 0);
        CREATE TABLE whiteboard (id TEXT PRIMARY KEY, name TEXT, is_trashed INTEGER DEFAULT 0);
        CREATE TABLE card_instance (whiteboard_id TEXT, card_id TEXT);
    """)
    body = lambda t: json.dumps({"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": t}]}]})
    T = "2026-01-01T00:00:00Z"
    conn.executemany("INSERT INTO card VALUES (?,?,?,?,?)", [
        ("c1", "Surface A", body("safe"), T, 0),
        ("c2", "Public Card", body("public"), T, 0),
        ("c3", "Private Card", body("secret content"), T, 0),   # on a non-whitelisted board
        ("c4", "Dual Card", body("dual"), T, 0),                # on both whitelist + blacklist
        ("c5", "Mapped Card", body("mapped"), T, 0),            # card_map, on no board
        ("c6", "Override Card", body("override"), T, 0),         # on a board + in card_map
        ("c7", "Sub Hidden", body("sub secret"), T, 0),          # on an un-named sub-whiteboard
        ("c8", "Has/Slash", body("slash"), T, 0),                # tests filename sanitizing
    ])
    conn.executemany("INSERT INTO whiteboard VALUES (?,?,?)", [
        ("wbW1", "Synced Board", 0), ("wbW2", "Sub Board", 0),
        ("wbB1", "Blocked Board", 0), ("wbX", "Other Board", 0), ("wbSub", "A Sub-whiteboard", 0),
    ])
    conn.executemany("INSERT INTO card_instance VALUES (?,?)", [
        ("wbW1", "c1"), ("wbW1", "c4"), ("wbW1", "c6"), ("wbW1", "c8"),
        ("wbW2", "c2"),
        ("wbB1", "c4"),     # c4 placed on two boards
        ("wbX", "c3"),      # private card on a non-whitelisted board
        ("wbSub", "c7"),    # sub-whiteboard not named
    ])
    return conn


conn = make_fixture()
cfg = {
    "base_output_resolved": Path("/OUT"),
    "board_output_resolved": Path("/BOARD"),
    "whitelist_whiteboards": {"Synced Board": "", "Sub Board": "sub"},
    "blacklist_whiteboards": ["Blocked Board"],
    "card_map": {"Mapped Card": "mapped/m.md", "Override Card": "override/ov.md"},
}
plan, stats = hs.build_plan(conn, cfg)
ids = set(plan.keys())
titles_in_plan = {v["card"]["title"] for v in plan.values()}
paths = {cid: str(v["path"]) for cid, v in plan.items()}

check("C1 plan holds only the cards to sync", ids == {"c1", "c2", "c5", "c6", "c8"}, str(ids))
check("C2-FAILCLOSED private c3 not in plan", "Private Card" not in titles_in_plan and "c3" not in ids)
check("C3-FAILCLOSED un-named sub-whiteboard c7 not read", "c7" not in ids)
check("C4 blacklist c4 excluded (wins over whitelist)", "c4" not in ids)
check("C5 blacklist-excluded count = 1", stats["blacklist_excluded"] == 1, str(stats["blacklist_excluded"]))
check("C6 card_map at base root (c5)", "c5" in ids and paths["c5"] == "/OUT/mapped/m.md", paths.get("c5"))
check("C7 card_map path overrides board (c6)", paths["c6"] == "/OUT/override/ov.md", paths.get("c6"))
check("C8 board card at board subfolder (c2)", paths["c2"] == "/BOARD/sub/Public Card.md", paths.get("c2"))
check("C9 empty dest = board root (c1)", paths["c1"] == "/BOARD/Surface A.md", paths.get("c1"))
check("C10 filename slash sanitized (c8)", paths["c8"] == "/BOARD/Has!Slash.md", paths.get("c8"))
check("C11 stats cardmap=2 board=3",
      stats["cardmap_cards"] == 2 and stats["board_cards"] == 3, str(stats))


# ============================================================
print("\n[D] Whiteboard resolution / helpers / example config")
# ============================================================
wl = hs.get_whiteboard_ids(conn, ["Synced Board", "Nonexistent Board", "Sub Board"])
check("D1 board name -> id (skips missing)", wl == {"Synced Board": "wbW1", "Sub Board": "wbW2"}, str(wl))
check("D2 surface card-id set", hs.get_board_card_ids(conn, "wbW1") == {"c1", "c4", "c6", "c8"})
check("D3 parse_hepta_time bad input", hs.parse_hepta_time("xx") == datetime.min)

with open(HERE / "config.example.json", encoding="utf-8") as f:
    example = json.load(f)
check("D4 config.example.json parses with required keys",
      all(k in example for k in ("db_path", "base_output_dir", "whitelist_whiteboards", "card_map")),
      str(list(example.keys())))


# ============================================================
print("\n[E] Nested section paths")
# ============================================================
def make_section_fixture():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE section (id TEXT, whiteboard_id TEXT, title TEXT);
        CREATE TABLE section_object (section_id TEXT, object_id TEXT, object_type TEXT);
        CREATE TABLE card_instance (id TEXT, whiteboard_id TEXT, card_id TEXT);
    """)
    # Board W: Exercise (parent) -> Compound-lifts (child); Calories (standalone)
    conn.executemany("INSERT INTO section VALUES (?,?,?)", [
        ("s_ex", "W", "Exercise"), ("s_big", "W", "Compound-lifts"), ("s_cal", "W", "Calories"),
    ])
    # cardInstance: ci1->ka (Compound-lifts), ci2->kb (Calories), ci3->kc (Exercise only)
    conn.executemany("INSERT INTO card_instance VALUES (?,?,?)", [
        ("ci1", "W", "ka"), ("ci2", "W", "kb"), ("ci3", "W", "kc"),
    ])
    conn.executemany("INSERT INTO section_object VALUES (?,?,?)", [
        ("s_ex", "s_big", "section"),        # Compound-lifts is a child of Exercise
        ("s_big", "ci1", "cardInstance"),    # ka in Compound-lifts
        ("s_ex", "ci1", "cardInstance"),     # ka also framed by parent Exercise (overlap)
        ("s_cal", "ci2", "cardInstance"),    # kb in Calories
        ("s_ex", "ci3", "cardInstance"),     # kc directly under Exercise only
    ])
    return conn

sconn = make_section_fixture()
paths = hs.get_section_paths(sconn, "W")
check("E1 parent/child overlap -> deepest path", paths.get("ka") == "Exercise/Compound-lifts", paths.get("ka"))
check("E2 standalone section", paths.get("kb") == "Calories", paths.get("kb"))
check("E3 parent only -> parent path", paths.get("kc") == "Exercise", paths.get("kc"))
check("E4 no section -> absent", "kx" not in paths)


print(f"\n===== Result: passed {PASS} / failed {FAIL} =====")
sys.exit(1 if FAIL else 0)
