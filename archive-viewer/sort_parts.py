#!/usr/bin/env python3
"""sort_parts.py — the key sort: cut a service into its parts and name each kind.

Saba's design, his own six categories:
    song · prayer · scripture · testimony · exhortation · sermon

and his own definitions, ruled 2026-07-28 (standing ruling #17) — testimony is a
sworn report of lived experience; exhortation is the urging toward growth
("encourage one another daily, while it is yet called today"); preaching is
exhortation carried inside taught content. NOT a duration rule. Not who is
holding the microphone.

Why it exists: a thousand transcript lines is not readable. Twenty named parts
is. This is the layer that makes an hour findable.

How it works, honestly:
  1. Lines whisper marked with the musical glyph are grouped as SONG outright.
  2. Everything else is cut into ~4-minute windows so a shift from prayer into
     testimony inside one message is actually caught.
  3. The local model (qwen3:4b via Ollama — private, nothing leaves the house)
     names each window's kind from Saba's definitions above.
  4. Adjacent windows of the same kind merge back into one part.

The machine proposes. Saba disposes — a part's `kind` is a machine reading and
`person` is only ever filled from what is already established (a service's
sermon_giver), never from a guess.

RawSegments is never written. Only Parts, and only for the services named.

Usage:
    sort_parts.py 2651 2652 2653          # sort these services
    sort_parts.py --from 2637             # every service from 2637 up
    sort_parts.py --unsorted              # every service with lines but no parts
"""
import sqlite3, json, urllib.request, time, sys, os, datetime, shutil

DB = "/Users/saba/Archive/Sermons.db"
OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen3:4b"
WINDOW_SECONDS = 240          # ~4 minutes: fine enough to catch a shift, coarse
                              # enough that an hour is ~15 model calls, not 900
LOGDIR = "/Volumes/Data/Video Archive/SQL Files/sort_parts"
KINDS = ("scripture", "song", "prayer", "testimony", "exhortation", "sermon")

PROMPT = """You are sorting a short block of spoken-church-service transcript into ONE category.
Definitions (use these exactly, not your own guess):
- prayer: words spoken directly TO God (addressed as "Lord", "Father", "Jesus")
- scripture: a passage of the Bible being READ ALOUD or quoted at length, not commented on
- song: sung lyrics, worship music, a hymn or chorus
- testimony: a sworn, first-person report of something the speaker personally lived through
- exhortation: urging listeners toward growth, encouragement to do better, without teaching content at length
- sermon: exhortation carried inside taught Bible content -- the main preaching/teaching block

Text:
---
{text}
---
Reply with ONLY one word: song, scripture, prayer, testimony, exhortation, or sermon."""


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    try:
        os.makedirs(LOGDIR, exist_ok=True)
        with open(os.path.join(LOGDIR, "sort_parts.log"), "a") as f:
            f.write(line + "\n")
    except OSError:
        pass          # drive not mounted — the console line still stands


