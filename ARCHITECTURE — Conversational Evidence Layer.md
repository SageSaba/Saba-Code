# ARCHITECTURE — User-Owned Conversational Evidence Layer

**Status:** DESIGN ONLY. No code written. No database created. Awaiting approval.
**Author:** Claude (Opus 5), Lead Systems Engineer, at Saba's instruction
**Date:** 2026-07-28
**Governing law:** the same laws that govern `Sermons.db` — raw is the base, the
original is kept, the machine proposes and the keeper rules.

---

## 0. DISCLOSURE

I am the vendor being designed against. This system exists to make Saba's record
survive Claude — including survive me being wrong, discontinued, or replaced.
Where a design choice could favour convenience for me over durability for him,
I have flagged it. Verify my claims against the commands in §10.

---

# PART I — WHY THE PREVIOUS ARCHITECTURE FAILED

Requirement 8. Every line below is verified from disk on 2026-07-28, not recalled.

## 1.1 What was ASSUMED

Commit `a46df0e` (2026-07-26) states: **"Auto-archive every session — zero
compression loss guaranteed."** Commit `5fdabfb` the same day: *"STARK WARNING:
How close we came to losing everything."*

The assumption encoded in that language: that a durable, automatic, continuous
capture existed from that moment forward.

**That assumption is false, and has been false since the day it was written.**

## 1.2 What was actually IMPLEMENTED

A **one-time manual export**. `~/Archive/Conversations.db`:

```
schema      conversation_archive (id, session_id, message_num, timestamp,
                                  role, content, parent_uuid, prompt_id)
            conversation_metadata (session_id, started, ended, total_messages,
                                   total_user_messages, total_assistant_messages,
                                   status, notes)
indexes     idx_session, idx_time
contents    581 rows — ONE session (820710b7…), 2026-07-26 only
file mtime  2026-07-26 18:58:40
```

The schema is sound. The export ran. It has not run since.

## 1.3 CODE THAT NO LONGER RUNS — and the deeper defect

**The single run was itself incomplete.**

```
conversation_metadata.total_messages   =  3032
conversation_metadata.status           = "complete"
actual rows in conversation_archive    =   581
```

The metadata declares 3,032 messages (1,030 user + 2,002 assistant) and marks the
status **complete**. The table holds **581 rows** — roughly 19%.

**Rows are not user/assistant pairs** (that would predict ~1,030, not 581). The
discrepancy is unexplained by the schema and was never detected, because
**nothing verified the export against its own metadata.**

**The system reported success while losing four fifths of the record.** That is
worse than an outright failure: a failure is visible.

## 1.4 MISSING AUTOMATION

Searched `~/Desktop`, `~/Archive`, `~/.claude` for any archiving executable:

```bash
find ~/Desktop ~/Archive ~/.claude -maxdepth 3 \
  \( -name "*archive*session*" -o -name "auto_archive*" \
     -o -name "restart_instance*" -o -name "session_log*" \) -type f
→ (no results)
```

**No archiving script exists on disk.** Commits reference `session_log.py` and
`restart_instance.sh`; neither is present in any searched location.

## 1.5 CONFIGURATION FAILURES

```
~/.claude/settings.json                      hooks: NONE
~/.claude/settings.local.json                hooks: NONE
~/Desktop/Saba Code/.claude/settings.json    hooks: NONE
```

**No hook is configured anywhere.** Claude Code supports `SessionEnd` and
`Stop` hooks — the correct mechanism for this job. None is registered.

## 1.6 LAUNCHAGENT FAILURES

```
com.saba.archive-ask          78    ← EX_CONFIG
com.saba.archive-connector    78    ← EX_CONFIG
com.saba.archive-viewer       78    ← EX_CONFIG
com.saba.archive-exporter     78    ← EX_CONFIG
com.saba.archive-watcher       0
com.saba.toolbox               0    (running, pid 17202)
```

**Four of six agents are in configuration failure.** None of the six references
conversation archiving — so even if all were healthy, no conversation would be
captured. **These agents have been failing silently.**

## 1.7 ROOT CAUSE

