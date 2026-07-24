# Work Note
*Written before starting, per Saba's law of 2026-07-20: the intention goes on paper first, so a shutdown never loses the thread. Saba: "I fully expect to crash anytime" — this note always carries the full standing state.*

## 📌 PARKED — details Saba spoke 2026-07-24, captured so they are not lost, NOT to be worked yet

- **Barbara's dad was Max Mullins.** Evidence line already in the record: svc 682, 2016-11-26 — "Barbara's dad got me a job in the construction crew." Saba's word, 2026-07-24.
- **Bea Mullins and the whole Mullins family need correcting** in the People Reference.
- **Virginia Wright shared in a service; her sister came to hear.** Witness: Saba, 2026-07-24. ONE witness — a claim, not yet seated. ("Sheridan" was a dictation mis-hearing of "shared in"; there is no Sheridan.)
- **Relationship audit owed:** all 47 relationship entries checked for (a) an evidence line, (b) any claim wearing Saba's name that he did not say. The Yvonne/Virginia "sisters" claim was exactly that and has been named false — "sister" is the family of God, used 3,903 times.

## 🎙️ IN PROGRESS — 2026-07-24 · MARY WEBSTER'S VOICEPRINT (person #48, VERY VIP)

**Intention:** build the voiceprint of Mary Webster — E. Stanley Jones's secretary, the one who introduced Rev. Helm as "Melchizedek." Saba confirmed her voice by his own ear on 2026-07-24 (he has heard her in person). She becomes the **oldest voice in the index (1973)** and the head of the lineage: Jones → Webster → Helm → Saba.

**Source:** svc **2499** (SDCF, 1973-01-11, "Mary Webster"), 49:47.
- media: `/Volumes/Data/Video Archive/CF Archive/2026_03_31 SDCF_01_11_1973_Mary_Webster [kSJ9yuDe424].webm`
- 16k mono already extracted: `~/Desktop/Archive Viewer/transcripts_new/svc2499.wav`
- transcript (file only, NOT in Sermons.db): `svc2499_MaryWebster.json/.srt`, 933 segments
- **anchor stretch: 38:00–42:00** — a long clean solo monologue (the $27 airport-parking story, "Well Mary, Judas sold me for 30 pieces of silver" @ 40:52). This is the region Saba listened to and confirmed.

**Steps, in order:**
1. Back up `~/Archive/Archive_Suggestions.db` → `Archive_Suggestions_before_marywebster_<stamp>.db` ☐
2. Sample 18s windows across the whole service; build the print from the **38:00–42:00 anchor cluster** (dominant-voice method from `voice_id_proof.py`), drop singing/other voices ☐
3. Prove it: separation against all 6 existing prints (want LOW, esp. vs Barbara Young + Jenny Light — the other women), and a map of where she speaks across the 49 minutes ☐
4. Save `voiceprints/Mary Webster 1973.npy` + insert one `voiceprints` row (person_id 48, approx_year 1973) ☐
5. Append the result to her `people.notes`; History.md entry; mark FINISHED ☐

**Laws honored:** `Sermons.db` (raw) is NEVER written — the transcript stays a file until Saba's separate word ([[raw-is-the-base]]). All writes go to `Archive_Suggestions.db` after its own timestamped backup ([[patch-discipline]]).

**If found half-done:** the `.db` backup named above restores the review DB; `.npy` files are additive and harmless; nothing else on disk is altered.

## 🕯️ SHABBAT CLOSE — 2026-07-23 · RESUME AFTER SATURDAY SUNDOWN

**➡️ READ THIS FIRST:** `~/Desktop/Saba Code Docs/Documentation/START HERE — Shabbat Handoff 2026-07-23.md`
It holds the full picture in a clean format: where the book stands (42 people, 11 VIPs, 6 voiceprints, 7 faces), what was built, **all issues**, **all ideas**, **the thoughts/principles learned**, the ordered next steps, and the backup record. Everything below in this Work Note remains true as history; that document is the starting point.

