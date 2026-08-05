# Data Architecture — Inventory and Proposal

*Written while Saba drove to West Virginia, 2026-07-29. Background work only — no files
moved, renamed, or deleted; no content ruled on. Source is sacred, this is a map of it.*

---

## PART ONE — INVENTORY

### 1. ~/Archive/ — what's actually in the house

130 items on disk, 17 GB total. Underneath the clutter there are really only **eight
living databases**, plus a long tail of timestamped safety copies.

**The eight live databases:**

| file | size | what it is |
|---|---|---|
| `Sermons.db` | 1.47 GB | THE archive — RawSegments, Services, Parts, Speakers, etc. |
| `Archive_Suggestions.db` | 1.9 MB | the ruling/review layer — people, rulings, suggestions, leads, open_items |
| `Archive.db` | 414 KB | a separate, smaller schema (conversations/people/raw_segments/rulings/voiceprints/services/receipt/pruned) — not the same shape as Sermons.db, looks like an earlier or parallel build |
| `Conversations.db` | 236 KB | conversation_archive / conversation_metadata |
| `Receipt.db` | 896 KB | receipt_index / receipt_input / receipt_output / receipt_processing |
| `SabaWords.db` | 348 KB | a `RawSegments` table of its own — Saba's own words, separate from the church RawSegments |
| `Saba_Archive.db` | 5.9 MB | `meta` / `raw` — another Saba's-own-words store |
| `MyWords.db` | 9.1 MB | `turns` |

The last four (`SabaWords.db`, `Saba_Archive.db`, `MyWords.db`, and probably `Conversations.db`/`Receipt.db`) belong to the *his-own-words* line of work (see "His own words, line by line" and "The turn to his own thoughts" in memory) rather than the church sermon archive. They live in the same folder as Sermons.db but are a different body of material. Flagging only — not touched, not judged.

**The backup clutter**, cataloged not touched:

- **86 files** matching `Archive_Suggestions*` (most are `_before_<name>_<timestamp>.db` save-points from patch discipline, ~600 KB–1.9 MB each, ~59 MB total)
- **14 files** matching `Sermons_*` (full 1.4 GB copies — `Sermons_20260720_150911_before_aiconsult.db`, `Sermons_CORRUPTED_20260726.db`, `Sermons_backup_20260726_164006.db`, `Sermons_before_2023originals_20260725_182437.db`, `Sermons_before_svc687_correction_20260728.db`, etc. — **6.8 GB** total, i.e. most of the 17 GB in this folder is Sermons.db backups)
- **6 files** matching `Saba_Archive_*` (~24 MB total)
- A few loose `-shm`/`-wal` sidecar files (SQLite write-ahead-log artifacts) sitting next to `Archive_Suggestions.db` and `Sermons.db` — normal SQLite housekeeping, not orphans, but they do mean those two databases have journals that should stay next to the base file if they're ever copied.
- `Archive_Suggestions.pre-trcf-seat.db` — a named save-point outside the timestamp pattern
- Two working directories: `MyWords/` and `Rev_Helm_Memories/`
- `Session Rescue 20260725/` — a rescue folder from the stalled-API day (see commit "The day that stuck")
- Misc: `The Book of the House.docx`, `The Waiting Model.md`, a couple of README `.txt` files, `archive_mcp.py`, `archive_viewer.html`, `exclusions.json`, one `.jsonl` session transcript (15 MB)

**None of this was touched.** This is a catalog, not a cleanup — per your word, "we just need to make sure the data is there then we can do the files later."

### 2. Desktop folders with "Archive" in the name

