#!/usr/bin/env python3
"""scan_trcf_speakers.py — identify the main speakers in TRCF 2023 videos.

Scans services 925-935 (the 2023 TRCF weekend) to map where Thomas Young,
Elizabeth Doss Young, and James Doss speak. These three are expected to cover
~90% of all speaking in these meetings.

Shows:
  - Speaker distribution across each service
  - Total speaking time per speaker
  - Services where each person is most present
  - Segments where all three appear together

Usage:
  scan_trcf_speakers.py [--video-root /path/to/Video Archive]

Reads media only; writes nothing.
"""
import subprocess
import sys
import json
import sqlite3
from pathlib import Path
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
import argparse

SUG = "/Users/saba/Archive/Archive_Suggestions.db"
SERMONS_DB = "/Users/saba/Archive/Sermons.db"
VIDEO_ROOT = "/Volumes/Data/Video Archive"
TMP = Path("/private/tmp/claude-501/trcf_scan")
TMP.mkdir(parents=True, exist_ok=True)

THRESH = 0.80          # confidence threshold for a match
DUR = 18               # seconds per window
TRCF_SERVICES = [925, 926, 933, 934, 927, 928, 929, 930, 931, 932, 935]  # 2023 TRCF

ENC = VoiceEncoder()

def hms(s):
    """Seconds to HH:MM:SS."""
    s = int(s)
    return f"{s//3600}:{s%3600//60:02d}:{s%60:02d}"

