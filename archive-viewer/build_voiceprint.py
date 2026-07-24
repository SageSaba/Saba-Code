#!/usr/bin/env python3
"""build_voiceprint.py — build ONE person's voiceprint from a spot a witness confirmed.

The companion to scan_for_voice.py. That tool asks "where did this person speak?";
this one asks "what does this person sound like?" — and it only trusts the stretch
a human named. Given a media file and an anchor window (the seconds a witness
listened to and confirmed), it:

  1. embeds short windows INSIDE the anchor and keeps only the ones that agree
     with each other (drops a cough, a stray "amen" from the room, a music bed),
  2. sweeps the WHOLE recording and keeps every window that matches that anchor
     voice — so the print is built from all of the person's speech, not one minute,
  3. reports separation against every voiceprint already in the book (a new print
     that sits close to an existing one is a warning, not a win),
  4. prints a map of where in the recording the voice was found.

Nothing is written until --save is passed. Sermons.db (raw) is never touched;
prints live in Archive_Suggestions.db and as .npy beside it.

Usage:
  build_voiceprint.py <person_id> <media> --anchor 38:00-42:00 [--year 1973]
                      [--era "note"] [--label "Name YEAR"] [--save]
"""
import argparse, json, sqlite3, subprocess, sys, datetime
from pathlib import Path

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

SUG = "/Users/saba/Archive/Archive_Suggestions.db"
PRINTS = Path("/Users/saba/Desktop/Archive Viewer/voiceprints")
TMP = Path("/private/tmp/claude-501/voiceprint_build")
TMP.mkdir(parents=True, exist_ok=True)

WIN = 18          # seconds per window
ANCHOR_STEP = 10  # windows inside the confirmed stretch overlap, for a tight core
SWEEP_STEP = 45   # windows across the whole recording
AGREE = 0.85      # windows this close to each other are the same voice
KEEP = 0.80       # windows this close to the anchor count as the same person

ENC = VoiceEncoder()


def tsec(t):
    """'38:00' or '1:02:30' or '2280' -> seconds."""
    parts = str(t).split(":")
    return sum(float(p) * 60 ** i for i, p in enumerate(reversed(parts)))


def hms(s):
    s = int(s)
    return f"{s//3600}:{s%3600//60:02d}:{s%60:02d}" if s >= 3600 else f"{s//60}:{s%60:02d}"


def duration(src):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", src], capture_output=True, text=True)
    return float(r.stdout.strip())


def embed_window(src, start, dur=WIN):
    out = TMP / "win.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(dur),
                    "-i", src, "-ac", "1", "-ar", "16000", str(out)], check=True)
    try:
        return ENC.embed_utterance(preprocess_wav(out))
    except Exception:
        return None


def embed_many(src, starts, tag):
    embs, kept = [], []
    for i, s in enumerate(starts):
        e = embed_window(src, s)
        if e is not None:
            embs.append(e); kept.append(s)
        print(f"\r  {tag}: {i+1}/{len(starts)} windows", end="", flush=True)
    print()
    return np.vstack(embs) if embs else np.zeros((0, 256)), kept


def core(E, thresh=AGREE):
    """The tight cluster inside a set of windows = the voice that dominates it."""
    S = E @ E.T
    seed = int(np.argmax((S >= thresh).sum(1)))
    keep = E[S[seed] >= thresh]
    v = keep.mean(0)
    return v / np.linalg.norm(v), len(keep)


def stored_prints():
    db = sqlite3.connect(SUG); db.row_factory = sqlite3.Row
    rows = db.execute("SELECT id, person_id, person_name, approx_year, embedding "
                      "FROM voiceprints ORDER BY id").fetchall()
    db.close()
    out = []
    for r in rows:
        v = np.array(json.loads(r["embedding"]), dtype=np.float32)
        out.append((r["person_name"], r["approx_year"] or "", v / np.linalg.norm(v)))
    return out


