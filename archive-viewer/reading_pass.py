#!/usr/bin/env python3
"""The reading pass, v1: give every service its story.

For each service whose clocks are TRUE (real from birth, or already
whisper-aligned by the clock repair) and not yet read, the local Ollama
model (qwen3:4b — private, nothing leaves the house) reads the words and
writes into Summaries, each row carrying its method:
  role='title'    — a short phrase naming what the night was
  role='summary'  — one line, what happened (service level, part_id NULL)
  role='summary' + part_id — one line per important part (sermon,
                    exhortation, testimony running 4+ minutes)

Laws: RawSegments never written. Parts never written (v1 reads, it does
not map — part mapping is v2, after Saba rules its shape). Rows are
replaced per service on re-run, so the pass is restartable at will.
Services still wearing even-spread clocks are skipped and picked up on
a later lap, once the clock repair has trued them.

Log: /Volumes/Data/Video Archive/SQL Files/reading_pass/reading.log
Run: nohup python3 reading_pass.py &
"""
import json, os, re, sqlite3, time, datetime, urllib.request

DB = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"
WORK = "/Volumes/Data/Video Archive/SQL Files/reading_pass"
LOG = os.path.join(WORK, "reading.log")
OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen3:4b"
METHOD = "qwen3:4b reading v1"
MIN_LINES = 30          # stubs seconds long are not nights to tell


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


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
            with urllib.request.urlopen(req, timeout=600) as r:
                reply = json.load(r)["message"]["content"]
            if "</think>" in reply:
                reply = reply.split("</think>")[-1]
            return reply.strip()
        except Exception as e:
            if attempt == retries:
                raise
            log(f"  ollama hiccup ({e}) — waiting 60s")
            time.sleep(60)


def parse_json(reply):
    m = re.search(r"\{.*\}", reply, re.DOTALL)
    return json.loads(m.group(0)) if m else None


def eligible_services(db):
    return db.execute("""
        SELECT s.ID, s.preach_date, COALESCE(s.title,'')
        FROM Services s
        WHERE (SELECT COUNT(*) FROM RawSegments r
               WHERE r.service_id = s.ID) >= ?
          AND NOT EXISTS (
              SELECT 1 FROM RawClockLayer l
              JOIN RawSegments r ON r.ID = l.segment_id
              WHERE r.service_id = s.ID AND l.method LIKE 'even-spread%')
          AND NOT EXISTS (
              SELECT 1 FROM Summaries m
              WHERE m.service_id = s.ID AND m.method = ?
                AND m.role = 'title')
        ORDER BY s.preach_date""", (MIN_LINES, METHOD)).fetchall()


def sample_lines(db, sid, limit=220):
    rows = db.execute(
        "SELECT text FROM RawSegments WHERE service_id=? ORDER BY start",
        (sid,)).fetchall()
    texts = [r[0] for r in rows if r[0] and not r[0].startswith("(")]
    if len(texts) <= limit:
        return texts
    head = texts[:60]
    step = max(1, (len(texts) - 60) // (limit - 60))
    return head + texts[60::step][:limit - 60]


def part_lines(db, sid, start, end, limit=100):
    rows = db.execute("""
        SELECT r.text FROM RawSegments r
        LEFT JOIN RawClockLayer l ON l.segment_id = r.ID
        WHERE r.service_id=? AND COALESCE(l.start, r.start) >= ?
          AND COALESCE(l.start, r.start) < ?
        ORDER BY COALESCE(l.start, r.start)""",
        (sid, start, end)).fetchall()
    texts = [r[0] for r in rows if r[0]]
    return texts[:limit] + (texts[-20:] if len(texts) > limit + 20 else [])


def read_service(db, sid, date, old_title):
    words = "\n".join(sample_lines(db, sid))
    reply = ask(f"""You are reading the transcript of a church service
({date}). From these spoken lines, answer in STRICT JSON only:
{{"title": "...", "summary": "..."}}
- title: a short phrase (under 8 words) naming what this night actually
  was — the message's subject if there is one, the event if it is a
  special night. Not a generic name like "Church service".
- summary: ONE sentence saying what happened.
Lines:
{words}""")
    data = parse_json(reply)
    if not data or not data.get("title"):
        raise ValueError("model gave no usable JSON")
    rows = [(sid, None, str(data["title"])[:80], METHOD, "title"),
            (sid, None, str(data.get("summary", ""))[:300], METHOD, "summary")]

    parts = db.execute("""
        SELECT ID, kind, person, start, end FROM Parts
        WHERE service_id=? AND lower(kind) IN
              ('sermon','exhortation','testimony')
        ORDER BY start""", (sid,)).fetchall()
    for pid, kind, person, start, end in parts:
        span = db.execute(
            "SELECT (strftime('%s','2000-01-01 '||?)"
            "      - strftime('%s','2000-01-01 '||?))", (end, start)
        ).fetchone()[0]
        if span is None or span < 240:
            continue
        text = "\n".join(part_lines(db, sid, start, end))
        if not text.strip():
            continue
        who = f" (speaker: {person})" if person else ""
        reply = ask(f"""One sentence: what is this {kind}{who} about?
Reply with the sentence only, no preamble.
Transcript excerpt:
{text}""")
        rows.append((sid, pid, reply[:300], METHOD, "summary"))
    return rows


def main():
    os.makedirs(WORK, exist_ok=True)
    log("reading pass v1 start")
    laps_without_work = 0
    while laps_without_work < 3:
        with sqlite3.connect(DB) as db:
            todo = eligible_services(db)
        if not todo:
            laps_without_work += 1
            log("no eligible services right now — waiting 30 min "
                "for the clock repair to true more")
            time.sleep(1800)
            continue
        laps_without_work = 0
        log(f"lap: {len(todo)} services eligible")
        for sid, date, old_title in todo:
            try:
                t0 = time.time()
                with sqlite3.connect(DB) as db:
                    rows = read_service(db, sid, date, old_title)
                    db.execute("DELETE FROM Summaries WHERE service_id=? "
                               "AND method=?", (sid, METHOD))
                    db.executemany(
                        "INSERT INTO Summaries (service_id, part_id, "
                        "summary, method, role) VALUES (?,?,?,?,?)", rows)
                    db.commit()
                title = next(r[2] for r in rows if r[4] == "title")
                log(f"svc {sid} {date}: \"{title}\" "
                    f"+{len(rows)-2} part summaries "
                    f"({(time.time()-t0)/60:.1f} min)")
            except Exception as e:
                log(f"svc {sid} {date}: FAILED — {e}")
    log("reading pass complete — three quiet laps, nothing left to read")


if __name__ == "__main__":
    main()
