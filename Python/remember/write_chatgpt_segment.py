#!/usr/bin/env python3
"""Writer for the ChatGPT-side store: ChatGPT_RawSegments.db.

Purpose: give the ChatGPT side one clock format that matches the Claude side
(write_segment.py) so a plain ORDER BY timestamp merges both stores correctly.

Timestamp format: YYYY-MM-DD HH:MM:SS in local time, no T separator,
no UTC offset — identical to write_segment.insert().

Usage:
    write_chatgpt_segment.py Saba    "what Saba said to ChatGPT"
    write_chatgpt_segment.py ChatGPT "what ChatGPT said back"
    write_chatgpt_segment.py Saba -            # text from stdin

Does not touch RawSegments.db. Does not rewrite existing rows.
Speaker restricted to {Saba, ChatGPT}; source is always 'ChatGPT'.
"""
import datetime
import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ChatGPT_RawSegments.db")
ALLOWED = {"Saba", "ChatGPT"}


def insert(speaker, text, source="ChatGPT"):
    text = (text or "").strip()
    if not text:
        return
    db = sqlite3.connect(DB_PATH)
    dup = db.execute(
        "SELECT 1 FROM RawSegments WHERE speaker=? AND text=? ORDER BY ID DESC LIMIT 1",
        (speaker, text),
    ).fetchone()
    if dup:
        db.close()
        return
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "INSERT INTO RawSegments (timestamp, speaker, text, source) VALUES (?, ?, ?, ?)",
        (now, speaker, text, source),
    )
    db.commit()
    db.close()


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            "usage: write_chatgpt_segment.py {Saba|ChatGPT} \"text\"   (or - to read stdin)\n"
        )
        sys.exit(2)
    speaker = sys.argv[1]
    if speaker not in ALLOWED:
        sys.stderr.write(f"speaker must be one of {sorted(ALLOWED)}\n")
        sys.exit(2)
    text = sys.argv[2]
    if text == "-":
        text = sys.stdin.read()
    insert(speaker, text)


if __name__ == "__main__":
    main()
