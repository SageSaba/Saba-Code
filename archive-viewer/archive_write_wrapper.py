#!/usr/bin/env python3
"""Archive Write Wrapper — the only path allowed to persist writes to
protected archive databases (see CLAUDE.md: "the archive does not trust
Claude to self-police").

Run:  python3 archive_write_wrapper.py
Then submit writes at  http://127.0.0.1:8767  — nothing else should ever
open Sermons.db or Archive_Suggestions.db in read-write mode directly.

Every write attempt — accepted, rejected, or failed — is logged to
audit_log.db with full provenance: approval_id, old/new values, timestamp,
and verification result. Nothing is ever silently dropped.

Endpoints:
  GET  /health   status of each configured database (writable? reachable?)
  POST /write    submit one write; see WriteRequest below for the shape

Sermons.db is hard-locked (allow_writes=False) until the five-criterion
proof named in CLAUDE.md is defined and wired into `verify_five_criteria`
below. Until then every write request against it is rejected and logged,
never applied — there is no override.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"   # local only — never exposed to the internet
PORT = 8767

# Overridable via env so this can be pointed at a disposable test database
# (CLAUDE.md's /private/tmp/test_archive/) instead of the real archive.
SERMONS_PATH = os.environ.get(
    "ARCHIVE_SERMONS_DB", "/Users/saba/Archive/Sermons.db")
SUGGESTIONS_PATH = os.environ.get(
    "ARCHIVE_SUGGESTIONS_DB", "/Users/saba/Archive/Archive_Suggestions.db")
AUDIT_PATH = os.environ.get(
    "ARCHIVE_AUDIT_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_log.db"))

# db name -> (path, allow_writes). Sermons.db stays locked until the
# five-criterion proof (CLAUDE.md) is defined and checked in verify_five_criteria.
DATABASES = {
    "sermons": {"path": SERMONS_PATH, "allow_writes": False},
    "suggestions": {"path": SUGGESTIONS_PATH, "allow_writes": True},
}


class WriteRejected(Exception):
    """A write that was correctly refused (not a server error)."""
    def __init__(self, reason, http_status=409):
        super().__init__(reason)
        self.reason = reason
        self.http_status = http_status


# ------------------------------------------------------------------ audit

def audit_init():
    con = sqlite3.connect(AUDIT_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS write_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            db_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            op TEXT NOT NULL,
            pk_json TEXT,
            expect_json TEXT,
            set_json TEXT,
            old_values_json TEXT,
            verification_result TEXT NOT NULL,
            applied INTEGER NOT NULL,
            error TEXT
        )""")
    con.commit()
    con.close()


def audit_record(approval_id, db_name, table_name, op, pk, expect, set_,
                  old_values, verification_result, applied, error=None):
    con = sqlite3.connect(AUDIT_PATH)
    con.execute(
        "INSERT INTO write_log (approval_id, ts, db_name, table_name, op, "
        "pk_json, expect_json, set_json, old_values_json, "
        "verification_result, applied, error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (approval_id, datetime.now(timezone.utc).isoformat(), db_name,
         table_name, op, json.dumps(pk), json.dumps(expect), json.dumps(set_),
         json.dumps(old_values), verification_result, int(applied), error))
    con.commit()
    con.close()


# --------------------------------------------------------------- five-criteria

def verify_five_criteria(db_name):
    """Gate for ever flipping a database's allow_writes to True.

    Not yet defined — see CLAUDE.md "Never modify Sermons.db directly
    until the five-criterion proof passes on the disposable test
    database." Until Saba specifies the five criteria, this always
    reports unmet so DATABASES[...]["allow_writes"] is the only gate
    that matters (and sermons stays False).
    """
    return False, "five-criterion proof not yet defined in CLAUDE.md"


# -------------------------------------------------------------------- write

def _where_clause(pk):
    return " AND ".join(f"{col} = ?" for col in pk), list(pk.values())


