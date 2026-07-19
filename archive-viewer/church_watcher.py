#!/usr/bin/env python3
"""The book keeps itself: after Sunday, look at the church's channel,
bring home anything new, and make it askable — no hands.

Road: yt-dlp checks @travelersrestchristfellows305 for recent videos
not yet in Services -> downloads with transcripts + info.json ->
trcf_yt_import walks them in (restartable, skips what's home) ->
meanings_build --passages teaches the index the new arrivals.

Dating law, livestream rung (2026-07-19): a LIVESTREAM's broadcast
date IS service-date evidence — the stream happened when the service
happened (unlike an upload of an old tape, which dates nothing).
trcf_yt_import reads the .info.json: was_live -> release/upload date
rules, source named; otherwise title date; otherwise undated.

Run by launchd on Sunday afternoons (and safe to run any time).
"""
import os, subprocess, sys, datetime

FOLDER = "/Volumes/Data/Video Archive/TRCF YouTube"
CHANNEL = "https://www.youtube.com/@travelersrestchristfellows305/videos"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(FOLDER, "church_watcher.log")


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def main():
    if not os.path.isdir(FOLDER):
        log("Data drive not mounted — will try again next run")
        return
    log("looking at the channel for new services…")
    r = subprocess.run(
        ["yt-dlp", "-f", "b[ext=mp4]/bv*+ba/b",
         "--merge-output-format", "mp4",
         "--write-auto-subs", "--write-subs", "--sub-langs", "en",
         "--convert-subs", "srt", "--write-info-json",
         "--playlist-end", "10",
         "--download-archive", os.path.join(FOLDER, "seen.txt"),
         "-o", "%(upload_date>%Y_%m_%d)s %(title)s [%(id)s].%(ext)s",
         CHANNEL],
        capture_output=True, text=True, cwd=FOLDER)
    tail = (r.stdout or "").strip().splitlines()[-3:]
    for t in tail:
        log("yt-dlp: " + t[:120])
    log("importing whatever landed…")
    subprocess.run([sys.executable,
                    os.path.join(HERE, "trcf_yt_import.py")])
    log("teaching the meaning index…")
    subprocess.run([sys.executable,
                    os.path.join(HERE, "meanings_build.py"), "--passages"])
    log("the book kept itself.")


if __name__ == "__main__":
    main()
