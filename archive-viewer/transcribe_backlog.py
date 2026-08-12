#!/usr/bin/env python3
"""The backlog: whisper reads every service that has media on disk and no words.

Found 2026-08-10 — 427 services hold zero transcript lines; 259 of them have a
media file present at their own media_path. This reads those 259 and no others.

Method is the proven one from bring_wog_home.py, unchanged:
  ffmpeg -> 16k mono wav -> whisper-cli -> timed .txt BESIDE THE MEDIA
  (the folder law) -> RawSegments lines.

What this tool will NOT do, by construction:
  - never creates a Services row (every row here already exists)
  - never edits a Services row (media_path, title, date, giver all untouched)
  - never writes into a service that already holds lines — re-checked inside
    the transaction, immediately before insert, not just at queue time
  - never deletes anything, ever

Restartable at every step: an existing .txt is not re-whispered, and a service
that gained lines since the queue was built is skipped. Safe to kill and rerun.
Waits politely while another whisper-cli is running so it never fights the
machine. Run under `taskpolicy -c background` to keep the Mac usable.
"""
import datetime
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time

DB = "/Users/saba/Archive/Sermons.db"
MODEL = "/Users/saba/ggml-large-v3-turbo.bin"
WORK = "/Volumes/Data/Video Archive/whisper_work"
LOG = "/Volumes/Data/Video Archive/backlog.log"
BACKUP_DIR = "/Volumes/Data/Video Archive/SQL Files/backups"


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def whisper_running():
    return subprocess.run(["pgrep", "-x", "whisper-cli"],
                          capture_output=True).returncode == 0


def whisper_to_txt(video, txt):
    os.makedirs(WORK, exist_ok=True)
    stem = os.path.splitext(os.path.basename(video))[0]
    wav = os.path.join(WORK, stem + ".wav")
    js = os.path.join(WORK, stem)
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video,
                        "-ar", "16000", "-ac", "1", wav], check=True)
        while whisper_running():
            time.sleep(60)
        subprocess.run(["whisper-cli", "-m", MODEL, "-f", wav,
                        "-oj", "-of", js], check=True,
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        data = json.load(open(js + ".json"))
        with open(txt, "w") as f:
            for seg in data.get("transcription", []):
                a = seg["timestamps"]["from"].replace(",", ".")
                b = seg["timestamps"]["to"].replace(",", ".")
                t = seg.get("text", "").strip()
                if t:
                    f.write(f"[{a} --> {b}]  {t}\n")
    finally:
        for f in (wav, js + ".json"):
            if os.path.exists(f):
                os.remove(f)


def parse_txt(path):
    out = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = re.match(r"\[(\d\d:\d\d:\d\d\.\d{3}) --> "
                     r"(\d\d:\d\d:\d\d\.\d{3})\]\s*(.*)", line)
        if m and m.group(3).strip():
            out.append((m.group(1), m.group(2), m.group(3).strip()))
    return out


def main():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bk = os.path.join(
        BACKUP_DIR,
        f"Sermons_{datetime.datetime.now():%Y%m%d_%H%M%S}_before_backlog.db")
    shutil.copy(DB, bk)
    log(f"backup: {os.path.basename(bk)}")

    db = sqlite3.connect(DB)
    queue = [
        (i, d, t, m) for i, d, t, m in db.execute(
            """SELECT s.ID, s.preach_date, s.title, s.media_path
                 FROM Services s
                WHERE s.media_path IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM RawSegments r
                                   WHERE r.service_id = s.ID)
                ORDER BY s.ID""")
        if m and os.path.exists(m)
    ]
    log(f"{len(queue)} services with media and no words")

    done = 0
    for sid, date, title, media in queue:
        stem = os.path.splitext(os.path.basename(media))[0]
        txt = os.path.splitext(media)[0] + ".txt"
        try:
            # A zero-byte .txt is a failed earlier read, not a finished one.
            # Treating "file exists" as "already heard" silently skipped 28
            # services on the first pass — found 2026-08-10, fixed here.
            if not os.path.exists(txt) or os.path.getsize(txt) == 0:
                t0 = time.time()
                log(f"svc {sid}: whisper reading {stem}…")
                whisper_to_txt(media, txt)
                log(f"svc {sid}: heard ({(time.time() - t0) / 60:.0f} min)")

            lines = parse_txt(txt)
            if not lines:
                log(f"svc {sid}: no usable speech — left alone")
                continue

            # The law, enforced at the last possible moment: if this service
            # gained lines while we were reading, we do not touch it.
            still_empty = db.execute(
                "SELECT NOT EXISTS (SELECT 1 FROM RawSegments "
                "WHERE service_id=?)", (sid,)).fetchone()[0]
            if not still_empty:
                log(f"svc {sid}: gained lines meanwhile — skipped, untouched")
                continue

            db.executemany(
                "INSERT INTO RawSegments (service_id, start, end, text) "
                "VALUES (?,?,?,?)",
                [(sid, s, e, t) for s, e, t in lines])
            db.commit()
            done += 1
            log(f"svc {sid}: home — {date}, {len(lines)} lines "
                f"({done}/{len(queue)})")
        except Exception as e:
            log(f"svc {sid}: FAILED — {e}")

    log(f"backlog pass complete — {done} services gained words "
        f"(anything that failed is named above)")
    db.close()


if __name__ == "__main__":
    main()
