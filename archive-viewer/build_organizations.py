#!/usr/bin/env python3
"""build_organizations.py — the banner layer over Services.

Saba's law (2026-07-15): every service belongs to one of three banners —

    TRCF  Travelers Rest Christ Fellowship   (2014-2025)
    EVM   Evangel Voice Missions             (Beaver City 2020; anything ZOOM)
    RFOD  Revival For Our Day                (1992)

This script creates the Organizations reference table and marks each
Service with its banner. It is a curated LAYER, in the spirit of the
Parts table:

  - RawSegments is never touched. Services gains two columns (org,
    org_source); nothing existing is altered or removed.
  - Assignment by rule, in rule order: Beaver City / Zoom -> EVM,
    1992 -> RFOD, 2014 or later -> TRCF. Older services (1986, 1990,
    1997, 1999 eras) get NO banner until Saba rules on them.
  - Hand corrections are law: set org_source to 'hand' on a row and
    this script will never overwrite it, no matter how often it re-runs.
  - The whole layer is removable: DROP TABLE Organizations and ignore
    the two columns, and the database is exactly as it was.

Run:  python3 build_organizations.py
"""

import sqlite3
import sys

DB_PATH = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"

BANNERS = [
    ("TRCF", "Travelers Rest Christ Fellowship", "2014-2025"),
    ("EVM",  "Evangel Voice Missions",           "Beaver City 2020; Zoom era"),
    ("RFOD", "Revival For Our Day",              "1992"),
]


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # 1. The reference table (INSERT OR IGNORE keeps any hand edits).
    cur.execute("""CREATE TABLE IF NOT EXISTS Organizations (
                       code      TEXT PRIMARY KEY,
                       full_name TEXT NOT NULL,
                       span      TEXT
                   );""")
    for code, name, span in BANNERS:
        cur.execute("INSERT OR IGNORE INTO Organizations VALUES (?,?,?);",
                    (code, name, span))

    # 2. The two columns on Services (added once; harmless if present).
    have = {r[1] for r in cur.execute("PRAGMA table_info(Services);")}
    if "org" not in have:
        cur.execute("ALTER TABLE Services ADD COLUMN org TEXT;")
    if "org_source" not in have:
        cur.execute("ALTER TABLE Services ADD COLUMN org_source TEXT;")

    # 3. Assignment by rule — never where a hand has ruled.
    guard = "(org IS NULL OR org_source IS NULL OR org_source = 'rule')"

    # EVM: Beaver City sessions, and anything that came through Zoom.
    cur.execute(f"""UPDATE Services
                    SET org='EVM', org_source='rule'
                    WHERE {guard}
                      AND (title LIKE '%beaver city%' COLLATE NOCASE
                           OR title LIKE '%zoom%' COLLATE NOCASE
                           OR media_path LIKE '%zoom%' COLLATE NOCASE);""")

    # RFOD: the 1992 revival.
    cur.execute(f"""UPDATE Services
                    SET org='RFOD', org_source='rule'
                    WHERE {guard} AND org IS NULL
                      AND strftime('%Y', preach_date) = '1992';""")

    # TRCF: the Travelers Rest years.
    cur.execute(f"""UPDATE Services
                    SET org='TRCF', org_source='rule'
                    WHERE {guard} AND org IS NULL
                      AND preach_date >= '2014-01-01';""")

    con.commit()

    # 4. The tally.
    print("Banner layer built. Services by banner:")
    for org, n in cur.execute(
            "SELECT COALESCE(org,'(unassigned)'), COUNT(*) FROM Services "
            "GROUP BY org ORDER BY 2 DESC;"):
        print(f"  {org:<14} {n}")
    hand = cur.execute(
        "SELECT COUNT(*) FROM Services WHERE org_source='hand';").fetchone()[0]
    print(f"  hand-ruled     {hand}  (never overwritten by this script)")
    con.close()


if __name__ == "__main__":
    sys.exit(main())
