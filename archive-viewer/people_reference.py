#!/usr/bin/env python3
"""people_reference.py — the People Reference goes live.

Creates a `people` table in Archive_Suggestions.db (the interpretation/
review layer — NEVER Sermons.db) and seeds it with the identities and
relationships Saba taught and corrected, so the TOOL — not just Claude's
memory — knows who these people are and stops confusing them.

Each person carries: canonical name, aliases (incl. Whisper mis-hearings),
a `family` group (the first form of the meaning-bearing connection code —
"show me the Wagner family" gathers by shared family), role, relationships,
whether they SPOKE in the record or only appear as a mention, and the
witness/source of the ruling.

Safe to re-run: rebuilds only the `people` table.

"This work is for everyone." — Saba, 2026-07-22
"""

import sqlite3

SUGGEST = "/Users/saba/Archive/Archive_Suggestions.db"
SRC = "Saba 2026-07-22"

# name, aliases, family, role, relationships, spoke, in_record, notes
PEOPLE = [
    # ---- The Wagner–Lloyd family (root to root with the Helm ministry) ----
    ("Vera Wagner-Sittler", "Vera Wagner; very Wagner; veer Wagner",
     "Wagner-Lloyd", "Rev. Loran Helm's personal secretary (decades)",
     "wife of Kenny Wagner Sr; mother of Jonathan Wagner and Lori Lloyd",
     "no", "mention", "Present at & testified in the Sukkot 2013 21-day meetings (no video); testimony moment not yet located. Whisper mis-hears her as 'very/veer Wagner'."),
    ("Kenny Wagner Sr", "Kenny Wagner",
     "Wagner-Lloyd", "father",
     "husband of Vera Wagner-Sittler; father of Jonathan Wagner; grandfather of Kenny Wagner Jr",
     "unknown", "mention", "The elder of two Kenny Wagners. Name passed to his grandson."),
    ("Jonathan Wagner", "Jonathan; Kenny Wagner's son",
     "Wagner-Lloyd", "minister; Saba trained him to program (1980s)",
     "son of Kenny Wagner Sr & Vera; husband of Yvonne Wagner; brother of Lori Lloyd; father of Kenny Wagner Jr",
     "no", "mention", "7 mentions 2013-2024, always quoted (never recorded speaking). Themes: his boy who called church 'the whipping place', and Saba teasing him about checking his watch. Restored to fellowship; dinner with Saba 2026-07-22. Candidate for Speakers table when his voice is found."),
    ("Kenny Wagner Jr", "Kenny",
     "Wagner-Lloyd", "Jonathan's oldest son",
     "oldest son of Jonathan Wagner; named after grandfather Kenny Wagner Sr",
     "unknown", "mention", "The younger of two Kenny Wagners."),
    ("Yvonne Wagner", "",
     "Wagner-Lloyd", "Jonathan's wife",
     "wife of Jonathan Wagner",
     "no", "not-found", "SOUGHT AND NOT FOUND in the record (searched hard 2026-07-22). The whole Wagner family appears except her. Do NOT confuse with Yvonne Karl (Hively). Ask Jonathan directly where she'd be named."),
    ("Lori Lloyd", "Lori Wagner; Laurie Wagner",
     "Wagner-Lloyd", "Jonathan's sister",
     "daughter of Kenny Wagner Sr & Vera; sister of Jonathan Wagner; wife of Andy Lloyd; mother of Spencer Lloyd",
     "yes", "mention", "Née Wagner. Did a DRAMATIC READING in the Sukkot 2013 21-day meetings (no video; moment not yet located — 'dramatic music' cues ~Sept 10, svc2601/2602 are the lead). Emailed Saba about a healing after prayer, 2013-09-20. Do NOT confuse with Lori Berquist."),
    ("Andy Lloyd", "Brother Andy Lloyd",
     "Wagner-Lloyd", "brother-in-law",
     "husband of Lori Lloyd; father of Spencer Lloyd; Jonathan Wagner's brother-in-law",
     "yes", "mention", "In the record 1999 (announcements) and 2013 (testified he felt hope from prayer)."),
    ("Spencer Lloyd", "Spenser Lloyd; Dr. Spencer Lloyd",
     "Wagner-Lloyd", "Pastor of Parker City Christ Fellowship (Rev. Helm's HOME CHURCH)",
     "son of Andy Lloyd & Lori Lloyd; grandson of Vera Wagner-Sittler",
     "unknown", "mention", "Record spells 'Spencer' (Saba wrote 'Spenser'). Most present of the family, 2016-2024; pursuing a doctorate ('almost Dr.', 2016). Closes the circle: his grandmother Vera was Helm's secretary; he now pastors Helm's home church (Parker City, Indiana)."),

    # ---- The OTHER Lori — a different family entirely ----
    ("Lori Berquist", "Laurie Berquist; Lori Perkins; Lori Evans",
     "Berquist", "Church of God evangelist's daughter",
     "daughter of Maurice Berquist; married name Perkins or Evans",
     "yes", "mention", "A COMPLETELY DIFFERENT Lori from Lori Lloyd (do not merge). Told the story of her father Maurice in the Sukkot 2013 meetings: services 2590 & 2591, 2013-09-06, ~14:00-27:00 (no video). Connected in the record back to 1983."),
    ("Maurice Berquist", "Maurice Bergquist; Dr. Berquist; brother Maurice",
     "Berquist", "Church of God evangelist (Anderson, Indiana); pioneer, missionary, author",
     "father of Lori Berquist",
     "no", "mention", "Real, famous public figure (Church of God / Anderson, IN). Not in this archive's own recordings but quoted by name (1981-11-04). Do NOT confuse with Maurice Sklarr (the violinist)."),

    # ---- The Hively sisters (six passes to get right, 2026-07-22) ----
    ("Virginia Wright", "Virginia Hively",
     "Hively", "pastor's wife, Maranatha Fellowship; SPEAKER (Speaker ID 3)",
     "née Hively; 1st wife of James Wright; sister of Yvonne Karl",
     "yes", "speaker", "Born Hively. Married James Wright (his 1st wife). She IS the one who has spoken (tagged Speaker ID 3, ~70 segments) — not her sister Yvonne."),
    ("Yvonne Karl", "sister Yvonne; Yvonne Hively",
     "Hively", "Virginia Wright's sister",
     "née Hively; sister of Virginia Wright; wife of Julius Karl",
     "no", "mention", "Born Hively; married Julius Karl (NOT James Wright — that was a correction). Probably has NOT spoken; the 1989 'sister Yvonne said...' is a quote of her, not her voice. Do NOT confuse with Yvonne Wagner."),
    ("Julius Karl", "",
     "Hively", "pastor/teacher (different circle from Saba's)",
     "husband of Yvonne Karl",
     "unknown", "not-found", "A pastor/teacher himself but moved in different circles — Saba: 'I just didn't travel in the same circles' — so his absence from this archive is expected, not a gap."),
    ("James Wright", "",
     "Hively", "pastor, Maranatha Fellowship; SPEAKER (Speaker ID 7)",
     "husband of Virginia Wright (Hively); Darren Powell is his 2nd-pastor successor",
     "yes", "speaker", "Pastored Maranatha Fellowship; 'asked for a thousand tongues' and saw it (2014 Life Friends notes)."),

    # ---- The three men named James (do not blur) ----
    ("James Doss", "James Everett Doss; Pastor Doss",
     "Doss", "current Pastor of TRCF (Travelers Rest Christ Fellowship)",
     "connected to the Young family (baby-in-arms prayer)",
     "yes", "mention", "Introduced to preach as 'James Everett Doss'. Found talked-about but rarely found speaking (speaker-tag gap). One of THREE different men named James — not Moore, not Ashworth."),
    ("James Moore", "",
     "Roundtree", "Brother Roundtree's associate and successor pastor",
     "associate of Brother Roundtree",
     "yes", "mention", "The 'James' of 1993-12-27 who said 'I can't preach' before Roundtree preached instead. RFOD context. NOT James Doss."),
    ("James Ashworth", "Brother James",
     "Ashworth", "minister with a healing ministry (CF / Christ Fellowship Archives)",
     "",
     "unknown", "mention", "The 'Brother James who healed' (Church of God minister, 2019-09-14) — confirmed by Saba as James Ashworth. Prayer-meeting man ('four hours a day', 1982). NOT James Doss, NOT James Moore."),

    # ---- Others corrected/added tonight ----
    ("Rev. Robert Morgan", "Rev. Morgan; brother Morgan; Robert Morgan",
     "Morgan", "Church of God evangelist",
     "directed the church to Rev. Loran Helm",
     "no", "mention", "First name ROBERT (Saba confirmed; Claude had only 'Rev. Morgan' and wrongly doubted 'Robert'). 43 written sermons in ~/Desktop/Books/Rev.Morgan. Belongs to the OLD (Helm/Vera) era — cannot have spoken of Lori Lloyd, a later generation."),
    ("Joanie Barton", "",
     "Barton", "Craig Barton's sister",
     "sister of Craig Barton",
     "unknown", "not-found", ""),
    ("Craig Barton", "",
     "Barton", "minister; Saba trained him in computers (decades ago)",
     "sister is Joanie Barton",
     "yes", "speaker", "Speaker ID 6. First VOICEPRINT built 2026-07-22 (his own TRCF service 649) — recognized at 0.95+, cleanly told from Thomas Young. The test case that proved voice-ID works."),
]


