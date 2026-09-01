# CURRENT_STATE.md

## As of 2026-09-01

### Done
- `.claude/hooks/session-start.sh` + `.claude/settings.json` — installs the
  Python packages the archive scripts import (numpy, httpx, anthropic, mcp,
  cffi) on Claude Code on the web sessions. Merged to `main`.
- `CLAUDE.md` — operating instructions: capability-based read/write
  boundary, startup procedure. Pushed to `claude/terminal-setup-awsquu`
  (not yet merged to `main`).
- `archive-viewer/archive_write_wrapper.py` — the write-boundary service
  described in `CLAUDE.md`. Runs on 127.0.0.1:8767, matching the
  connector.py/ask_archive.py house style (stdlib `http.server`, no
  external framework). Every write attempt (accepted or rejected) is
  logged with approval_id, old/new values, timestamp, and verification
  result to `archive-viewer/audit_log.db`. Tested in-sandbox against
  synthetic databases only — see "Blocked" below.

### Decided (2026-09-01)
- Scope of the wrapper: **AI-driven writes only.** The existing manual
  bulk-rebuild scripts (`people_reference.py`, `build_organizations.py`,
  `name_scanner.py`, etc.) keep writing directly to `Archive_Suggestions.db`
  as they always have — they are Saba-run, one-off table reseeds, not
  row-level corrections, and are out of scope for `archive_write_wrapper.py`.
  The wrapper governs only writes Claude makes on Saba's behalf going
  forward; no migration of those scripts is planned.

### Blocked
- The "five-criterion proof" that `CLAUDE.md` requires before any write
  ever touches the real `Sermons.db` is not defined anywhere in this repo
  (grepped for "criteri", "proof" — only the `CLAUDE.md` reference to it
  exists). Until Saba defines it, `archive_write_wrapper.py` hard-disables
  writes to the `sermons` database entry (`allow_writes: False`) —
  writes to `Archive_Suggestions.db` are allowed and audited, since that
  database was already writable by existing scripts.
- Nothing in this session has ever run against the real `~/Archive/Sermons.db`
  or `~/Archive/Archive_Suggestions.db` — this is a cloud sandbox with no
  access to `/Users/saba/...` paths. All wrapper testing used synthetic
  disposable SQLite files in the sandbox's scratch directory.

### Forbidden right now
- No direct writes to `Sermons.db` — enforced in code (wrapper rejects
  and logs any write request for `db: "sermons"`).
- No write to `Archive_Suggestions.db` (or any protected DB) that bypasses
  `archive_write_wrapper.py`, once a session is calling it for a given task.

### Next action
1. Saba defines the five-criterion proof (what must be demonstrated on
   the disposable test database before Sermons.db writes are ever enabled)
   — asked in chat 2026-09-01, answer pending.
2. Once (1) is answered, wire the proof's checks into
   `verify_five_criteria()` in `archive_write_wrapper.py` and re-test
   against the disposable database at `/private/tmp/test_archive/` on the
   actual Mac (this sandbox can't reach that path).
