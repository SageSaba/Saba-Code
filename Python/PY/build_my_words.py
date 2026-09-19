#!/usr/bin/env python3
"""build_my_words.py — Saba's own words, pulled out of Claude Code's session
transcripts (~/.claude/projects/*/*.jsonl) and into one searchable database.

The transcripts already exist as a byproduct of every session; this only
reads them. Nothing here is line-by-line like RawSegments — each turn is
kept whole, as a memo-field block of text, exactly as it was said.

Only genuine typed turns are kept: human-authored user messages (not tool
results, not slash-command plumbing, not injected skill text) and the
assistant's visible reply text (not internal thinking, not tool calls).

Usage:
  build_my_words.py            build/refresh MyWords.db from every session
  build_my_words.py --project NAME   limit to one project folder
"""
import argparse
import json
import sqlite3
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
DB_PATH = Path.home() / "Archive" / "MyWords.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY,
    project TEXT NOT NULL,
    session_id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    timestamp TEXT,
    speaker TEXT NOT NULL,   -- 'saba' or 'scribe'
    text TEXT NOT NULL,      -- the memo field: the whole turn, as said
    UNIQUE(session_id, seq, speaker)
);
CREATE INDEX IF NOT EXISTS idx_turns_project ON turns(project);
CREATE INDEX IF NOT EXISTS idx_turns_time ON turns(timestamp);
"""


def human_text(entry):
    """A genuine typed message from Saba, or None."""
    if entry.get("type") != "user":
        return None
    if entry.get("origin", {}).get("kind") != "human":
        return None
    content = entry.get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        return None
    return content.strip()


def scribe_text(entry):
    """The visible reply text Saba actually saw, or None."""
    if entry.get("type") != "assistant":
        return None
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return None
    parts = [b.get("text", "") for b in content
             if isinstance(b, dict) and b.get("type") == "text"]
    text = "\n".join(p for p in parts if p.strip()).strip()
    return text or None


def each_session_file(only_project=None):
    for proj_dir in sorted(PROJECTS.iterdir()):
        if not proj_dir.is_dir():
            continue
        if only_project and proj_dir.name != only_project:
            continue
        for jsonl in sorted(proj_dir.glob("*.jsonl")):
            yield proj_dir.name, jsonl


def load_session(path):
    rows = []
    seq = 0
    try:
        lines = path.read_text(errors="replace").splitlines()
    except Exception:
        return rows
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except Exception:
            continue
        ts = entry.get("timestamp")
        h = human_text(entry)
        if h:
            rows.append((seq, ts, "saba", h))
            seq += 1
            continue
        s = scribe_text(entry)
        if s:
            rows.append((seq, ts, "scribe", s))
            seq += 1
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    args = ap.parse_args()

    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)

    sessions_seen = 0
    turns_added = 0
    for project, jsonl in each_session_file(args.project):
        session_id = jsonl.stem
        rows = load_session(jsonl)
        if not rows:
            continue
        sessions_seen += 1
        for seq, ts, speaker, text in rows:
            cur = con.execute(
                "INSERT OR IGNORE INTO turns (project, session_id, seq, timestamp, speaker, text) "
                "VALUES (?,?,?,?,?,?)",
                (project, session_id, seq, ts, speaker, text),
            )
            turns_added += cur.rowcount
    con.commit()

    total = con.execute("SELECT COUNT(*) FROM turns").fetchone()[0]
    saba_total = con.execute("SELECT COUNT(*) FROM turns WHERE speaker='saba'").fetchone()[0]
    con.close()

    print(f"sessions read: {sessions_seen}")
    print(f"turns added this run: {turns_added}")
    print(f"turns in database: {total}  (saba: {saba_total}, scribe: {total - saba_total})")
    print(f"database: {DB_PATH}")


if __name__ == "__main__":
    main()
