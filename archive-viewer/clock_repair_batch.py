#!/usr/bin/env python3
"""Reread every counterfeit-clock service's video with whisper and replace
its even-spread layer clocks with TRUE aligned clocks.

Restartable: a service whose layer already carries whisper methods is
skipped, so the batch can be stopped and started at will. RawSegments is
never written — only RawClockLayer rows change, one service at a time.

Order: oldest service first. Waits politely if another whisper-cli is
already running (e.g. a single-service run) before starting its own.

Log: /Volumes/Data/Video Archive/SQL Files/clock_repair/batch.log
Run:  nohup python3 clock_repair_batch.py &
"""
import os, sqlite3, subprocess, time, datetime, sys

DB = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"
WORK = "/Volumes/Data/Video Archive/SQL Files/clock_repair"
MODEL = "/Users/saba/ggml-medium.en-q5_0.bin"
ALIGN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "align_service_clocks.py")
LOG = os.path.join(WORK, "batch.log")
SKIP = set()   # 573 rejoins the queue — batch owns everything now


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def whisper_running():
    r = subprocess.run(["pgrep", "-x", "whisper-cli"], capture_output=True)
    return r.returncode == 0


def services_to_do():
    with sqlite3.connect("file:" + DB + "?mode=ro", uri=True) as db:
        return db.execute("""
            SELECT s.ID, s.preach_date, s.media_path
            FROM Services s
            WHERE s.ID IN (
                SELECT DISTINCT r.service_id
                FROM RawClockLayer l
                JOIN RawSegments r ON r.ID = l.segment_id
                WHERE l.method LIKE 'even-spread%')
            ORDER BY s.preach_date""").fetchall()


def already_done(sid):
    with sqlite3.connect("file:" + DB + "?mode=ro", uri=True) as db:
        n = db.execute("""
            SELECT COUNT(*) FROM RawClockLayer l
            JOIN RawSegments r ON r.ID = l.segment_id
            WHERE r.service_id=? AND l.method LIKE 'whisper%'""",
            (sid,)).fetchone()[0]
    return n > 0


def main():
    os.makedirs(WORK, exist_ok=True)
    todo = services_to_do()
    log(f"batch start — {len(todo)} counterfeit-clock services in scope")
    done = fail = skip = 0
    for sid, date, path in todo:
        if sid in SKIP or already_done(sid):
            skip += 1
            continue
        if not path or not os.path.exists(path):
            log(f"svc {sid} {date}: video missing ({path}) — skipped")
            fail += 1
            continue
        while whisper_running():
            time.sleep(60)
        wav = os.path.join(WORK, f"svc{sid}.wav")
        js = os.path.join(WORK, f"svc{sid}")
        try:
            t0 = time.time()
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path,
                            "-ar", "16000", "-ac", "1", wav], check=True)
            subprocess.run(["whisper-cli", "-m", MODEL, "-f", wav,
                            "-oj", "-of", js], check=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            r = subprocess.run([sys.executable, ALIGN, str(sid), js + ".json"],
                               capture_output=True, text=True, check=True)
            log(f"svc {sid} {date}: {r.stdout.strip()} "
                f"({(time.time()-t0)/60:.0f} min)")
            done += 1
        except subprocess.CalledProcessError as e:
            log(f"svc {sid} {date}: FAILED — {e}")
            fail += 1
        finally:
            for f in (wav,):
                if os.path.exists(f):
                    os.remove(f)
    log(f"batch complete — done {done}, skipped {skip}, failed {fail}")


if __name__ == "__main__":
    main()
