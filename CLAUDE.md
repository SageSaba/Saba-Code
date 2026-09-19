# Claude Code Operator — Saba-Code Project

## Operating Environment

- **Project:** Saba-Code archive system
- **Canonical archive:** `~/Archive/Sermons.db` (read-only to Claude until proof passes)
- **Working environment:** `/Users/saba/Desktop/Saba-Code/`
- **Test environment:** `/private/tmp/test_archive/` (disposable)

## Architectural Enforcement

**Capability-based boundaries, not conversational rules:**

1. **Read access** — Claude has broad, unrestricted read access to archive metadata for diagnostic inspection
2. **Write access** — Protected. Only the `archive_write_wrapper` service (Python, separate process) can perform persistent writes to protected databases
3. **Audit trail** — Every protected write is logged with full provenance (approval_id, old/new values, timestamp, verification result)

The archive does not trust Claude to self-police. The system makes the authorized operation the only viable operation.

## Startup Procedure

Every session:
1. Read `CLAUDE.md` (this file) — orientation
2. Read `CURRENT_STATE.md` — yesterday's stopping point and next action
3. Report startup state (one line: what is done, what is in progress, what is forbidden)
4. Continue

## If Something Is Missing

Check `CURRENT_STATE.md`. It is the source of truth for where work stands and what must not be touched.

## Never

- Modify `Sermons.db` directly until the five-criterion proof passes on the disposable test database
- Write to the archive without going through the wrapper service
- Use conversational assumptions about what was done yesterday — read `CURRENT_STATE.md`
