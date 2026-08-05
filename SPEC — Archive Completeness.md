# SPECIFICATION — What It Means For A Conversational Archive To Be Complete

**Status:** SPECIFICATION. No code. No database. Awaiting approval.
**Author:** Claude (Opus 5), Lead Systems Engineer
**Reviewer:** ChatGPT, Development Team Engineer
**Date:** 2026-07-28
**Supersedes:** any notion of completeness based on row counts.

---

## 0. THE REQUIREMENT

> Define — in precise, testable terms — what it means for an archive to be
> complete. Independent of row counts or database state. Based on preservation
> of evidence, successful reconciliation, and verified chain of custody.

---

## 1. WHY ROW COUNTS CANNOT DEFINE COMPLETENESS

The prior system held **581 rows** and declared `status = 'complete'` against a
metadata figure of **3,032**. Both numbers lived in the same database. The
archive was its own witness, and it certified itself.

**A count is a claim about a set you have. Completeness is a claim about a set
you may not have.** No quantity of rows can establish that nothing is missing,
because the missing rows are precisely the ones not counted.

Completeness must therefore be defined as a **relation between two artifacts** —
the sealed source and the derived archive — computable by a **third program that
wrote neither**.

---

## 2. DEFINITIONS

**2.1 SOURCE** — a `.jsonl` conversation file produced by a vendor. Newline-
delimited; one record per line. **The source is the evidence.** The archive is a
representation of it.

**2.2 SEALED COPY** — a byte-for-byte copy of a SOURCE held in the user's vault,
with its SHA-256 recorded at copy time. Once sealed, never rewritten.

**2.3 ADDRESS** — the identity of a single record:

```
ADDRESS := (source_sha256, line_no)
```

**⚠ The address is NOT the content hash.** Testing today on a live 6.07 MB
session found **1,680 lines but only 1,460 distinct line-hashes — 220 duplicate
lines.** Session-metadata records (`mode`, `custom-title`, `ai-title`,
`queue-operation`, `last-prompt`) legitimately repeat byte-for-byte. Content
hashing would silently collapse 220 real records into fewer.

`line_no` is unique by construction. The address always resolves.

**2.4 SEGMENT** — a record carrying a vendor `uuid`. **1,237 of 1,680** in the
tested file. These form the causal DAG and are evidentiary.

**2.5 SESSION EVENT** — a record carrying no `uuid`. **443 of 1,680**, in five
types. Mutable session metadata; preserved, but not evidentiary.

**2.6 DECLARED EXCLUSION** — a source line deliberately not imported as a
segment, recorded with its address and a machine-readable reason. **An exclusion
is not an omission.** An unexplained absence is an omission and fails
completeness.

**2.7 OPEN vs SEALED SOURCE**

A source is **OPEN** while its session may still be written to.
A source is **SEALED** once it demonstrably cannot grow.

**This distinction was proven necessary empirically.** During this very audit the
live session file grew from **1,638 to 1,680 lines** between two measurements
minutes apart. Any completeness assertion computed against an OPEN file is
invalid the moment it is made.

Seal criteria (all must hold):
- no write to the file for ≥ 30 minutes, **and**
- the owning session-id is not the currently running session, **and**
- the recorded SHA-256 matches on two reads ≥ 30 minutes apart

**Completeness is never asserted over an OPEN source.** It is reported as
`OPEN — not assertable`, with the observed line count and time of observation.

---

## 3. THE COMPLETENESS PREDICATES

An archive is COMPLETE **with respect to a named set of SEALED sources** if and
only if all five predicates hold. Each is independently testable, and each fails
loudly by naming the offending address.

### P1 — PRESERVATION
> For every source, a sealed copy exists in the vault and re-hashes to the
> SHA-256 recorded at seal time.

Failure means the evidence itself is gone or altered. No other predicate matters
if P1 fails.

### P2 — TOTAL ADDRESSABILITY
> For every line *l* in every sealed source, the archive contains **exactly one**
> of: a segment at that address, a session event at that address, or a declared
> exclusion at that address.

No line unaccounted. No line counted twice. **Not a count — a bijection over
addresses.** This is the predicate whose absence produced 581-of-3,032.

### P3 — FIDELITY
> For every stored row, re-reading its address from the sealed source and hashing
> the bytes yields the row's stored `row_sha256`.

Detects drift, truncation, encoding damage, and tampering — at a named line.

### P4 — RECONSTRUCTION
> For each sealed source, the archive can emit a byte stream identical to the
> sealed copy, byte-for-byte.

**The strongest test, and verified implementable today:** joining the split lines
of the live file reproduced all 6,074,043 bytes exactly, matching SHA-256
`8f30ba5f…`.

