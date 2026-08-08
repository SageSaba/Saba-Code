#!/usr/bin/env python3
"""recall.py — memory retrieval for Scribe. Saba's ask, 2026-08-07:
*"I really want you to make a memory retrieval system for you."*

## The problem it solves

There are 100 memory files and 29,763 messages of our own history. Everything
cannot be held in mind at once. Loading it all at session start and hoping is
what produced a whole afternoon of drift on 2026-08-07 — the rules were all
written down and still got broken, because they were read once and then stopped
being present.

Reading everything is impossible. Reading nothing is drift. So: retrieve the few
things that actually bear on THIS moment, at the moment they matter.

## How

`nomic-embed-text` (local, via Ollama — nothing leaves the house) turns each
memory and each past exchange into a vector. A question does the same, and the
nearest neighbours come back. Semantic, not keyword: ask "how does Saba want to
be corrected" and the reflect-before-proceeding and wait-for-engage memories
surface even though neither contains the word "corrected".

Two bodies are searched, and they are NOT the same kind of thing:
  MEMORY  — the 100 distilled memory files. What was decided and ruled.
  HISTORY — Sir Archive: what was actually said, in his own words, with dates.

Memory can drift from truth; history cannot. When they disagree, history is the
witness and memory is the interpretation — same relation RawSegments has to the
sermon book.

## Usage

    recall.py build                 # index the memory files (fast, ~100)
    recall.py build --vault         # also index the Vault + Secondary Wisdom
    recall.py build --history       # also index Sir Archive (slow, one-time)
    recall.py build --all           # everything
    recall.py "how should I correct him"          # ask memory
    recall.py "the red alert" --history           # ask our actual history
    recall.py "voiceprint" --both -n 8            # both, 8 results

Rebuild after memories change. `build` is safe to re-run — it replaces its own
index and touches nothing else.
"""
import json, os, re, sqlite3, sys, urllib.request, math, time

MEMORY_DIR = "/Users/saba/.claude/projects/-Users-saba-Desktop-Saba-Code/memory"
CONVERSATIONS = "/Users/saba/Archive/Conversations.db"
# The Vault — his own writings, and the Secondary Wisdom shelf he keeps beside them.
# Added 2026-08-08 at his word: "These are a few of the things that determine who I
# want to be... Remind me in your lovely matrix."
VAULT = "/Users/saba/Vault"
INDEX = "/Users/saba/Archive/Recall.db"
OLLAMA = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"


CHUNK = 1400          # nomic-embed-text tops out near 2048 tokens; stay well under


def chunk_text(text, size=CHUNK):
    """Split on paragraph boundaries where possible — a long memory holds several
    ideas, and each deserves to be findable on its own."""
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    out, cur = [], ""
    for para in text.split("\n\n"):
        if len(cur) + len(para) + 2 <= size:
            cur += ("\n\n" if cur else "") + para
        else:
            if cur:
                out.append(cur)
            while len(para) > size:          # a single huge paragraph
                out.append(para[:size])
                para = para[size:]
            cur = para
    if cur:
        out.append(cur)
    return out


def embed(text, retries=2):
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text[:CHUNK]}).encode()
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                OLLAMA + "/api/embeddings", data=payload,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)["embedding"]
        except Exception:
            if attempt == retries:
                raise
            time.sleep(5)


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def con():
    db = sqlite3.connect(INDEX)
    db.execute("""CREATE TABLE IF NOT EXISTS shard (
        id INTEGER PRIMARY KEY, body TEXT, ref TEXT, kind TEXT,
        title TEXT, when_ TEXT, text TEXT, vec TEXT)""")
    db.execute("CREATE INDEX IF NOT EXISTS ix_shard_body ON shard(body)")
    return db


# ---------------------------------------------------------------- building

def build_memory(db):
    db.execute("DELETE FROM shard WHERE body='memory'")
    n = 0
    for f in sorted(os.listdir(MEMORY_DIR)):
        if not f.endswith(".md") or f == "MEMORY.md":
            continue
        path = os.path.join(MEMORY_DIR, f)
        txt = open(path, encoding="utf-8", errors="ignore").read()
        desc = re.search(r'^description:\s*"?(.*?)"?\s*$', txt, re.M)
        kind = re.search(r'^\s*type:\s*(\w+)', txt, re.M)
        body = txt.split("---", 2)[-1].strip()
        name = f[:-3]
        d = desc.group(1) if desc else ""
        # the name and description carry as much signal as the body, so they ride
        # on every chunk — a fragment from the middle still knows what it belongs to
        head = f"{name.replace('-', ' ')}. {d}"
        pieces = chunk_text(body) or [""]
        for i, piece in enumerate(pieces):
            blob = f"{head}\n\n{piece}"[:CHUNK]
            db.execute(
                "INSERT INTO shard (body, ref, kind, title, when_, text, vec) "
                "VALUES ('memory',?,?,?,?,?,?)",
                (name if len(pieces) == 1 else f"{name} ({i+1}/{len(pieces)})",
                 kind.group(1) if kind else "?", d, "", piece[:4000],
                 json.dumps(embed(blob))))
        n += 1
        if n % 20 == 0:
            print(f"  …{n} memories", flush=True)
    db.commit()
    return n