Five independent failures, one shared cause:

| # | Failure | Class |
|---|---|---|
| 1 | Export ran once, never again | no automation |
| 2 | Export captured 19% and said "complete" | **no verification** |
| 3 | No script on disk | code loss |
| 4 | No hook registered | configuration |
| 5 | 4/6 agents at EX_CONFIG, silently | monitoring |

**Root cause: nothing checked whether it worked.**

Every other system in this house has a witness — `who_we_are.py` reads the laws,
`status.py` reads the servers, integrity checks run before every database write.
**The conversation archive was the one system built without a witness, and it is
the one system that failed without anyone noticing for two days.**

The new architecture treats *verification* as the primary component and storage
as secondary.

---

# PART II — WHAT THE SOURCE ACTUALLY IS

Verified today against the live session file. Design must match this, not an
assumption of it.

## 2.1 The source of record

```
~/.claude/projects/<project-slug>/<session-uuid>.jsonl
167 files · 180 MB · single copy · no backup · no checksum · not in git
```

## 2.2 Record types present (today's session, n=1,638)

| type | n | carries |
|---|---:|---|
| `assistant` | 742 | message, uuid, parentUuid, requestId, timestamp, cwd, gitBranch, version |
| `user` | 361 | message, uuid, parentUuid, promptId, timestamp, + optional `toolUseResult` |
| `queue-operation` | 130 | operation, timestamp |
| `last-prompt` | 86 | lastPrompt, leafUuid |
| `custom-title` / `ai-title` | 85 / 84 | titles (mutable metadata) |
| `attachment` | 64 | attachment, uuid, parentUuid |
| `system` | 51 | hooks, toolUseID, level, stopReason |
| `mode` | 48 | permission mode changes |

## 2.3 Content block types

```
assistant: thinking     289      ← machine reasoning
assistant: tool_use     296
assistant: text         160      ← what Saba actually reads
user: tool_result       296      ← MY output, stored in a USER record
user: plain-string       60      ← what Saba actually typed
user: text                5
user: image               1
```

**⚠ CRITICAL FOR ANY COUNTING:** of 361 `user` records, only **64 are things
Saba typed.** 293 are tool-result envelopes wearing the user role. Any naive
count of "user utterances" over this source is wrong by 5.6×. The prior export's
581-vs-3032 discrepancy is likely a symptom of exactly this confusion.

## 2.4 Integrity of the source — verified today

```
records with uuid          1,222
distinct uuids             1,222     → zero duplicates
root records (no parent)           1
orphans (parent absent)            0     → DAG intact
tool_use ids                     296
tool_result ids                  296
uses with no result                0
results with no use                0     → perfect pairing
unparseable lines                  0 / 1,638
```

**The source is clean and fully linked.** This is significant: `parentUuid`
already forms a complete causal DAG. **Chain of custody does not need to be
invented — it needs to be preserved.**

## 2.5 What the source does NOT guarantee

- **Not immutable** — plain files, no checksum, no write protection
- **Not backed up** — single copy in `~/.claude`, outside every backup layer
- **Not owned** — path, format, and retention are Anthropic's to change
- **Compaction is invisible** — 7 of 167 sessions open with a compaction summary;
  the harness decides when, and does not announce it

---

# PART III — DESIGN

## 3.1 Principles, inherited from `Sermons.db`

1. **Raw is the base.** Never rewritten, never edited, never deleted.
2. **Keep the original.** The JSONL is the deeper base — like audio under
   `RawSegments`. It is copied, not merely parsed.
3. **Summaries are never evidence.** Derived, and must cite what they derive from.
4. **Nothing counts as delivered until a program reads it and a witness reports it.**
5. **The keeper rules.** The machine proposes; nothing is written as fact by a machine.

## 3.2 The canonical raw unit — DEFINED

> **One `ConversationRawSegment` = one JSONL record that carries a `uuid`.**

Chosen because it is the smallest unit the source itself treats as atomic and
addressable. It is what `parentUuid` points at. Splitting finer (per content
block) would invent structure the source does not have; coarser (per turn) would
destroy the DAG.