def ask(prompt, retries=2):
    payload = json.dumps({
        "model": MODEL, "stream": False, "think": False,
        "messages": [{"role": "user", "content": prompt}],
        "options": {"temperature": 0.1},
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


def clock_to_sec(c):
    h, m, s = str(c).split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def sec_to_clock(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    return f"{h:02d}:{m:02d}:{sec % 60:06.3f}"


def sort_service(db, sid):
    """Cut one service into named parts. Returns the number of parts written."""
    person = db.execute("SELECT sermon_giver FROM Services WHERE ID=?", (sid,)).fetchone()
    person = (person[0] if person else None) or ""

    rows = db.execute(
        "SELECT start, end, text FROM RawSegments WHERE service_id=? ORDER BY start",
        (sid,)).fetchall()
    if not rows:
        log(f"svc {sid}: no lines — skipped")
        return 0
    try:
        tagged = [(clock_to_sec(s), clock_to_sec(e), "♪" in t, t.replace("♪", "").strip())
                  for s, e, t in rows if s and e]
    except (ValueError, AttributeError):
        log(f"svc {sid}: clocks unreadable (untimed transcript) — skipped")
        return 0
    if not tagged:
        log(f"svc {sid}: no usable clocks — skipped")
        return 0

    # runs of consecutive same-tag (song vs speech) lines
    runs, cur = [], None
    for s, e, is_song, text in tagged:
        if cur is None or is_song != cur[2]:
            if cur:
                runs.append(cur)
            cur = [s, e, is_song, []]
        cur[1] = e
        if text:
            cur[3].append(text)
    if cur:
        runs.append(cur)

    # song runs stand whole; speech runs get cut into windows
    windows = []
    for start, end, is_song, texts in runs:
        if is_song:
            windows.append((start, end, "song", " ".join(texts)))
            continue
        chunk_start, chunk_end, chunk = start, start, []
        for s, e, sng, t in tagged:
            if sng or s < start or e > end or not t:
                continue
            if s - chunk_start >= WINDOW_SECONDS and chunk:
                windows.append((chunk_start, chunk_end, None, " ".join(chunk)))
                chunk_start, chunk = s, []
            chunk_end = e
            chunk.append(t)
        if chunk:
            windows.append((chunk_start, chunk_end, None, " ".join(chunk)))

    # name each window
    named = []
    for start, end, kind, text in windows:
        if kind != "song":
            if len(text.strip()) < 15:
                continue
            reply = ask(PROMPT.format(text=text[:1200])).lower()
            kind = next((k for k in KINDS if k in reply), "sermon")
        named.append((start, end, kind, text))

    # merge neighbours of the same kind
    merged = []
    for start, end, kind, text in named:
        if merged and merged[-1][2] == kind:
            ms, _, mk, mt = merged[-1]
            merged[-1] = (ms, end, mk, mt + " " + text)
        else:
            merged.append((start, end, kind, text))

    db.execute("DELETE FROM Parts WHERE service_id=?", (sid,))
    for start, end, kind, text in merged:
        title = text.strip()[:120] + ("…" if len(text.strip()) > 120 else "")
        db.execute(
            "INSERT INTO Parts (service_id, kind, person, title, start, end, "
            "machine_person, machine_title) VALUES (?,?,?,?,?,?,?,?)",
            (sid, kind, person, title, sec_to_clock(start), sec_to_clock(end),
             person, title))
    db.commit()
    kinds = ", ".join(sorted({k for _, _, k, _ in merged}))
    log(f"svc {sid}: {len(merged)} parts ({kinds})")
    return len(merged)


def pick_services(db, argv):
    if "--unsorted" in argv:
        return [r[0] for r in db.execute("""
            SELECT s.ID FROM Services s
            WHERE EXISTS (SELECT 1 FROM RawSegments r WHERE r.service_id = s.ID)
              AND NOT EXISTS (SELECT 1 FROM Parts p WHERE p.service_id = s.ID)
            ORDER BY s.ID""")]
    if "--from" in argv:
        lo = int(argv[argv.index("--from") + 1])
        return [r[0] for r in db.execute(
            "SELECT ID FROM Services WHERE ID >= ? ORDER BY ID", (lo,))]
    return [int(a) for a in argv[1:] if a.isdigit()]


def main():
    db = sqlite3.connect(DB)
    ids = pick_services(db, sys.argv)
    if not ids:
        print(__doc__)
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bk = f"/Users/saba/Archive/Sermons_{stamp}_before_sort_parts.db"
    shutil.copy(DB, bk)
    log(f"backup: {os.path.basename(bk)}")
    log(f"sorting {len(ids)} service(s)")

    total = 0
    for sid in ids:
        try:
            total += sort_service(db, sid)
        except Exception as e:
            log(f"svc {sid}: FAILED — {e}")
    log(f"done — {total} parts across {len(ids)} service(s)")


if __name__ == "__main__":
    main()