def duration(src):
    """Get duration of media file."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", src], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except:
        return 0.0

def load_prints(person_id):
    """Load all voiceprints for a person."""
    db = sqlite3.connect(SUG)
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT person_name, embedding FROM voiceprints WHERE person_id=?",
                      (person_id,)).fetchall()
    db.close()

    prints = [np.array(json.loads(r["embedding"]), dtype=np.float32) for r in rows]
    prints = [p/np.linalg.norm(p) for p in prints]
    name = rows[0]["person_name"] if rows else f"person {person_id}"
    return name, prints

def get_person_id(name):
    """Find person ID by name."""
    db = sqlite3.connect(SUG)
    db.row_factory = sqlite3.Row
    row = db.execute("SELECT id FROM people WHERE name LIKE ?", (f"%{name}%",)).fetchone()
    db.close()
    return row["id"] if row else None

def find_media_for_service(service_id):
    """Find the media file for a service."""
    # First check for .mkv files in Data/Video Archive
    patterns = [
        f"{VIDEO_ROOT}/WOG_*.mkv",
        f"{VIDEO_ROOT}/*/*.mkv",
        f"{VIDEO_ROOT}/*2023*.mkv",
    ]
    for pattern in patterns:
        matches = list(Path(pattern.split("*")[0]).glob(pattern.split(pattern.split("*")[0])[-1]))
        if matches:
            # Try to find the right one by checking metadata
            for m in matches:
                if m.exists():
                    dur = duration(str(m))
                    if dur > 300:  # Likely a service (>5 min)
                        return str(m)
    return None

def scan_service_for_speakers(service_id, thomas_prints, elizabeth_prints, james_prints):
    """Scan one service for the three speakers."""
    db = sqlite3.connect(SERMONS_DB)
    db.row_factory = sqlite3.Row
    svc = db.execute("SELECT title, duration FROM Services WHERE ID=?", (service_id,)).fetchone()
    db.close()

    if not svc:
        return None

    # Find media file for this service
    media_file = find_media_for_service(service_id)
    if not media_file:
        return {"service_id": service_id, "title": svc["title"], "error": "no media file"}

    dur = duration(media_file)
    if dur < 60:
        return {"service_id": service_id, "title": svc["title"], "error": "media too short"}

    # Sample windows throughout the service
    n_windows = max(10, int(dur / 180))  # ~1 window per 3 minutes
    starts = np.linspace(dur * 0.05, dur * 0.95, n_windows)

    results = {
        "service_id": service_id,
        "title": svc["title"],
        "duration": dur,
        "windows": []
    }

    for s in starts:
        wav_file = TMP / "scan_win.wav"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-ss", str(int(s)), "-t", str(DUR),
            "-i", media_file,
            "-ac", "1", "-ar", "16000", str(wav_file)
        ], capture_output=True)

        try:
            e = ENC.embed_utterance(preprocess_wav(wav_file))

            # Score against all three speakers
            thomas_score = max(float(e @ p) for p in thomas_prints) if thomas_prints else 0.0
            elizabeth_score = max(float(e @ p) for p in elizabeth_prints) if elizabeth_prints else 0.0
            james_score = max(float(e @ p) for p in james_prints) if james_prints else 0.0

            # Determine who's likely speaking (highest score above threshold)
            scores = [
                ("Thomas Young", thomas_score),
                ("Elizabeth Doss Young", elizabeth_score),
                ("James Doss", james_score)
            ]
            scores.sort(key=lambda x: x[1], reverse=True)
            speaker = scores[0][0] if scores[0][1] >= THRESH else "Unknown"

            results["windows"].append({
                "time": int(s),
                "time_hms": hms(s),
                "thomas": round(thomas_score, 3),
                "elizabeth": round(elizabeth_score, 3),
                "james": round(james_score, 3),
                "speaker": speaker
            })
        except Exception as e:
            results["windows"].append({
                "time": int(s),
                "time_hms": hms(s),
                "error": str(e)
            })

    # Tally speakers
    speakers = {}
    for w in results["windows"]:
        if "speaker" in w:
            s = w["speaker"]
            speakers[s] = speakers.get(s, 0) + 1
    results["speaker_tally"] = speakers

    return results

def main():
    ap = argparse.ArgumentParser(description="Scan TRCF 2023 videos for speaker identification")
    ap.add_argument("--video-root", default=VIDEO_ROOT, help="Path to Video Archive root")
    ap.add_argument("--services", nargs="+", type=int, help="Specific services to scan (default: all TRCF)")
    args = ap.parse_args()

    # Find person IDs
    thomas_id = get_person_id("Thomas Young")
    elizabeth_id = get_person_id("Elizabeth Doss Young")
    james_id = get_person_id("James Doss")

    if not thomas_id:
        print("❌ Could not find Thomas Young in People Reference")
        return

    print(f"\n📊 SCANNING TRCF 2023 VIDEOS FOR SPEAKER IDENTIFICATION\n")
    print(f"  Thomas Young (id {thomas_id})")
    if elizabeth_id:
        print(f"  Elizabeth Doss Young (id {elizabeth_id})")
    else:
        print(f"  Elizabeth Doss Young — NOT YET IN PEOPLE REFERENCE")
        elizabeth_id = None
    if james_id:
        print(f"  James Doss (id {james_id})")
    else:
        print(f"  James Doss — NOT YET IN PEOPLE REFERENCE")
        james_id = None

    # Load voiceprints
    thomas_name, thomas_prints = load_prints(thomas_id)
    elizabeth_prints = load_prints(elizabeth_id)[1] if elizabeth_id else []
    james_prints = load_prints(james_id)[1] if james_id else []

    print(f"\n  Thomas voiceprints: {len(thomas_prints)}")
    print(f"  Elizabeth voiceprints: {len(elizabeth_prints)}")
    print(f"  James voiceprints: {len(james_prints)}\n")

    services_to_scan = args.services or TRCF_SERVICES

    print(f"  Scanning {len(services_to_scan)} services...\n")
    print("=" * 80)

    for svc_id in services_to_scan:
        results = scan_service_for_speakers(svc_id, thomas_prints, elizabeth_prints, james_prints)

        if not results:
            continue

        if "error" in results:
            print(f"\n  svc {svc_id}: {results['title']}")
            print(f"    ⚠️  {results['error']}")
            continue

        print(f"\n  svc {svc_id}: {results['title'][:60]}")
        print(f"    duration: {hms(results['duration'])}")
        print(f"    windows sampled: {len(results['windows'])}")

        if results["speaker_tally"]:
            print(f"    speakers detected:")
            total = sum(results["speaker_tally"].values())
            for speaker, count in sorted(results["speaker_tally"].items(),
                                       key=lambda x: x[1], reverse=True):
                pct = 100 * count / total
                print(f"      {speaker:<25} {count:>3} windows ({pct:>5.1f}%)")

        print(f"\n    sample windows:")
        for w in results["windows"][:5]:  # Show first 5
            if "speaker" in w:
                print(f"      {w['time_hms']}  T:{w['thomas']:.3f}  E:{w['elizabeth']:.3f}  "
                      f"J:{w['james']:.3f}  -> {w['speaker']}")

    print("\n" + "=" * 80)
    print("\n✅ Scan complete. Check if three speakers cover ~90% of TRCF meetings.\n")

if __name__ == "__main__":
    main()
