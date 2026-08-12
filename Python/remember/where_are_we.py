#!/usr/bin/env python3
"""Read-only 'Where Are We?' view over RawSegments.db.

Deterministic keyword/pattern lookups only — no AI, no inference,
no writes. Every row shown is quoted with its ID and timestamp so
it can be checked against the database directly.
"""
import os
import re
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RawSegments.db")

GOAL_PATTERNS = [
    r"\btrying to\b",
    r"\bwant to\b",
    r"\bwe want\b",
    r"\bthe goal\b",
    r"\bthe plan\b",
    r"\bthe purpose\b",
    r"\bnext step\b",
    r"\blarger purpose\b",
    r"\bthe point\b",
]

APPROVAL_PATTERNS = [
    r"\bengage\b",
    r"\bapproved\b",
    r"\bgo ahead\b",
    r"\bproceed\b",
    r"\bdo it\b",
    r"\bbuild it\b",
    r"\bship it\b",
    r"\byes[.!, ]",
    r"^yes$",
    r"\bthat works\b",
]

PROBLEM_PATTERNS = [
    r"\bno change\b",
    r"\bnot working\b",
    r"\bdoesn'?t work\b",
    r"\bdidn'?t work\b",
    r"\bbroken\b",
    r"\bwrong\b",
    r"\bnope\b",
    r"\bfailed\b",
    r"\berror\b",
    r"\bfix\b",
]

RECENT_LIMIT = 10


def load_rows():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    uri = f"file:{DB_PATH}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    try:
        rows = db.execute(
            "SELECT ID, timestamp, speaker, text FROM RawSegments ORDER BY ID"
        ).fetchall()
    finally:
        db.close()
    return rows


def match_any(text, patterns):
    for p in patterns:
        if re.search(p, text, flags=re.IGNORECASE | re.MULTILINE):
            return True
    return False


def preview(text, width=200):
    t = text.strip().replace("\n", " ")
    if len(t) <= width:
        return t
    return t[:width].rstrip() + "…"


def print_header(title):
    print()
    print(title)
    print("-" * len(title))


def print_row(row):
    rid, ts, speaker, text = row
    print(f"[{rid}] {ts}  {speaker}: {preview(text)}")


def print_none():
    print("(none found)")


def section_stated_goal(rows):
    print_header("Stated goal — Saba turns matching goal phrases")
    matches = [r for r in rows if r[2] == "Saba" and match_any(r[3], GOAL_PATTERNS)]
    if not matches:
        print_none()
        return
    for r in matches:
        print_row(r)


def section_recent_turns(rows):
    print_header(f"Recent turns — last {RECENT_LIMIT} rows")
    for r in rows[-RECENT_LIMIT:]:
        print_row(r)


def section_explicit_approvals(rows):
    print_header("Explicit approvals — Saba turns matching approval phrases")
    matches = [r for r in rows if r[2] == "Saba" and match_any(r[3], APPROVAL_PATTERNS)]
    if not matches:
        print_none()
        return
    for r in matches:
        print_row(r)


def section_problem_signals(rows):
    print_header("Explicit problem signals — Saba turns matching problem phrases")
    matches = [r for r in rows if r[2] == "Saba" and match_any(r[3], PROBLEM_PATTERNS)]
    if not matches:
        print_none()
        return
    for r in matches:
        print_row(r)


def section_questions(rows):
    print_header("Explicit questions from Saba — turns containing '?'")
    matches = [r for r in rows if r[2] == "Saba" and "?" in r[3]]
    if not matches:
        print_none()
        return
    for r in matches:
        print_row(r)


def section_latest_exchange(rows):
    print_header("Latest exchange — last Saba turn and last Claude turn")
    last_saba = next((r for r in reversed(rows) if r[2] == "Saba"), None)
    last_claude = next((r for r in reversed(rows) if r[2] == "Claude"), None)
    if last_saba:
        print_row(last_saba)
    else:
        print("Saba: (none)")
    if last_claude:
        print_row(last_claude)
    else:
        print("Claude: (none)")


def main():
    rows = load_rows()
    total = len(rows)
    saba_count = sum(1 for r in rows if r[2] == "Saba")
    claude_count = sum(1 for r in rows if r[2] == "Claude")
    first_ts = rows[0][1] if rows else "(empty)"
    last_ts = rows[-1][1] if rows else "(empty)"

    print(f"RawSegments.db — {total} rows ({saba_count} Saba, {claude_count} Claude)")
    print(f"Span: {first_ts}  →  {last_ts}")
    print(f"Source: {DB_PATH}")

    section_stated_goal(rows)
    section_recent_turns(rows)
    section_explicit_approvals(rows)
    section_problem_signals(rows)
    section_questions(rows)
    section_latest_exchange(rows)


if __name__ == "__main__":
    main()
