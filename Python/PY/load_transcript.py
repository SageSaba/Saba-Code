#!/usr/bin/env python3
"""load_transcript.py — put a read transcript into the book, additively.

Only fills services that hold NO lines. Never updates, never deletes, never
touches a line that already exists. If the service already has words, it says so
and does nothing — bringing a BETTER transcript over an existing one is a
different ruling and is not this tool's business.

    ./load_transcript.py <service_id> [...]
"""
import json, sqlite3, sys
from pathlib import Path

DB = Path.home() / "Archive/Sermons.db"
OUT = Path.home() / "Desktop/Archive Viewer/transcripts_new"

def clock(t):
    return t.replace(",", ".")

for sid in sys.argv[1:]:
    sid = int(sid)
    js = sorted(OUT.glob(f"svc{sid}_*.json"))
    if not js:
        print(f"svc {sid}: no transcript file — skipped"); continue
    c = sqlite3.connect(DB)
    have = c.execute("select count(*) from RawSegments where service_id=?", (sid,)).fetchone()[0]
    if have:
        print(f"svc {sid}: already holds {have:,} lines — LEFT ALONE"); c.close(); continue
    rows = json.loads(js[0].read_text())["transcription"]
    data = [(sid, clock(r["timestamps"]["from"]), clock(r["timestamps"]["to"]),
             r["text"].strip()) for r in rows if r["text"].strip()]
    c.executemany("insert into RawSegments (service_id,start,end,text) values (?,?,?,?)", data)
    c.commit()
    now = c.execute("select count(*) from RawSegments where service_id=?", (sid,)).fetchone()[0]
    title = c.execute("select title from Services where ID=?", (sid,)).fetchone()[0]
    print(f"svc {sid}: {now:,} lines written — {title}")
    c.close()