**Round-trip reconstruction subsumes every count-based argument.** If the source
can be rebuilt from the archive, nothing was lost — regardless of how many rows
any table holds.

### P5 — CUSTODY CLOSURE
> Every derived artifact — summary, embedding, topic, interpretation — resolves
> through provenance to ≥ 1 segment, and every such segment resolves to an
> address in a sealed source satisfying P1–P3.

A derived artifact that cannot name its origin is an **orphan**. Orphans are
quarantined, never rendered as evidence, and never silently dropped.

---

## 4. COMPLETENESS IS NOT A BOOLEAN

Reporting a single true/false is how the prior system lied. The archive reports
**one state per source**, plus an aggregate that is never better than its worst
member.

| State | Meaning | Assertable? |
|---|---|---|
| `COMPLETE` | P1–P5 all pass over a SEALED source | yes |
| `OPEN` | source may still grow | **no — by design** |
| `INCOMPLETE` | ≥ 1 predicate fails; failing addresses listed | no |
| `UNVERIFIED` | never reconciled since last change | no |
| `SOURCE_LOST` | original gone; sealed copy is now sole evidence | qualified |
| `QUARANTINED` | orphan derived artifacts present | no |

**Rule:** the archive's overall state is the **worst** state among its sources.
One `INCOMPLETE` source makes the archive `INCOMPLETE`. There is no partial
credit, and no averaging.

**Plain-language reporting is mandatory** (Principle 5). Not a status code —
a sentence naming what is missing and why:

> *"INCOMPLETE — 3 of 167 sources fail P2. Session f03463fb line 412 has no
> segment, no event, and no declared exclusion. Reconciled 2026-07-28 16:02."*

---

## 5. RECONCILIATION MUST BE EXTERNAL

Principle 3, made concrete.

```
   ~/.claude/projects/**/*.jsonl        (vendor writes)
              │
              ▼
    ┌──────────────────┐         ┌──────────────────┐
    │    IMPORTER      │         │   RECONCILER     │
    │  writes Layer 1  │         │  READ-ONLY on    │
    │                  │         │  BOTH artifacts  │
    └────────┬─────────┘         └────────┬─────────┘
             │                            │
             ▼                            ▼
      Conversations.db  ◀───reads────  verdict + failing addresses
```

**Binding constraints:**

1. The reconciler shares **no code** with the importer — not a module, not a
   parser, not a helper. A shared parser bug would pass both.
2. The reconciler **never writes** to `ConversationRawSegments`. It writes only
   to `IntegrityChecks`.
3. The reconciler reads the **sealed vault copy**, never the live vendor file —
   the live file can change mid-check.
4. **The importer may not set completeness state.** It records what it did.
   Only the reconciler assigns a state.
5. The reconciler must be runnable standalone, from a shell, with the database
   present and no other component of this system installed.

**Corollary:** an importer reporting `status='ok'` means *"I finished without
raising."* It never means *"the archive is complete."* Those are different
claims and must never be printed by the same program.

---

## 6. SEMANTIC CLASSIFICATION AT THE EVIDENCE LAYER

Principle 4. The observation was that only **64 of 361** `user` records are human
utterances; 293 are tool-result envelopes wearing the user role. Inferring that
later is how a 5.6× counting error becomes a 581-vs-3,032 discrepancy.

Classification is therefore computed **at import**, stored as a first-class
column, and **versioned**:

```sql
speech_class            TEXT NOT NULL,   -- see below
classification_rule_ver TEXT NOT NULL    -- e.g. 'v1.2026-07-28'
```

| `speech_class` | Definition | Today's count |
|---|---|---:|
| `human-utterance` | typed or spoken by Saba | 64 |
| `assistant-reply` | assistant text block shown to Saba | 160 |
| `assistant-reasoning` | assistant thinking block | 289 |
| `tool-invocation` | assistant tool_use block | 296 |
| `tool-result` | tool output in a user-role record | 296 |
| `attachment-ref` | image or file reference | 1 |
| `system-injected` | `isMeta`, reminders, hook context | — |
| `session-event` | no uuid; mode, title, queue | 443 |

**Three rules governing this:**

1. Classification is **derived**, never authoritative. `record_type` and
   `content_json` remain verbatim; classification sits beside them.
2. **Rule versions are never retroactively overwritten.** A changed rule
   produces a new version and a recomputation pass, and both stay visible.
3. Classification failure is **not** a completeness failure. An unclassifiable
   record is stored as `unclassified` and reported — it is still preserved.

---

## 7. TEST SUITE

Each predicate maps to a concrete, repeatable test. Verified feasible today.

