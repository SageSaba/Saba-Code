# Next Load — Review of the Paused Branches
*Written 2026-07-20 (Sunday), after Saba's ruling: Sukkot fix YES, the rest PAUSE.*

## What was done today
- **Merged into main:** `claude/are-you-back-d6a0cd` — only sane session numbers (1–63) walk the Sukkot calendar. Fast-forward, one commit, no conflicts. The working copy already carried the identical fix; now it is committed law.
- **Still open from that work:** the stray **`20130911 1pm.mp3`** — the map's own blank slot, self-dated — still waits for the keeper's ruling on where it enters the calendar. The fix only keeps it safely outside; it does not place it.

---

## The real finding: the book is behind the shelf

The live Archive Viewer on the Desktop (`~/Desktop/Archive Viewer/`) has moved ahead of git main for several files. The paused branches are not simply "waiting to merge" — parts of them are already superseded by main, parts are the only git record of things now live, and parts of the live truth are in **no branch at all**.

State of each file (branch = `clean-mtnl-module-6b0be8`):

| File | main | branch | Desktop (live) | Verdict |
|---|---|---|---|---|
| connector.py | 1053 lines | 906 | 1053 = main | branch **superseded** — main already matches live |
| ask_archive.py | 600 | 373 | 600 = main | branch **superseded** |
| Ask the Archive.html | 134 | 134 | 134 = main | branch **superseded** |
| index.html (approved screen) | 308 | 313 | 313 = branch | **main is behind live**; branch holds the live version |
| screen.html | — | 244 | 244 = branch | not in main at all; branch = live |
| viewer.py | 398 | 498 | 498, **differs from branch** | main behind; live is newest; branch is a middle snapshot |
| transcript_exporter.py | — | 220 | 220, **differs from branch** | not in main; live is newest (it is running right now on port 8767) |
| Transcript 2016-12-03.html | — | 258 | = branch | branch = live |
| Sermon Reader.html | — | 118 | = branch | branch = live |
| Start-*.command, READMEs | — | yes | live copies partly differ | live is newest |

## Branch: `claude/website-review-e92192` — the Parts layer builders
One commit (July 9): `build_parts.py` (191 lines), `summarize.py` (316), `Summaries.json` (32k lines), `Summaries.md`.

**These four files exist NOWHERE else** — not on main, not on the Desktop. The Parts table itself lives in Sermons.db and the Summaries lines are the menu of the Ask app (the spread law) — but the machines that built them are only on this branch. If this branch is ever deleted, the Parts builders are gone.

**Need for next load:**
1. Rescue `build_parts.py` and `summarize.py` into main — small, clean, code only.
2. Decide separately whether `Summaries.json/md` belong in git (they are derived data, rebuildable from the db; 35k lines of weight) or whether they belong beside the db on the Desktop / in the Vault.

## Branch: `claude/clean-mtnl-module-6b0be8` — the long July run
Ten commits: Transcript Exporter, first standalone HTML transcript, Sermon Reader, Ask the Archive's first HTML, screen.html, the ArchiveScreen Xcode app, connector/ask beginnings.

**Do NOT straight-merge this branch.** A plain merge would try to drag connector.py and ask_archive.py backwards (branch versions are ~150–230 lines older than main/live). Its remaining value is:
- History: it holds the birth commits of tools now grown up on main.
- The only git copy of screen.html, index.html-as-live, and the transcript HTML pages.
- An old snapshot of ArchiveScreen — but ArchiveScreen's real home is now the Desktop (`SermonArchiveXcode`), outside git by design.

**Need for next load — the "bring the book up to date" patch (recommended instead of merging):**
1. Copy the LIVE Desktop versions into main as one focused patch: `viewer.py`, `index.html`, `transcript_exporter.py`, `screen.html`, `Transcript Exporter.html`, `Transcript 2016-12-03.html`, `Sermon Reader.html`, the three Start-commands, the two READMEs. Live is the truth; git should record it.
2. After that patch, both paused branches hold nothing main lacks (except history, which stays readable on the branch refs). They can then be retired or left standing — Saba's word.

