#!/usr/bin/env python3
"""Build the Meanings table — the meaning index over the archive.

A derived layer, like Summaries: every row is numbers computed FROM
the base, keyed back to it, receipted with the model that read it.
Raw is never written. Drop the table and this script rebuilds it.

Two kinds of rows:
  summary — one per Summaries row (the reading pass's phrases and
            one-liners), keyed by summary_id.
  passage — consecutive RawSegments lines from one service grouped
            into ~120-word passages, keyed by the first and last
            segment ID with their real clocks, so every match points
            at a moment in the video.

Embeddings come from Ollama (nomic-embed-text, 768 dims, local —
nothing leaves the house), stored as float32 blobs.

Restartable: existing rows are skipped. Run --summaries first
(minutes), prove the matches, then --passages (the long grind;
wrap in `taskpolicy -c background` to keep the machine usable).
"""
import argparse, array, json, sqlite3, urllib.request

DB = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"
MODEL = "nomic-embed-text"
OLLAMA = "http://localhost:11434/api/embed"
BATCH = 32
PASSAGE_WORDS = 120  # conservative default; chunking ruling still Saba's

SCHEMA = """
CREATE TABLE IF NOT EXISTS Meanings (
    ID INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,              -- 'summary' | 'passage'
    summary_id INTEGER,              -- Summaries.ID when kind='summary'
    service_id INTEGER NOT NULL,
    part_id INTEGER,
    seg_first INTEGER,               -- RawSegments.ID span for passages
    seg_last INTEGER,
    start TIME, end TIME,
    text TEXT NOT NULL,              -- the exact words that were embedded
    embedding BLOB NOT NULL,         -- 768 x float32, little-endian
    model TEXT NOT NULL,
    created TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_meanings_kind ON Meanings(kind);
CREATE INDEX IF NOT EXISTS idx_meanings_service ON Meanings(service_id);
"""


def embed(texts):
    req = urllib.request.Request(
        OLLAMA, json.dumps({"model": MODEL, "input": texts}).encode(),
        {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        vecs = json.load(r)["embeddings"]
    return [array.array("f", v).tobytes() for v in vecs]


def build_summaries(db):
    rows = db.execute(
        "SELECT s.ID, s.service_id, s.part_id, s.summary FROM Summaries s "
        "WHERE s.ID NOT IN (SELECT summary_id FROM Meanings "
        "WHERE kind='summary' AND summary_id IS NOT NULL) "
        "AND length(trim(s.summary)) > 0").fetchall()
    print(f"summaries to embed: {len(rows)}")
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        vecs = embed([r[3] for r in batch])
        db.executemany(
            "INSERT INTO Meanings (kind, summary_id, service_id, part_id, "
            "text, embedding, model) VALUES ('summary',?,?,?,?,?,?)",
            [(r[0], r[1], r[2], r[3], v, MODEL)
             for r, v in zip(batch, vecs)])
        db.commit()
        print(f"  {min(i + BATCH, len(rows))}/{len(rows)}", flush=True)


def passages_for_service(db, service_id):
    segs = db.execute(
        "SELECT ID, start, end, text FROM RawSegments "
        "WHERE service_id=? AND text IS NOT NULL AND length(trim(text))>0 "
        "ORDER BY start, ID", (service_id,)).fetchall()
    group, words = [], 0
    for seg in segs:
        group.append(seg)
        words += len(seg[3].split())
        if words >= PASSAGE_WORDS:
            yield group
            group, words = [], 0
    if group:
        yield group


def build_passages(db):
    done = {r[0] for r in db.execute(
        "SELECT DISTINCT service_id FROM Meanings WHERE kind='passage'")}
    services = [r[0] for r in db.execute(
        "SELECT DISTINCT service_id FROM RawSegments ORDER BY service_id")
        if r[0] not in done]
    print(f"services to index: {len(services)} ({len(done)} already done)")
    for n, sid in enumerate(services, 1):
        rows = []
        for group in passages_for_service(db, sid):
            rows.append((sid, group[0][0], group[-1][0],
                         group[0][1], group[-1][2],
                         " ".join(s[3].strip() for s in group)))
        for i in range(0, len(rows), BATCH):
            batch = rows[i:i + BATCH]
            vecs = embed([r[5] for r in batch])
            db.executemany(
                "INSERT INTO Meanings (kind, service_id, seg_first, seg_last,"
                " start, end, text, embedding, model)"
                " VALUES ('passage',?,?,?,?,?,?,?,?)",
                [(r[0], r[1], r[2], r[3], r[4], r[5], v, MODEL)
                 for r, v in zip(batch, vecs)])
            db.commit()
        print(f"  service {sid}: {len(rows)} passages  ({n}/{len(services)})",
              flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summaries", action="store_true")
    ap.add_argument("--passages", action="store_true")
    args = ap.parse_args()
    db = sqlite3.connect(DB)
    db.executescript(SCHEMA)
    if args.summaries:
        build_summaries(db)
    if args.passages:
        build_passages(db)
    if not (args.summaries or args.passages):
        print("nothing asked: use --summaries and/or --passages")
    db.close()


if __name__ == "__main__":
    main()