def build_vault(db):
    """His own writings, and the borrowed wisdom he keeps beside them.

    Two kinds, kept apart on purpose — 'his own' is Saba's word and outranks
    everything; 'secondary' is water carried from somewhere else and never rules.
    Same discipline as a machine voice wearing its label.
    """
    if not os.path.isdir(VAULT):
        print("no Vault directory"); return 0
    db.execute("DELETE FROM shard WHERE body='vault'")
    n = 0
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, VAULT)
            kind = "secondary" if rel.startswith("Secondary Wisdom") else "his own"
            try:
                txt = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            title = f[:-3]
            for i, piece in enumerate(chunk_text(txt)):
                blob = f"{title}\n\n{piece}"[:CHUNK]
                db.execute(
                    "INSERT INTO shard (body, ref, kind, title, when_, text, vec) "
                    "VALUES ('vault',?,?,?,?,?,?)",
                    (rel if i == 0 else f"{rel} ({i+1})", kind, title, "",
                     piece[:4000], json.dumps(embed(blob))))
            n += 1
            if n % 10 == 0:
                db.commit()
                print(f"  …{n} vault documents", flush=True)
    db.commit()
    return n


def build_history(db, min_chars=120):
    """Index Saba's own words from Sir Archive. His messages only — what he
    actually said is the witness; my replies are commentary on it."""
    if not os.path.exists(CONVERSATIONS):
        print("no Conversations.db — run conversation_archive.py import --all first")
        return 0
    src = sqlite3.connect(CONVERSATIONS)
    rows = src.execute(
        "SELECT session_id, message_num, timestamp, content FROM conversation_archive "
        "WHERE role='user' AND length(content) >= ? ORDER BY timestamp", (min_chars,)
    ).fetchall()
    db.execute("DELETE FROM shard WHERE body='history'")
    n = 0
    for sid, num, ts, content in rows:
        content = " ".join(content.split())
        if content.startswith(("[tool", "<", "Base directory", "Caveat:")):
            continue          # machinery, not his voice
        db.execute(
            "INSERT INTO shard (body, ref, kind, title, when_, text, vec) "
            "VALUES ('history',?,?,?,?,?,?)",
            (f"{sid[:8]}#{num}", "saba", "", (ts or "")[:19], content[:4000],
             json.dumps(embed(content))))
        n += 1
        if n % 200 == 0:
            db.commit()
            print(f"  …{n} of his messages indexed", flush=True)
    db.commit()
    return n


# ---------------------------------------------------------------- asking

def ask(question, bodies, n=5):
    db = con()
    q = embed(question)
    marks = ",".join("?" * len(bodies))
    rows = db.execute(
        f"SELECT body, ref, kind, title, when_, text, vec FROM shard "
        f"WHERE body IN ({marks})", bodies).fetchall()
    if not rows:
        print("nothing indexed yet — run: recall.py build")
        return
    scored = sorted(
        ((cosine(q, json.loads(r[6])), r) for r in rows),
        key=lambda x: -x[0])[:n]

    for score, (body, ref, kind, title, when_, text, _) in scored:
        head = f"[{score:.2f}] "
        if body == "vault":
            label = "HIS OWN WRITING" if kind == "his own" else "SECONDARY WISDOM"
            print(head + f"{label}  {ref}")
            print(f"        {' '.join(text.split())[:280]}…\n")
        elif body == "memory":
            head += f"MEMORY  {ref}" + (f"  ({kind})" if kind else "")
            print(head)
            if title:
                print(f"        {title}")
            print(f"        {' '.join(text.split())[:260]}…\n")
        else:
            print(head + f"HIS OWN WORDS  {when_}  ({ref})")
            print(f"        \"{' '.join(text.split())[:300]}…\"\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    if sys.argv[1] == "build":
        db = con()
        print("indexing memory…")
        n = build_memory(db)
        print(f"  {n} memories indexed")
        if "--vault" in sys.argv or "--all" in sys.argv:
            print("indexing the Vault (his own writings + Secondary Wisdom)…")
            v = build_vault(db)
            print(f"  {v} vault documents indexed")
        if "--history" in sys.argv or "--all" in sys.argv:
            print("indexing Sir Archive (Saba's own messages)…")
            m = build_history(db)
            print(f"  {m} messages indexed")
        print("done —", INDEX)
        return

    question = sys.argv[1]
    n = 5
    if "-n" in sys.argv:
        n = int(sys.argv[sys.argv.index("-n") + 1])
    if "--all" in sys.argv:
        bodies = ["memory", "history", "vault"]
    elif "--both" in sys.argv:
        bodies = ["memory", "history"]
    elif "--history" in sys.argv:
        bodies = ["history"]
    elif "--vault" in sys.argv:
        bodies = ["vault"]
    else:
        bodies = ["memory"]
    ask(question, bodies, n)


if __name__ == "__main__":
    main()