def words_at(transcript, start, dur=WIN):
    """The words spoken during a window, from a whisper.cpp json — so the report
    shows not just a number but what was being said."""
    if not transcript:
        return ""
    segs = json.load(open(transcript))["transcription"]
    out = []
    for s in segs:
        o = s["offsets"]["from"] / 1000.0
        if start <= o < start + dur:
            out.append(s["text"].strip())
    return " ".join(out)


def write_windows(a, name, kept, sims, anchor_starts, A, v0, lo, hi):
    """Write every window as a playable clip plus a report listing time, score,
    verdict and words. The point is that a person can LISTEN to what the machine
    averaged together, instead of taking the number on faith."""
    out = Path(a.windows_out)
    out.mkdir(parents=True, exist_ok=True)
    a_sims = A @ v0
    rows = []
    for t, s in zip(anchor_starts, a_sims):
        rows.append((float(t), float(s), "ANCHOR"))
    for t, s in zip(kept, sims):
        rows.append((float(t), float(s), "KEPT" if s >= KEEP else "DROPPED"))
    rows.sort()

    print(f"\n  Writing {len(rows)} window clips to {out} …")
    for i, (t, s, verdict) in enumerate(rows):
        clip = out / f"{int(t//60):02d}m{int(t%60):02d}s  {s:.3f}  {verdict}.m4a"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t), "-t", str(WIN),
                        "-i", a.media, "-ac", "1", "-c:a", "aac", "-b:a", "64k", str(clip)],
                       check=True)
        print(f"\r    {i+1}/{len(rows)}", end="", flush=True)
    print()

    lines = [f"# {name} — the windows the voiceprint was built from", "",
             f"*Source: `{Path(a.media).name}`  ·  anchor (witness-confirmed): "
             f"**{hms(lo)}–{hms(hi)}**  ·  window length {WIN}s  ·  keep threshold {KEEP}*", "",
             "Every row below is a real clip in this folder — click it and hear exactly what the",
             "machine used. **ANCHOR** = inside the stretch a witness confirmed. **KEPT** = the sweep",
             "found this voice there and it went into the print. **DROPPED** = not this voice; left out.", "",
             "| time | score | verdict | what is being said |", "|---|---|---|---|"]
    for t, s, verdict in rows:
        w = words_at(a.transcript, t).replace("|", "/")[:120]
        lines.append(f"| {hms(t)} | {s:.3f} | {verdict} | {w} |")
    n_drop = sum(1 for r in rows if r[2] == "DROPPED")
    lines += ["", f"**{len(rows)} windows · {n_drop} dropped.** The dropped ones are the honest test: "
                  "if they are music, silence, or another person, the wiring is right."]
    rpt = out / "THE WINDOWS.md"
    rpt.write_text("\n".join(lines))
    print(f"  Report: {rpt}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("person_id", type=int)
    ap.add_argument("media")
    ap.add_argument("--anchor", required=True, help="confirmed stretch, e.g. 38:00-42:00")
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--era", default="")
    ap.add_argument("--label", default=None, help="filename for the .npy")
    ap.add_argument("--built-from", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--windows-out", default=None,
                    help="folder: write every window as a playable clip + a report, "
                         "so a witness can hear exactly what the print was built from")
    ap.add_argument("--transcript", default=None,
                    help="whisper.cpp json, to show the words spoken in each window")
    a = ap.parse_args()

    db = sqlite3.connect(SUG); db.row_factory = sqlite3.Row
    person = db.execute("SELECT id, name FROM people WHERE id=?", (a.person_id,)).fetchone()
    db.close()
    if not person:
        sys.exit(f"No person {a.person_id} in the People Reference.")
    name = person["name"]

    lo, hi = [tsec(t) for t in a.anchor.split("-")]
    dur = duration(a.media)
    print(f"\nBuilding voiceprint for: {name}  (person {a.person_id})")
    print(f"  media   : {Path(a.media).name}   [{hms(dur)}]")
    print(f"  anchor  : {hms(lo)}–{hms(hi)}  (the stretch a witness confirmed)\n")

    # 1 — the confirmed core
    anchor_starts = list(np.arange(lo, max(lo + 1, hi - WIN), ANCHOR_STEP))
    A, _ = embed_many(a.media, anchor_starts, "anchor")
    if len(A) < 2:
        sys.exit("Anchor stretch gave too little usable audio.")
    v0, n0 = core(A)
    print(f"  -> anchor core built from {n0}/{len(A)} agreeing windows")

    # 2 — everywhere else this voice appears
    sweep_starts = [s for s in np.arange(5, dur - WIN, SWEEP_STEP)]
    S, kept = embed_many(a.media, sweep_starts, "sweep ")
    sims = S @ v0
    hits = [(t, float(s)) for t, s in zip(kept, sims) if s >= KEEP]
    if hits:
        H = np.vstack([S[i] for i, s in enumerate(sims) if s >= KEEP])
        allE = np.vstack([H, A[A @ v0 >= KEEP]])
        v = allE.mean(0); v /= np.linalg.norm(v)
        n_used = len(allE)
    else:
        v, n_used = v0, n0
    print(f"  -> voice found in {len(hits)}/{len(kept)} windows across the recording")
    print(f"  -> final print averaged from {n_used} windows\n")

    # 3 — where the voice is (a map, in tenths of the recording)
    print("  WHERE THIS VOICE SPEAKS")
    bucket = dur / 20
    for b in range(20):
        b0, b1 = b * bucket, (b + 1) * bucket
        inb = [s for t, s in zip(kept, sims) if b0 <= t < b1]
        mark = "" if not inb else ("█" if max(inb) >= KEEP else ("▒" if max(inb) >= KEEP - .06 else "·"))
        print(f"    {hms(b0):>6}–{hms(b1):<6} {mark or '·'}   {max(inb) if inb else 0:.3f}")

    # 4 — separation against every print already in the book
    print("\n  SEPARATION (want these LOW — a high one means the book already has this voice)")
    worst = 0.0; worst_who = ""
    for who, yr, p in stored_prints():
        c = float(v @ p)
        if c > worst: worst, worst_who = c, f"{who} {yr}"
        flag = "  <-- TOO CLOSE" if c >= 0.80 else ""
        print(f"    vs {who} {yr:<6} {c:+.3f}{flag}")
    print(f"\n  closest existing print: {worst_who} at {worst:.3f}")
    verdict = ("✅ distinct — this is a voice the book did not have"
               if worst < 0.80 else "⚠️  close to an existing print — confirm before saving")
    print(f"  {verdict}\n")

    # 5 — show the windows themselves, so a witness can check the wiring
    if a.windows_out:
        write_windows(a, name, kept, sims, anchor_starts, A, v0, lo, hi)

    if not a.save:
        print("  (dry run — nothing written. Re-run with --save to keep it.)")
        return

    label = a.label or f"{name} {a.year or ''}".strip()
    npy = PRINTS / f"{label}.npy"
    np.save(npy, v)
    era = a.era or ""
    era += f" | built from {len(hits)} sweep windows + {n0} anchor windows; closest existing print {worst_who} {worst:.3f}"
    db = sqlite3.connect(SUG)
    db.execute("""INSERT INTO voiceprints
        (person_id, person_name, model, dim, embedding, built_from, n_windows,
         sep_score, npy_path, source, created_at, approx_year, era_note)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (a.person_id, name, "resemblyzer", 256,
         json.dumps([round(float(x), 6) for x in v]),
         a.built_from or f"{Path(a.media).name} @ {a.anchor}",
         n_used, None, str(npy), a.source,
         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), a.year, era.strip(" |")))
    db.commit()
    rid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    print(f"  SAVED — voiceprints row {rid}, {npy.name}")


if __name__ == "__main__":
    main()