## Housekeeping seen in passing (no action taken)
- Main working tree has untracked: `CHURCH.docx`, `I want a screen mockup….docx`, `Python/remember/Without_Walls_Broadened_Prospectus.docx`, `Python/remember/backup_db.py`. Word docs may fall under the no-cloud-documents ruling (repo vs ~/Vault) — worth one ruling.
- `com.saba.archive-*` launchd agents all healthy; church_watcher idle between its Sunday/Monday rounds, as designed.

## Suggested order for the next load
1. Bring-the-book-up-to-date patch (live Desktop → main).
2. Rescue the Parts builders from website-review.
3. Rule on the stray `20130911 1pm.mp3`.
4. Rule on Summaries.json's home and the loose Word docs.
5. Retire the emptied branches if Saba says so.

---

# THE PLAN — written 2026-07-20, waiting for Saba's go
*Saba's word: "Make the plan to do it and present to me next time." Nothing below runs until he says go, patch by patch.*

## Patch 1 — branch `claude/bring-the-book-up-to-date`
**What:** one branch off main that makes git record the live Desktop truth.

**Steps:**
1. Full comparison first: every `.py / .html / .command / .txt` in `~/Desktop/Archive Viewer/` against `main:archive-viewer/` — three piles: SAME (leave alone), AHEAD (live differs — copy in), MISSING (not in main — add). Show Saba the piles before copying.
2. Expected AHEAD/MISSING from what's already verified: `viewer.py`, `index.html`, `transcript_exporter.py`, `screen.html`, `Transcript Exporter.html`, `Transcript 2016-12-03.html`, `Sermon Reader.html`, `READ ME FIRST.txt`, both READMEs, the Start commands. Expected SAME: `connector.py`, `ask_archive.py`, `Ask the Archive.html` (verify byte-equal, then untouched).
3. **Excluded always:** databases, `logs/`, `__pycache__/`, zips, `SermonArchiveXcode/`, and the dated backup `ask_archive_before_meaning_20260718.py` (unless Saba rules it in).
4. One focused commit on the branch. Show the diff.

**Tests:**
- Byte-identity: every copied file must equal its Desktop original — and those originals are proven daily, three of them serving live right now (8765 viewer, 8767 exporter, 8768 ask).
- `py_compile` every `.py` on the branch.
- Re-test old features: curl all four live ports after the work — the patch touches only git, never the Desktop, so all four must answer unchanged.

**Merge to main only on Saba's word.**

## Patch 2 — branch `claude/rescue-parts-builders`
**What:** save the two machines that exist nowhere but the paused branch.

**Steps:**
1. Branch off main; extract `build_parts.py` and `summarize.py` from `claude/website-review-e92192` via `git show` (the branch itself stays paused, untouched).
2. **NOT** `Summaries.json` / `Summaries.md` — their home awaits Saba's ruling (derived data, rebuildable, 35k lines).
3. One focused commit. Show the diff.

**Tests:**
- `py_compile` both files.
- Read-only inspection: confirm what they open and what they write (expected: read Sermons.db, build the Parts table / Summaries lines).
- **No run against the real Sermons.db.** If Saba wants a live proof: copy Sermons.db to the scratchpad, run the builders against the copy only, compare Parts counts with the real table, then delete the copy.

**Merge to main only on Saba's word.**

## Rulings queue (Saba's calls, no branches needed)
1. ~~The stray `20130911 1pm.mp3`~~ — **RULED 2026-07-20: "Shabbath."** Seated as session 20 (2013-09-11, 1pm) — the map's blank line, the restful session (Elizabeth singing the 23rd Psalm in Hebrew, dreams and visions, the hall of remembrance). Renamed `20 Shabbath.mp3`, whisper-read, entered by `bring_sukkot_home.py`. Still open: the 1pm line in *Contents of 21 days.docx* is Saba's to fill in his own hand.
2. `Summaries.json/md` — git, Desktop, or Vault.
3. The loose Word docs in the repo root — track them, or move to ~/Vault under the no-cloud law.
4. After both patches merge: retire the two emptied branches, or leave them standing as history.

