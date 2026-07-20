# The Structure
*The house's shape: how data is evaluated as it comes in and settled into the pile. Written for Saba the builder, 2026-07-20. This is the reference — when a new thing arrives, this page says where it belongs.*

---

## I. The Shelves (where things live)

**The book itself — Sermons.db (~/Archive, live):**
| Shelf | What it holds | Law |
|---|---|---|
| **RawSegments** | Every spoken line, timestamped | THE PROTECTED BASE. Never written over, never edited. Raw is the base. |
| **Services** | One row per service: date, title, media_path, org, giver, notes | PURELY SERVICES (ruled 2026-07-17, confirmed 07-20). No papers, no blankets — empty beats guessed. |
| **ChurchRecords** | The church's papers: business meetings, later letters/records | Church business is teaching — it belongs in records, never in Services. |
| **Parts** | Machine timestamps of songs/sermons inside services | Machine layer — Parts are NOT sermons. |
| **Speakers** | The voices | No blanket names. Unnamed stays unnamed until ruled. |

**The ruling layer — Archive_Suggestions.db (~/Archive, live):**
| Shelf | What it holds |
|---|---|
| **suggestions / pending / review_history** | Corrections offered (hearing, naming, meaning) — teacher outranks machine; only APPROVED rulings ride into answers. Writes touch ONLY this db. |
| **questions** | Every question asked of the site, with answer + receipts — the journal. |

**Designed, unbuilt (awaiting Saba's go):**
- **Stories + StoryMoments** — threads across services (telling/song/review/mention/GAP-with-witness).
- **Collections map** — preselect doors (CF Archive, RFOD Tapes from Saba, TRCF, EVM…) gathering ~80 banners under a few buttons; a law OVER the rows, no row retended.

**Outside the book:**
| Home | What it holds | Law |
|---|---|---|
| **/Volumes/Data (Data drive)** | Media (video/audio), db backups | Media's home; every db write is preceded by a backup here. |
| **~/Archive** | The live databases | Non-synced. |
| **~/Vault** | Documents (the credo), vault db copies | Documents NEVER in cloud; Drive is a ferry, not a home. |
| **Saba Code repo** | Code, laws, plans, Work Note, History | Every ruling and patch committed; the git log is the deep chronicle. |
| **Claude's long memory** | The laws, relationships, standing projects | Read at every session's birth; Work Note read first. |

---

## II. The Intake Road (evaluate as it comes in)

Every arriving thing walks these steps, in order:

1. **STEP ZERO — search every shelf first.** All db tables AND the memory's full body: has this thing (or a ruling about it) already been handled? (Law learned 2026-07-20, the duplicate business meeting.)
2. **Work Note before work.** Intention + steps + status on paper before a finger moves.
3. **Date it by the dating law:** folder year (hand ruling) > filename date > file stamp when it agrees > date in text. Livestream broadcast date IS the service date; old-upload dates prove nothing. Never bare file stamps.
4. **Name its KIND** — the kind decides the shelf (see the table below).
5. **Backup before any write** (Data drive shelf, named backup).
6. **If audio/video: whisper reads it** → txt beside the file per the folder law → lines into RawSegments with real clocks.
7. **Enter with a source line** — every row says where it came from and by whose ruling. Org and giver stay EMPTY unless evidenced or ruled.
8. **Verify it reads back whole.** Then mark the Work Note FINISHED and give History its entry.

**The keeper's word gates every step that changes state.** Machine offers; Saba rules.

---

## III. The Decision Table (kind → pile)

| What arrives | Where it settles |
|---|---|
| A service recording (tape, mp3, livestream, Zoom) | Services row + media on Data drive + whisper → RawSegments |
| A church paper (business minutes, letters) | ChurchRecords |
| A written sermon record (Sharon-style notes) | Services (notes carry the text + source line) |
| A correction (mishearing, wrong name, meaning) | Archive_Suggestions → Saba's review → approved rulings ride |
| A question asked | questions journal (automatic) |
| A story's telling (or a remembered gap) | StoryMoments when built; until then, the plan file holds threads on paper |
| A document of the house (credo, charters, prospectus) | ~/Vault (ferried off any cloud) |
| A design/idea spoken | Scribed into the plan file (Next Load), committed; built only on Saba's go |
| A law from Saba's mouth | Long memory + practiced immediately |
| A tape trove lead (DV boxes, PBG cousin, 4TB drive) | dv-tape-era memory + TO DO; labels first, buy for what's there |
| A new voice/curator relationship | Gates design: scoped seat, suggestion door for their wing only |

---

## IV. The Rhythm (the day's shape)

**Work Note (present) → the work (gated by Saba's word) → History (past).**
Session start: read memory → read Work Note → finish the unfinished → present what awaits the keeper.
Session end: nothing half-done unwritten; crash expected anytime, and it can't take anything.

*The structure serves the credo: the ear listens first, the mouth serves the house, the house keeps remembrance, the seed carries it on.*