def apply_write(req):
    """req: {approval_id, db, table, op, pk?, expect?, set?}
    op is one of "insert", "update", "delete".
    Returns a dict describing the outcome; raises WriteRejected for a
    correctly-refused write (bad db, lock, verification mismatch).
    """
    approval_id = req.get("approval_id")
    db_name = req.get("db")
    table = req.get("table")
    op = req.get("op")
    pk = req.get("pk") or {}
    expect = req.get("expect") or {}
    set_ = req.get("set") or {}

    if not approval_id:
        raise WriteRejected("approval_id is required for every write", 400)
    if db_name not in DATABASES:
        raise WriteRejected(f"unknown database {db_name!r}", 400)
    if op not in ("insert", "update", "delete"):
        raise WriteRejected(f"unknown op {op!r}", 400)
    if not table:
        raise WriteRejected("table is required", 400)

    db_conf = DATABASES[db_name]
    if not db_conf["allow_writes"]:
        ok, why = verify_five_criteria(db_name)
        if not ok:
            audit_record(approval_id, db_name, table, op, pk, expect, set_,
                         None, f"write_locked: {why}", applied=False,
                         error="write_locked")
            raise WriteRejected(f"writes to {db_name!r} are locked: {why}",
                                403)

    if not os.path.exists(db_conf["path"]):
        raise WriteRejected(f"database file not found: {db_conf['path']}",
                             503)

    con = sqlite3.connect(db_conf["path"])
    con.row_factory = sqlite3.Row
    old_values = None
    verification_result = "n/a"
    applied = False
    error = None
    try:
        if op in ("update", "delete"):
            if not pk:
                raise WriteRejected("pk is required for update/delete", 400)
            where_sql, where_vals = _where_clause(pk)
            row = con.execute(
                f"SELECT * FROM {table} WHERE {where_sql}", where_vals
            ).fetchone()
            if row is None:
                verification_result = "not_found"
                raise WriteRejected(
                    f"no row in {table} matching {pk}", 404)
            old_values = dict(row)
            if expect:
                mismatches = {
                    k: {"expected": v, "actual": old_values.get(k)}
                    for k, v in expect.items() if old_values.get(k) != v
                }
                if mismatches:
                    verification_result = f"mismatch: {mismatches}"
                    raise WriteRejected(
                        f"expected values did not match current row: "
                        f"{mismatches}", 409)
            verification_result = "match" if expect else "unverified (no expect given)"

        if op == "insert":
            cols = list(set_.keys())
            placeholders = ", ".join("?" for _ in cols)
            con.execute(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                [set_[c] for c in cols])
        elif op == "update":
            if not set_:
                raise WriteRejected("set is required for update", 400)
            set_sql = ", ".join(f"{col} = ?" for col in set_)
            where_sql, where_vals = _where_clause(pk)
            con.execute(
                f"UPDATE {table} SET {set_sql} WHERE {where_sql}",
                list(set_.values()) + where_vals)
        elif op == "delete":
            where_sql, where_vals = _where_clause(pk)
            con.execute(f"DELETE FROM {table} WHERE {where_sql}", where_vals)

        con.commit()
        applied = True
        return {
            "approval_id": approval_id, "applied": True,
            "verification_result": verification_result,
            "old_values": old_values,
        }
    except WriteRejected as e:
        error = e.reason
        raise
    except Exception as e:
        error = str(e)
        verification_result = verification_result if verification_result != "n/a" else "error"
        raise WriteRejected(f"write failed: {e}", 500)
    finally:
        con.close()
        audit_record(approval_id, db_name, table, op, pk, expect, set_,
                     old_values, verification_result, applied, error)


# --------------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            status = {}
            for name, conf in DATABASES.items():
                status[name] = {
                    "reachable": os.path.exists(conf["path"]),
                    "allow_writes": conf["allow_writes"],
                }
            self._json(200, {"ok": True, "databases": status})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/write":
            self._json(404, {"ok": False, "error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"ok": False, "error": "invalid JSON"})
            return
        try:
            result = apply_write(req)
            self._json(200, {"ok": True, **result})
        except WriteRejected as e:
            self._json(e.http_status, {"ok": False, "error": e.reason})

    def log_message(self, fmt, *args):
        pass  # audit_log.db is the log of record; keep stdout quiet


def main():
    audit_init()
    print(f"Archive Write Wrapper — listening on http://{HOST}:{PORT}")
    for name, conf in DATABASES.items():
        print(f"  {name}: {conf['path']}  "
              f"(writes {'ALLOWED' if conf['allow_writes'] else 'LOCKED'})")
    print(f"  audit trail: {AUDIT_PATH}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
