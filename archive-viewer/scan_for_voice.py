#!/usr/bin/env python3
"""scan_for_voice.py — find WHERE a person spoke, by their VOICE.

Loads a person's stored voiceprint(s) from Archive_Suggestions.db (voiceprints
table), samples windows across each given media file, and reports the windows
whose voice matches — i.e., where that person likely spoke. Matches against ALL
of a person's era-prints (best wins), so an aged voice still gets found. Reads
media only; writes nothing.

Usage:  scan_for_voice.py <person_id> <media_file> [<media_file> ...]
"""
import subprocess, sys, json, sqlite3
from pathlib import Path
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

SUG = "/Users/saba/Archive/Archive_Suggestions.db"
TMP = Path("/private/tmp/claude-501/voiceprint_build")   # stable: was tied to one dead session's scratchpad
TMP.mkdir(parents=True, exist_ok=True)
THRESH = 0.80          # flag windows at/above this as "likely the person"
NWIN = 10              # windows sampled per file
DUR = 18
ENC = VoiceEncoder()

def load_prints(person_id):
    db = sqlite3.connect(SUG); db.row_factory = sqlite3.Row
    rows = db.execute("SELECT person_name, embedding FROM voiceprints WHERE person_id=?",
                      (person_id,)).fetchall()
    db.close()
    prints = [np.array(json.loads(r["embedding"]), dtype=np.float32) for r in rows]
    prints = [p/np.linalg.norm(p) for p in prints]
    name = rows[0]["person_name"] if rows else f"person {person_id}"
    return name, prints

def duration(src):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of",
                        "default=nk=1:nw=1", src], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except: return 0.0

def hms(s): return f"{int(s//3600)}:{int(s%3600//60):02d}:{int(s%60):02d}"

def scan_file(src, prints):
    dur = duration(src)
    if dur < 60: return []
    starts = np.linspace(dur*0.05, dur*0.92, NWIN)
    hits = []
    for s in starts:
        w = TMP / "scan_win.wav"
        subprocess.run(["ffmpeg","-y","-v","error","-ss",str(int(s)),"-t",str(DUR),
                        "-i",src,"-ac","1","-ar","16000",str(w)])
        try:
            e = ENC.embed_utterance(preprocess_wav(w))
        except Exception:
            continue
        best = max(float(e @ p) for p in prints)
        hits.append((s, best))
    return hits

def main():
    if len(sys.argv) < 3:
        print("usage: scan_for_voice.py <person_id> <media_file> ..."); return
    pid = int(sys.argv[1]); files = sys.argv[2:]
    name, prints = load_prints(pid)
    if not prints:
        print(f"No voiceprint stored for person {pid}."); return
    print(f"Scanning for: {name}  ({len(prints)} era-print(s), threshold {THRESH})\n")
    for src in files:
        hits = scan_file(src, prints)
        if not hits:
            print(f"  {Path(src).name[:62]}: unreadable/short"); continue
        mx = max(h[1] for h in hits)
        spoke = [h for h in hits if h[1] >= THRESH]
        tag = "LIKELY PRESENT" if spoke else ("worth a listen" if mx >= THRESH-0.05 else "not found")
        print(f"  {Path(src).name[:62]}")
        print(f"    max {mx:.3f} | windows>={THRESH}: {len(spoke)}/{len(hits)}  -> {tag}")
        for s, sc in sorted(hits, key=lambda x:-x[1])[:4]:
            print(f"      candidate {hms(s)}  ({sc:.3f})")

if __name__ == "__main__":
    main()
