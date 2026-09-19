#!/usr/bin/env python3
"""name_scanner.py — find every name in the archive and decide, for each
appearance: (1) was the person QUOTED (talked about) or did they SPEAK
(introduced / handed the service), and (2) what KIND of moment it was —
Song, Prayer, Testimony, Scripture, Exhortation, or Sermon.

Reads Sermons.db READ-ONLY (never writes to the raw base — house law).
Writes findings to Archive_Suggestions.db (the interpretation layer):
  - people_mentions : one row per appearance (name, service, time, kind, spoke/quoted, snippet)
  - people_scan     : per-person totals + life-span
  - people_kinds    : per-person, per-part-kind breakdown of spoke/quoted
Safe to re-run: it rebuilds only those three tables and touches nothing else.

This closes the gap the archive keeps hitting: names like Joe Nance or
James Doss are found *mentioned* but the transcripts aren't tagged by who
*spoke* or in what kind of moment. Here we read the words around each name,
and the part-spans under it, to infer both.
"""

import re
import sqlite3
import time

SERMONS = "file:/Users/saba/Archive/Sermons.db?mode=ro"
SUGGEST = "/Users/saba/Archive/Archive_Suggestions.db"

# Cue phrases meaning the named person is being HANDED THE SERVICE — about
# to speak. Matched case-insensitively in a window around the name.
SPOKE_CUES = [
    r"welcome", r"come and share", r"coming to share", r"to share",
    r"going to share", r"share the word", r"stand and applaud",
    r"would you (?:come|dismiss|pray|lead|share)", r"come up",
    r"is coming", r"invite", r"i give you", r"receive brother",
    r"receive pastor", r"bring (?:us|you) brother", r"turn it over",
    r"have (?:brother|pastor|sister) \w+ come",
]
SPOKE_RE = re.compile("|".join(SPOKE_CUES), re.IGNORECASE)


def hms_to_sec(hms):
    if not hms:
        return None
    p = str(hms).split(":")
    try:
        if len(p) == 3:
            return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])
        if len(p) == 2:
            return int(p[0]) * 60 + float(p[1])
        return float(p[0])
    except ValueError:
        return None


def load_names(scur):
    """Every tagged speaker plus a curated set of known people not yet tagged.
    Returns {display_name: compiled_regex}."""
    names = {}
    for (full,) in scur.execute("SELECT full_name FROM Speakers WHERE full_name IS NOT NULL"):
        if full and full.strip():
            names[full.strip()] = None
    for extra in [
        "Joe Nance", "James Moore", "James Ashworth", "Joanie Barton",
        "Oliver Hogue", "Buster Miles", "Thomas Mullins", "Howard Mullins",
        "Loran Helm", "Edward Helm", "Georgine Christiansen", "Joe Young",
        "Jonathan Wagner", "Barbara Young", "Sharon Powell", "Sharon Key",
    ]:
        names.setdefault(extra, None)
    for n in list(names):
        names[n] = re.compile(r"\b" + re.escape(n) + r"\b", re.IGNORECASE)
    return names


def load_parts(scur):
    """All part-spans grouped by service, as sorted (start_sec, end_sec, kind)
    lists, so a segment's kind can be found by the span it falls inside."""
    parts = {}
    for sid, kind, start, end in scur.execute(
            "SELECT service_id, kind, start, end FROM Parts"):
        a, b = hms_to_sec(start), hms_to_sec(end)
        if a is None:
            continue
        parts.setdefault(sid, []).append((a, b if b is not None else a + 1e9, kind))
    for sid in parts:
        parts[sid].sort()
    return parts


def kind_at(parts, service_id, sec):
    if sec is None:
        return None
    for a, b, kind in parts.get(service_id, ()):
        if a <= sec < b:
            return (kind or "").lower()
    return None


def classify(text, match):
    a = max(0, match.start() - 60)
    b = min(len(text), match.end() + 60)
    return "spoke" if SPOKE_RE.search(text[a:b]) else "quoted"


