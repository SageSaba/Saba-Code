#!/usr/bin/env python3
"""conversation_archive.py — Sir Archive: our own history, kept and searchable.

Saba declared the red alert on 2026-07-26 as he watched the conversation
compress away: "we have to find a method of transferring the data." The JSONL
exports were written that same hour. The import that was supposed to follow
stopped at message 580 of 3,032 and the README was written as though it had
finished. This finishes it.

The raw .jsonl exports in ~/Archive are the ORIGINAL — never edited, never
deleted. This tool only reads them and files what it finds into
Conversations.db, the same way RawSegments sits under the sermon book.

Usage:
    python3 conversation_archive.py import              # import every .jsonl found
    python3 conversation_archive.py list                # what's archived
    python3 conversation_archive.py find "text"         # search everything we've said
    python3 conversation_archive.py find "text" --saba  # search only Saba's own words
    python3 conversation_archive.py show <session_id> [n]  # read a session
"""
import json, os, sqlite3, sys, glob, datetime

DB = "/Users/saba/Archive/Conversations.db"
EXPORTS = "/Users/saba/Archive"
# Claude Code writes every session here as it happens — these are the live
# originals, not copies. Found 2026-08-07: 208 of them, back to 2026-07-11.
LIVE_SESSIONS = "/Users/saba/.claude/projects"


def con():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def ensure(db):
    db.execute("""CREATE TABLE IF NOT EXISTS conversation_archive (
        id INTEGER PRIMARY KEY, session_id TEXT, message_num INTEGER,
        timestamp TEXT, role TEXT, content TEXT,
        parent_uuid TEXT, prompt_id TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS conversation_metadata (
        session_id TEXT PRIMARY KEY, started TEXT, ended TEXT,
        total_messages INTEGER, total_user_messages INTEGER,
        total_assistant_messages INTEGER, status TEXT, notes TEXT)""")
    db.execute("CREATE INDEX IF NOT EXISTS ix_ca_session ON conversation_archive(session_id)")
    db.execute("CREATE INDEX IF NOT EXISTS ix_ca_role ON conversation_archive(role)")
    db.commit()


