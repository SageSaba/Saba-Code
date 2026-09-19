#!/usr/bin/env python3
"""Ask the meaning index a question, get moments with receipts.

Proof tool for the Meanings layer (and the seed of the connector's
future meaning-search): embeds the question with the same model that
read the archive, compares against every Meanings row, and prints
the closest matches — each with service date, title, org, speaker,
and clock, so every answer points back at the base.

Usage: meanings_search.py "how am I saved by the blood" [-n 10]
                          [--kind summary|passage]
"""
import argparse, array, json, sqlite3, urllib.request
import numpy as np

DB = "/Users/saba/Archive/Sermons.db"
MODEL = "nomic-embed-text"
OLLAMA = "http://localhost:11434/api/embed"


def embed_one(text):
    req = urllib.request.Request(
        OLLAMA, json.dumps({"model": MODEL, "input": [text]}).encode(),
        {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return np.array(json.load(r)["embeddings"][0], dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("-n", type=int, default=8)
    ap.add_argument("--kind", default=None)
    args = ap.parse_args()

    db = sqlite3.connect(DB)
    where = "WHERE kind=?" if args.kind else ""
    params = (args.kind,) if args.kind else ()
    rows = db.execute(
        f"SELECT ID, kind, service_id, part_id, seg_first, start, end, "
        f"text, embedding FROM Meanings {where}", params).fetchall()
    if not rows:
        print("Meanings is empty — run meanings_build.py first")
        return

    mat = np.frombuffer(b"".join(r[8] for r in rows),
                        dtype=np.float32).reshape(len(rows), -1)
    mat = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    q = embed_one(args.question)
    q = q / np.linalg.norm(q)
    best = np.argsort(mat @ q)[::-1][:args.n]

    print(f"Q: {args.question}\n")
    for rank, i in enumerate(best, 1):
        ID, kind, sid, pid, seg1, start, end, text, _ = rows[i]
        svc = db.execute(
            "SELECT preach_date, title, org, sermon_giver FROM Services "
            "WHERE ID=?", (sid,)).fetchone()
        date, title, org, giver = (svc or ("?", "?", "", ""))
        who = giver or ""
        if pid:
            p = db.execute("SELECT kind, person, title FROM Parts WHERE ID=?",
                           (pid,)).fetchone()
            if p:
                who = p[1] or who
        clock = f" @ {start}" if start else ""
        score = float(mat[i] @ q)
        print(f"{rank}. [{score:.3f}] {date}  {org or '?'}  "
              f"{who or 'speaker unassigned'}{clock}  (service {sid})")
        print(f"   {title or ''}")
        print(f"   {text[:160].strip()}\n")
    db.close()


if __name__ == "__main__":
    main()
