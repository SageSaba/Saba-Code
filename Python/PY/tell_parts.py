#!/usr/bin/env python3
"""tell_parts.py — the summary layer: one line per part, so an hour is readable.

Saba's design, 2026-08-07: *"This might be a good place to build a AI layer that
gives the information of what happened during four minutes. So somebody could
look at an hour long message and see twenty pieces rather than a thousand."*

Runs AFTER sort_parts.py has cut a service into named parts. For each part it
reads the actual words in that span and writes ONE plain sentence saying what
happens there — into Summaries, role='summary', part_id set. Twenty findable
pieces instead of a thousand lines.

The precedent already existed: Summaries has rows from a 2026-07-17 pass with
part_id set, e.g. "The message: Elijah's road through famine, ravens, and
Carmel — experiences before usefulness." This finishes what that started.

RawSegments never written. Parts never written. Only Summaries.
Restartable: a part that already carries a summary by this method is skipped.

Usage:
    tell_parts.py 2651 2652         # summarise these services' parts
    tell_parts.py --from 2637       # every service from 2637 up
    tell_parts.py --untold          # every part that has no summary yet
"""
import sqlite3, json, urllib.request, time, sys, os, datetime

DB = "/Users/saba/Archive/Sermons.db"
OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen3:4b"
METHOD = "qwen3:4b part-summary v1"
LOGDIR = "/Volumes/Data/Video Archive/SQL Files/sort_parts"

PROMPT = """This is one stretch of a church service. It has already been sorted as: {kind}

Say in ONE plain sentence what actually happens in this stretch — the substance, so
someone scanning a list of these can find the piece they want. Name the scripture,
the story, or the point if there is one. No preamble, no "In this passage".

Text:
---
{text}
---
One sentence:"""


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    try:
        os.makedirs(LOGDIR, exist_ok=True)
        with open(os.path.join(LOGDIR, "tell_parts.log"), "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def ask(prompt, retries=2):
    payload = json.dumps({
        "model": MODEL, "stream": False, "think": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.2},
    }).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                OLLAMA + "/api/chat", data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                reply = json.load(r)["message"]["content"]
            if "</think>" in reply:
                reply = reply.split("</think>")[-1]
            return reply.strip()
        except Exception as e:
            if attempt == retries:
                raise
            log(f"  ollama hiccup ({e}) — waiting 15s")
            time.sleep(15)


def pick_services(db, argv):
    if "--untold" in argv:
        return [r[0] for r in db.execute("""
            SELECT DISTINCT p.service_id FROM Parts p
            WHERE NOT EXISTS (SELECT 1 FROM Summaries m
                              WHERE m.part_id = p.ID AND m.method = ?)
            ORDER BY p.service_id""", (METHOD,))]
    if "--from" in argv:
        lo = int(argv[argv.index("--from") + 1])
        return [r[0] for r in db.execute(
            "SELECT DISTINCT service_id FROM Parts WHERE service_id >= ? "
            "ORDER BY service_id", (lo,))]
    return [int(a) for a in argv[1:] if a.isdigit()]


def tell_service(db, sid):
    parts = db.execute(
        "SELECT ID, kind, start, end FROM Parts WHERE service_id=? ORDER BY start",
        (sid,)).fetchall()
    if not parts:
        log(f"svc {sid}: no parts yet — run sort_parts.py first")
        return 0

    done = 0
    for pid, kind, start, end in parts:
        if db.execute("SELECT 1 FROM Summaries WHERE part_id=? AND method=?",
                      (pid, METHOD)).fetchone():
            continue
        rows = db.execute(
            "SELECT text FROM RawSegments WHERE service_id=? AND start >= ? "
            "AND end <= ? ORDER BY start", (sid, start, end)).fetchall()
        text = " ".join(r[0].replace("♪", "").strip() for r in rows if r[0]).strip()
        if len(text) < 40:
            continue
        line = ask(PROMPT.format(kind=kind, text=text[:2000]))
        line = line.strip().strip('"').split("\n")[0][:400]
        db.execute(
            "INSERT INTO Summaries (service_id, part_id, role, summary, method) "
            "VALUES (?,?,?,?,?)", (sid, pid, "summary", line, METHOD))
        db.commit()
        done += 1
    log(f"svc {sid}: {done} part summaries written")
    return done


def main():
    db = sqlite3.connect(DB)
    ids = pick_services(db, sys.argv)
    if not ids:
        print(__doc__)
        return
    log(f"telling {len(ids)} service(s)")
    total = 0
    for sid in ids:
        try:
            total += tell_service(db, sid)
        except Exception as e:
            log(f"svc {sid}: FAILED — {e}")
    log(f"done — {total} summaries")


if __name__ == "__main__":
    main()
