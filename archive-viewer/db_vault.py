#!/usr/bin/env python3
"""Vault the living databases onto a DIFFERENT physical disk.

The live Sermons.db, its dated backups, and even the Time Machine
volume all sit on the one 8 TB external (disk7). One drive failure
would take every copy at once. This script carries a consistent
snapshot of each database to the internal disk — the only other
spindle in the machine — where Time Machine then copies it again.

Uses SQLite's backup API, so the copy is sound even if taken while
the database is being written. Verifies each copy with quick_check.
Never deletes anything; old vault copies accumulate (~100 MB each)
until Saba rules on pruning.
"""
import os, sqlite3, datetime

# Each database is vaulted onto the OTHER physical disk from where it
# lives: Sermons.db (internal) -> the Data drive; EVM.db (Data drive)
# -> the internal DB Vault. Two spindles for everything, always.
SOURCES = [
    ("/Users/saba/Archive/Sermons.db",
     "/Volumes/Data/Video Archive/SQL Files/backups"),
    ("/Volumes/Data/Video Archive/SQL Files/EVM.db",
     os.path.expanduser("~/Desktop/DB Vault")),
]


def main():
    stamp = f"{datetime.datetime.now():%Y%m%d_%H%M%S}"
    for src, vault in SOURCES:
        os.makedirs(vault, exist_ok=True)
        if not os.path.exists(src):
            print("MISSING (drive unplugged?):", src)
            continue
        name = os.path.splitext(os.path.basename(src))[0]
        dest = os.path.join(vault, f"{name}_{stamp}.db")
        with sqlite3.connect(src) as s, sqlite3.connect(dest) as d:
            s.backup(d)
            ok = d.execute("PRAGMA quick_check").fetchone()[0]
        if ok != "ok":
            print("FAILED CHECK — copy not trusted:", dest, "->", ok)
            continue
        mb = os.path.getsize(dest) / 1e6
        print(f"vaulted: {os.path.basename(dest)}  {mb:.0f} MB  check: {ok}")


if __name__ == "__main__":
    main()
