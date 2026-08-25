#!/usr/bin/env python3
"""Bring the wilderness in: the CF Archive downloads become Services.

The @thecfarchive7816 channel — an unknown kindred archivist's
digitization of cassettes from the fellowship churches, 1970s-1990s —
was downloaded to /Volumes/Data/Video Archive/CF Archive/ with YouTube
.en.srt transcripts alongside. Each media file becomes one Services
row (per-video, like XWalls; meetings can be re-cut later — these rows
are the base, not an obstacle), its srt lines entering RawSegments
with real clocks. No speaker claimed — the filename's own words stay
in the title; naming is a ruling for later.

Dating law: the TRUE service date is embedded in the filename
(CODE_MM_DD_YYYY, e.g. SDCF_08_13_1989a) — the leading YYYY_MM_DD is
only the channel's upload date and is ignored. Files with no embedded
date are logged to cf_unparsed.log for Saba's ruling, never guessed.

Org: the filename's congregation code (SDCF, PCCF, RFOD, ...) goes to
Services.org with org_source naming the evidence. The Organizations
table is NOT written — banners are Saba's to rule.

Restartable: a media_path already in Services is skipped.
Backup taken at start.
"""
import os, re, sqlite3, datetime, shutil

DB = "/Users/saba/Archive/Sermons.db"
FOLDER = "/Volumes/Data/Video Archive/CF Archive"
LOG = os.path.join(FOLDER, "cf_import.log")
UNPARSED = os.path.join(FOLDER, "cf_unparsed.log")
MEDIA_EXT = ("webm", "m4a", "mp4", "mkv", "opus")


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def parse_srt(path):
    """-> [(start 'HH:MM:SS.mmm', end, text)] with scroll-duplicates folded."""
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


def parse_name(name):
    """-> (date 'YYYY-MM-DD', code, title) or None if no embedded date."""
    m = re.match(r"^\d{4}_\d{2}_\d{2}\s+(.+?)\s*\[[^\]]+\]\.\w+$", name)
    mid = m.group(1) if m else os.path.splitext(name)[0]
    dm = re.search(r"(?:^|_)(\d{2})_(\d{2})_(\d{4})[a-z]{0,2}(?=_|$)", mid)
    if not dm:
        return None
    mo, dy, yr = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
    if not (1 <= mo <= 12 and 1 <= dy <= 31 and 1950 <= yr <= 2030):
        return None
    code = re.sub(r"^\d+_", "", mid[:dm.start()]).strip("_")
    code = code.replace("_", " ").strip() or "CF"
    title = mid[dm.end():].strip("_").replace("_", " ").strip()
    if not title:
        title = f"{code} {yr}-{mo:02d}-{dy:02d}"
    return f"{yr}-{mo:02d}-{dy:02d}", code, title


def main():
    bk = ("/Volumes/Data/Video Archive/SQL Files/backups/"
          f"Sermons_{datetime.datetime.now():%Y%m%d_%H%M%S}"
          "_before_cf_import.db")
    shutil.copy(DB, bk)
    log(f"backup: {os.path.basename(bk)}")

    db = sqlite3.connect(DB)
    existing = {r[0] for r in db.execute(
        "SELECT media_path FROM Services WHERE media_path IS NOT NULL")}
    added = lines_total = skipped = no_srt = unparsed = 0
    for name in sorted(os.listdir(FOLDER)):
        if not name.lower().endswith(MEDIA_EXT):
            continue
        path = os.path.join(FOLDER, name)
        if os.path.exists(path + ".part") or name.endswith(".part"):
            continue
        if path in existing:
            skipped += 1
            continue
        parsed = parse_name(name)
        if not parsed:
            with open(UNPARSED, "a") as f:
                f.write(name + "\n")
            unparsed += 1
            continue
        date, code, title = parsed
        srt = os.path.join(FOLDER, os.path.splitext(name)[0] + ".en.srt")
        lines = parse_srt(srt) if os.path.exists(srt) else []
        cur = db.execute(
            "INSERT INTO Services (preach_date, title, media_path, org, "
            "org_source, notes) VALUES (?,?,?,?,?,?)",
            (date, title, path, code, "filename (CF Archive)",
             "CF Archive — digitized cassette (@thecfarchive7816)"))
        sid = cur.lastrowid
        db.executemany(
            "INSERT INTO RawSegments (service_id, start, end, text) "
            "VALUES (?,?,?,?)",
            [(sid, s, e, t) for s, e, t in lines])
        db.commit()
        added += 1
        lines_total += len(lines)
        if not lines:
            no_srt += 1
        if added % 100 == 0:
            log(f"  {added} services in so far…")
    log(f"done: {added} services added ({lines_total} lines), "
        f"{skipped} already home, {no_srt} without transcript (whisper "
        f"later), {unparsed} filenames left for Saba's ruling")
    db.close()


if __name__ == "__main__":
    main()
