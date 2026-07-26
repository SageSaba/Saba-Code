#!/usr/bin/env python3
"""match_originals.py — which meeting is this camera file?

Listens to a few short windows of an original camera recording, then asks the
book which service says the same words. Machine proposes; the witness disposes.

READS ONLY — nothing is copied, converted, or written anywhere.
"""
import json, os, re, sqlite3, subprocess, sys, tempfile
from pathlib import Path

DB = Path.home() / "Archive/Sermons.db"
MODEL = Path.home() / "ggml-large-v3-turbo.bin"
BIN = "/opt/homebrew/bin"
SCOPE = [925, 926, 933, 934]        # the four that had no words until tonight
WINDOWS = (0.20, 0.45, 0.70)        # where to listen, as a fraction of the file
SECS = 150

def dur(f):
    out = subprocess.run([f"{BIN}/ffprobe","-v","error","-show_entries","format=duration",
                          "-of","csv=p=0",f],capture_output=True,text=True).stdout.strip()
    return float(out or 0)

def hear(f, at):
    """Read one window. The room mic is quiet, so it gets normalised first."""
    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run([f"{BIN}/ffmpeg","-v","error","-y","-ss",str(int(at)),"-t",str(SECS),
                    "-i",f,"-af","loudnorm=I=-16:TP=-1.5","-ac","1","-ar","16000",wav],
                   check=False)
    out = subprocess.run([f"{BIN}/whisper-cli","-m",str(MODEL),"-f",wav,"-l","en",
                          "-nt","-np","-t","8"],capture_output=True,text=True).stdout
    os.remove(wav)
    return " ".join(l.strip() for l in out.splitlines() if l.strip())

def phrases(text, n=6):
    """Distinctive n-word runs — the fingerprints we ask the book about."""
    words = re.findall(r"[a-z']+", text.lower())
    out = []
    for i in range(0, len(words) - n, 3):
        run = words[i:i+n]
        if len(set(run)) >= 5:                      # skip 'praise the lord praise the lord'
            out.append(" ".join(run))
    return out

def ask_book(ph, c):
    hits = {}
    for p in ph:
        for sid, start in c.execute(
                "select service_id, start from RawSegments where service_id in "
                f"({','.join('?'*len(SCOPE))}) and lower(text) like ?",
                (*SCOPE, f"%{p}%")):
            hits.setdefault(sid, []).append((p, start))
    return hits

if __name__ == "__main__":
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    titles = dict(c.execute(
        f"select ID, title from Services where ID in ({','.join('?'*len(SCOPE))})", SCOPE))
    for f in sys.argv[1:]:
        d = dur(f)
        print(f"\n\033[1m{Path(f).name}\033[0m  ({d/60:.0f} min)")
        tally, evidence = {}, {}
        for w in WINDOWS:
            heard = hear(f, d * w)
            if not heard:
                print(f"  {w:.0%} — nothing heard"); continue
            print(f"  {w:.0%} — \"{heard[:88]}…\"")
            for sid, hs in ask_book(phrases(heard), c).items():
                tally[sid] = tally.get(sid, 0) + len(hs)
                evidence.setdefault(sid, []).extend(hs[:2])
        if not tally:
            print("  \033[33mno service in the book says these words\033[0m")
            continue
        for sid, n in sorted(tally.items(), key=lambda x: -x[1]):
            print(f"  \033[32m→ svc {sid}\033[0m  {n} matching phrases — {titles.get(sid,'')}")
            for p, st in evidence[sid][:3]:
                print(f"       {st}  \"{p}\"")
    c.close()
