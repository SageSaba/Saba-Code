#!/usr/bin/env python3
"""Bring the Without Walls teachings home: one Services row per
downloaded video (banner XWalls by rule), and its YouTube .srt timed
transcript into RawSegments as spoken-line base — real clocks from
birth, no speaker claimed (evidence fills names, never blankets).

Waits politely for yt-dlp to finish, then imports whatever landed in
/Volumes/Data/Video Archive/Without Walls/. Restartable: a video whose
date+title row already exists is skipped. Backup taken at start.

Log: prints to its own nohup file (xwalls_import.log beside videos).
"""
import os, re, sqlite3, subprocess, time, datetime, shutil

DB = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"
FOLDER = "/Volumes/Data/Video Archive/Without Walls"
LOG = os.path.join(FOLDER, "xwalls_import.log")


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def ytdlp_running():
    return subprocess.run(["pgrep", "-f", "yt-dlp"],
                          capture_output=True).returncode == 0


def parse_srt(path):
    """-> [(start 'HH:MM:SS.mmm', end, text)] with duplicates folded."""
    raw = open(path, encoding="utf-8", errors="ignore").read()
    out = []
    for block in re.split(r"\n\s*\n", raw):
        m = re.search(r"(\d\d:\d\d:\d\d)[,.](\d{3})\s*-->\s*"
                      r"(\d\d:\d\d:\d\d)[,.](\d{3})", block)
        if not m:
            continue
        start = f"{m.group(1)}.{m.group(2)}"
        end = f"{m.group(3)}.{m.group(4)}"
        text = " ".join(
            l.strip() for l in block.splitlines()
            if l.strip() and "-->" not in l and not l.strip().isdigit())
        text = re.sub(r"<[^>]+>", "", text).strip()
        # auto-caption srt repeats lines as they scroll; keep first look
        if text and (not out or out[-1][2] != text):
            out.append((start, end, text))
    return out


def main():
    while ytdlp_running():
        time.sleep(120)
    log("yt-dlp finished — importing Without Walls")
    bk = ("/Volumes/Data/Video Archive/SQL Files/backups/"
          f"Sermons_{datetime.datetime.now():%Y%m%d_%H%M%S}"
          "_before_xwalls_import.db")
    shutil.copy(DB, bk)
    log(f"backup: {os.path.basename(bk)}")

    db = sqlite3.connect(DB)
    existing = {(r[0], r[1]) for r in db.execute(
        "SELECT preach_date, title FROM Services WHERE org='XWalls'")}
    added = lines_total = skipped = 0
    for name in sorted(os.listdir(FOLDER)):
        m = re.match(r"^(\d{4})_(\d{2})_(\d{2}) (.+)\.(mp4|mkv|webm)$", name)
        if not m:
            continue
        date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        title = m.group(4).replace("_", " ").strip()
        if (date, title) in existing:
            skipped += 1
            continue
        path = os.path.join(FOLDER, name)
        srt = os.path.join(FOLDER, name.rsplit(".", 1)[0] + ".en.srt")
        cur = db.execute(
            "INSERT INTO Services (preach_date, title, media_path, org, "
            "org_source) VALUES (?,?,?,?,'rule')",
            (date, title, path, "XWalls"))
        sid = cur.lastrowid
        n = 0
        if os.path.exists(srt):
            rows = [(sid, s, e, t) for s, e, t in parse_srt(srt)]
            db.executemany(
                "INSERT INTO RawSegments (service_id, start, end, text) "
                "VALUES (?,?,?,?)", rows)
            n = len(rows)
        db.commit()
        lines_total += n
        added += 1
        log(f"{date} \"{title}\": service {sid}, {n} timed lines")
    log(f"done — {added} teachings in, {lines_total} lines, "
        f"{skipped} already present")


if __name__ == "__main__":
    main()
