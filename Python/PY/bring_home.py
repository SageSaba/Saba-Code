#!/usr/bin/env python3
"""bring_home.py — carry a file into the archive without ever risking the original.

Built 2026-08-07 after doing this same dance five times by hand in one day:
Music Machine (Saba's first video, the only copy), the Thorns collection, Rev.
Morgan's 41 writings, the TRCF Zoom recordings, the 2013 broadcast. Every time:
copy it somewhere safe, prove the copy is byte-identical, never touch what was
there. This is that, as a tool.

The law it keeps (standing ruling #3): keep the original so someone else can see
and understand why that was chosen. Nothing is moved. Nothing is deleted.
Nothing is overwritten — if the destination exists, it stops.

It also fixes a real trap found the same day: files written by old Flash-era
streaming software carry an "f4v" container brand, and strict players (QuickTime,
phones) refuse to open them even though the video inside is ordinary H.264.
--remux repackages the container ONLY — not one frame is re-encoded, and the
original file stays exactly as it was.

Usage:
    bring_home.py <source> <destination>
    bring_home.py <source> <destination> --remux     # also write a playable copy
    bring_home.py <source> <dest-directory>/         # keep the original filename
"""
import hashlib, os, shutil, subprocess, sys


def md5(path, chunk=1024 * 1024):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


def container_brand(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format_tags=major_brand",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return out or None
    except Exception:
        return None


def remux(src, dest):
    """Repackage the container. No re-encode: -c copy means the stream is
    carried across bit for bit."""
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-c", "copy", "-movflags", "+faststart",
         "-brand", "mp42", dest, "-loglevel", "error"], check=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_remux = "--remux" in sys.argv
    if len(args) != 2:
        print(__doc__)
        return 1

    src, dest = args
    if not os.path.exists(src):
        print(f"source does not exist: {src}")
        return 1

    if dest.endswith(os.sep) or os.path.isdir(dest):
        dest = os.path.join(dest, os.path.basename(src))
    if os.path.exists(dest):
        print(f"STOPPED — destination already exists, nothing overwritten:\n  {dest}")
        return 1

    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)

    size = os.path.getsize(src)
    print(f"copying {human(size)} …")
    shutil.copy2(src, dest)

    a, b = md5(src), md5(dest)
    if a != b:
        print(f"CHECKSUM MISMATCH — the copy is NOT identical.\n  source {a}\n  copy   {b}")
        print("The original is untouched. Delete the bad copy and try again.")
        return 1
    print(f"verified identical — md5 {a}")
    print(f"  original (untouched): {src}")
    print(f"  archive copy:         {dest}")

    brand = container_brand(dest)
    if brand and brand.strip().lower().startswith("f4v"):
        print(f"\nNOTE: container brand is '{brand.strip()}' (Flash-era). Some players "
              f"will refuse to open it.")
        if not do_remux:
            print("      Re-run with --remux to also write a playable copy.")

    if do_remux:
        root, ext = os.path.splitext(dest)
        fixed = f"{root}_playable.mp4"
        if os.path.exists(fixed):
            print(f"playable copy already exists, left alone: {fixed}")
        else:
            print("\nremuxing (container only — no re-encode) …")
            remux(dest, fixed)
            print(f"  playable copy:        {fixed}")
            print(f"  brand now:            {container_brand(fixed)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
