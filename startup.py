#!/usr/bin/env python3
"""
Startup loader for Saba-Code operations.
Reads CLAUDE.md (orientation) and CURRENT_STATE.md (checkpoint).
Reports concise startup state.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
CURRENT_STATE_MD = PROJECT_ROOT / "CURRENT_STATE.md"

def read_file(path):
    """Read a markdown file and return its content."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return None

def extract_startup_summary(current_state_content):
    """Extract the operational checkpoint from CURRENT_STATE.md."""
    if not current_state_content:
        return "CURRENT_STATE.md not found"

    lines = current_state_content.split('\n')

    # Extract key sections
    done = ""
    in_progress = ""
    forbidden = ""
    next_step = ""

    section = None
    for line in lines:
        if line.startswith("## What Is Done"):
            section = "done"
        elif line.startswith("## What Is In Progress"):
            section = "in_progress"
        elif line.startswith("## What Must Not Be Touched"):
            section = "forbidden"
        elif line.startswith("## Next Exact Step"):
            section = "next"
        elif line.startswith("## "):
            section = None
        elif section and line.strip() and not line.startswith("**"):
            if section == "done":
                done = line.strip()
            elif section == "in_progress":
                in_progress = line.strip()
            elif section == "forbidden":
                forbidden = line.strip()
            elif section == "next":
                next_step = line.strip()

    return {
        "done": done,
        "in_progress": in_progress,
        "forbidden": forbidden,
        "next": next_step
    }

def startup():
    """Run startup sequence."""
    print("\n" + "="*70)
    print("STARTUP")
    print("="*70)

    # Read files
    claude_content = read_file(CLAUDE_MD)
    current_state_content = read_file(CURRENT_STATE_MD)

    if not claude_content:
        print("ERROR: CLAUDE.md not found")
        sys.exit(1)

    # Extract checkpoint
    checkpoint = extract_startup_summary(current_state_content)

    # Report startup state
    print("\nOperator environment loaded.")
    print(f"Project: Saba-Code")
    print(f"Archive: ~/Archive/Sermons.db (protected)")
    print()

    if checkpoint.get("done"):
        print(f"✓ Complete: {checkpoint['done']}")

    if checkpoint.get("in_progress"):
        print(f"→ In progress: {checkpoint['in_progress']}")
    else:
        print("→ No in-progress work")

    if checkpoint.get("forbidden"):
        print(f"🚫 Protected: {checkpoint['forbidden']}")

    if checkpoint.get("next"):
        print(f"Next: {checkpoint['next']}")

    print("\nReady.\n")
    print("="*70)
    print()

if __name__ == "__main__":
    startup()