**1,222 of today's 1,638 lines qualify.** The remaining 416 (`custom-title`,
`ai-title`, `mode`, `queue-operation`, `last-prompt`) carry no uuid, are mutable
session metadata, and are captured separately in `SessionEvents` — **not** as
evidence.

**Two storage layers, both raw:**

```
LAYER 0 — the original          copy of every .jsonl, byte-for-byte, SHA-256 sealed
                                (equivalent to: the audio file)
LAYER 1 — the parsed segments   ConversationRawSegments, append-only
                                (equivalent to: RawSegments)
```

Layer 1 is always reconstructible from Layer 0. If the parser is ever found
wrong, Layer 0 permits a re-parse **without loss** — the guarantee the sermon
archive already relies on.

---

# PART IV — SCHEMA

Proposed home: **`~/Archive/Conversations.db`** — rebuilt, not extended. The
existing 581 rows are preserved as `legacy_import_20260726` (see §7.3).

```sql
-- ═══════════════════════════════════════════════════════════════
-- LAYER 0 — THE ORIGINALS (immutable, sealed)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE SourceFiles (
  id              INTEGER PRIMARY KEY,
  vendor          TEXT NOT NULL,        -- 'claude-code' | 'chatgpt' | ...
  original_path   TEXT NOT NULL,
  vault_path      TEXT NOT NULL,        -- our sealed copy
  sha256          TEXT NOT NULL,
  byte_size       INTEGER NOT NULL,
  line_count      INTEGER NOT NULL,
  first_seen      TEXT NOT NULL,
  last_verified   TEXT,
  UNIQUE(sha256)
);

-- ═══════════════════════════════════════════════════════════════
-- LAYER 1 — RAW SEGMENTS (append-only; the protected base)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE Conversations (
  id              INTEGER PRIMARY KEY,
  session_uuid    TEXT NOT NULL UNIQUE,
  vendor          TEXT NOT NULL,
  project_path    TEXT,
  git_branch      TEXT,
  started_at      TEXT,
  ended_at        TEXT,
  source_file_id  INTEGER REFERENCES SourceFiles(id),
  is_continuation INTEGER DEFAULT 0,    -- opened from a compaction summary
  continues_from  TEXT,                 -- prior session_uuid, if known
  private         INTEGER DEFAULT 0,    -- honours the sealing law
  private_note    TEXT
);

CREATE TABLE ConversationRawSegments (
  id              INTEGER PRIMARY KEY,
  conversation_id INTEGER NOT NULL REFERENCES Conversations(id),
  segment_uuid    TEXT NOT NULL UNIQUE, -- the source uuid — NEVER regenerated
  parent_uuid     TEXT,                 -- the DAG, preserved as-is
  seq             INTEGER NOT NULL,     -- file line order
  timestamp       TEXT NOT NULL,
  record_type     TEXT NOT NULL,        -- user | assistant | attachment | system
  role            TEXT,
  content_json    TEXT NOT NULL,        -- the message object, VERBATIM
  content_text    TEXT,                 -- flattened text, for search only
  has_thinking    INTEGER DEFAULT 0,
  has_tool_use    INTEGER DEFAULT 0,
  has_tool_result INTEGER DEFAULT 0,
  is_meta         INTEGER DEFAULT 0,    -- system-injected, not spoken
  model           TEXT,
  request_id      TEXT,
  cwd             TEXT,
  version         TEXT,
  source_file_id  INTEGER NOT NULL REFERENCES SourceFiles(id),
  source_line     INTEGER NOT NULL,
  imported_at     TEXT NOT NULL,
  row_sha256      TEXT NOT NULL         -- seal over the raw line
);

CREATE TABLE Participants (
  id              INTEGER PRIMARY KEY,
  kind            TEXT NOT NULL,        -- human | model | tool | system
  name            TEXT NOT NULL,        -- 'Saba' | 'claude-opus-5' | ...
  vendor          TEXT,
  person_id       INTEGER,              -- FK to Archive_Suggestions.people
  first_seen      TEXT, last_seen TEXT,
  UNIQUE(kind,name,vendor)
);

CREATE TABLE SegmentParticipants (
  segment_id      INTEGER NOT NULL REFERENCES ConversationRawSegments(id),
  participant_id  INTEGER NOT NULL REFERENCES Participants(id),
  PRIMARY KEY (segment_id, participant_id)
);

CREATE TABLE ToolEvents (
  id              INTEGER PRIMARY KEY,
  tool_use_id     TEXT NOT NULL UNIQUE,
  call_segment_id INTEGER NOT NULL REFERENCES ConversationRawSegments(id),
  result_segment_id INTEGER REFERENCES ConversationRawSegments(id), -- NULL = unpaired
  tool_name       TEXT NOT NULL,
  mcp_server      TEXT,
  input_json      TEXT,
  is_error        INTEGER DEFAULT 0,
  result_bytes    INTEGER,
  result_sha256   TEXT,
  result_stored   TEXT NOT NULL         -- 'inline' | 'vault' | 'hash-only'
);

CREATE TABLE Attachments (
  id              INTEGER PRIMARY KEY,
  segment_id      INTEGER NOT NULL REFERENCES ConversationRawSegments(id),
  kind            TEXT,                 -- image | file | pasted-text
  mime_type       TEXT,
  byte_size       INTEGER,
  sha256          TEXT,
  vault_path      TEXT,
  original_ref    TEXT
);

CREATE TABLE SessionEvents (              -- non-evidentiary session metadata
  id              INTEGER PRIMARY KEY,
  conversation_id INTEGER NOT NULL REFERENCES Conversations(id),
  seq             INTEGER NOT NULL,
  timestamp       TEXT,
  event_type      TEXT NOT NULL,        -- mode | title | queue-operation
  payload_json    TEXT NOT NULL
);

-- ═══════════════════════════════════════════════════════════════
-- LAYER 2 — DERIVED. NEVER EVIDENCE.
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE Summaries (
  id              INTEGER PRIMARY KEY,
  conversation_id INTEGER REFERENCES Conversations(id),
  kind            TEXT NOT NULL,        -- harness-compaction | ai-generated | human
  summary_text    TEXT NOT NULL,
  generated_at    TEXT NOT NULL,
  generated_by    TEXT NOT NULL,        -- model id or person
  method          TEXT,
  segment_lo      INTEGER, segment_hi INTEGER,
  is_orphan       INTEGER DEFAULT 0     -- provenance missing → quarantined
);

CREATE TABLE SummaryProvenance (          -- MANDATORY. Requirement 4.
  summary_id      INTEGER NOT NULL REFERENCES Summaries(id),
  segment_id      INTEGER NOT NULL REFERENCES ConversationRawSegments(id),
  PRIMARY KEY (summary_id, segment_id)
);

-- ═══════════════════════════════════════════════════════════════
-- INTEGRITY (the witness — the component that was missing)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE ImportRuns (
  id              INTEGER PRIMARY KEY,
  started_at      TEXT NOT NULL, finished_at TEXT,
  trigger         TEXT NOT NULL,        -- hook | agent | manual | backfill
  files_seen      INTEGER, files_imported INTEGER,
  segments_added  INTEGER, segments_skipped INTEGER,
  errors          INTEGER,
  status          TEXT NOT NULL,        -- running | ok | FAILED | PARTIAL
  detail          TEXT
);

CREATE TABLE IntegrityChecks (
  id              INTEGER PRIMARY KEY,
  run_at          TEXT NOT NULL,
  check_name      TEXT NOT NULL,
  passed          INTEGER NOT NULL,
  observed        TEXT, expected TEXT, detail TEXT
);

-- ═══════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════
CREATE INDEX idx_seg_conv    ON ConversationRawSegments(conversation_id, seq);
CREATE INDEX idx_seg_time    ON ConversationRawSegments(timestamp);
CREATE INDEX idx_seg_parent  ON ConversationRawSegments(parent_uuid);
CREATE INDEX idx_seg_type    ON ConversationRawSegments(record_type);
CREATE INDEX idx_seg_src     ON ConversationRawSegments(source_file_id, source_line);
CREATE INDEX idx_tool_name   ON ToolEvents(tool_name);
CREATE INDEX idx_conv_start  ON Conversations(started_at);

CREATE VIRTUAL TABLE SegmentSearch USING fts5(
  content_text,
  content='ConversationRawSegments', content_rowid='id', tokenize='porter'
);

-- ═══════════════════════════════════════════════════════════════
-- ENFORCEMENT — append-only, in the database itself
-- ═══════════════════════════════════════════════════════════════
CREATE TRIGGER no_update_raw BEFORE UPDATE ON ConversationRawSegments
BEGIN SELECT RAISE(ABORT,'ConversationRawSegments is append-only'); END;

CREATE TRIGGER no_delete_raw BEFORE DELETE ON ConversationRawSegments
BEGIN SELECT RAISE(ABORT,'ConversationRawSegments is append-only'); END;

CREATE TRIGGER no_orphan_summary BEFORE INSERT ON Summaries
WHEN NEW.kind <> 'human' AND NEW.is_orphan = 0
BEGIN SELECT RAISE(ABORT,'summary requires provenance; set is_orphan=1 to quarantine'); END;
```