| folder | what's in it |
|---|---|
| `~/Desktop/Archive Viewer/` | the live app — 79 items: `index.html`, `viewer.py`, `connector.py`, `ask_archive.py`, `status.py`, `work_lists.py`, voiceprint/name-scan tooling, `_backups/`, `_retired (old versions)/`, `transcripts_new/`, `faces/`, `voiceprints/`, `logs/`, and a **0-byte `Archive_Suggestions.db`** (see §4 below) |
| `~/Desktop/Archive Screen/` | the native Mac app project — `ArchiveScreen/`, `ArchiveScreen.app`, `ArchiveScreen.xcodeproj`, two dated "RETURN DOCUMENT" notes, two zipped save-points |
| `~/Desktop/🚪 Archive Door/` | a folder of **symlinks only** — the tidy front door into everything else: `CF Archive` → `/Volumes/Data/Video Archive/CF Archive`, `Live Archive — Sermons.db` → `/Users/saba/Archive`, `SQL Files — EVM + backups` → `/Volumes/Data/Video Archive/SQL Files`, `Suggestions db` → `/Users/saba/Archive/Archive_Suggestions.db`, `Vault copies` → `/Users/saba/Vault`, `WOG tapes` → `/Volumes/Data/Video Archive/WOG_`, plus `The Book of the House.docx` |
| `~/Desktop/Archive` (no extension) | a stray **0-byte file** sitting loose on the Desktop — not a folder, not a working database, just an empty file. Flagging in case it's a leftover from a `touch` or a failed drag. Not deleted. |
| `~/Desktop/Archive Viewer in Chrome.command` | a launcher script, not a folder |
| `~/Desktop/Ask the Archive.html alias` | an alias file |

The Door folder confirms the intended architecture already: one real live database (`~/Archive`), one video volume (`/Volumes/Data/Video Archive`), symlinked in from a clean front door rather than copied. That's the shape to extend, not replace.

### 3. Sermons.db schema — the raw base and what sits on it

```
RawSegments   — service_id, start, end, speaker_id, location_id, type_id, text
                (3,026,090 rows — THE protected base, never written)
Services      — preach_date, title, notes, media_path, json_path,
                org, org_source, sermon_giver, sermon_giver_source
                (2,635 rows)
Speakers      — full_name, times_appeared, segment_count (20 rows)
Locations     — short_name, description
Types         — Song, Prayer, Testimony, Scripture, Exhortation, Sermon (6 rows,
                a legacy type list — note this is NOT the same list as Parts.kind's
                song/sermon/testimony/prayer/exhortation; Scripture has no Parts
                equivalent, worth a look sometime but not urgent)
Parts         — service_id, kind, person, title, start, end,
                machine_person, machine_title (1,356 rows — the curated,
                machine-timestamped sort layer; see Task 2 document)
Organizations — code, full_name, span (4 rows only: TRCF, EVM, RFOD, XWalls —
                see PART TWO, this is the seed of the taxonomy layer)
PartEvidence  — the receipts behind a Parts kind/person/sermon_giver value
RawClockLayer — segment_id, start, end, method (a secondary/corrected clock)
Summaries     — per-service and per-part one-liners, with role/method
ChurchRecords — business-meeting minutes and other papers (kind, notes)
Meanings      — embeddings (768-dim) over summaries and raw passages, for search
SummaryVecs*  — the vector-search index tables built on Meanings/Summaries
AIConsult     — machine passes/confidence over service_id/part_id, logged
```

This is a clean, already-layered design: **RawSegments is the floor**, everything else
(Services metadata, Parts, Summaries, Meanings, AIConsult) is a reference or derived
layer that points at it by `service_id`/`segment_id`. Nothing in the schema requires
writing to RawSegments to add a new kind of tag — which is exactly the shape your
"reference files that point to the raw" instinct describes. The `Organizations` table
already anticipates a source taxonomy; it just currently only has 4 of the ~90 codes in
active use (see PART TWO).

### 4. Archive_Suggestions.db schema — the ruling layer

```
people (186), people_mentions, people_kinds, people_scan   — the person layer
rulings (22), speaker_rulings (227), book_rulings (2)       — teacher-outranks-machine
open_items (24), leads (8)                                  — the two work lists
questions (61)                                               — the Ask-the-Archive log
suggestions / pending_suggestions / review_history           — the correction pipeline
marks (2), name_reviews (2), voiceprints (13)                — smaller working tables
session_log, receipt                                         — process/audit trail
```

