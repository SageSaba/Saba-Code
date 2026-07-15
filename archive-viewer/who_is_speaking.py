#!/usr/bin/env python3
"""who_is_speaking.py — evidence-based names and kinds over Parts.

Saba's law (2026-07-15): NO blanket defaults. A name or a kind is
written only when something in the service actually says it, and the
evidence — the very line and its timestamp — is stored beside the
claim in the PartEvidence table. Unnamed stays honestly unnamed.

What one run does:
  1. TESTIMONY and PRAYER: short spoken parts (currently over-declared
     as "sermon") are re-kinded when the surrounding words declare it
     ("testimony"/"testify" nearby; a prayer opening in the first lines).
  2. WHO IS SPEAKING: a part gets a person only when exactly one known
     speaker (Speakers table) is named in the lines just before or at
     the start of the part — full name, or Brother/Sister/Pastor +
     surname. Ambiguity (two names) writes nothing.
  3. SERMON GIVER: one per service (Saba's rule; EVM shared the pulpit).
     From the service title ("with Pastor X") or from the longest
     sermon part's evidenced speaker. Never guessed.

Guards, per the Parts law:
  - person is written only where person == machine_person (a hand
    ruling, where they differ, is never touched).
  - re-runs are safe: evidence rows are refreshed per run, hand
    corrections survive.
  - RawSegments is never written.
"""

import re
import sqlite3
from datetime import datetime

DB_PATH = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"

SHORT_PART = 600.0          # seconds; parts longer than this keep their kind
BEFORE_WINDOW = 90.0        # seconds of raw lines examined before a part
INTO_WINDOW = 60.0          # seconds examined into the part

TESTIMONY_CUE = re.compile(r"\btestimon\w*|\btestif\w*", re.I)
PRAYER_OPEN = re.compile(
    r"\bheavenly father\b|\bdear lord\b|\bfather god\b|\blet us pray\b|"
    r"\blet's pray\b|\bwe come before you\b", re.I)


