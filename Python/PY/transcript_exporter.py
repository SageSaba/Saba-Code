#!/usr/bin/env python3
"""Transcript Exporter — a separate, stand-alone tool.

Run:  python3 transcript_exporter.py
Then open  http://127.0.0.1:8767  in your browser.

Enter a date (or a range), pick the service(s), and the full transcript
appears in one ordinary text box — ready for Command+A, Command+C, and
pasting anywhere.

This tool is intentionally exterior: it shares nothing with the Archive
Viewer (port 8765) or the AI Connector (port 8766) and changes nothing.
The database is opened in SQLite read-only mode (mode=ro) on every
request — writing to it is impossible through this program.
"""

import json
import os
import re
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = "/Users/saba/Archive/Sermons.db"
HOST = "127.0.0.1"          # local only — never exposed to the internet
PORT = 8767
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "Transcript Exporter.html"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def connect_ro():
    if not os.path.exists("/Volumes/Data"):
        raise ExporterError(503, "Data drive not connected — plug in the "
                                 "Data drive and try again.")
    if not os.path.exists(DB_PATH):
        raise ExporterError(503, f"Database not found at {DB_PATH}.")
    con = sqlite3.connect(f"file:{urllib.parse.quote(DB_PATH)}?mode=ro",
                          uri=True)
    con.row_factory = sqlite3.Row
    return con


class ExporterError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def time_to_seconds(t):
    parts = (t or "0").split(":")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = "0", parts[0], parts[1]
    else:
        return 0.0
    try:
        return int(h) * 3600 + int(m) * 60 + float(s)
    except ValueError:
        return 0.0


def services_between(date_from, date_to):
    """Matching services in the inclusive range, with their speakers."""
    con = connect_ro()
    try:
        rows = con.execute(
            """
            SELECT ID, preach_date, title, sermon_giver
            FROM Services
            WHERE preach_date >= ? AND preach_date <= ?
            ORDER BY preach_date, ID
            """, (date_from, date_to)).fetchall()
        if not rows:
            return []
        ids = [r["ID"] for r in rows]
        marks = ",".join("?" * len(ids))
        by_service = {}
        for r in con.execute(
                f"""
                SELECT r.service_id, sp.full_name
                FROM RawSegments r JOIN Speakers sp ON sp.ID = r.speaker_id
                WHERE r.service_id IN ({marks})
                GROUP BY r.service_id, sp.full_name
                ORDER BY sp.full_name
                """, ids):
            by_service.setdefault(r["service_id"], []).append(r["full_name"])
        return [
            {"service_id": r["ID"], "date": r["preach_date"],
             "title": r["title"] or "",
             "sermon_giver": r["sermon_giver"] or "",
             "speakers": by_service.get(r["ID"], [])}
            for r in rows
        ]
    finally:
        con.close()


def transcript_of(service_ids):
    """Full transcripts for the chosen services, segments de-duplicated
    (the table stores some lines twice) and in true time order."""
    con = connect_ro()
    try:
        out = []
        for sid in service_ids:
            svc = con.execute(
                "SELECT ID, preach_date, title, sermon_giver "
                "FROM Services WHERE ID = ?", (sid,)).fetchone()
            if not svc:
                raise ExporterError(404, f"No service with ID {sid}.")
            segs = con.execute(
                """
                SELECT r.start, r.end, r.text,
                       COALESCE(sp.full_name, '') AS speaker
                FROM RawSegments r
                LEFT JOIN Speakers sp ON sp.ID = r.speaker_id
                WHERE r.service_id = ?
                GROUP BY r.start, r.text
                ORDER BY r.start
                """, (sid,)).fetchall()
            out.append({
                "service_id": svc["ID"], "date": svc["preach_date"],
                "title": svc["title"] or "",
                "sermon_giver": svc["sermon_giver"] or "",
                "segments": [
                    {"start": round(time_to_seconds(r["start"]), 2),
                     "end": round(time_to_seconds(r["end"]), 2),
                     "speaker": r["speaker"], "text": r["text"] or ""}
                    for r in segs
                ],
            })
        return out
    finally:
        con.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, PAGE), "rb") as f:
                    body = f.read()
            except OSError:
                self.send_error(500, f"{PAGE} missing next to this script")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        try:
            if parsed.path == "/api/services":
                date_from = (qs.get("from", [""])[0]).strip()
                date_to = (qs.get("to", [""])[0]).strip() or date_from
                if not DATE_RE.match(date_from) or not DATE_RE.match(date_to):
                    raise ExporterError(400, "Dates must be YYYY-MM-DD.")
                if date_to < date_from:
                    date_from, date_to = date_to, date_from
                self.send_json({"services": services_between(date_from,
                                                             date_to)})
                return

            if parsed.path == "/api/transcript":
                raw = (qs.get("ids", [""])[0]).strip()
                try:
                    ids = [int(x) for x in raw.split(",") if x.strip()]
                except ValueError:
                    raise ExporterError(400, "ids must be numbers, "
                                             "comma-separated.")
                if not ids:
                    raise ExporterError(400, "Choose at least one service.")
                self.send_json({"services": transcript_of(ids)})
                return
        except ExporterError as e:
            self.send_json({"error": e.message}, e.status)
            return
        except sqlite3.Error as e:
            self.send_json({"error": f"Database error: {e}"}, 500)
            return

        self.send_error(404)


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Database not found: {DB_PATH} — is the Data "
                         "drive mounted?")
    print(f"Transcript Exporter running — open http://{HOST}:{PORT}")
    print("Read-only over", DB_PATH)
    print("Press Ctrl+C to stop.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
