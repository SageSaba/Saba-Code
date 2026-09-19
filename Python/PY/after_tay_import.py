#!/usr/bin/env python3
"""The after-TAY services come home: TRCF Sunday mornings 2024-2025
from the Desktop folder, whisper-read and entered as they finish.

Dating law: the filename's leading capture stamp (YYYY_MM_DD__HH_MM_SS,
written by the recorder at stream time) is filename evidence — day-
precise. Title typos in the human half of the name (e.g. "12.15.25" on
a 2024 Advent service) do NOT outrank the stamp; they stay in the
title as found. The one file with no stamp (01.28.24 Sunday Morning
Service) is dated from its own leading MM.DD.YY.

Org TRCF, source named as the folder's word ("TRCF after TAY") —
re-ruling is Saba's. Two mornings have two captures each (04.14.24,
06.30.24): both enter as their own rows, honestly; re-cutting is
later work, these rows are the base.

Same road as bring_wog_home: ffmpeg -> wav -> whisper-cli medium.en ->
timed .txt beside the video (folder law), then Services + RawSegments.
Restartable everywhere; waits politely for any other whisper-cli.
Backup at start. Run under `taskpolicy -c background`.
"""
import json, os, re, sqlite3, subprocess, time, datetime, shutil

DB = "/Users/saba/Archive/Sermons.db"
FOLDER = "/Users/saba/Desktop/TRCF after TAY 2024-2025"
MODEL = "/Users/saba/ggml-medium.en-q5_0.bin"
WORK = os.path.join(FOLDER, "whisper_work")
LOG = os.path.join(FOLDER, "after_tay.log")


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def whisper_running():
    return subprocess.run(["pgrep", "-x", "whisper-cli"],
                          capture_output=True).returncode == 0


def date_and_title(name):
    m = re.match(r"^(\d{4})_(\d{2})_(\d{2})__\d{2}_\d{2}_\d{2}"
                 r"(.+?)\.hd\.mp4$", name)
    if m:
        title = m.group(4).strip()
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", title
    m = re.match(r"^(\d{2})\.(\d{2})\.(\d{2})\s*(.+?)\.hd\.mp4$", name)
    if m:
        return f"20{m.group(3)}-{m.group(1)}-{m.group(2)}", \
               f"{m.group(4).strip()} {m.group(1)}.{m.group(2)}.{m.group(3)}"
    return None, None


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
    bk = ("/Volumes/Data/Video Archive/SQL Files/backups/"
          f"Sermons_{datetime.datetime.now():%Y%m%d_%H%M%S}"
          "_before_after_tay.db")
    shutil.copy(DB, bk)
    log(f"backup: {os.path.basename(bk)}")

    db = sqlite3.connect(DB)
    existing = {r[0] for r in db.execute(
        "SELECT media_path FROM Services WHERE media_path IS NOT NULL")}
    names = sorted(n for n in os.listdir(FOLDER) if n.endswith(".mp4"))
    log(f"{len(names)} services in the queue")
    for name in names:
        path = os.path.join(FOLDER, name)
        if path in existing:
            log(f"{name}: already home — skipped")
            continue
        date, title = date_and_title(name)
        if not date:
            log(f"{name}: no date I can trust — left for Saba's ruling")
            continue
        txt = os.path.splitext(path)[0] + ".txt"
        try:
            if not os.path.exists(txt):
                t0 = time.time()
                log(f"{name}: whisper reading…")
                whisper_to_txt(path, txt)
                log(f"{name}: heard ({(time.time()-t0)/60:.0f} min)")
            lines = parse_txt(txt)
            cur = db.execute(
                "INSERT INTO Services (preach_date, title, media_path, "
                "org, org_source, notes) VALUES (?,?,?,?,?,?)",
                (date, title, path, "TRCF", "folder (TRCF after TAY)",
                 "TRCF after TAY 2024-2025"))
            db.executemany(
                "INSERT INTO RawSegments (service_id, start, end, text) "
                "VALUES (?,?,?,?)",
                [(cur.lastrowid, s, e, t) for s, e, t in lines])
            db.commit()
            log(f"{name}: home — {date}, {len(lines)} lines")
        except Exception as e:
            log(f"{name}: FAILED — {e}")
    log("after-TAY era is home (failures, if any, named above)")
    db.close()


if __name__ == "__main__":
    main()
