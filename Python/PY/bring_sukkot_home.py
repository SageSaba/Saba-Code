#!/usr/bin/env python3
"""The 21 days come home: Sukkot 2013 — the meeting the hunt sought
for years was sleeping in Sermon Notes as 51 numbered MP3s beside its
own contents map.

Dating law: Saba's own "Contents of 21 days.docx" maps three sessions
a day (7am, 1pm, 7pm) from 2013-09-05, and the recordings' numbers
walk that calendar: session n -> day (n-1)//3 after Sept 5, slot
(n-1)%3. Day-precise, session-precise, by the keeper's own document.
Missing numbers are honest gaps (sessions not recorded).

Org TRCF (the 2013 house), source names the map. Whisper reads each
mp3 (medium.en), txt lands beside it per the folder law, lines enter
RawSegments with real clocks. Restartable; waits politely; backup at
start. Run under taskpolicy -c background.
"""
import datetime as dt
import json, os, re, sqlite3, subprocess, time, shutil

DB = "/Users/saba/Archive/Sermons.db"
FOLDER = ("/Users/saba/Desktop/Sermon Notes/2013/Sukkot 2013/"
          "Sukkot 2013")
MODEL = "/Users/saba/ggml-medium.en-q5_0.bin"
WORK = os.path.join(FOLDER, "whisper_work")
LOG = os.path.join(FOLDER, "sukkot_home.log")
DAY0 = dt.date(2013, 9, 5)
SLOTS = ["7am", "1pm", "7pm"]


def log(msg):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def whisper_running():
    return subprocess.run(["pgrep", "-x", "whisper-cli"],
                          capture_output=True).returncode == 0


def whisper_to_txt(audio, txt):
    os.makedirs(WORK, exist_ok=True)
    stem = os.path.splitext(os.path.basename(audio))[0]
    wav = os.path.join(WORK, stem + ".wav")
    js = os.path.join(WORK, stem)
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", audio,
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
          f"Sermons_{dt.datetime.now():%Y%m%d_%H%M%S}"
          "_before_sukkot.db")
    shutil.copy(DB, bk)
    log(f"backup: {os.path.basename(bk)}")
    db = sqlite3.connect(DB)
    db.execute("PRAGMA busy_timeout=60000")
    existing = {r[0] for r in db.execute(
        "SELECT media_path FROM Services WHERE media_path IS NOT NULL")}
    names = sorted(n for n in os.listdir(FOLDER)
                   if n.lower().endswith(".mp3"))
    log(f"{len(names)} sessions in the crate")
    for name in names:
        m = re.match(r"^(\d+)\s+(.+)\.mp3$", name)
        if not m or not (1 <= int(m.group(1)) <= 63):
            log(f"{name}: no sane session number — left for Saba's ruling")
            continue
        n = int(m.group(1))
        date = (DAY0 + dt.timedelta(days=(n - 1) // 3)).isoformat()
        slot = SLOTS[(n - 1) % 3]
        title = (f"Sukkot 21 Days — {m.group(2).strip()} "
                 f"({slot}, session {n})")
        path = os.path.join(FOLDER, name)
        if path in existing:
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
                (date, title, path, "TRCF",
                 "contents map + session numbering (Sukkot 2013, "
                 "Saba's own document)",
                 "Sukkot 21-day meeting, Sept 2013 — three sessions "
                 "daily; found 2026-07-19 in Sermon Notes. Saba: 'a "
                 "very good transition meeting for me.'"))
            db.executemany(
                "INSERT INTO RawSegments (service_id, start, end, text) "
                "VALUES (?,?,?,?)",
                [(cur.lastrowid, s, e, t) for s, e, t in lines])
            db.commit()
            log(f"{name}: home — {date} {slot}, {len(lines)} lines")
        except Exception as e:
            log(f"{name}: FAILED — {e}")
    log("the 21 days are home")
    db.close()


if __name__ == "__main__":
    main()
