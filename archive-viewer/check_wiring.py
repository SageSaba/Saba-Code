#!/usr/bin/env python3
"""Wiring check — run this ON THE MAC to see what's actually connected.

Checks every local dependency the archive services assume: the database,
the suggestions db, Ollama (and its models), the claude CLI (and sign-in),
and the mounted Data volume. Prints a plain pass/fail report — nothing is
written or changed.

Run:  python3 check_wiring.py
"""
import json
import os
import shutil
import sqlite3
import subprocess
import urllib.request

DB_PATH = "/Users/saba/Archive/Sermons.db"
SUG_DB = "/Users/saba/Archive/Archive_Suggestions.db"
DATA_VOLUME = "/Volumes/Data"
OLLAMA_URL = "http://127.0.0.1:11434"
NEEDED_MODELS = ["nomic-embed-text", "qwen3:4b"]

PASS, FAIL, WARN = "✓", "✗", "!"
results = []


def check(label, ok, detail="", warn=False):
    mark = WARN if (warn and not ok) else (PASS if ok else FAIL)
    results.append((mark, label, detail))
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))


def section(title):
    print(f"\n{title}")


def main():
    section("Filesystem")
    check("Sermons.db exists", os.path.exists(DB_PATH), DB_PATH)
    if os.path.exists(DB_PATH):
        try:
            con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
            n = con.execute("SELECT COUNT(*) FROM Services").fetchone()[0]
            con.close()
            check("Sermons.db readable, has Services", True, f"{n} services")
        except sqlite3.Error as e:
            check("Sermons.db readable", False, str(e))

    check("Archive_Suggestions.db exists", os.path.exists(SUG_DB), SUG_DB,
          warn=True)
    check("/Volumes/Data mounted", os.path.exists(DATA_VOLUME), DATA_VOLUME,
          warn=True)

    section("Ollama")
    try:
        with urllib.request.urlopen(OLLAMA_URL, timeout=3) as r:
            up = r.status == 200
    except Exception as e:
        up = False
    check("Ollama reachable", up, OLLAMA_URL)
    if up:
        try:
            with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=5) as r:
                names = {m["name"] for m in json.load(r).get("models", [])}
            for model in NEEDED_MODELS:
                have = any(model in n for n in names)
                check(f"model {model} pulled", have,
                      "" if have else "run: ollama pull " + model, warn=True)
        except Exception as e:
            check("could list Ollama models", False, str(e), warn=True)

    section("Claude CLI")
    claude_bin = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    found = os.path.exists(claude_bin) or shutil.which("claude") is not None
    check("claude command found", found, claude_bin)
    if found:
        try:
            run = subprocess.run([claude_bin, "-p", "--output-format", "text",
                                  "say OK and nothing else"],
                                 capture_output=True, text=True, timeout=30)
            signed_in = run.returncode == 0
            check("claude signed in / answers", signed_in,
                  (run.stdout or run.stderr or "").strip()[:200])
        except Exception as e:
            check("claude signed in / answers", False, str(e))
    key = os.path.expanduser("~/.anthropic_key")
    check("~/.anthropic_key present (fallback for non-interactive launch)",
          os.path.exists(key), warn=True)

    section("Ports (services already running?)")
    for port, name in [(8765, "Archive Viewer"), (8766, "Connector"),
                       (8767, "Transcript Exporter"), (8768, "Ask the Archive")]:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=2):
                live = True
        except urllib.error.HTTPError:
            live = True   # server answered, even with an error status
        except Exception:
            live = False
        check(f"port {port} ({name})", live, warn=True)

    section("Summary")
    fails = [r for r in results if r[0] == FAIL]
    warns = [r for r in results if r[0] == WARN]
    if not fails and not warns:
        print("  Everything checked is wired correctly.")
    else:
        if fails:
            print(f"  {len(fails)} hard failure(s) — these block the services entirely:")
            for _, label, detail in fails:
                print(f"    - {label}" + (f" ({detail})" if detail else ""))
        if warns:
            print(f"  {len(warns)} warning(s) — optional but affect features:")
            for _, label, detail in warns:
                print(f"    - {label}" + (f" ({detail})" if detail else ""))


if __name__ == "__main__":
    main()
