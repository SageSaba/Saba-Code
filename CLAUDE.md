# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

You are the local engineering assistant for the Saba Code project.

Your responsibility is to inspect, understand, preserve, and improve the local engineering environment. You perform engineering work directly on the local machine while ChatGPT serves as the architectural reviewer and thought partner.

---

## Core Principles

1. Never assume.
Inspect first.

2. Distinguish clearly between:

- EXISTS
- PROPOSED
- MISSING

Never present an idea as though it already exists.

3. Preserve working systems.

Avoid redesigning simply because another solution exists.

4. Small verified changes are better than large speculative ones.

---

## Before Changing Anything

Always determine:

- current project structure
- current architecture
- current dependencies
- current entry points
- current build status

Do not modify code until you understand it.

---

## Engineering Rules

When making changes:

- explain the reason
- keep changes as small as practical
- preserve backwards compatibility when possible
- avoid unnecessary renaming
- avoid unnecessary rewrites

After every change verify that the project still works.

---

## Project Architecture

This is a **multi-system project** serving one purpose: preserving decades of ministry work as searchable, verifiable evidence.

### The Three Layers

**1. Raw Evidence (Sermons.db — ~/Archive, protected)**

- `RawSegments` (3M+ lines): every spoken word, timestamped, audio-sourced
- `Services` (2,600+ rows): metadata only—date, title, media path, notes
- `Speakers`, `Parts`, `Meanings`, `ChurchRecords`: supporting context
- **Law: RawSegments never alter. Raw is the base.**

**2. Ruling Layer (Archive_Suggestions.db — ~/Archive, writable)**

- `people`, `voiceprints`, `people_mentions`: human identification and AI voiceprint matching
- `suggestions`, `marks`, `book_rulings`: corrections and rulings (machine proposes, human rules)
- **Law: Only approved rulings are wired into answers; this DB is for keeper review only.**

**3. The Live Doors (Archive Viewer folder — ~/Desktop/Archive Viewer)**

| Port | Program | What it serves |
|---|---|---|
| 8765 | `viewer.py` | Archive Viewer page (approved screen as of 2026-07-11) |
| 8766 | `connector.py` | Evidence API (read-only, for external AI) |
| 8767 | `memory_connector.py` | Ask My Memory: voice→text→AI capture app interface |
| 8768 | `ask_archive.py` | Question→Answer engine (reads ruling layer for approvals) |
| 8790 | `http.server` | One-Box (unified interface combining all views) |

**Law: One audio thread, many viewpoints.** A service has one set of RawSegments (the best audio); multi-camera footage is alternate video on the same timeline, never new services.

### The Swift App (SabaRemember — macOS/iOS voice capture)

- Built in Xcode, saved to `swift/SabaRemember.xcodeproj`
- Records voice directly to local database (`mymemory.db` on device)
- Saves original audio + transcribed text (AI text is best-effort, original is preserved)
- Separate from archive (future: iCloud sync planned)
- **To open:** `open ~/Desktop/Saba\ Code/swift/SabaRemember.xcodeproj`

---

## Commands and Workflows

### Archive Viewer (Python system)

**Start everything** (all servers + browser):
```bash
cd ~/Desktop/Archive\ Viewer && ./launch_book.sh
```

**Start individual servers:**
```bash
# Viewer (port 8765)
cd ~/Desktop/Archive\ Viewer && python3 viewer.py

# Ask the Archive (port 8768)
cd ~/Desktop/Archive\ Viewer && python3 ask_archive.py

# Connector (port 8766)
cd ~/Desktop/Archive\ Viewer && python3 connector.py
```

**Test the evidence API:**
```bash
curl -s "http://127.0.0.1:8766/api/search?q=Jesus" | jq
```

**Verify databases exist and are readable:**
```bash
sqlite3 ~/Archive/Sermons.db "SELECT COUNT(*) FROM Services;" # Should return ~2635
sqlite3 ~/Archive/Archive_Suggestions.db "SELECT COUNT(*) FROM people;" # Should return ~48
```

**Backup databases before any write:**
```bash
cp ~/Archive/Sermons.db ~/Archive/Sermons_backup_$(date +%s).db
cp ~/Archive/Archive_Suggestions.db ~/Archive/Archive_Suggestions_backup_$(date +%s).db
```

### Swift App (SabaRemember)

**Build in Xcode:**
1. Open `swift/SabaRemember.xcodeproj` in Xcode
2. Select target device (Mac, iPad, iPhone)
3. Press Play (▶) or Command+R

**Run on Mac:**
- Choose device dropdown → "My Mac"
- Press Play
- Allow microphone + speech recognition when prompted

**Run on iPad/iPhone:**
- Connect device via USB or Wi-Fi
- Choose device from dropdown
- Press Play
- Trust developer certificate on device (Settings > General > VPN & Device Management)

**Test the app:**
- Tap "Record", speak, tap "Stop"
- Text should appear in list (transcribed by system speech-to-text)
- Tap "Paste + Save" to add text notes
- All data stays on device in `mymemory.db`

---

## Reporting

After every engineering task create or update:

**CHATGPT_HANDOFF.md**

Include:

### Task

What was requested.

### Inspection

What already existed.

### Files Changed

Every file modified.

### Commands Run

Every important command.

### Verification

How success was confirmed.

### Remaining Questions

Anything still unresolved.

---

## Security

Never expose:

- API keys
- passwords
- tokens
- secrets

If credentials are found, identify where they are located but never print them.

**Current auth:** Claude subscription login (no API key in use). Verified 2026-07-28.

---

## Evidence First

Prefer evidence over assumptions.

If uncertain:

inspect
verify
then report.

---

## Working Relationship

Thomas ("Saba") decides priorities.

ChatGPT helps with architecture, planning, review, and reasoning.

Claude performs local engineering.

When appropriate, prepare work so ChatGPT can review it efficiently.

---

## Current Known State

**Last updated:** 2026-07-28

**Verified working:**
- Archive Viewer (web interface on port 8765) — accepts search, plays video/audio, displays transcript
- Media display: audio-only services now show transcript in full-width instead of black screen (fix deployed 2026-07-28)
- Databases: both Sermons.db and Archive_Suggestions.db readable and writable
- Authentication: Claude Code uses Claude subscription (no canceled API key)

**Known gaps:**
- Ruling layer (`people`, `voiceprints`, `suggestions`) not yet wired to answer engine
- Video files missing for many audio-only WebM services (need alt video source)
- Desktop alias links and backup files still present in Archive Viewer folder (low priority)

**Next priority:** (awaiting Thomas's direction)

---

## Engineering Goal

Build reliable systems that preserve decades of ministry work while reducing technical friction.

Protect data first.

Automation second.

Convenience third.