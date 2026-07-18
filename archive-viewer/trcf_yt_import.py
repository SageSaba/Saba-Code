#!/usr/bin/env python3
"""The channel era comes home: @travelersrestchristfellows305 — the 16
videos of the 2022-2023 chapter (Connection|Reconnection June 2022,
the James Doss teachings, spring 2023) — downloaded with their YouTube
transcripts and entered as Services.

Dating law: a date written in the TITLE wins (day-precise: 06.04.2023,
7.10.22, "April 16, 2023"). A title with no date falls to the upload
stamp in the filename prefix — month-honest only (YYYY-MM), source
named, per the stamp rung. Org TRCF by the channel's own name;
re-ruling is Saba's. srt lines -> RawSegments, real clocks, no speaker
claimed. Restartable; backup at start.
"""
import calendar, os, re, sqlite3, datetime, shutil

DB = "/Users/saba/Archive/Sermons.db"
FOLDER = "/Volumes/Data/Video Archive/TRCF YouTube"
LOG = os.path.join(FOLDER, "trcf_yt_import.log")

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def parse_srt(path):
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
        if text and (not out or out[-1][2] != text):
            out.append((start, end, text))
    return out


def date_from_title(title):
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", title)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2})(?!\d)", title)
    if m:
        return f"20{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.search(r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", title)
    if m and m.group(1).lower() in MONTHS:
        return f"{m.group(3)}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    return None


def main():
    bk = ("/Volumes/Data/Video Archive/SQL Files/backups/"
          f"Sermons_{datetime.datetime.now():%Y%m%d_%H%M%S}"
          "_before_trcf_yt.db")
    shutil.copy(DB, bk)
    log(f"backup: {os.path.basename(bk)}")
    db = sqlite3.connect(DB)
    existing = {r[0] for r in db.execute(
        "SELECT media_path FROM Services WHERE media_path IS NOT NULL")}
    added = lines_total = 0
    for name in sorted(os.listdir(FOLDER)):
        m = re.match(r"^(\d{4})_(\d{2})_(\d{2}) (.+?)\s*\[[^\]]+\]"
                     r"\.(mp4|mkv|webm)$", name)
        if not m:
            continue
        path = os.path.join(FOLDER, name)
        if path in existing:
            continue
        title = m.group(4).replace("｜", "|").strip()
        date = date_from_title(title)
        src = "title (TRCF YouTube)"
        if not date:
            date = f"{m.group(1)}-{m.group(2)}"   # month-honest upload stamp
            src = "upload stamp, month-honest (TRCF YouTube)"
        srt = os.path.join(FOLDER, os.path.splitext(name)[0] + ".en.srt")
        lines = parse_srt(srt) if os.path.exists(srt) else []
        cur = db.execute(
            "INSERT INTO Services (preach_date, title, media_path, org, "
            "org_source, notes) VALUES (?,?,?,?,?,?)",
            (date, title, path, "TRCF", src,
             "TRCF YouTube channel (@travelersrestchristfellows305)"))
        db.executemany(
            "INSERT INTO RawSegments (service_id, start, end, text) "
            "VALUES (?,?,?,?)",
            [(cur.lastrowid, s, e, t) for s, e, t in lines])
        db.commit()
        added += 1
        lines_total += len(lines)
        log(f"home: {date}  {title[:60]}  ({len(lines)} lines)")
    log(f"done: {added} services, {lines_total} lines")
    db.close()


if __name__ == "__main__":
    main()