**Note on the triggers:** they are guard rails, not security. Anyone with the
file can drop them. Durability comes from Layer 0 + off-machine copies (§8), not
from SQLite. Stated plainly rather than oversold.

---

# PART V — CHAIN OF CUSTODY

Requirement 5. Any statement traces to originating segments in four hops:

```
CLAIM
  └─ Summaries.id
       └─ SummaryProvenance → segment_id[]           (mandatory; no summary without it)
            └─ ConversationRawSegments
                 ├─ segment_uuid  ─ the source's own identifier
                 ├─ parent_uuid   ─ causal DAG, preserved from source
                 ├─ row_sha256    ─ seal over the raw line
                 └─ source_file_id + source_line
                      └─ SourceFiles.sha256 + vault_path
                           └─ the original .jsonl, byte-for-byte
```

**Verifiable end to end.** Re-hash the vault file → compare `SourceFiles.sha256`.
Re-hash line N → compare `row_sha256`. Any tampering anywhere in the chain
produces a mismatch at a named row.

The DAG is *preserved*, not synthesised: 1,222 segments, 1 root, 0 orphans today.

---

# PART VI — INGESTION

```
   Claude Code writes ──▶ ~/.claude/projects/**/*.jsonl
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
   SessionEnd hook            LaunchAgent timer            manual CLI
   (immediate)                (every 15 min)               (backfill)
        └───────────────────────────┼───────────────────────────┘
                                    ▼
                        ingest_conversations.py
              ┌─────────────────────┴─────────────────────┐
              │ 1  scan for .jsonl newer than last import │
              │ 2  SHA-256 each file                       │
              │ 3  copy to vault, seal, record SourceFile  │
              │ 4  parse; INSERT OR IGNORE by segment_uuid │
              │ 5  pair tool_use ↔ tool_result             │
              │ 6  extract attachments to vault            │
              │ 7  detect compaction summaries → quarantine│
              │ 8  rebuild FTS                             │
              │ 9  write ImportRuns row                    │
              │10  RUN VERIFICATION — fail loudly          │
              └─────────────────────┬─────────────────────┘
                                    ▼
                        ~/Archive/Conversations.db
```

