#!/usr/bin/env python3
"""
backup_db.py  —  Make a safe, timestamped backup of a SQLite database.

Safe by design: this ONLY reads your live database and writes a NEW copy
into a 'backups/' folder. It never modifies or deletes your real data.
It uses SQLite's online backup API, so the copy is consistent even if the
app happens to be writing at the same moment.

By default it keeps the most recent 30 backups and quietly removes older
ones (older backups are only ever deleted, never your live database).

Usage:
    python3 backup_db.py                 # backs up mymemory.db next to this script
    python3 backup_db.py /path/to/other.db
"""
import os
import sys
import sqlite3
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "mymemory.db")
KEEP = 30  # how many recent backups to retain


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB

    if not os.path.exists(db_path):
        print(f"✗ No database found at: {db_path}")
        sys.exit(1)
    if os.path.getsize(db_path) == 0:
        print(f"⚠ Database is empty (0 bytes): {db_path}")
        print("  Backing it up anyway, but there is no data in it.")

    bdir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(bdir, exist_ok=True)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.splitext(os.path.basename(db_path))[0]
    dest = os.path.join(bdir, f"{base}.backup-{stamp}.db")

    # Online backup: consistent snapshot, read-only on the source.
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    # Report
    rows = "?"
    try:
        c = sqlite3.connect(f"file:{dest}?mode=ro", uri=True)
        rows = c.execute("SELECT COUNT(*) FROM memories;").fetchone()[0]
        c.close()
    except sqlite3.Error:
        pass
    size_kb = os.path.getsize(dest) / 1024
    print(f"✓ Backup saved: {dest}")
    print(f"  ({size_kb:.1f} KB, memories rows: {rows})")

    # Prune old backups (only deletes files in backups/, never the live DB)
    bks = sorted(
        (f for f in os.listdir(bdir) if f.startswith(base + ".backup-") and f.endswith(".db")),
        key=lambda f: os.path.getmtime(os.path.join(bdir, f)),
        reverse=True,
    )
    for old in bks[KEEP:]:
        os.remove(os.path.join(bdir, old))
    kept = min(len(bks), KEEP)
    print(f"  {kept} backup(s) kept in {bdir}")


if __name__ == "__main__":
    main()
