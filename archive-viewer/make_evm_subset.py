#!/usr/bin/env python3
"""Make the gift copy: EVM.db — the EVM/RFOD subset of the master,
for giving away. The master (Sermons.db) is never touched; the subset
is derived and rebuildable — run again anytime to refresh the gift.

Included: every Services row wearing the RFOD or EVM banner, with its
RawSegments lines, Parts, Summaries, PartEvidence, the Organizations
table, and only the Speakers actually referenced. A README table
inside says what this is and where it came from.

Output: /Volumes/Data/Video Archive/SQL Files/EVM.db
NOTE for the giver: media_path points at Saba's drive — hand the
video files alongside, or the receiver gets text and clocks only.
"""
import os, sqlite3, datetime

MASTER = "/Volumes/Data/Video Archive/SQL Files/Sermons.db"
GIFT = "/Volumes/Data/Video Archive/SQL Files/EVM.db"
BANNERS = ("RFOD", "EVM")


def main():
    if os.path.exists(GIFT):
        os.remove(GIFT)
    db = sqlite3.connect(MASTER)
    db.execute("ATTACH ? AS gift", (GIFT,))
    # schema copied from the master for the tables the gift carries
    for tbl in ["Organizations", "Services", "RawSegments", "Parts",
                "Summaries", "PartEvidence", "Speakers", "RawClockLayer"]:
        sql = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (tbl,)).fetchone()[0]
        db.execute(sql.replace(f"TABLE {tbl}", f"TABLE gift.{tbl}", 1)
                      .replace(f'TABLE "{tbl}"', f'TABLE gift."{tbl}"', 1))
    marker = ",".join("?" * len(BANNERS))
    db.execute(f"INSERT INTO gift.Organizations "
               f"SELECT * FROM Organizations WHERE code IN ({marker})",
               BANNERS)
    db.execute(f"INSERT INTO gift.Services SELECT * FROM Services "
               f"WHERE org IN ({marker})", BANNERS)
    db.execute("INSERT INTO gift.RawSegments SELECT r.* FROM RawSegments r "
               "JOIN gift.Services s ON s.ID = r.service_id")
    db.execute("INSERT INTO gift.RawClockLayer SELECT l.* FROM RawClockLayer l "
               "JOIN RawSegments r ON r.ID = l.segment_id "
               "JOIN gift.Services s ON s.ID = r.service_id")
    db.execute("INSERT INTO gift.Parts SELECT p.* FROM Parts p "
               "JOIN gift.Services s ON s.ID = p.service_id")
    db.execute("INSERT INTO gift.Summaries SELECT m.* FROM Summaries m "
               "JOIN gift.Services s ON s.ID = m.service_id")
    db.execute("INSERT INTO gift.PartEvidence SELECT e.* FROM PartEvidence e "
               "JOIN gift.Services s ON s.ID = e.service_id")
    db.execute("INSERT INTO gift.Speakers SELECT DISTINCT sp.* FROM Speakers sp "
               "JOIN RawSegments r ON r.speaker_id = sp.ID "
               "JOIN gift.Services s ON s.ID = r.service_id")
    db.execute("""CREATE TABLE gift.README (line TEXT)""")
    db.executemany("INSERT INTO gift.README VALUES (?)", [
        ("EVM.db — a gift subset of the Travelers Rest archive,",),
        ("prepared by Thomas Young's archive. Contains the RFOD 1992",),
        ("Word of God meetings and EVM-banner services, with timed",),
        (f"transcript lines. Made {datetime.date.today()}. The master",),
        ("record remains with the Young archive; this copy is derived",),
        ("and may be refreshed. Video files travel separately.",),
    ])
    db.commit()
    for row in db.execute(
            "SELECT (SELECT COUNT(*) FROM gift.Services), "
            "(SELECT COUNT(*) FROM gift.RawSegments)"):
        print(f"gift built: {row[0]} services, {row[1]} lines -> {GIFT}")
    db.close()


if __name__ == "__main__":
    main()