This is the "book of its own" layer described in the recent commit history — lists,
rulings, and leads that sit beside the raw record rather than inside it.

### 5. The dead path — diagnosed

**`/Users/saba/Desktop/Archive Viewer/Archive_Suggestions.db` is confirmed 0 bytes —
empty, broken.** `file` reports it as literally empty. It sits alongside a
`Archive_Suggestions.db-shm` (32 KB) and `Archive_Suggestions.db-wal` (0 bytes) dated
July 19, and a `Archive_Suggestions_schema.sql` (263 bytes, July 19) — so at some point
a real database here got initialized-but-emptied, or was symlinked/copied and the copy
lost its content, or the working copy was moved to `~/Archive/Archive_Suggestions.db`
(1.9 MB, alive, actively growing — last written today) and this one was simply never
cleaned up. **The live, real Archive_Suggestions.db is the one in `~/Archive/`.** The
`🚪 Archive Door/Suggestions db` symlink already points at the correct live copy, not
at this dead one — so the front door is not affected by the dead file. Any tool or
script that still hard-codes the `Archive Viewer/` path instead of following the Door
symlink would be reading zero rows silently. Not fixed, not deleted — flagged for your
word on whether to remove it or leave it as a marker.

---

## PART TWO — DESIGN PROPOSAL: mapping the source taxonomy onto `org`

**This is a proposal, not a decision.** Everything below is offered for you to rule on,
narrow, or throw out.

### What already exists

The `Services.org` column already carries a source/collection signal for every one of
the 2,635 services, and the `Organizations` table (code, full_name, span) is already
built as the lookup that would explain those codes in plain language — it's just only
4 rows deep (TRCF, EVM, RFOD, XWalls) against **82 distinct codes actually in use.**

### Proposed shape: `org` stays as-is, `Organizations` becomes the taxonomy layer

Nothing about `Services.org` needs to move or be rewritten. The proposal is to treat
`Organizations` as the reference table that groups the 82 raw codes under your five
named sources (TRCF / WOG / CFA / YouTube / new sources), by adding a `collection`
column (or a second small lookup table, `Organizations` → `Collections`) that each
`org` code points to. That's a pure reference layer — one new column, or one new small
table, no rewriting of the 2,635 `Services.org` values, no touching RawSegments.

A first-pass grouping, from what the codes and their date ranges actually show:

**TRCF** (Travelers Rest Christ Fellowship) — `TRCF` (846 rows, 2013–present),
`XWalls` (31 rows, 2011–2023, Without Walls — the successor/adjacent name),
`EVM` (5 rows, 2020, Zoom era) — these three already read as one continuous line:
TRCF's own ministry across its names and seasons.

