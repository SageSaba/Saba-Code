#!/usr/bin/env python3
"""voice_id_proof.py — proof that a per-person voiceprint works, v2.

The first pass guessed two time-points and caught mixed audio. This version
is more honest about not knowing where clean speech is: it samples MANY short
windows across each service, embeds every one, and keeps only the windows
that AGREE with each other — that cluster is the service's dominant voice
(Craig in his service, Thomas in his). Comparing those cleaned voiceprints is
a fairer test of whether the archive can tell two men apart by voice.

Reads video files only; writes nothing to any database.
"""

import subprocess
from pathlib import Path

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

SCRATCH = Path("/private/tmp/claude-501/-Users-saba-Desktop-Saba-Code-swift--claude-worktrees-where-are-we-c3a7af/60a9f262-6386-461c-ab9e-e99176f3054b/scratchpad")
CRAIG = "/Volumes/Data/Video Archive/Video Look up/2021_07_14__19_01_51Wednesday 7.14.21 with Pastor Craig Barton.hd.mp4"
THOMAS = "/Volumes/Data/Video Archive/Video Look up/2016_12_03__18_40_31Christ Fellowship.hd.mp4"

ENC = VoiceEncoder()


def windows(src, tag, starts, dur=20):
    """Embed several short windows; return their embeddings."""
    embs = []
    for i, s in enumerate(starts):
        out = SCRATCH / f"{tag}_{i}.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(s), "-t", str(dur),
                        "-i", src, "-ac", "1", "-ar", "16000", str(out)], check=True)
        try:
            embs.append(ENC.embed_utterance(preprocess_wav(out)))
        except Exception:
            pass
    return embs


def dominant_voiceprint(embs, thresh=0.85):
    """Find the tight cluster of windows that are the SAME voice (the person
    who dominates the service), and build the print from only those. Start
    from the densest window (most high-similarity neighbors), then keep only
    windows within `thresh` of it and average. Drops music, silence, and
    other voices instead of averaging them in."""
    E = np.vstack(embs)
    S = E @ E.T                                   # pairwise cosine similarity
    neighbors = (S >= thresh).sum(1)             # how many windows each agrees with
    seed = int(np.argmax(neighbors))             # the densest = the dominant voice
    keep = E[S[seed] >= thresh]                  # its cluster
    v = keep.mean(0); v /= np.linalg.norm(v)
    return v, len(keep)


def main():
    print("Sampling many windows across each service (this takes a minute)…")
    craig_starts = [420, 600, 780, 960, 1140, 1320, 1500, 1680, 1860, 2040]
    thomas_starts = [420, 600, 780, 960, 1140, 1320, 1500]

    craig_embs = windows(CRAIG, "craig", craig_starts)
    thomas_embs = windows(THOMAS, "thomas", thomas_starts)

    v_craig, n_craig = dominant_voiceprint(craig_embs)
    v_thomas, n_thomas = dominant_voiceprint(thomas_embs)
    print(f"  (Craig print built from {n_craig} agreeing windows, "
          f"Thomas from {n_thomas})")

    # Hold out: test each Craig window against the cleaned Craig print and
    # the Thomas print — a per-window verdict, which is how real scanning works.
    print("\nPer-window test — is each Craig window closer to Craig or Thomas?")
    right = 0
    for i, e in enumerate(craig_embs):
        cs, ts = float(e @ v_craig), float(e @ v_thomas)
        verdict = "Craig ✓" if cs > ts else "Thomas ✗"
        if cs > ts:
            right += 1
        print(f"  window {i:>2}: craig {cs:.3f} | thomas {ts:.3f}  -> {verdict}")

    cross = float(v_craig @ v_thomas)
    print("\n================= RESULT =================")
    print(f"  Cleaned Craig print  vs  Thomas print : {cross:.3f}   (want LOW)")
    print(f"  Craig windows correctly called Craig  : {right}/{len(craig_embs)}")
    print("------------------------------------------")
    if right >= 0.8 * len(craig_embs) and cross < 0.80:
        print("  ✅ WORKS — Craig's voice is reliably his own.")
        print("     Ready to scan other TRCF videos for that voice.")
    elif right >= 0.6 * len(craig_embs):
        print("  ~ PROMISING — mostly separates; a cleaner/longer sample")
        print("    or a stronger model (ECAPA) would tighten it.")
    else:
        print("  ✗ Still muddy — resemblyzer may be too light for these old")
        print("    recordings; ECAPA-TDNN (speechbrain) is the next lever.")
    print("==========================================")


if __name__ == "__main__":
    main()