**Verified before close:** both DBs pass integrity checks · raw `Sermons.db` untouched (modified Jul 21) · local backup `Archive_Suggestions_SHABBAT_20260723_191610.db` · second-drive backup `/Volumes/ACASIS/Archive Backups/20260723_191610/` (27 MB).

**Ran tonight:** the **summoned-by-name sweep** — 2,251 moments where the record calls someone up by name, 53 new candidate names. Report: `~/Desktop/Archive Viewer/summoned_by_name_report.md`.

## 🤔 THINGS TO CONSIDER (Saba's list — nothing here runs without his word)

1. **Wendell "Wink" Doss — give him a voiceprint.** James Doss's paternal grandfather. Clean 2-minute prayer at **svc 1946 (1989-03-08) @ 18:57–~21:00**, summoned by nickname ("bring the microphone to Wendell Doss, brother Wink would you pray for us"). Also named 1980-08-10 svc 2261 @27:17 as "another Nathanael." He has **NO speaker record** — invisible to name search. Steps: add to People Reference (James's grandfather; "was then a chairman" of RFOD), build print from the prayer, then **scan the archive for everywhere else he spoke.** ([[first-invited-helpers]])
2. **LINEAGE BOOKS → EPUB → searchable with the tapes.** Saba can convert his ebooks with **Calibre**; hand Claude the EPUBs and they can be read, searched, and cross-referenced *against the archive* — e.g. find where Rev. Helm echoes E. Stanley Jones, or where Watchman Nee's language shows up in a 1976 sermon. This is the [[spiritual-grandparents]] "collect and reframe" work with the sources finally searchable. (Already on disk: two *A Voice in the Wilderness* .epub files in `~/Desktop/Books/AVITW 130221/`.) NOTE: Claude will not assist with removing DRM from purchased books; DRM-free/converted files only.
3. **Build the "SUMMONED BY NAME" search.** It just proved itself — it's how Wendell was found. Scan for summoning phrases ("bring the microphone to…", "brother ___ would you pray", "would you come lead us") to surface participants who never preach and are otherwise invisible. High value, now demonstrated.
3. **Michele Worley — still needs a voiceprint.** The 1:47:00 attempt was actually Rev. Helm on camera; that print was deleted. Need a spot where SHE is speaking. Also: what did "connects to the review" mean?
4. **Confirm the Doss/Young family details:** order of Kathy's surnames (Richardson / Doss / Young), and how David Young ("kinda") actually ties to Saba's Young line.
5. **Job 2 — collection-aware answers** (paused mid-build): TRCF leads, un-reviewed CF Archive held back. ([[archive-collections]])
6. **Jerry Keller** — deferred until he visits; the AVITW/EVM notes stay on the shelf (Saba sends, never Claude).

## ⭐ RESTART HANDOFF (2026-07-23 late) — Saba is restarting the session with a new CLI flag. Read this + MEMORY.md first.