| ID | Predicate | Method | Passes when |
|---|---|---|---|
| T1 | P1 | `sha256(vault_copy)` vs `SourceFiles.sha256` | equal, all sources |
| T2 | P2 | build address set from source; left-join archive | zero unmatched both ways |
| T3 | P2 | group archive rows by address | zero addresses with count > 1 |
| T4 | P3 | re-hash bytes at each address | matches `row_sha256`, all rows |
| T5 | P4 | emit reconstruction, hash it | equals `SourceFiles.sha256` |
| T6 | P5 | summaries left-join provenance | zero orphans |
| T7 | P5 | provenance left-join segments | zero dangling refs |
| T8 | seal | line count + hash stable across two reads ≥30 min | stable ⇒ SEALED |
| T9 | coverage | filesystem scan vs `SourceFiles` | every `.jsonl` present |
| T10 | liveness | most recent successful reconciliation | within 24 h |

**T5 is the master test.** T2, T3 and T4 localise a failure to an address; T5
proves the whole file. A design where T5 can pass while data is missing is a
broken design.

**T9 is the test whose absence caused the 2026-07-26 failure** — it consults the
filesystem, not the database's opinion of itself.

**Negative testing is required before production.** Each of T1–T7 must be shown
to *fail* against a deliberately damaged copy: a deleted line, a duplicated line,
a flipped byte, a summary with its provenance removed. **A check never observed
failing is not known to work.**

---

## 8. WHAT COMPLETENESS DOES NOT CLAIM

Principle 6. Stated plainly, in advance.

Completeness means: **every byte of every sealed source is preserved,
addressable, faithful, reconstructable, and every derived claim traces back to
it.**

It does **not** mean:

- **That the source captured everything that happened.** If the vendor omits a
  record before writing, no downstream system can know. Completeness is relative
  to the source, and says so.
- **That compaction was prevented.** Harness-side summarisation is recorded and
  detectable; it is not preventable by us. 7 of 167 sessions show it.
- **That conversations outside Claude Code are present.** ChatGPT, Grok, Gemini
  are not on this machine. An archive complete over Claude sources is silent
  about the rest — and must state that rather than imply coverage.
- **That the archive survives disk failure.** Off-machine copies are a separate
  control with separate evidence.
- **That triggers cannot fail.** They can. T9 and T10 make failure *visible
  within 24 hours*, which is the claim — not that it cannot occur.

**The word "guaranteed" does not appear in this specification.** It appeared in
the architecture that lost 81% of a conversation.

---

## 9. FINDINGS FROM TESTING THAT CHANGED THIS SPEC

Both were discovered by running tests against the live source, not by reasoning.

**9.1 Content hash cannot be the key.**
1,680 lines produced 1,460 distinct hashes — **220 legitimate duplicate lines**.
Had the address been the content hash, 220 records would have silently collapsed.
**The address is `(source_sha256, line_no)`.**

**9.2 The seal state is not theoretical.**
The live session file grew **1,638 → 1,680 lines** during this audit. Any
completeness verdict computed against an open file is stale on arrival.
`OPEN — not assertable` is a required state, not a convenience.

**9.3 Byte-exact reconstruction is implementable.**
Verified: 6,074,043 bytes reproduced exactly, SHA-256 `8f30ba5f…`. P4 is not
aspirational.

---

## 10. THE DEFINITION, IN ONE PARAGRAPH

> An archive is **complete with respect to a named set of sealed sources** when an
> independent reconciler — sharing no code with the importer — can demonstrate
> that every sealed copy re-hashes to its recorded seal; that every line of every
> sealed source maps to exactly one segment, session event, or declared exclusion;
> that every stored row re-hashes to the bytes at its address; that each sealed
> source can be reconstructed byte-for-byte from the archive alone; and that every
> derived artifact resolves through provenance to segments meeting those
> conditions. Completeness is asserted per source, never over open sources, and
> the archive's state is the worst state among its sources. It is not a count. It
> is a demonstration, repeatable by anyone holding the vault and the reconciler.

---

## 11. AWAITING APPROVAL

This specification adds two decisions to the ten in the architecture document:

**D11 — Seal window.** 30 minutes of quiescence proposed. Shorter seals faster
and risks premature verdicts; longer is safer and delays assertability.
**Recommend 30 minutes**, with the currently-running session always OPEN
regardless of quiescence.

**D12 — Storage cost of P4.** Byte-exact reconstruction requires either storing
each raw line verbatim (roughly doubling database size — ~180 MB today) or
reconstructing by reading the sealed vault copy at verification time (no
duplication, but P4 then depends on P1 holding).
**Recommend the second:** reconstruct from the vault. It keeps the database
lean, and P1 is tested first in every run anyway — if the vault is damaged, no
verdict should be trusted regardless.

**Nothing proceeds until D1–D12 are ruled.**
