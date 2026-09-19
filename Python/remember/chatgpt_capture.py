#!/usr/bin/env python3
"""Manual bridge: append one ChatGPT-session turn to RawSegments.db.

Usage:
    chatgpt_capture.py Saba "text of what Saba said"
    chatgpt_capture.py ChatGPT "text of ChatGPT's reply"
    chatgpt_capture.py Saba -        # read text from stdin

Reuses write_segment.insert() so the row shape, timestamp format, and
dedup rule are identical to the Claude hook path. Does not touch hooks,
schema, or the Claude capture. Speaker is restricted to {Saba, ChatGPT}
so this bridge cannot silently produce Claude rows.
"""
import sys
from write_segment import insert

ALLOWED = {"Saba", "ChatGPT"}


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(
            "usage: chatgpt_capture.py {Saba|ChatGPT} \"text\"   (or - to read stdin)\n"
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
