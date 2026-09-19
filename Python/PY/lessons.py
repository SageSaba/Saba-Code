#!/usr/bin/env python3
"""lessons.py — learn how Saba works, from what Saba actually said.

His ask, 2026-08-07: *"I want you to build the most efficient of memory retaining
and improve it with experience."*

And nine days before that, unheeded until now (2026-07-29):
    "You took the wrong answer from that. I wanted you to study how it worked and
     provide yourself a method of how I work. I'm not asking you to do it."

## Why this exists

The 100 memory files were written by hand, by Claude, when Claude happened to
notice something. That is the weak link: it only learns what it was already
paying attention to. On 2026-08-07 there were 22 feedback memories and the
afternoon still drifted — and afterward, a single semantic probe over the history
turned up a whole working mode ("Silent Mode", 2026-07-28) that no memory file
had ever recorded.

The corrections were always there. Nobody went and looked.

So this does not ask Claude what it learned. It goes to the record of what Saba
actually said — 1,739 of his own messages in Sir Archive — and finds the moments
where he corrected, stopped, or re-aimed the work. Those moments ARE the
experience. Everything else is commentary.

## The law it keeps

Machine proposes, witness disposes. This NEVER writes a memory file. It surfaces
candidates with their date and their exact words, and Saba rules. A lesson he did
not confirm is not a lesson — it is a guess about a man, which is the one thing
this house does not permit.

## Improving with experience

Re-run it. As Sir Archive grows (`conversation_archive.py import --all`), the
same probes reach further, and corrections made since last time surface. Lessons
already ruled are remembered in `lessons` (Archive_Suggestions.db) and not
offered twice.

## Usage

    lessons.py find                 # probe the history, show candidates
    lessons.py find --all           # include ones already ruled
    lessons.py keep <id> [note]     # Saba rules: this is a real lesson
    lessons.py drop <id> [note]     # Saba rules: not a lesson
    lessons.py list                 # what has been ruled so far
"""
import json, os, sqlite3, sys, math, urllib.request, datetime, hashlib

RECALL = "/Users/saba/Archive/Recall.db"
SUG = "/Users/saba/Archive/Archive_Suggestions.db"
OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
THRESHOLD = 0.58

# Each probe is a different SHAPE of correction. They are written as things a man
# actually says, not as categories, because the index matches meaning — and a
# sentence retrieves better than a label.
PROBES = [
    ("correction",  "no that is wrong, you misunderstood what I meant"),
    ("not-hearing", "you are not listening to me, you did not hear what I said"),
    ("overreach",   "stop, I did not ask you to do that, you went too far"),
    ("too-slow",    "you are being mechanical and timid, just do the work"),
    ("how-I-work",  "this is how I work, this is the method I want you to use"),
    ("a-rule",      "from now on always do it this way, this is the rule"),
    ("a-mode",      "when I say this word, behave this way, respond only like this"),
    ("hard-no",     "never do that again, do not ever say that to me"),
    ("what-hurts",  "that frustrated me, that was painful, do not put me through that"),
    ("what-helps",  "that was exactly right, that is what I needed you to do"),
]


def embed(text):
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text[:1400]}).encode()
    req = urllib.request.Request(OLLAMA + "/api/embeddings", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["embedding"]


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def ledger():
    db = sqlite3.connect(SUG)
    db.execute("""CREATE TABLE IF NOT EXISTS lessons (
        id TEXT PRIMARY KEY,      -- hash of the exact words, so one saying is one lesson
        shape TEXT,               -- which probe found it
        said_on TEXT,
        said TEXT,                -- his exact words, never edited
        score REAL,
        status TEXT,              -- proposed | kept | dropped
        note TEXT,                -- Saba's word when he rules it
        ruled_at TEXT,
        found_at TEXT)""")
    db.commit()
    return db


def key(text):
    return hashlib.md5(" ".join(text.split()).lower().encode()).hexdigest()[:10]


def cmd_find(show_all=False):
    if not os.path.exists(RECALL):
        print("no index — run: recall.py build --history")
        return
    idx = sqlite3.connect(RECALL)
    rows = idx.execute(
        "SELECT when_, text, vec FROM shard WHERE body='history'").fetchall()
    if not rows:
        print("no history indexed — run: recall.py build --history")
        return
    vecs = [(w, t, json.loads(v)) for w, t, v in rows]

    db = ledger()
    ruled = {r[0] for r in db.execute("SELECT id FROM lessons WHERE status != 'proposed'")}

    found = {}
    for shape, probe in PROBES:
        q = embed(probe)
        for when_, text, vec in vecs:
            s = cosine(q, vec)
            if s < THRESHOLD:
                continue
            k = key(text)
            if k in found and found[k][0] >= s:
                continue
            found[k] = (s, shape, when_, text)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for k, (s, shape, when_, text) in found.items():
        db.execute(
            "INSERT OR IGNORE INTO lessons (id, shape, said_on, said, score, status, found_at) "
            "VALUES (?,?,?,?,?, 'proposed', ?)", (k, shape, when_, text, s, now))
    db.commit()

    out = sorted(
        ((k, v) for k, v in found.items() if show_all or k not in ruled),
        key=lambda kv: -kv[1][0])
    if not out:
        print("nothing new — every candidate has already been ruled.")
        return

    print(f"{len(out)} candidate lesson(s) — his own words. Machine proposes; you dispose.\n")
    for k, (s, shape, when_, text) in out:
        print(f"[{k}]  {shape:<12} {when_[:10]}  ({s:.2f})")
        print(f"   \"{' '.join(text.split())[:320]}\"\n")
    print("rule them:  lessons.py keep <id> [note]   |   lessons.py drop <id> [note]")


def cmd_rule(kid, status, note):
    db = ledger()
    row = db.execute("SELECT said FROM lessons WHERE id=?", (kid,)).fetchone()
    if not row:
        print(f"no candidate {kid} — run: lessons.py find")
        return
    db.execute("UPDATE lessons SET status=?, note=?, ruled_at=? WHERE id=?",
               (status, note or "", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), kid))
    db.commit()
    print(f"{status}: {' '.join(row[0].split())[:120]}")
    if status == "kept":
        print("\nA kept lesson still needs a memory file written by hand, in his idiom,")
        print("with the why. This ledger records the ruling, not the teaching.")


def cmd_list():
    db = ledger()
    for st in ("kept", "dropped", "proposed"):
        rows = db.execute(
            "SELECT id, shape, said_on, said, note FROM lessons WHERE status=? "
            "ORDER BY said_on", (st,)).fetchall()
        if not rows:
            continue
        print(f"--- {st.upper()} ({len(rows)}) ---")
        for i, shape, on, said, note in rows:
            print(f"  [{i}] {shape:<12} {on[:10]}  {' '.join(said.split())[:110]}")
            if note:
                print(f"        Saba: {note}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    c = sys.argv[1]
    if c == "find":
        cmd_find("--all" in sys.argv)
    elif c in ("keep", "drop"):
        if len(sys.argv) < 3:
            print(f"usage: lessons.py {c} <id> [note]"); sys.exit(1)
        cmd_rule(sys.argv[2], "kept" if c == "keep" else "dropped",
                 " ".join(sys.argv[3:]))
    elif c == "list":
        cmd_list()
    else:
        print(__doc__)
