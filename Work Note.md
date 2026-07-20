# Work Note
*Written before starting, per Saba's law of 2026-07-20: the intention goes on paper first, so a shutdown never loses the thread. Saba: "I fully expect to crash anytime" — this note always carries the full standing state.*

## STANDING STATE (as of 2026-07-20, after Shabbath came home)
- **Nothing is half-done.** 2637 duplicate resolved: removed 2026-07-20 by Saba's ruling ("Church business is a sermon (teaching) so should be in records") — minutes stand in ChurchRecords row 1.
- Sukkot 2013: COMPLETE — 51 sessions home incl. session 20 "Shabbath" (service 2636). Videos still missing: leads = Elizabeth's 4TB drive OR the DV tapes.
- THE PLAN (two patches: bring-the-book-up-to-date, rescue-parts-builders) is written in "Next Load — paused branches review.md" — awaits presentation + Saba's go. Branches website-review + clean-mtnl stay PAUSED.
- DV tape era: standing to-do (same file + task list) — Saba finds boxes/labels first; buy nothing but the ~$80 adapter chain.
- Sharon's notes: 169 in Services; 8 undated 2013 files await dating-by-text or ruling; Dec 17 2011 stray to re-chase. Business meetings live in ChurchRecords (Saba's 2026-07-17 ruling).
- Rulings open: Summaries.json home; loose Word docs in repo root; branch retirement; video player on the reading pages (patch candidate, unnamed).
- **FINDING 2026-07-20 (Saba: "No video"):** the approved screen's player gets 404 from /video/2636 AND /video/2604 — the Sukkot tapes are not being served (likely: viewer serves media only from its allowed root, and the mp3s live in ~/Desktop/Sermon Notes, outside it — unconfirmed). Whether older webm services still play: NOT yet tested. Search works (found Shabbath's "almost doze" moment perfectly). Needs a named patch on Saba's word; diagnosis paused at his stop.
- **CONFIRMED 2026-07-20:** questions asked of the site ARE saved — Archive_Suggestions.db `questions` table, 9 journaled with full answers + receipts.
- **THE SILENT YEAR (found 2026-07-20, via Saba's Carpenter's Story memory):** the book holds NO services from 2021-07-15 to 2022-06-08 — eleven months missing (Zoom-era tail; Wed+Sat were TRCF on Zoom). Saba remembers sharing the Carpenter's Story on the Wednesday PM before Elizabeth's 2022-06-10 telling (service 2528, ~8:40) — that Wednesday (2022-06-08) is in the gap. HUNT NEEDED: were the Zoom services recorded? Where do recordings live (Zoom cloud expires; local recordings folder; OneDrive; unsearched drives)? Saba's answer decides the hunt.

## STATUS: STARTING — write "The Structure.md" (Saba: "Give me the structure. I'm building to evaluate data as it comes in and settle it into the pile.") One reference doc: the shelves, the intake road, the decision table. Then commit, mark finished.
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