## Order of the load
Present this plan → Saba says go (per patch) → Patch 1, tests, show → his word → Patch 2, tests, show → his word → merges → rulings 1–4 as he pleases.

---

# DESIGN CAPTURED — Collection preselect buttons (Saba, 2026-07-20; awaiting his go to build)
*Saba's word: "maybe a preselect button that says CF Archive, RFOD Tapes from Saba, TRCF, EVM." Choosable gates on the asking screens — the asker picks which wing of the book supplies evidence. Fits the spread law (machine offers, never blends) and the gates design (EVM is a classification, not a top).*

**The shape:** buttons above the search/ask box — press one (or several) and the evidence hunt stays inside those collections. All-off = whole book, as today.

**The mapping layer (the real work):** a Collections map — collection name → the org banners (and title patterns) it gathers. Today's ~80 org values are two kinds mixed: true houses (SDCF 954, TRCF 846, PCCF 214, RFOD 167, XWalls 31, EVM 5...) and tape-crate labels ("Tape 10 RFOD", "Tape 3 DCF", "Tape 05 Louisville KY", per-tape rows). The map gathers the fragments under their doors WITHOUT rewriting any row's org — a law over the rows, not row-tending.

**Draft mapping for Saba's correction:**
- **RFOD Tapes from Saba** → RFOD + every "Tape NN RFOD" + Music Tapes RFOD + likely the WoG/Helm/DCF/Ashboro/Louisville tape sets (his crates — his ruling on the edges)
- **TRCF** → TRCF (incl. Zoom era)
- **EVM** → the EVM classification (make_evm_subset.py already knows this cut?) — NOT just the 5 rows bannered "EVM"
- **CF Archive** → nothing yet — that wing imports later (the 5,800-video channel); button arrives with the wing. **Saba's ruling 2026-07-20: the CF Archive's curator gets their press** — the unknown kindred archivist (@thecfarchive7816, maker possibly deceased, Facebook page linked from the channel) is to be named and honored when the wing comes in: credit carried on the wing itself (its button/door and its services' source lines), and a candidate spot on the memorial/VIP roll. Saba may attempt contact via the Facebook page — their story belongs with their work.
- (Open: where do SDCF 954, PCCF 214, XWalls, and the small houses stand — more buttons, or an "Everything else" door?)

**Where the buttons live:** Ask the Archive first (the evidence hunt); possibly the viewer search too. Patch discipline: named patch, Saba's go first.

---

# TO DO — the DV tape era (standing project, added 2026-07-20)
*Saba: "I have years on the DV." A whole wing of the book still on cassette; the Sukkot 2013 videos likely among them. Full design in memory (dv-tape-era.md).*

1. **Saba:** find the tape boxes; read the labels — dates, brand, MiniDV vs full-size vs Digital8. **Buy nothing before this.**
2. Early cheap purchase (any time): the adapter chain, ~$80–100 — Thunderbolt 3→2 + Thunderbolt 2→FireWire 800 + FW800→4-pin cable. Generic Apple gear, serves any player.
3. Format confirmed → buy a **used Sony DSR-11 deck** (~$300–800; plays both tape sizes; seller with returns). Claude hunts the right unit that week.
4. Capture via DaVinci Resolve (free) over FireWire — byte-for-byte digital, no loss. Real-time: one tape per sitting, a background season like whisper.
5. **First captures: Sukkot 2013** — transcripts already in the book; the videos need only their media_path seats. Then by Saba's ruling.
6. The rest walk the proven road: capture → Services row → whisper → RawSegments. Tapes keep dry and cool; the tapes remain the originals — raw is the base.
