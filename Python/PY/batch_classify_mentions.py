#!/usr/bin/env python3
"""batch_classify_mentions.py — re-judge every name mention with Claude.

The name_scanner classified each of the 776 mentions quoted-vs-spoke using
regex cues (fast, ~80% right). This sends each mention's real text to Claude
via the Message Batches API (50% cheaper, async) for a truer judgment:
  - quoted   : the person is being talked ABOUT
  - spoke    : the person is being introduced / handed the service to speak
  - directing: the person is telling someone ELSE to do something (e.g. "X, come pray")
  - unclear  : not enough context

SUBMIT:  python3 batch_classify_mentions.py submit
CHECK:   python3 batch_classify_mentions.py check <batch_id>
APPLY:   python3 batch_classify_mentions.py apply <batch_id>   (writes ai_kind back)

Reads people_mentions from Archive_Suggestions.db (backed up before this ran).
Writes results only into a new ai_kind column there — never Sermons.db.
"""

import json
import sqlite3
import sys

import anthropic

SUGGEST = "/Users/saba/Archive/Archive_Suggestions.db"
MODEL = "claude-haiku-4-5-20251001"

PROMPT = """In a church service transcript, the name "{name}" appears in this line:

"{snippet}"

Was {name}:
- "spoke": being introduced or handed the service to speak/preach/pray/sing themselves
- "quoted": being talked ABOUT by whoever is speaking (a story, a mention, a reference)
- "directing": the speaker is telling {name} to do something, or {name} is telling someone else to
- "unclear": not enough to tell

Reply with ONLY a JSON object: {{"kind": "spoke|quoted|directing|unclear", "confidence": "high|medium|low"}}"""


def key():
    return open("/Users/saba/.anthropic_key").read().strip()


def submit():
    con = sqlite3.connect(SUGGEST); cur = con.cursor()
    rows = cur.execute(
        "SELECT id, name, snippet FROM people_mentions ORDER BY id").fetchall()
    con.close()
    print(f"Building a batch of {len(rows)} classification requests…")

    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    reqs = [
        Request(
            custom_id=f"m{mid}",
            params=MessageCreateParamsNonStreaming(
                model=MODEL, max_tokens=60,
                messages=[{"role": "user",
                           "content": PROMPT.format(name=name, snippet=(snippet or "")[:400])}],
            ),
        )
        for mid, name, snippet in rows
    ]
    client = anthropic.Anthropic(api_key=key())
    batch = client.messages.batches.create(requests=reqs)
    print(f"\nSubmitted.  BATCH ID:  {batch.id}")
    print(f"status: {batch.processing_status}  ({batch.request_counts})")
    print(f"\nCheck it later with:\n  python3 batch_classify_mentions.py check {batch.id}")


def check(bid):
    client = anthropic.Anthropic(api_key=key())
    b = client.messages.batches.retrieve(bid)
    print(f"status: {b.processing_status}")
    print(f"counts: {b.request_counts}")
    if b.processing_status == "ended":
        print(f"\nReady. Apply the results with:\n  python3 batch_classify_mentions.py apply {bid}")


def apply(bid):
    con = sqlite3.connect(SUGGEST); cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(people_mentions)")]
    if "ai_kind" not in cols:
        cur.execute("ALTER TABLE people_mentions ADD COLUMN ai_kind TEXT")
        cur.execute("ALTER TABLE people_mentions ADD COLUMN ai_confidence TEXT")

    client = anthropic.Anthropic(api_key=key())
    n = 0
    for result in client.messages.batches.results(bid):
        if result.result.type != "succeeded":
            continue
        mid = int(result.custom_id[1:])
        text = next((b.text for b in result.result.message.content if b.type == "text"), "")
        try:
            j = json.loads(text[text.find("{"):text.rfind("}") + 1])
            cur.execute("UPDATE people_mentions SET ai_kind=?, ai_confidence=? WHERE id=?",
                        (j.get("kind"), j.get("confidence"), mid))
            n += 1
        except Exception:
            pass
    con.commit()

    # Show where AI disagreed with the regex cue — the interesting cases.
    print(f"Applied {n} AI judgments.\n")
    print("Where AI disagreed with the quick regex classification:")
    for r in cur.execute(
            "SELECT name, kind, ai_kind, ai_confidence, substr(snippet,1,60) "
            "FROM people_mentions WHERE ai_kind IS NOT NULL AND ai_kind != kind "
            "AND ai_kind != 'unclear' ORDER BY name LIMIT 40"):
        print(f"  {r[0]:<18} was:{r[1]:<7} -> AI:{r[2]:<9}({r[3]}) …{r[4]}")
    con.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "submit"
    if cmd == "submit":
        submit()
    elif cmd == "check":
        check(sys.argv[2])
    elif cmd == "apply":
        apply(sys.argv[2])
    else:
        print("usage: submit | check <id> | apply <id>")