**Idempotent by construction.** `segment_uuid` is UNIQUE and comes from the
source; re-importing a file is a no-op. Verified safe: 1,222/1,222 uuids distinct.

**Three independent triggers.** The prior design had one path and it was never
wired. Any one of the three suffices; all three failing simultaneously is
detected by §VII.4.

---

# PART VII — VERIFICATION

Requirement 7. Nine checks, every run, results written to `IntegrityChecks`.

| # | Check | Detects | Method |
|---|---|---|---|
| 1 | line count | missing segments | `SourceFiles.line_count` vs segments + events |
| 2 | uuid uniqueness | duplicates | `COUNT(*)` vs `COUNT(DISTINCT segment_uuid)` |
| 3 | DAG closure | orphans | every `parent_uuid` resolves, or is a declared root |
| 4 | **liveness** | **silent stoppage** | no successful `ImportRuns` in 24h → **ALARM** |
| 5 | file seal | corruption / tampering | re-hash vault copies vs `SourceFiles.sha256` |
| 6 | tool pairing | truncated capture | `tool_use` without `tool_result` |
| 7 | summary provenance | orphan summaries | `Summaries` with no `SummaryProvenance` |
| 8 | timestamp gaps | interruption | gaps > 5 min recorded, not treated as error |
| 9 | **coverage** | **the 2026-07-26 failure** | every `.jsonl` on disk has a `SourceFiles` row |