def main():
    con = sqlite3.connect(SUGGEST); cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS people")
    cur.execute("""
        CREATE TABLE people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            aliases TEXT,          -- other names / spellings / Whisper mis-hearings
            family TEXT,           -- family group: the seed of the connection code
            role TEXT,
            relationships TEXT,    -- who they connect to and how
            spoke TEXT,            -- yes / no / unknown : did they speak in the record
            in_record TEXT,        -- speaker / mention / not-found
            notes TEXT,
            source TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
    for name, aliases, family, role, rel, spoke, in_record, notes in PEOPLE:
        cur.execute(
            "INSERT INTO people (name, aliases, family, role, relationships, spoke, in_record, notes, source) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (name, aliases, family, role, rel, spoke, in_record, notes, SRC))
    con.commit()

    n = cur.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    print(f"People Reference is LIVE — {n} people now in Archive_Suggestions.db.\n")
    print("By family:")
    for fam, cnt in cur.execute(
            "SELECT family, COUNT(*) FROM people GROUP BY family ORDER BY COUNT(*) DESC"):
        names = [r[0] for r in cur.execute("SELECT name FROM people WHERE family=? ORDER BY id", (fam,))]
        print(f"  {fam:<14} ({cnt}): {', '.join(names)}")
    con.close()


if __name__ == "__main__":
    main()
