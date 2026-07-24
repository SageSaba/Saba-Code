# What Is What — Archive Viewer folder

A plain map of this folder, so nothing is lost and anyone can find their way.
(Made during cleanup, 2026-07-23. Nothing here was deleted — only organized.)

---

## ⭐ THE LIVE SYSTEM — do not move or rename these

These are the running "One Box." Three programs, one book:

| File | What it is | Port |
|---|---|---|
| `one-box.html` | The page you look at — ask, answer, moment, video | served on 8790 |
| `ask_archive.py` | The **answer** engine (writes the answer) | 8768 |
| `connector.py` | The **evidence/search** service (finds moments, read-only) | 8766 |
| `spell_correct.py` | Fixes typos in searches (isreal → israel); used by `ask_archive.py` | — |
| `archive_vocab.json` | The word list the spell-fixer checks against | — |
| `viewer.py` | Older viewer the connector still references | — |
| `launch_book.sh` | Starts all servers + opens the page | — |
| `book_icon.png` | Icon for the Desktop launcher | — |

**To start everything:** the **Book of Remembrance** app on the Desktop (or run `launch_book.sh`).

## 📚 The data (NOT in this folder — lives in ~/Archive)
- `~/Archive/Sermons.db` — the **raw record**. Never altered. The base of everything.
- `~/Archive/Archive_Suggestions.db` — the **AI + human-review** layer (People Reference, corrections).
  (The `Archive_Suggestions.db-shm` / `-wal` files here are just its live working files.)

---

## 🧰 One-off tools (run when needed, not part of the live loop)
- `name_scanner.py` — reads all segments, decides who was quoted vs. who spoke
- `voice_id_proof.py` — voiceprint proof (recognized Craig Barton's voice)
- `people_reference.py` — builds/seeds the People Reference (the 21 people)
- `batch_classify_mentions.py` — the Batch-API name classifier
- `build_organizations.py` — organization/collection builder
- `who_is_speaking.py` — speaker-ID helper
- `transcript_exporter.py` — export a transcript
- `archive_mcp.py` — MCP bridge in front of the connector (for claude.ai)
- `dictate.sh`, `talk.py`, `talk.sh` — the **voice tools** (speak → text → AI)

## 🗄️ _backups/ (save-points from before edits — kept just in case)
Six `*_before_*` files moved here 2026-07-23. Safe to ignore; nothing uses them.

---

## 🗃️ _retired (old versions)/ — kept for later, not deleted
Superseded versions moved here 2026-07-23 (retired at Saba's word):
- **The Xcode version** — `SermonArchiveXcode.zip` + `SermonArchiveXcode/`
- `four-box.html`, `Sermon Reader.html` — early interface tries nothing references.

## ⚠️ Still LIVE — do NOT retire (learned the hard way)
- `index.html` + `screen.html` — served by `viewer.py` on 8765 (`index.html` is the **ratified** screen).
- `Ask the Archive.html` — served by `ask_archive.py` on 8768 (it names this page via the `PAGE=` variable; moving it 500s the answer engine).
- `xwalls-home.html` — links into the live `one-box.html`.

## 🕰️ Other older bits — LEFT IN PLACE, your call
- `Book of Remembrance.command`, `Start *.command` — old launchers (the Desktop **app** replaced them).
- `AVITW_text.txt` — **VERIFY before trusting**: may be the wrong (Carver-folder) extraction Saba rejected. Authentic AVITW is `~/Desktop/PDF Files/AVITW.pdf`.
- `Transcript 2016-12-03.html`, README files — reference material.
