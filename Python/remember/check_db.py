#!/usr/bin/env python3
"""
check_db.py  —  Read-only health check for a SQLite database.

Safe by design: the database is opened in READ-ONLY mode, so running this
can NEVER modify, delete, or corrupt your data. Run it any time you want
reassurance that your memories are present and intact.

Usage:
    python3 check_db.py                 # checks mymemory.db next to this script
    python3 check_db.py /path/to/other.db
"""
import os
import sys
import sqlite3
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "mymemory.db")


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n/1:.0f} {unit}" if False else f"{n:.1f} {unit}"
        n /= 1024


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    line = "=" * 62

    print(line)
    print("  DATABASE HEALTH CHECK")
    print(f"  {db_path}")
    print(f"  checked: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
    print(line)

    # 1. File exists?
    if not os.path.exists(db_path):
        print(f"File:        MISSING  ✗   (no file at this path)")
        print(line)
        print("RESULT: DATABASE NOT FOUND ✗")
        print(line)
        sys.exit(1)

    size = os.path.getsize(db_path)
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(db_path))
    print(f"File:        OK   ({human_size(size)}, last changed {mtime:%Y-%m-%d %H:%M})")

    if size == 0:
        print("Contents:    EMPTY  ⚠   (file exists but is 0 bytes — no data)")
        print(line)
        print("RESULT: FILE IS EMPTY ⚠")
        print(line)
        sys.exit(1)

    # 2. Open READ-ONLY (cannot alter data)
    try:
        uri = f"file:{db_path}?mode=ro"
        con = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as e:
        print(f"Open:        FAILED  ✗   ({e})")
        print(line)
        print("RESULT: COULD NOT OPEN DATABASE ✗")
        print(line)
        sys.exit(1)
    print("Opened:      READ-ONLY  (this check cannot change your data)")

    cur = con.cursor()

    # 3. Integrity check
    try:
        integ = cur.execute("PRAGMA integrity_check;").fetchone()[0]
    except sqlite3.Error as e:
        integ = f"error: {e}"
    print(f"Integrity:   {'OK' if integ == 'ok' else 'PROBLEM ⚠  ' + str(integ)}")

    # 4. Tables and row counts
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name;").fetchall()]
    print("\nTables & row counts:")
    counts = {}
    for t in tables:
        try:
            counts[t] = cur.execute(f'SELECT COUNT(*) FROM "{t}";').fetchone()[0]
        except sqlite3.Error:
            counts[t] = "?"
        print(f"  {t:<20} {counts[t]}")

    # 5. Detail on the 'memories' table if present
    if "memories" in tables:
        cols = [c[1] for c in cur.execute("PRAGMA table_info(memories);").fetchall()]
        total = counts.get("memories", 0)
        print("\nMemories:")
        print(f"  total entries:     {total}")
        if "timestamp" in cols and total:
            with_ts = cur.execute(
                "SELECT COUNT(*) FROM memories "
                "WHERE timestamp IS NOT NULL AND TRIM(timestamp) <> '';").fetchone()[0]
            rng = cur.execute(
                "SELECT MIN(timestamp), MAX(timestamp) FROM memories "
                "WHERE timestamp IS NOT NULL AND TRIM(timestamp) <> '';").fetchone()
            print(f"  with timestamp:    {with_ts}")
            missing = total - with_ts
            print(f"  missing timestamp: {missing}{'   ⚠' if missing else ''}")
            if rng and rng[0]:
                print(f"  date range:        {rng[0]}  →  {rng[1]}")
        if "source" in cols and total:
            by_src = cur.execute(
                "SELECT COALESCE(source,'(none)'), COUNT(*) FROM memories "
                "GROUP BY source ORDER BY 2 DESC;").fetchall()
            print("  by source:         " + ", ".join(f"{s}={n}" for s, n in by_src))

        # Most recent entries
        if "timestamp" in cols and "content" in cols and total:
            print("\nMost recent entries:")
            rows = cur.execute(
                "SELECT timestamp, COALESCE(source,''), substr(content,1,60) "
                "FROM memories ORDER BY timestamp DESC LIMIT 5;").fetchall()
            for ts, src, snip in rows:
                ts = ts or "(no time)"
                snip = (snip or "").replace("\n", " ")
                print(f"  {ts:<20} [{src}] {snip}")

    # 6. Backups present?
    bdir = os.path.join(os.path.dirname(db_path), "backups")
    if os.path.isdir(bdir):
        bks = sorted(f for f in os.listdir(bdir) if f.endswith(".db"))
        if bks:
            newest = max(bks, key=lambda f: os.path.getmtime(os.path.join(bdir, f)))
            when = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(bdir, newest)))
            print(f"\nBackups:     {len(bks)} found   (newest: {newest}, {when:%Y-%m-%d %H:%M})")
        else:
            print("\nBackups:     none yet  ⚠   (run backup_db.py to make one)")
    else:
        print("\nBackups:     none yet  ⚠   (run backup_db.py to make one)")

    con.close()

    print(line)
    ok = (integ == "ok") and counts.get("memories", 0) not in (0, "?")
    if ok:
        print("RESULT: DATA PRESENT AND READABLE  ✓")
    else:
        print("RESULT: SEE WARNINGS ABOVE  ⚠")
    print(line)


if __name__ == "__main__":
    main()
