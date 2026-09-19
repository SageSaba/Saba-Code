#!/usr/bin/env python3
"""Start the years: whisper reads the un-heard WOG tapes and each one
enters the master as it finishes — 1986 Agape, 1990, February 1992,
1997. (June 1992 came home already; December 1992 and 1999 are empty
folders — their tapes are hunt targets, not import targets.)

Dating law, per folder and filename — never file stamps:
  1986 Agape/Deny Self.mpg      -> 1986        (year-honest)
  1990/1990 Tape *.mp4          -> 1990        (year-honest)
  1992/02 February/92022401.mp4 -> 1992-02-24  (filename testifies)
  1997/WOG19970301.mkv          -> 1997-03-01  (filename testifies)
  1997/WOG040297*.mpg           -> 1997-04-02  (MMDDYY; AM kept in title)

Org RFOD by the June 1992 rule (WOG_ folder lineage); org_source says
so — re-ruling is Saba's anytime.

For each video without a .txt beside it: ffmpeg -> wav -> whisper-cli
(medium.en) -> timed .txt IN THE TAPE'S OWN FOLDER (the folder law),
then one Services row + RawSegments lines. Restartable at every step:
existing .txt is not re-whispered, existing media_path not re-imported.
Waits politely if another whisper-cli is running. Backup at start.
Run under `taskpolicy -c background` to keep the machine usable.
"""
import json, os, re, sqlite3, subprocess, time, datetime, shutil

DB = "/Users/saba/Archive/Sermons.db"
ROOT = "/Volumes/Data/Video Archive/WOG_"
MODEL = "/Users/saba/ggml-medium.en-q5_0.bin"
WORK = os.path.join(ROOT, "whisper_work")
LOG = os.path.join(ROOT, "wog_years.log")
MEDIA_EXT = (".mp4", ".mpg", ".mkv", ".avi", ".mov", ".m4v")

FOLDERS = ["1986 Agape", "1990", "1992/02 February", "1997"]


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def whisper_running():
    return subprocess.run(["pgrep", "-x", "whisper-cli"],
                          capture_output=True).returncode == 0


def date_and_title(folder, stem):
    if folder == "1986 Agape":
        return "1986", f"WOG 1986 Agape — {stem}"
    if folder == "1990":
        return "1990", f"WOG 1990 — {stem}"
    if folder == "1992/02 February":
        m = re.match(r"^92(\d{2})(\d{2})", stem)
        if m:
            return f"1992-{m.group(1)}-{m.group(2)}", \
                   f"WOG February 1992 — {stem}"
        return "1992-02", f"WOG February 1992 — {stem}"
    if folder == "1997":
        m = re.match(r"^WOG(\d{4})(\d{2})(\d{2})$", stem)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", \
                   f"WOG 1997 — {stem}"
        m = re.match(r"^WOG(\d{2})(\d{2})(\d{2})", stem)
        if m:
            return f"19{m.group(3)}-{m.group(1)}-{m.group(2)}", \
                   f"WOG 1997 — {stem}"
        return "1997", f"WOG 1997 — {stem}"
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
          "_before_wog_years.db")
    shutil.copy(DB, bk)
    log(f"backup: {os.path.basename(bk)}")

    videos = []
    for folder in FOLDERS:
        d = os.path.join(ROOT, folder)
        for name in sorted(os.listdir(d)):
            if name.lower().endswith(MEDIA_EXT):
                videos.append((folder, os.path.join(d, name)))
    log(f"{len(videos)} tapes in the queue")

    db = sqlite3.connect(DB)
    existing = {r[0] for r in db.execute(
        "SELECT media_path FROM Services WHERE media_path IS NOT NULL")}
    for folder, path in videos:
        stem = os.path.splitext(os.path.basename(path))[0]
        txt = os.path.splitext(path)[0] + ".txt"
        if path in existing:
            log(f"{stem}: already home — skipped")
            continue
        try:
            if not os.path.exists(txt):
                t0 = time.time()
                log(f"{stem}: whisper reading…")
                whisper_to_txt(path, txt)
                log(f"{stem}: heard ({(time.time()-t0)/60:.0f} min)")
            date, title = date_and_title(folder, stem)
            lines = parse_txt(txt)
            cur = db.execute(
                "INSERT INTO Services (preach_date, title, media_path, "
                "org, org_source, notes) VALUES (?,?,?,?,?,?)",
                (date, title, path, "RFOD",
                 "rule (WOG folder, June 1992 precedent)",
                 "Word of God meetings — brought home from the year "
                 "folders"))
            db.executemany(
                "INSERT INTO RawSegments (service_id, start, end, text) "
                "VALUES (?,?,?,?)",
                [(cur.lastrowid, s, e, t) for s, e, t in lines])
            db.commit()
            log(f"{stem}: home — {date}, {len(lines)} lines")
        except Exception as e:
            log(f"{stem}: FAILED — {e}")
    log("the years are home (whatever failed is named above)")
    db.close()


if __name__ == "__main__":
    main()
