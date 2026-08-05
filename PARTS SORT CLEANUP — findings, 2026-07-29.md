# Parts Sort/Kind Cleanup — Findings

*Written while Saba drove to West Virginia, 2026-07-29. Read-only investigation against
`~/Archive/Sermons.db`, except for the one normalization described below, which touched
`Parts` only — never `RawSegments`. Context read first from
`/Users/saba/Desktop/Saba Code/The Sorts and the Questions.md`.*

---

## Is Parts safe to edit? — checked before touching anything

Yes. `Parts` is a separate, derived/curated table — it has its own `ID` primary key and
points at `Services` by `service_id`; it has no foreign key into `RawSegments` and no
trigger or view that writes back to it. `RawSegments` (3,026,090 rows) was not written
to, read from only. The raw base stayed sealed the whole time.

## Current counts — confirmed, and one number doesn't match

```
SELECT kind, COUNT(*) FROM Parts GROUP BY kind;
```

**Before the fix:**

| kind | count |
|---|---|
| song | 819 |
| sermon | 522 |
| testimony | 9 |
| prayer | 3 |
| exhortation | 2 |
| **Sermon** | **1** |

Total: 1,356 — which is the *entire* Parts table. There is **no room left over** for
any blank-kind rows in that arithmetic, and a direct check confirms it:

```
SELECT COUNT(*) FROM Parts WHERE kind IS NULL OR TRIM(kind)='';
→ 0
```

**I could not find the 24 blank-kind rows described in "The Sorts and the Questions.md."**
I checked the live database and three historical backups — `Sermons_20260720_150911_before_aiconsult.db`
(7/20), `Sermons_before_2023originals_20260725_182437.db` (7/25, the same day that note
was written), and `Sermons_before_svc687_correction_20260728.db` (7/28) — and every one
shows the identical breakdown: the same six kinds, the same 1,356 total, zero blank or
null rows in all four snapshots. The closest thing I found to a "24" was **20 rows with
a blank `title`** (title IS NULL or empty) — not the same field, and not 24 either. I
did not find a script or log anywhere in `Archive Viewer/` that computed a 24-blank-kind
figure, so I can't trace where that count came from.

**This is a genuine "not resolved by me, needs your eyes" item** — either the 24-blank
figure was from a database state that predates even the 7/20 backup and got fixed
before that snapshot was taken, or it was counting something else (title? a different
table?) and got described as "kind" in the note, or I'm missing a database file you had
in mind. I'm reporting the discrepancy plainly rather than guessing which. **No blank
kind rows exist to tag right now** — there's nothing currently waiting on your judgment
for this particular part of the cleanup, but it's worth you confirming this isn't
masking a real problem in a file I didn't check.

## The stray "Sermon" row — found, given context, and fixed

**Parts.ID 84**, service_id 9.

| field | value |
|---|---|
| service | ID 9, **2016-12-03**, title "Christ Fellowship," org TRCF, sermon_giver Thomas Young |
| person / machine_person | Thomas Young |
| start / end | 00:24:28.420 – 00:58:00.160 (about 33.5 minutes) |
| title / machine_title | "- Reverend Helm had found his number. It had always seemed that he…" (this is the raw stored text — it genuinely ends mid-sentence with an ellipsis in the database, not a display artifact) |

**Surrounding raw text, for context** (from `RawSegments`, same service):

Just before the part begins (00:24:24–00:24:28): *"(audience laughing)"* following a
song and some back-and-forth banter — then the part opens at 00:24:28 with *"Reverend
Helm had found his number. It had always seemed that he called people that were at
their lowest in great need... Then Reverend Helm told him that he was taking him to
Israel..."* — read in third person, describing "Pastor Thomas."

Near the end, around 00:57:00–00:57:35: *"...It was in this home that I learned what
the heart of a loving father looked like... Their willingness to take in a troubled 16
year old girl is something I will always be grateful for... Your faith has made you
well."* — followed by applause.

This reads as a **personal testimony/life-story delivered in narrative form** (part
third-person, part first-person, audience present and responding) — Thomas Young's own
account of being found by Rev. Helm and sent to Israel, told at a 2016-12-03 TRCF
service. Whether it should ultimately sit under `sermon` or `testimony` is a content
call that belongs to you (both are valid readings — it was tagged "sermon," just
miscapitalized). I did **not** move it to `testimony`; I only normalized the casing,
which is the one unambiguous technical fix the task authorized.

**Fix applied:**

```sql
UPDATE Parts SET kind='sermon' WHERE kind='Sermon';
```

Verified after: `Parts` now shows exactly `song 819 / sermon 523 / testimony 9 /
prayer 3 / exhortation 2` — 1,356 total, unchanged, no `Sermon` variant left. This was
a straight lowercase normalization matching the existing convention already used by the
other 522 sermon rows — not a reclassification, not a guess about content.

## The 24 blank-kind rows — could not be located to report on

Since no rows with a blank or null `kind` exist in the current table (or in the three
backups checked), there is nothing to list service_id/timestamps/context for. If you
recall a specific database file, date, or tool that produced the "24" figure, point me
at it and I'll pull the same service_id/timestamp/context treatment for those rows that
I did for the "Sermon" row above.

---

**Files referenced:** `~/Archive/Sermons.db` (`Parts` table — one row's `kind` field
normalized), `/Users/saba/Desktop/Saba Code/The Sorts and the Questions.md` (source of
the 24-blank-row claim, not yet reconciled with the live data).