def main():
    t0 = time.time()
    scon = sqlite3.connect(SERMONS, uri=True); scur = scon.cursor()
    dcon = sqlite3.connect(SUGGEST); dcur = dcon.cursor()

    names = load_names(scur)
    print(f"Loading part-spans…")
    parts = load_parts(scur)
    print(f"Scanning for {len(names)} names across the archive "
          f"({sum(len(v) for v in parts.values()):,} part-spans loaded)…")

    any_name = re.compile(
        "|".join(r"\b" + re.escape(n) + r"\b" for n in names), re.IGNORECASE)

    for t in ("people_mentions", "people_scan", "people_kinds"):
        dcur.execute(f"DROP TABLE IF EXISTS {t}")
    dcur.execute("""
        CREATE TABLE people_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, service_id INTEGER, start TEXT,
            kind TEXT NOT NULL CHECK (kind IN ('spoke','quoted')),
            part_kind TEXT, snippet TEXT,
            scanned_at TEXT NOT NULL DEFAULT (datetime('now')))""")
    dcur.execute("""
        CREATE TABLE people_scan (
            name TEXT PRIMARY KEY,
            spoke_count INTEGER DEFAULT 0, quoted_count INTEGER DEFAULT 0,
            services INTEGER DEFAULT 0, first_date TEXT, last_date TEXT)""")
    dcur.execute("""
        CREATE TABLE people_kinds (
            name TEXT NOT NULL, part_kind TEXT,
            spoke_count INTEGER DEFAULT 0, quoted_count INTEGER DEFAULT 0,
            PRIMARY KEY (name, part_kind))""")

    tot = {n: {"spoke": 0, "quoted": 0, "services": set()} for n in names}
    kinds = {}  # (name, part_kind) -> {spoke, quoted}

    seen = mentions = 0
    batch = []
    for service_id, start, text in scur.execute(
            "SELECT service_id, start, text FROM RawSegments WHERE text IS NOT NULL"):
        seen += 1
        if seen % 500000 == 0:
            print(f"  …{seen:,} segments read, {mentions:,} mentions "
                  f"({time.time()-t0:.0f}s)")
        if not any_name.search(text):
            continue
        pk = kind_at(parts, service_id, hms_to_sec(start))
        for name, rgx in names.items():
            m = rgx.search(text)
            if not m:
                continue
            k = classify(text, m)
            tot[name][k] += 1
            tot[name]["services"].add(service_id)
            kk = kinds.setdefault((name, pk), {"spoke": 0, "quoted": 0})
            kk[k] += 1
            a = max(0, m.start() - 40); b = min(len(text), m.end() + 60)
            batch.append((name, service_id, start, k, pk, text[a:b].strip()))
            mentions += 1
            if len(batch) >= 2000:
                dcur.executemany("INSERT INTO people_mentions "
                    "(name, service_id, start, kind, part_kind, snippet) "
                    "VALUES (?,?,?,?,?,?)", batch); batch.clear()
    if batch:
        dcur.executemany("INSERT INTO people_mentions "
            "(name, service_id, start, kind, part_kind, snippet) "
            "VALUES (?,?,?,?,?,?)", batch)

    for name, t in tot.items():
        if not (t["spoke"] or t["quoted"]):
            continue
        svc = sorted(t["services"])
        fd = ld = None
        if svc:
            q = ("SELECT MIN(preach_date), MAX(preach_date) FROM Services "
                 "WHERE ID IN (%s)" % ",".join("?" * len(svc)))
            fd, ld = scur.execute(q, svc).fetchone()
        dcur.execute("INSERT INTO people_scan "
            "(name, spoke_count, quoted_count, services, first_date, last_date) "
            "VALUES (?,?,?,?,?,?)",
            (name, t["spoke"], t["quoted"], len(t["services"]), fd, ld))
    for (name, pk), c in kinds.items():
        dcur.execute("INSERT INTO people_kinds "
            "(name, part_kind, spoke_count, quoted_count) VALUES (?,?,?,?)",
            (name, pk, c["spoke"], c["quoted"]))
    dcon.commit()

    print(f"\nDone in {time.time()-t0:.0f}s — {seen:,} segments read, "
          f"{mentions:,} mentions filed.\n")
    print(f"{'NAME':<24}{'SPOKE':>7}{'QUOTED':>8}{'SVCS':>6}   SPAN")
    print("-" * 68)
    for r in dcur.execute("SELECT name, spoke_count, quoted_count, services, "
            "first_date, last_date FROM people_scan "
            "ORDER BY (spoke_count+quoted_count) DESC"):
        span = f"{(r[4] or '?')[:10]} -> {(r[5] or '?')[:10]}"
        print(f"{r[0]:<24}{r[1]:>7}{r[2]:>8}{r[3]:>6}   {span}")

    scon.close(); dcon.close()


if __name__ == "__main__":
    main()
