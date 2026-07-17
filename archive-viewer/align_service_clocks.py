#!/usr/bin/env python3
"""Align ONE service's raw lines to whisper's reread of its video, and
write TRUE clocks into RawClockLayer (replacing the even-spread guesses).

Law: RawSegments is never written. The layer holds the clocks:
  matched lines   -> method 'whisper-aligned v1'
  unmatched lines -> interpolated between matched neighbors,
                     method 'whisper-interp v1' (still estimates, keep ~)
Backup taken by the caller before running.
"""
import sqlite3, json, re, sys
from difflib import SequenceMatcher

DB = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"
SERVICE = int(sys.argv[1])
WHISPER_JSON = sys.argv[2]

def norm_words(text):
    return re.findall(r"[a-z0-9']+", text.lower())

# ---- whisper word stream: (word, time) via linear spread inside segment
wstream = []
with open(WHISPER_JSON) as f:
    data = json.load(f)
for seg in data["transcription"]:
    t0 = seg["offsets"]["from"] / 1000.0
    t1 = seg["offsets"]["to"] / 1000.0
    words = norm_words(seg["text"])
    if not words:
        continue
    step = (t1 - t0) / len(words)
    for i, w in enumerate(words):
        wstream.append((w, t0 + i * step, t0 + (i + 1) * step))

# ---- raw line word stream, tagged by line
lines = []          # [{id, words:[(idx in rstream)...]}]
rstream = []        # words in raw order
with sqlite3.connect("file:" + DB + "?mode=ro", uri=True) as db:
    for lid, text in db.execute(
            "SELECT ID, text FROM RawSegments WHERE service_id=? ORDER BY start",
            (SERVICE,)):
        idxs = []
        for w in norm_words(text):
            idxs.append(len(rstream))
            rstream.append(w)
        lines.append({"id": lid, "idx": idxs})

# ---- one global alignment of the two word streams
sm = SequenceMatcher(None, [w for w in rstream],
                     [w for (w, _, _) in wstream], autojunk=False)
r2time = {}   # raw word index -> (start, end)
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        r2time[a + k] = (wstream[b + k][1], wstream[b + k][2])

# ---- per line: clock from its matched words
rows = []     # (segment_id, start, end, method)
misses = []
for ln in lines:
    times = [r2time[i] for i in ln["idx"] if i in r2time]
    if times:
        rows.append((ln["id"], min(t[0] for t in times),
                     max(t[1] for t in times), "whisper-aligned v1"))
    else:
        misses.append(ln["id"])

# interpolate the unmatched between their matched neighbors
byid = {r[0]: r for r in rows}
ordered = [ln["id"] for ln in lines]
for i, lid in enumerate(ordered):
    if lid in byid:
        continue
    prev = next((byid[ordered[j]] for j in range(i - 1, -1, -1)
                 if ordered[j] in byid), None)
    nxt = next((byid[ordered[j]] for j in range(i + 1, len(ordered))
                if ordered[j] in byid), None)
    if prev and nxt:
        s, e = prev[2], nxt[1]
    elif prev:
        s, e = prev[2], prev[2] + 2.0
    elif nxt:
        s, e = max(0.0, nxt[1] - 2.0), nxt[1]
    else:
        continue
    byid[lid] = (lid, s, e, "whisper-interp v1")

def hms(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"

with sqlite3.connect(DB) as db:
    db.execute("DELETE FROM RawClockLayer WHERE segment_id IN "
               "(SELECT ID FROM RawSegments WHERE service_id=?)", (SERVICE,))
    db.executemany(
        "INSERT INTO RawClockLayer (segment_id, start, end, method) "
        "VALUES (?,?,?,?)",
        [(lid, hms(s), hms(e), m) for lid, s, e, m in byid.values()])
    db.commit()

n_aligned = sum(1 for r in byid.values() if r[3] == "whisper-aligned v1")
n_interp = len(byid) - n_aligned
print(f"lines: {len(lines)}  aligned: {n_aligned}  "
      f"interpolated: {n_interp}  no-clock: {len(lines) - len(byid)}")