def flatten(content):
    """A message's content may be a plain string or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for p in content:
            if isinstance(p, dict):
                if p.get("type") == "text" or "text" in p:
                    out.append(p.get("text", ""))
                elif p.get("type") == "tool_use":
                    out.append(f"[tool: {p.get('name','')}]")
                elif p.get("type") == "tool_result":
                    r = p.get("content")
                    out.append("[tool result]" if not isinstance(r, str) else f"[tool result] {r[:400]}")
        return " ".join(x for x in out if x)
    return ""


def import_jsonl(path, db):
    session_id = os.path.basename(path).replace("session_", "").replace(".jsonl", "")
    rows, first_ts, last_ts = [], None, None
    n_user = n_asst = 0

    with open(path, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            msg = d.get("message") or {}
            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue
            content = flatten(msg.get("content"))
            if not content.strip():
                continue
            ts = d.get("timestamp", "") or ""
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            if role == "user":
                n_user += 1
            else:
                n_asst += 1
            rows.append((session_id, len(rows), ts, role, content,
                         d.get("parentUuid"), d.get("requestId")))

    # replace this session's rows wholesale — restartable, never partial
    db.execute("DELETE FROM conversation_archive WHERE session_id=?", (session_id,))
    db.executemany(
        "INSERT INTO conversation_archive "
        "(session_id, message_num, timestamp, role, content, parent_uuid, prompt_id) "
        "VALUES (?,?,?,?,?,?,?)", rows)
    db.execute("DELETE FROM conversation_metadata WHERE session_id=?", (session_id,))
    db.execute(
        "INSERT INTO conversation_metadata (session_id, started, ended, total_messages, "
        "total_user_messages, total_assistant_messages, status, notes) VALUES (?,?,?,?,?,?,?,?)",
        (session_id, first_ts, last_ts, len(rows), n_user, n_asst, "complete",
         f"imported in full from {os.path.basename(path)} on "
         f"{datetime.date.today().isoformat()} — every message in the export"))
    db.commit()
    return session_id, len(rows), n_user, n_asst


def cmd_import(all_sessions=False):
    db = con(); ensure(db)
    files = sorted(glob.glob(os.path.join(EXPORTS, "session_*.jsonl")))
    if all_sessions:
        files += sorted(glob.glob(os.path.join(LIVE_SESSIONS, "**", "*.jsonl"),
                                  recursive=True))
    if not files:
        print("no session exports found"); return

    seen, done, skipped = set(), 0, 0
    for p in files:
        sid = os.path.basename(p).replace("session_", "").replace(".jsonl", "")
        if sid in seen:      # ~/Archive copy and the live original are the same session
            continue
        seen.add(sid)
        try:
            sid, total, nu, na = import_jsonl(p, db)
        except Exception as e:
            print(f"  SKIPPED {os.path.basename(p)}: {e}")
            skipped += 1
            continue
        if total == 0:
            continue
        done += 1
        print(f"{sid[:8]}  {total:>6} messages  ({nu:>5} Saba, {na:>5} Scribe)")

    grand = db.execute("SELECT COUNT(*) FROM conversation_archive").fetchone()[0]
    saba = db.execute("SELECT COUNT(*) FROM conversation_archive WHERE role='user'").fetchone()[0]
    sess = db.execute("SELECT COUNT(*) FROM conversation_metadata").fetchone()[0]
    print(f"\nSir Archive now holds {grand:,} messages ({saba:,} of them Saba's own) "
          f"across {sess} sessions" + (f" — {skipped} unreadable" if skipped else ""))


def cmd_list():
    db = con(); ensure(db)
    for r in db.execute("SELECT * FROM conversation_metadata ORDER BY started"):
        print(f"{r['session_id']}  {str(r['started'])[:10]} .. {str(r['ended'])[:10]}  "
              f"{r['total_messages']:>6} messages ({r['total_user_messages']} Saba)  [{r['status']}]")


def cmd_find(term, saba_only=False, limit=40):
    db = con(); ensure(db)
    q = ("SELECT session_id, message_num, timestamp, role, content FROM conversation_archive "
         "WHERE content LIKE ?")
    args = [f"%{term}%"]
    if saba_only:
        q += " AND role='user'"
    q += " ORDER BY timestamp LIMIT ?"
    args.append(limit)
    hits = db.execute(q, args).fetchall()
    if not hits:
        print(f'nothing found for "{term}"'); return
    print(f'{len(hits)} hit(s) for "{term}"\n')
    for h in hits:
        who = "SABA " if h["role"] == "user" else "scribe"
        text = " ".join(h["content"].split())
        i = text.lower().find(term.lower())
        start = max(0, i - 90)
        snip = ("…" if start else "") + text[start:i + len(term) + 150] + "…"
        print(f"[{str(h['timestamp'])[:19]}] {who} (msg {h['message_num']})")
        print(f"   {snip}\n")


def cmd_show(session_id, n=40):
    db = con(); ensure(db)
    for r in db.execute(
            "SELECT message_num, timestamp, role, content FROM conversation_archive "
            "WHERE session_id LIKE ? ORDER BY message_num LIMIT ?", (session_id + "%", n)):
        who = "SABA " if r["role"] == "user" else "scribe"
        print(f"[{str(r['timestamp'])[:19]}] {who}: {' '.join(r['content'].split())[:300]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "import":
        cmd_import(all_sessions="--all" in sys.argv)
    elif cmd == "list":
        cmd_list()
    elif cmd == "find":
        term = sys.argv[2]
        cmd_find(term, saba_only="--saba" in sys.argv)
    elif cmd == "show":
        cmd_show(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 40)
    else:
        print(__doc__)
