#!/usr/bin/env python3
"""Hook target: appends one real turn to RawSegments.db.
Called by Claude Code's UserPromptSubmit and Stop hooks — never by Claude itself.

UserPromptSubmit gives us the user's prompt text directly on stdin.
Stop does not reliably carry Claude's final response text, so for the
Claude side we read the session's own transcript file (already written
to disk by the time Stop fires) and take the last assistant text turn.
"""
import json
import sys
import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RawSegments.db")


def flatten_text(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text", "").strip()
                if t:
                    parts.append(t)
        return "\n\n".join(parts)
    return ""


def is_real_human_message(obj):
    if obj.get("isMeta"):
        return False
    if obj.get("origin", {}).get("kind") != "human":
        return False
    if obj.get("sourceToolUseID"):
        return False
    return True


def insert(speaker, text):
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
        "INSERT INTO RawSegments (timestamp, speaker, text) VALUES (?, ?, ?)",
        (now, speaker, text),
    )
    db.commit()
    db.close()


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    event = payload.get("hook_event_name", "")

    if event == "UserPromptSubmit":
        text = payload.get("prompt", "")
        insert("Saba", text)
        return

    if event == "Stop":
        transcript_path = payload.get("transcript_path")
        if not transcript_path or not os.path.exists(transcript_path):
            return
        last_text, last_ts = None, None
        with open(transcript_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "assistant":
                    continue
                text = flatten_text(obj.get("message", {}).get("content"))
                if text:
                    last_text = text
                    last_ts = obj.get("timestamp")
        if last_text:
            insert("Claude", last_text)
        return


if __name__ == "__main__":
    main()
