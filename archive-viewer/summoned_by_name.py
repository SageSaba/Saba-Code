#!/usr/bin/env python3
"""summoned_by_name.py — find everyone the record CALLS UP by name.

Saba's insight: participants who never preach are still *named aloud* when they
are summoned — "bring the microphone to ___", "brother ___ would you pray",
"___ would you come lead us". Those moments put an otherwise-invisible person's
name into the audio. This is how Wendell "Wink" Doss (no speaker record at all)
and Barbara Young (zero credited lines) were both found.

Reads Sermons.db READ-ONLY. Writes a report file only.
"""
import sqlite3, re, json, os
from collections import Counter, defaultdict

DB   = "file:/Users/saba/Archive/Sermons.db?mode=ro"
SUG  = "/Users/saba/Archive/Archive_Suggestions.db"
OUT  = "/Users/saba/Desktop/Archive Viewer/summoned_by_name_report.md"

# phrases that mean "someone is being called up"
PHRASES = [
    "bring the mic", "bring the microphone", "give the mic", "hand the mic",
    "pass the mic", "passing the mic", "take the mic",
    "would you pray", "would you read", "would you sing", "would you lead",
    "would you come", "will you pray", "will you read", "will you sing",
    "will you come", "come up here", "come on up", "come and share",
    "let's hear from", "lets hear from", "would you share",
]
SQL_OR = " OR ".join(["LOWER(r.text) LIKE ?" for _ in PHRASES])
PARAMS = [f"%{p}%" for p in PHRASES]

# name cues: brother/sister/pastor/rev + a word, or "to <Name>"
NAME_RE = re.compile(
    r"\b(?:brother|sister|bro\.?|sis\.?|pastor|rev\.?|reverend|miss|mrs\.?|mr\.?)\s+([a-z][a-z'\-]{2,})",
    re.I)
TO_RE = re.compile(r"\b(?:mic(?:rophone)?\s+to|hear from)\s+(?:a\s+)?([a-z][a-z'\-]{2,}(?:\s+[a-z][a-z'\-]{2,})?)", re.I)

STOP = {"you","the","us","me","and","that","this","him","her","them","god","jesus","lord",
        "our","your","his","she","he","it","in","on","for","with","up","out","here","there",
        "just","now","one","who","what","all","was","are","is","be","come","pray","read","sing"}

def known_names():
    names=set()
    try:
        d=sqlite3.connect(SUG)
        for (n,) in d.execute("SELECT name FROM people"):
            for tok in re.split(r"[^A-Za-z']+", n or ""):
                if len(tok)>2: names.add(tok.lower())
        d.close()
    except Exception: pass
    c=sqlite3.connect(DB, uri=True)
    for (n,) in c.execute("SELECT full_name FROM Speakers"):
        for tok in re.split(r"[^A-Za-z']+", n or ""):
            if len(tok)>2: names.add(tok.lower())
    c.close()
    return names

def main():
    known = known_names()
    c=sqlite3.connect(DB, uri=True); c.row_factory=sqlite3.Row
    q=f"""SELECT s.preach_date, s.org, r.service_id, r.start, r.text
          FROM RawSegments r JOIN Services s ON s.ID=r.service_id
          WHERE {SQL_OR} ORDER BY s.preach_date"""
    rows=c.execute(q, PARAMS).fetchall()
    c.close()

    seen=set(); hits=[]
    for r in rows:
        t=" ".join((r["text"] or "").split())
        k=t.lower()
        if not t or any(k in x or x in k for x in seen): continue
        seen.add(k)
        cands=set()
        for m in NAME_RE.finditer(t):
            w=m.group(1).lower()
            if w not in STOP: cands.add(w)
        for m in TO_RE.finditer(t):
            for w in m.group(1).lower().split():
                if w not in STOP: cands.add(w)
        hits.append({"date":r["preach_date"],"org":r["org"],"svc":r["service_id"],
                     "at":(r["start"] or "")[:8],"text":t,"names":sorted(cands)})

    counter=Counter()
    for h in hits:
        for n in h["names"]: counter[n]+=1
    new_names=[(n,c_) for n,c_ in counter.most_common() if n not in known and c_>=2]

    with open(OUT,"w") as f:
        f.write("# Summoned by Name — sweep report\n\n")
        f.write(f"Scanned every transcript line for {len(PHRASES)} summoning phrases.\n\n")
        f.write(f"- **{len(rows)}** raw matching lines → **{len(hits)}** distinct summoning moments\n")
        f.write(f"- **{len(counter)}** distinct names cued\n")
        f.write(f"- **{len(new_names)}** names NOT already in the People Reference or Speakers (cued 2+ times)\n\n")
        f.write("## Names not yet in the book (candidates to add)\n\n")
        for n,c_ in new_names[:80]:
            f.write(f"- **{n}** — cued {c_}×\n")
        f.write("\n## Most-summoned names overall\n\n")
        for n,c_ in counter.most_common(40):
            mark = "" if n in known else "  ← NEW"
            f.write(f"- {n} — {c_}×{mark}\n")
        f.write("\n## All summoning moments (date · org · service @ time)\n\n")
        for h in hits:
            nm = ", ".join(h["names"]) if h["names"] else "—"
            f.write(f"- `{h['date']}` [{h['org'] or '?'}] svc{h['svc']} @{h['at']} — **{nm}** — {h['text'][:160]}\n")
    print(f"raw lines: {len(rows)} | distinct moments: {len(hits)}")
    print(f"names cued: {len(counter)} | NEW (not in book, 2+): {len(new_names)}")
    print("\nTop NEW names:")
    for n,c_ in new_names[:25]: print(f"  {n} — {c_}x")
    print(f"\nreport -> {OUT}")

if __name__ == "__main__":
    main()