**WOG** (Waiting on God) — a real open question, see below. The literal string `WoG`
only covers 8 rows from 1976. The much larger body of actual "Waiting on God" material
— the 1992 June tapes (`Services` IDs 894–907, 14 rows, exactly the "14 tapes
remuxed+sealed" from memory) and the 1992 "Waiting on God with Rev Loran Helm" tapes
(IDs 2352–2371, 20 rows) — are coded `org='RFOD'`, not `org='WoG'`. So today, "WOG" as
you mean it is **scattered inside the RFOD code**, distinguishable only by title text
("WOG June 1992", "Waiting on God with..."), not by org.

**CFA** (Christian Fellowship Archive, Barbara's preferred capitalization) — candidate
umbrella for the family of local "___ CF" congregation codes that aren't TRCF and
aren't the RFOD/WOG revival-meeting line: `SDCF` (954, 1973–2007), `PCCF` (214,
1982–2003), `Mentone CF` (42, 1976–1988), `KCF` (18, 1978–1997), `MFC` (14, 1979–1992),
`WSCF` (9, 1984–1987), `FCF` (9, 1983–1987), `MCF` (3, 1980–1986), `PBGCF` (4,
1987–1995), `TCF` (2, 2002), `CF` (3, 1973–1975). That's ~1,260 services — roughly
half the whole database — sitting under a family of two/three/four-letter "Christian
Fellowship" codes with no umbrella label yet. This is the strongest candidate for what
"CFA" names.

**YouTube** — no `org` code carries this; it shows up instead in `org_source`
(`"title (TRCF YouTube)"`, 13 rows) and in the CF Archive material generally
(`org_source = "filename (CF Archive)"`, 1,562 rows — by far the largest single
provenance group in the database). Whether YouTube should be its own `collection` tag
or a `provenance`/`org_source` distinction layered under TRCF/CFA is itself a question
— YouTube is a *distribution channel*, not a *congregation*, so it may not belong at
the same taxonomy level as TRCF/WOG/CFA at all. Flagging rather than deciding.

**new sources** — no mapping needed yet; the design just needs the `Organizations`/
`collection` table to be an open-ended lookup (which it already is, structurally) so a
new source is one new row, never a schema change.

### Org-code collisions and apparent historical name changes — for you to resolve, not me

- **`WoG` (8 rows, 1976) vs. the 1992 "Waiting on God" material filed under `RFOD`** —
  is WOG a *meeting type* that happened inside RFOD (so RFOD is correctly the org and
  "WOG" should be a `Parts`/tag-level label, not an org), or is WOG its own
  organization that RFOD's tape archive mis-filed? This is the single biggest open
  question in the whole taxonomy, because it decides whether ~34+ services move
  conceptually (not physically — org column unchanged either way) into WOG or stay in
  RFOD.
- **`GVCOG` (4 rows) vs. `GVCOD` (1 row)** — same three dates (1976-03-15 to
  1976-03-20), almost certainly one organization typed two ways (Church of God vs.
  a "D" typo, or two different transcription passes). Possible duplicate/typo.
- **`Mentone` (1 row, 1976-03-28) vs. `Mentone CF` (42 rows, 1976–1988)** — the single
  `Mentone` row falls inside the `Mentone CF` date range; likely the same congregation,
  just tagged at different granularity by whoever entered it.
- **`PCCF` (214 rows) vs. `PCCF at Parker City Lions Bldg` (1 row, 1992-05-21)** —
  same org, one row carries the venue in the code itself rather than in a location
  field. Not a conflict, just inconsistent granularity.
- **`MFC` (14 rows, 1979–1992) vs. `MCF` (3 rows, 1980–1986)** — different codes,
  overlapping years — could be two distinct fellowships with similar names, or a
  transposition typo on one or the other. Genuinely unclear without your knowledge of
  which fellowships these were.
- **The "Tape NN ___" org values** — `Tape 01 RFOD` through `Tape 16 RFOD` (several,
  1–5 rows each), `Tape N DCF` (12 rows, one per tape, no consolidated `DCF` code
  exists elsewhere), `Tape N Ashboro NC` (12 rows), `Tape NN Lousiville KY` (10 rows,
  note the source spelling "Lousiville"). These read like raw tape-box labels used as
  a fallback `org` value when no clean organization code was available — a different
  granularity problem than the others: real org codes describe a *congregation*, these
  describe a *physical tape*. `DCF` never appears as a plain code the way `SDCF`/`PCCF`
  do, so it's unclear whether "DCF" is a fourth CFA-family congregation that only ever
  got tape-label treatment, or something else entirely.
- **168 services with a blank `org`** (2011-09-17 to 2014-01-04, `org_source` also
  blank) — this window sits right before TRCF's 2013-09-05 formal start and overlaps
  it. These may be pre-TRCF home-meeting material that predates the org being named,
  or simply not yet classified. Worth a pass once WOG/CFA are settled, since some of
  these may turn out to be early TRCF.

None of the above was changed. `org` values are exactly as they were before this
inventory ran.

---

**Files referenced:** `~/Archive/Sermons.db`, `~/Archive/Archive_Suggestions.db`,
`~/Desktop/Archive Viewer/`, `~/Desktop/Archive Screen/`, `~/Desktop/🚪 Archive Door/`,
`~/Desktop/Archive` (stray empty file), `~/Desktop/Archive Viewer/Archive_Suggestions.db`
(confirmed dead/empty).
