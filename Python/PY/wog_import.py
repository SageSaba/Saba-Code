#!/usr/bin/env python3
"""Bring the WOG 1992 June tapes into the MASTER (Sermons.db).

One Services row per tape — born RFOD by rule, preach_date '1992-06'
(month-honest: the exact June days are not yet established, and a made-
up day would be a lie) — and every timed-text line into RawSegments
with its real clock. Tapes may later be re-cut into the nine meetings;
these rows are the base for that work, not an obstacle to it.

Restartable: a tape whose Services row already exists is skipped.
Backup taken at start.
"""
import os, re, sqlite3, shutil, datetime

DB = "/Users/saba/Archive/Sermons.db"
FOLDER = "/Volumes/Data/Video Archive/WOG_/1992/05 June"


def parse_txt(path):
    out = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = re.match(r"\[(\d\d:\d\d:\d\d\.\d{3}) --> "
                     r"(\d\d:\d\d:\d\d\.\d{3})\]\s*(.*)", line)
        if m and m.group(3).strip():
            out.append((m.group(1), m.group(2), m.group(3).strip()))
    return out


def main():
    bk = ("/Volumes/Data/Video Archive/SQL Files/backups/"
          f"Sermons_{datetime.datetime.now():%Y%m%d_%H%M%S}"
          "_before_wog_import.db")
    shutil.copy(DB, bk)
    print("backup:", os.path.basename(bk))
    db = sqlite3.connect(DB)
    existing = {r[0] for r in db.execute(
        "SELECT title FROM Services WHERE org='RFOD'")}
    added = lines_total = 0
    for name in sorted(os.listdir(FOLDER)):
        m = re.match(r"^(1992 Tape (\d+))\.mp4$", name)
        if not m:
            continue
        title = "WOG June 1992 — Tape " + m.group(2)
        if title in existing:
            continue
        txt = os.path.join(FOLDER, m.group(1) + ".txt")
        cur = db.execute(
            "INSERT INTO Services (preach_date, title, media_path, org, "
            "org_source) VALUES ('1992-06', ?, ?, 'RFOD', 'rule')",
            (title, os.path.join(FOLDER, name)))
        sid = cur.lastrowid
        rows = [(sid, s, e, t) for s, e, t in parse_txt(txt)] \
            if os.path.exists(txt) else []
        db.executemany("INSERT INTO RawSegments (service_id, start, end, "
                       "text) VALUES (?,?,?,?)", rows)
        db.commit()
        added += 1
        lines_total += len(rows)
        print(f"{title}: service {sid}, {len(rows)} timed lines")
    print(f"done — {added} tapes, {lines_total} lines")


if __name__ == "__main__":
    main()