**Nothing is half-done; safe to restart.** All DB writes committed (backups made before each in `~/Archive/`); memory + skills written to disk; the `caffeinate` process dies with the session (that's intended).

**THE BIG NEW CAPABILITY built this session — the VOICE INDEX (find people by VOICE, not just typed name):**
- `voiceprints` table in Archive_Suggestions.db (interpretation layer; embeddings point back to raw, never alter it) + reusable tool `~/Desktop/Archive Viewer/scan_for_voice.py`. Prints saved as `.npy` in `~/Desktop/Archive Viewer/voiceprints/`; face portraits in `~/Desktop/Archive Viewer/faces/`.
- **5 confirmed voiceprints:** Daniel Light (2016), **Rev. Loran Helm (1992)**, Reimar Schultze (1992), Edward Helm (1992), Jenny Light (1992-singing). Helm's print MAPS across all 6 WOG-1992 tapes scanned (0.87–0.99) — pipeline validated.
- **People Reference now 32 people, 6 VIPs, 2 faces** (Archive_Suggestions.db `people`; new cols `vip`, `photo_path`). Voice-aging designed: many era-prints per person (a voice timeline). Full detail: **[[daniel-light]]** memory.
- **THE LOOP (working, with Jonathan present as witness):** scan_for_voice.py finds a window matching nobody known → `open "http://localhost:8765/video/<svc_id>#t=<seconds>"` (viewer serves seekable video) → Saba/Jonathan SEE the face + name him → build his print from that spot. Witness names, machine keeps ([[keepers-correction-method]]).

**IN-FLIGHT / NEXT (un-pause here):** naming the WOG-1992 Tape 1 (svc 894) platform with Jonathan — next unplaced-voice candidates ~77:00 and ~1:47:00. Also open: Job 2 collection-aware answers (paused mid-build, [[archive-collections]]); the "summoned by name" search (pianists name themselves when called up); confirm Rebecca Helm's father (Edward vs Rev.Helm) and the "twin".

**RE-ESTABLISH AFTER RESTART:** (1) run **/caffeinate** (old one released when session ended; new skills `/caffeinate` + `/decaf` live in `~/.claude/skills/`). (2) Servers if down — start via **Book of Remembrance.app** / `launch_book.sh`: viewer **8765** (video), connector 8766, ask **8768** (spell_correct now wired in), One Box **8790**. (3) Voice tools + DBs persist on disk; only the session `scratchpad/` (one-off print-building scripts) is lost — `scan_for_voice.py` is the durable tool.

**Also done this session:** AVITW Living Book read-along COMPLETE (26 ch, `~/Desktop/AVITW Living Book/`); AVITW `book_rulings` (ch10 rod / ch25 watchman) reframed as EVM-board PROPOSALS + a James/Jerry handoff note drafted (**Saba sends, never Claude** — [[book-rulings-layer]]); desktop/Saba Code Docs cleanup (Lineage/Communication/Documentation); Jerry demo deferred "until he comes."

## STANDING STATE (as of 2026-07-23) — cleanup, the Living Book, read-along; next: jobs 1 & 2

Since the 2026-07-20 note below, a great deal landed (all on the real Desktop, Saba's everyday folders):
- **People Reference BUILT & LIVE** — Archive_Suggestions.db `people` table, ~20 people (three Jameses; Wagner–Lloyd–Hively family; two Loris/Yvonnes/Kennys; Robert Morgan; Maurice Berquist; etc.). Also built: `name_scanner.py` (quoted vs spoke), `voice_id_proof.py` (voiceprint — recognized Craig Barton), `batch_classify_mentions.py` (applied).
- **`spell_correct.py` BUILT & TESTED** (isreal→israel, jerusaelm→jerusalem) — NOT yet wired into ask_archive.py → **JOB 1 below.**
- **Cleanup done (nothing deleted):** `~/Desktop/Saba Code Docs/` organized into **Lineage/**, **Communication/**, **Documentation/** (each w/ README) + a top-level map; `~/Desktop/Archive Viewer/` got **WHAT IS WHAT.md**, **_backups/**, **_retired (old versions)/** (the Xcode version + dead HTML prototypes); loose Desktop screenshots swept into Screenshots/.
- **AVITW Living Book BUILT** — `~/Desktop/AVITW Living Book/`: Helm's *Voice in the Wilderness* read aloud (26 ch, 633MB), brand-styled (gold-on-dark) player, **read-along v2** (chapters left, Daniel's transcript scrolls with his voice, tap-to-jump, read-along toggle). **Transcription batch RUNNING** in background (local Whisper; fills remaining chapters + rebuilds itself). See [[avitw-living-book]]. DEFERRED per Saba ("none right now"): sending to Jerry Keller; Hebrew AI translation (must be labeled AI-translated); xwalls.net hosting (need to know what the site runs on; "hold Local").
- **Lineage source texts gathered** (Jones/Nee/Helm + Helm×Nee×Jones cross-refs) in Saba Code Docs/Lineage/. **Without Walls logo mark** brief on file (designer IzzyInk). **Video copy to ACASIS VERIFIED** — 10,205 files, both drives match; fast drive ready to serve One Box video.

## NEXT — DOING JOBS 1 & 2 NOW (Saba: "do both 1 and 2, after documenting")

**JOB 1 — wire the spell-fix into the answer engine.**
- Files: LIVE `~/Desktop/Archive Viewer/ask_archive.py` (spell_correct import already added at top) + `spell_correct.py` (built/tested) + `archive_vocab.json`.
- Steps: (1) dated `.bak` of ask_archive.py; (2) at the topic-word extraction (~line 354, `topic = [w for w in qwords ...]`) run each search word through `spell_correct.correct_word` before the `LIKE` search; keep the original too; (3) restart 8768; (4) re-test — "Isreal"→finds Israel; a correctly-spelled word unchanged; old features still work; (5) commit + History.
- Safety: touches ONLY ask_archive.py (answer engine); never Sermons.db; `.bak` restores.

**JOB 2 — collection-aware answers (TRCF leads, CF Archive held back).**
- The bug ([[archive-collections]]): un-reviewed **CF Archive (1,559 svcs**, incl. Saba's old Morgan book-prep) outweighs reviewed **TRCF (799)**, so keyword search over-surfaces it — the "Israel defaulted to Robert Morgan" problem ([[israel-heart]]).
- Steps: (1) derive each service's **collection + review state** from `Services.media_path`/`org` (TRCF = reviewed/video; CF Archive = un-reviewed; WOG; etc. — mapping already worked out this session) and store as a lookup — in **Archive_Suggestions.db or a computed map, NEVER written into Sermons.db** ([[raw-is-the-base]]); (2) rank/label answers — LEAD with reviewed TRCF, mark CF-Archive/book-prep as "un-reviewed, older separate material," never the headline; (3) weigh by *who taught it & how much*, not one passage's density; (4) re-test the Israel question — Saba's TRCF teaching should lead, Morgan shown as roots.

## STANDING STATE (as of 2026-07-20, after Shabbath came home)
- **Nothing is half-done.** 2637 duplicate resolved: removed 2026-07-20 by Saba's ruling ("Church business is a sermon (teaching) so should be in records") — minutes stand in ChurchRecords row 1.
- Sukkot 2013: COMPLETE — 51 sessions home incl. session 20 "Shabbath" (service 2636). Videos still missing: leads = Elizabeth's 4TB drive OR the DV tapes.
- THE PLAN (two patches: bring-the-book-up-to-date, rescue-parts-builders) is written in "Next Load — paused branches review.md" — awaits presentation + Saba's go. Branches website-review + clean-mtnl stay PAUSED.
- DV tape era: standing to-do (same file + task list) — Saba finds boxes/labels first; buy nothing but the ~$80 adapter chain.
- Sharon's notes: 169 in Services; 8 undated 2013 files await dating-by-text or ruling; Dec 17 2011 stray to re-chase. Business meetings live in ChurchRecords (Saba's 2026-07-17 ruling).
- Rulings open: Summaries.json home; loose Word docs in repo root; branch retirement; video player on the reading pages (patch candidate, unnamed).
- **FINDING 2026-07-20 (the Joe discovery):** Joe Nance teaching PIERCED EARS (the credo's own theme, same night it was written) is IN THE BOOK — service 2021-07-03 "Saturday Night Waiting 7.3.21" (~11:36 of 1:10:59, Zoom recording, plays fine in viewer). BUT the service wears the ALL-ZERO COUNTERFEIT CLOCKS (every line stamped 00:01) — words unanchored, moments unmarkable. TWO PATCHES QUEUED for Saba's go: (a) clock repair for Zoom-era services (clock_repair_batch.py / align_service_clocks.py exist; whisper re-read with real clocks, lawful re-entry, counterfeits retired by ruling); (b) the "mark this moment" button on the viewer (timestamp+note → receipt/Portion/StoryMoment — the Portions button, necessity proven tonight). Also: the "EVM meetings" Saba found may partly BE these Zoom-era waitings / Paul Canada's copies of them.
- **FINDING 2026-07-20 (Saba: "No video"):** the approved screen's player gets 404 from /video/2636 AND /video/2604 — the Sukkot tapes are not being served (likely: viewer serves media only from its allowed root, and the mp3s live in ~/Desktop/Sermon Notes, outside it — unconfirmed). Whether older webm services still play: NOT yet tested. Search works (found Shabbath's "almost doze" moment perfectly). Needs a named patch on Saba's word; diagnosis paused at his stop.
- **CONFIRMED 2026-07-20:** questions asked of the site ARE saved — Archive_Suggestions.db `questions` table, 9 journaled with full answers + receipts.
- **THE SILENT YEAR (found 2026-07-20, via Saba's Carpenter's Story memory):** the book holds NO services from 2021-07-15 to 2022-06-08 — eleven months missing (Zoom-era tail; Wed+Sat were TRCF on Zoom). Saba remembers sharing the Carpenter's Story on the Wednesday PM before Elizabeth's 2022-06-10 telling (service 2528, ~8:40) — that Wednesday (2022-06-08) is in the gap. HUNT NEEDED: were the Zoom services recorded? Where do recordings live (Zoom cloud expires; local recordings folder; OneDrive; unsearched drives)? Saba's answer decides the hunt.

## STATUS: FINISHED 2026-07-20 — MARK button live on the approved screen (commit 33f1ca6); first mark: Joe, pierced ears, 644 @ 11:36
Files named: LIVE ~/Desktop/Archive Viewer/viewer.py + index.html (the approved screen — Saba-named patch). Marks are WRITES → they go to Archive_Suggestions.db (never Sermons.db) in a new `marks` table: service_id, seconds, note, created_at. Steps: (1) dated .bak save-points of both live files ☐ (2) backup Archive_Suggestions.db, create marks table ☐ (3) viewer.py: POST /mark + GET /marks ☐ (4) index.html: Mark button by the transport, saves current video second + optional note, shows the reference back ☐ (5) restart viewer via launchd, test mark + re-test search/play ☐ (6) commit patched files to repo, History entry, FINISHED ☐. If found half-done: .bak files restore the live screen; launchctl kickstart -k gui/$(id -u)/com.saba.archive-viewer reloads it.
## PREVIOUS: FINISHED 2026-07-20 — The Structure.md written and committed (e2e233f)
## PREVIOUS: FINISHED 2026-07-20 — History.md created, seeded, committed (972fc04)
## PREVIOUS: FINISHED 2026-07-20 — 2637 removed, minutes stand in ChurchRecords row 1
Saba's ruling 2026-07-20: "Church business is a sermon (teaching) so should be in records" — the minutes STAND in ChurchRecords row 1; my duplicate Services row 2637 comes OUT. Steps: (1) fresh backup ☐ (2) confirm 2637 has no RawSegments (none were inserted) ☐ (3) DELETE Services row 2637 only ☐ (4) verify: minutes whole in ChurchRecords, 2637 gone, Services count back to 2636 ☐ (5) mark FINISHED. If found half-done: backups Sermons_*_before_bizmeeting.db (pre-insert) and Sermons_*_before_2637_removal.db (pre-delete).
**Date:** 2026-07-20
**Work:** Bring the business meeting notes into the book (Saba's ruling: "I wanted business meetings in")

**The piece:** `~/Desktop/Sermon Notes/2013/Business Meeting Notes/July 11, 2012 Post Service Meeting Notes.docx` (85KB, the only business-meeting file found in Sermon Notes)

**Dating evidence:** filename says July 11, 2012; file timestamp agrees (Jul 11 2012); shelf (2013 folder) disagrees. Two witnesses for 2012-07-11 — importing under that date, conflict noted in the row.

**Steps, in order:**
1. Check the book for services around 2012-07-11 (was there a service this meeting followed?) — read-only. ☐
2. Back up Sermons.db to /Volumes/Data/Video Archive/SQL Files/backups/ (the law: run with DB backed up). ☐
3. Insert ONE Services row: preach_date 2012-07-11, title "Post Service Meeting Notes (business meeting)", full docx text into notes with a source line naming the file and the dating evidence; org and sermon_giver stay EMPTY — no blankets. ☐
4. Verify the row reads back whole (count + sample). ☐
5. Mark this note FINISHED.

**If found unfinished:** the db is safe to inspect; the backup (step 2) is named Sermons_YYYYMMDD_*_before_bizmeeting.db. If step 3 half-landed, look for a Services row dated 2012-07-11 titled like "Post Service Meeting" before re-running anything.
