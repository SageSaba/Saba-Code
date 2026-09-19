#!/usr/bin/env python3
"""status.py — what is up, what is working, what is safe.

Saba's one-look answer to "where does everything stand right now."
READS ONLY. It opens nothing for writing, starts nothing, stops nothing.

    ./status.py
"""
import os, re, sqlite3, subprocess, time
from pathlib import Path

HOME = Path.home()
BIN = "/opt/homebrew/bin"

SERVERS = {
    8765: "the Archive Viewer — the approved screen",
    8766: "the AI connector — evidence, read-only",
    8767: "Ask My Memory",
    8768: "Ask the Archive",
    8792: "the Toolbox — his channel",
}

BOOKS = [
    (HOME / "Archive/Sermons.db", "the raw book — never written"),
    (HOME / "Archive/Archive_Suggestions.db", "the ruling layer"),
    (HOME / "Archive/SabaWords.db", "his own words, line by line"),
]

WORKERS = [
    ("whisper-cli", "reading a recording"),
    ("retranscribe_service.sh", "the reading job"),
    ("yt-dlp", "pulling from YouTube"),
    ("ffmpeg", "handling audio or video"),
    ("caffeinate", "holding the Mac awake"),
]


def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except Exception:
        return ""


def head(t):
    print(f"\n\033[1m{t}\033[0m")


def ago(seconds):
    m, h = seconds / 60, seconds / 3600
    if m < 60:
        return f"{m:.0f} min"
    if h < 48:
        return f"{h:.1f} h"
    return f"{h/24:.0f} days"


def servers():
    head("THE SERVERS")
    live = sh("lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null")
    for port, what in SERVERS.items():
        row = [l for l in live.splitlines() if f":{port} " in l or l.endswith(f":{port}")]
        if not row:
            print(f"  \033[31m✗\033[0m  {port}  DOWN            {what}")
            continue
        pid = row[0].split()[1]
        addr = row[0].split()[8]
        up = sh(f"ps -o etime= -p {pid}").strip()
        reach = "the whole network" if addr.startswith("*") else "this Mac only"
        print(f"  \033[32m●\033[0m  {port}  up {up:<12} {what}")
        if addr.startswith("*"):
            print(f"      \033[33m↳ open to {reach}\033[0m")


def workers():
    head("WHAT IS WORKING")
    found = False
    for name, what in WORKERS:
        out = sh(f"pgrep -f '{name}' | head -4")
        for pid in [p for p in out.splitlines() if p.strip()]:
            args = sh(f"ps -o args= -p {pid}")
            # a shell that merely mentions the job is not the job
            if "shell-snapshots" in args or args.startswith(("/bin/zsh -c", "/bin/bash -c")):
                continue
            args = args[:78]
            el = sh(f"ps -o etime= -p {pid}").strip()
            cpu = sh(f"ps -o pcpu= -p {pid}").strip()
            print(f"  \033[36m▶\033[0m  {what:<24} {el:>10}  {cpu:>5}% cpu")
            print(f"      {args}")
            found = True
    if not found:
        print("  nothing running — the house is quiet")


def books():
    head("THE BOOKS")
    for path, what in BOOKS:
        if not path.exists():
            print(f"  \033[31m✗\033[0m  {path.name}  NOT FOUND")
            continue
        size = path.stat().st_size / 1e9
        touched = ago(time.time() - path.stat().st_mtime)
        try:
            c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            tables = {r[0] for r in c.execute(
                "select name from sqlite_master where type='table'")}
            bits = []
            for t, label in (("Services", "services"), ("RawSegments", "lines"),
                             ("people", "people"), ("Parts", "parts")):
                if t in tables:
                    bits.append(f"{c.execute(f'select count(*) from {t}').fetchone()[0]:,} {label}")
            c.close()
            counts = " · ".join(bits)
        except Exception as e:
            counts = f"could not read ({e})"
        print(f"  {path.name:<28} {size:6.2f} GB   last written {touched} ago")
        print(f"      {what} — {counts}")


def backups():
    head("THE LAST BACKUPS")
    acasis = Path("/Volumes/ACASIS/Archive Backups")
    if acasis.is_dir():
        rows = sorted([d for d in acasis.iterdir() if d.is_dir()],
                      key=lambda d: d.stat().st_mtime, reverse=True)[:3]
        for d in rows:
            print(f"  ACASIS   {d.name:<38} {ago(time.time()-d.stat().st_mtime)} ago")
    else:
        print("  \033[33mACASIS is not mounted — the off-machine copy is out of reach\033[0m")
    local = sorted(HOME.glob("Archive/*_*.db"), key=lambda p: p.stat().st_mtime,
                   reverse=True)[:3]
    for p in local:
        print(f"  local    {p.name:<38} {ago(time.time()-p.stat().st_mtime)} ago")


def drives():
    head("THE DRIVES")
    for v in sorted(Path("/Volumes").iterdir()):
        try:
            st = os.statvfs(v)
            free = st.f_bavail * st.f_frsize / 1e12
            total = st.f_blocks * st.f_frsize / 1e12
            print(f"  {v.name:<16} {total:5.1f} TB   {free:5.1f} TB free")
        except Exception:
            print(f"  {v.name:<16} (could not read)")


def mic():
    head("THE TOOLBOX EAR")
    out = sh("curl -s --max-time 3 -X POST http://127.0.0.1:8792/mic/state")
    if '"live": true' in out:
        print("  \033[31m●\033[0m  the microphone is LIVE")
    elif '"live": false' in out:
        print("  ○  the microphone is off")
    else:
        print("  the Toolbox did not answer")


if __name__ == "__main__":
    print(f"\n\033[1mTHE HOUSE — {time.strftime('%A %d %B %Y, %H:%M')}\033[0m")
    servers(); workers(); books(); backups(); drives(); mic()
    print()