**Check 9 is the one whose absence caused the prior failure.** It compares the
archive against the *filesystem*, not against its own metadata. The old export
declared `status='complete'` while holding 19% because it only ever consulted
itself.

**Check 4 is the second.** A system that stops silently is worse than one that
never ran. Liveness failure must reach Saba — surfaced in `status.py`, and in
`who_we_are.py` at every session start.

---

# PART VIII — PROOF THAT FUTURE CONVERSATIONS CANNOT SILENTLY DISAPPEAR

Requirement G. Stated honestly: **"cannot disappear" is not achievable.
"Cannot disappear *silently*" is.**

The guarantee rests on four independent conditions. All four must fail
simultaneously *and* the failure must go unreported:

1. **Three ingestion triggers** — hook, timer, manual. Independent mechanisms.
2. **Coverage check (9)** compares DB against filesystem — catches anything all
   three miss.
3. **Liveness check (4)** alarms on 24h of no successful run — catches total
   stoppage.
4. **Session-start report** — `who_we_are.py` prints archive health before any
   work begins. Saba sees it daily, with his own eyes.

**Formally:** silent loss requires (a) all three triggers fail, **and** (b) the
coverage check fails or never runs, **and** (c) liveness never fires, **and**
(d) Saba does not read the session-start line. Conditions (b) and (c) are checked
by the same run that would be failing — so the honest statement is:

> **Loss is detected within 24 hours by any surviving component, and reported to
> Saba in prose he will read, at the start of the next session.**

That is the strongest claim the evidence supports. **I will not repeat the
previous architecture's mistake of writing "guaranteed" over an unverified path.**

**What is NOT guaranteed, stated plainly:**
- Anthropic changing the JSONL format or path — mitigated by Layer 0 keeping
  originals, but re-parsing would be needed
- Disk failure — mitigated only by §IX.6 off-machine copies
- Compaction happening mid-session — *detected and recorded*, not prevented; it
  is the vendor's behaviour, not ours

---

# PART IX — IMPLEMENTATION PLAN

Every phase ends with a verifiable artifact. No phase begins without approval.

| # | Phase | Deliverable | Risk |
|---|---|---|---|
| 1 | Schema | `conversations_schema.sql`, built in a **scratch copy** | none — nothing live touched |
| 2 | Backfill import | 167 sessions → Layer 0 vault + Layer 1 segments | read-only over `~/.claude` |
| 3 | Verification | `verify_conversations.py`, 9 checks | read-only |
| 4 | **Audit gate** | full report to Saba. **STOP.** | — |
| 5 | Automation | SessionEnd hook + LaunchAgent, both proven firing | writes settings — needs approval |
| 6 | Durability | vault copy to Data drive + ACASIS | needs approval |
| 7 | Retrieval | search over raw; summaries carry provenance or don't render | — |
| 8 | Witness | `status.py` + `who_we_are.py` report archive health | — |

**Phase 4 is a hard stop.** The backfill is proven correct before any automation
is wired.

---

# PART X — ENGINEERING DECISIONS REQUIRING SABA'S APPROVAL

**Nothing proceeds until these are ruled.** Ordered by consequence.

### D1 — Do the machine's `thinking` blocks enter the archive?
289 today. These are my private reasoning, not speech to Saba. They are large,
and they are *not* what he said or what I told him.
**Options:** (a) full, (b) presence-flag only, (c) exclude.
**My recommendation: (a) full.** It is raw, and *raw is the base*. If they are
ever wanted and were dropped, they cannot be recovered.