def secs(t):
    """'01:28:47.280' -> seconds."""
    h, m, s = str(t).split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS PartEvidence (
                       ID INTEGER PRIMARY KEY,
                       service_id INTEGER,
                       part_id INTEGER,
                       field TEXT NOT NULL,      -- 'kind' | 'person' | 'sermon_giver'
                       value TEXT NOT NULL,
                       evidence_text TEXT,
                       evidence_time TEXT,
                       method TEXT,
                       created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                   );""")
    cur.execute("DELETE FROM PartEvidence;")   # evidence is derived; rebuilt per run

    # The cast: known speakers and the ways a service names them aloud.
    speakers = [r["full_name"] for r in cur.execute(
        "SELECT full_name FROM Speakers")]
    patterns = []
    for name in speakers:
        parts = name.split()
        surname = parts[-1]
        patterns.append((name, re.compile(re.escape(name), re.I)))
        patterns.append((name, re.compile(
            r"\b(?:brother|sister|pastor|reverend|rev\.?)\s+" +
            re.escape(surname) + r"\b", re.I)))

    # Cast out the blanket default: machine-made names (person ==
    # machine_person) claim knowledge nothing declared. They become
    # honestly unnamed; hand rulings (where the two differ) survive.
    cur.execute("UPDATE Parts SET person='', machine_person='' "
                "WHERE person = machine_person AND person <> '';")
    wiped = cur.rowcount

    services = list(cur.execute("SELECT ID, title, org FROM Services"))
    n_kind, n_person, n_giver = 0, 0, 0

    for svc in services:
        sid = svc["ID"]
        raw = list(cur.execute(
            "SELECT start, text FROM RawSegments WHERE service_id=? "
            "ORDER BY start", (sid,)))
        raw_s = [(secs(r["start"]), r["start"], r["text"] or "") for r in raw]
        parts = list(cur.execute(
            "SELECT ID, kind, person, machine_person, start, end "
            "FROM Parts WHERE service_id=? ORDER BY start", (sid,)))

        def window(p0, back, ahead):
            lo, hi = p0 - back, p0 + ahead
            return [(t, ts, tx) for (t, ts, tx) in raw_s if lo <= t <= hi]

        for p in parts:
            p0, p1 = secs(p["start"]), secs(p["end"])
            dur = p1 - p0
            win = window(p0, BEFORE_WINDOW, min(INTO_WINDOW, dur))

            # --- kind: testimony / prayer (short spoken parts only) ---
            if p["kind"] == "sermon" and dur < SHORT_PART:
                hit = next(((ts, tx) for (t, ts, tx) in win
                            if TESTIMONY_CUE.search(tx)), None)
                if hit:
                    cur.execute("UPDATE Parts SET kind='testimony' WHERE ID=?",
                                (p["ID"],))
                    cur.execute("INSERT INTO PartEvidence (service_id, part_id,"
                                " field, value, evidence_text, evidence_time,"
                                " method) VALUES (?,?,?,?,?,?,?)",
                                (sid, p["ID"], "kind", "testimony",
                                 hit[1][:200], hit[0], "cue-word near part"))
                    n_kind += 1
                else:
                    opening = [(t, ts, tx) for (t, ts, tx) in raw_s
                               if p0 <= t <= p0 + 30][:3]
                    hit = next(((ts, tx) for (t, ts, tx) in opening
                                if PRAYER_OPEN.search(tx)), None)
                    if hit:
                        cur.execute("UPDATE Parts SET kind='prayer' WHERE ID=?",
                                    (p["ID"],))
                        cur.execute("INSERT INTO PartEvidence (service_id,"
                                    " part_id, field, value, evidence_text,"
                                    " evidence_time, method) VALUES (?,?,?,?,?,?,?)",
                                    (sid, p["ID"], "kind", "prayer",
                                     hit[1][:200], hit[0], "prayer opening"))
                        n_kind += 1

            # --- person: exactly one known name in the window ---
            found = {}
            for (t, ts, tx) in win:
                for name, rx in patterns:
                    if rx.search(tx):
                        found.setdefault(name, (ts, tx))
            if len(found) == 1:
                name, (ts, tx) = next(iter(found.items()))
                hand_ruled = (p["person"] or "") != (p["machine_person"] or "")
                if not hand_ruled:
                    cur.execute("UPDATE Parts SET person=?, machine_person=? "
                                "WHERE ID=?", (name, name, p["ID"]))
                    n_person += 1
                cur.execute("INSERT INTO PartEvidence (service_id, part_id,"
                            " field, value, evidence_text, evidence_time,"
                            " method) VALUES (?,?,?,?,?,?,?)",
                            (sid, p["ID"], "person", name, tx[:200], ts,
                             "named in surrounding lines"))

        # --- sermon giver: one per service, from title or evidenced part ---
        giver, source, ev = None, None, None
        m = re.search(r"\bwith\s+(?:pastor|brother|sister|rev\.?|reverend)?"
                      r"\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", svc["title"] or "")
        if m:
            giver, source, ev = m.group(1), "title", svc["title"]
        else:
            best = cur.execute(
                'SELECT p.person FROM Parts p '
                'JOIN PartEvidence e ON e.part_id = p.ID AND e.field=\'person\' '
                'WHERE p.service_id=? AND p.kind=\'sermon\' AND p.person<>\'\' '
                'ORDER BY (strftime(\'%s\',\'1970-01-01 \'||substr(p."end",1,8)) - '
                'strftime(\'%s\',\'1970-01-01 \'||substr(p."start",1,8))) DESC LIMIT 1',
                (sid,)).fetchone()
            if best:
                giver, source = best["person"], "evidenced sermon part"
        if giver:
            cur.execute("UPDATE Services SET sermon_giver=?, "
                        "sermon_giver_source=? WHERE ID=? AND "
                        "(sermon_giver_source IS NULL OR "
                        " sermon_giver_source <> 'hand')",
                        (giver, source, sid))
            cur.execute("INSERT INTO PartEvidence (service_id, field, value,"
                        " evidence_text, method) VALUES (?,?,?,?,?)",
                        (sid, "sermon_giver", giver, (ev or "")[:200], source))
            n_giver += 1

    con.commit()

    print(f"Run {datetime.now():%Y-%m-%d %H:%M}")
    print(f"  blanket-default names cleared:      {wiped}")
    print(f"  parts re-kinded (testimony/prayer): {n_kind}")
    print(f"  parts given a speaker (evidence):   {n_person}")
    print(f"  services with a sermon giver:       {n_giver}")
    print("Kinds now:")
    for k, n in cur.execute("SELECT kind, COUNT(*) FROM Parts GROUP BY kind "
                            "ORDER BY 2 DESC"):
        print(f"  {k:<12} {n}")
    named = cur.execute("SELECT COUNT(*) FROM Parts WHERE person<>'' AND "
                        "person<>'Thomas Young'").fetchone()[0]
    print(f"Parts named other than the old default: {named}")
    con.close()


if __name__ == "__main__":
    main()