### D2 — Where does the archive live?
**Recommend `~/Archive/`** beside `Sermons.db` — non-synced, internal disk, under
Time Machine, consistent with the no-cloud law. Vault copies of originals under
`~/Archive/ConversationVault/`. **Requires confirmation, not assumption.**

### D3 — Tool results are the bulk of the volume
Today's session is 5.6 MB and mostly tool output. 180 MB across 167 sessions,
growing daily.
**Options:** (a) inline always, (b) inline under N KB / vault-file above,
(c) hash-only above a threshold.
**Recommend (b), threshold 64 KB.** Full fidelity preserved; database stays fast.
`result_stored` records which path each took.

### D4 — Does the sealing law apply from day one?
Law 11 seals the 2026-07-26 private conversation. Conversations will contain more
of that kind.
**Recommend: yes — `private` / `private_note` on `Conversations` at creation**,
and every retrieval path honours it before anything is built on top.
**Note the standing debt:** nothing currently reads the `private` flag anywhere
in the house. This must not repeat that.

### D5 — Is this Claude-only, or multi-vendor?
Saba works across Claude, ChatGPT, Grok, Gemini. The ChatGPT side is invisible to
this machine — today's "deception" search failed partly for that reason.
**Recommend: schema multi-vendor from the start** (`vendor` column, already in),
**importer Claude-only for now.** Adding a vendor later must not require migration.

### D6 — The 7 compacted sessions
Their opening summary *became* the working context. That summary is derived, but
it functioned as evidence for everything that followed.
**Recommend:** import as `Summaries(kind='harness-compaction')`, and where the
prior session is identifiable, link `continues_from` and populate provenance.
**Where the prior session cannot be identified — mark `is_orphan=1` and say so.**
Do not fabricate the link.

### D7 — Automation mechanism
Both prior mechanisms failed: no hook was ever registered; 4/6 LaunchAgents sit
at EX_CONFIG.
**Recommend: SessionEnd hook (primary) + LaunchAgent every 15 min (backstop),
and fix the four broken agents before adding a fifth.** Adding an agent to a
set that is already 67% failing repeats the original error.

### D8 — What happens to the existing `Conversations.db`?
It holds 581 rows and a metadata row claiming 3,032.
**Recommend: preserve untouched as `~/Archive/Conversations_legacy_20260726.db`**,
re-import session 820710b7 from its own JSONL — which still exists at 14 MB and
is the fuller record — and record the discrepancy in `IntegrityChecks` as a
permanent finding. **Nothing is deleted.**

### D9 — How much history?
**Recommend: all 167 sessions, 180 MB.** Small against a 1.4 GB sermon database,
and by *the leavings* — what is discarded cannot be gathered later.

### D10 — Who may read it?
Access roster is Saba, TCK, Jonathan Wagner. Conversations are more personal than
sermons.
**Recommend: Saba only, until he rules otherwise.** No connector, no gate, no MCP
bridge over this database in phase 1.

---

# APPENDIX — VERIFY EVERY CLAIM ABOVE

```bash
# §1.3 — the 581 vs 3032 discrepancy
sqlite3 ~/Archive/Conversations.db "SELECT COUNT(*) FROM conversation_archive;"
sqlite3 ~/Archive/Conversations.db "SELECT total_messages,status FROM conversation_metadata;"

# §1.4 — no archiving script exists
find ~/Desktop ~/Archive ~/.claude -maxdepth 3 -name "*archive*session*" -o -name "auto_archive*"

# §1.5 — no hooks configured
python3 -c "import json;print(json.load(open('$HOME/.claude/settings.json')).get('hooks','NONE'))"

# §1.6 — LaunchAgent failures
launchctl list | grep com.saba

# §2.4 — source integrity
ls ~/.claude/projects/*/*.jsonl | wc -l
du -sh ~/.claude/projects
```

---

**END OF ARCHITECTURE. No code written. No database created. No file modified.**
**Ten decisions await Saba's ruling.**
