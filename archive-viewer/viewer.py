#!/usr/bin/env python3
"""Archive Viewer — local server wiring the display to Sermons.db.

Run:  python3 viewer.py
Then open  http://localhost:8765  in your browser.

Serves three things:
  /                     the viewer page (index.html, same folder)
  /api/search?q=...     segments whose text contains the words, with times
  /video/<service_id>   streams that service's video (with seeking support)
"""

import json
import mimetypes
import os
import re
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = "/Users/saba/Archive/Sermons.db"
SUGGESTIONS_DB = "/Users/saba/Archive/Archive_Suggestions.db"
VIDEO_ROOT = "/Volumes/Data/Video Archive"
PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))
MAX_HITS = 500


def time_to_seconds(t):
    """'01:59:10.520' -> 7150.52"""
    parts = t.split(":")
    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h, m, s = "0", parts[0], parts[1]
    else:
        return 0.0
    return int(h) * 3600 + int(m) * 60 + float(s)


# Words that carry no meaning in a spoken question like
# "show me where Joe Nance spoke" — dropped before searching.
FILLER_WORDS = {
    "show", "me", "where", "when", "did", "i", "want", "to", "hear", "who",
    "spoke", "speak", "speaks", "speaking", "said", "say", "says", "talk",
    "talked", "talking", "play", "find", "search", "for", "all", "times",
    "every", "time", "the", "a", "an", "clip", "clips", "video", "videos",
    "see", "watch", "listen", "his", "her", "him", "them", "was", "is",
    "please", "can", "you", "everything", "anything", "moments", "places",
    "about", "on", "of", "in", "at", "and", "or", "with", "what", "how",
    "look", "looking", "ask", "asking", "asked", "she", "he", "we", "us",
    "that", "this", "it", "is", "are", "be",
}

# Words meaning the person is singing — transcripts mark sung lines with ♪.
SING_WORDS = {"sing", "sings", "sang", "sung", "singing", "song", "songs"}


def like_escape(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def words_of(s):
    return [w.strip("'") for w in re.split(r"[^\w']+", s.lower()) if w.strip("'")]


def find_speaker(con, query_words):
    """Return (id, name, name_words) if a speaker's name appears in the query.
    Full name always wins; a single first or last name works when only one
    speaker has it (e.g. 'elizabeth' — but 'doss' alone stays ambiguous)."""
    qset = set(query_words)
    partial = []
    for sid, name in con.execute("SELECT ID, full_name FROM Speakers"):
        nwords = words_of(name or "")
        if not nwords:
            continue
        if all(w in qset for w in nwords):          # full name present
            return sid, name, nwords
        matched = [w for w in nwords if len(w) > 2 and w in qset]
        if matched:
            partial.append((sid, name, matched))
    if len({sid for sid, _, _ in partial}) == 1:     # unambiguous single name
        return partial[0]
    return None


def hit_row(r, text=None, speaker=None):
    return {
        "id": r["id"],
        "service_id": r["service_id"],
        "date": r["preach_date"],
        "title": r["title"] or "",
        "speaker": speaker if speaker is not None else (r["speaker"] or ""),
        "start": round(time_to_seconds(r["start"]), 2),
        "end": round(time_to_seconds(r["end"]), 2),
        "text": text if text is not None else (r["text"] or ""),
        "has_video": bool(r["media_path"]) and os.path.exists(r["media_path"]),
    }


def text_search(con, phrase, and_words=None):
    """Phrase match, or all-words match when and_words is given."""
    if and_words:
        where = " AND ".join(["r.text LIKE ? ESCAPE '\\'"] * len(and_words))
        params = ["%" + like_escape(w) + "%" for w in and_words]
    else:
        where = "r.text LIKE ? ESCAPE '\\'"
        params = ["%" + like_escape(phrase) + "%"]
    rows = con.execute(
        f"""
        SELECT MIN(r.ID) AS id, r.service_id, r.start, r.end, r.text,
               s.preach_date, s.title, s.media_path,
               COALESCE(sp.full_name, '') AS speaker
        FROM RawSegments r
        JOIN Services s ON s.ID = r.service_id
        LEFT JOIN Speakers sp ON sp.ID = r.speaker_id
        WHERE {where}
        GROUP BY r.service_id, r.start, r.text
        ORDER BY s.preach_date, r.start
        LIMIT ?
        """,
        params + [MAX_HITS],
    ).fetchall()
    return [hit_row(r) for r in rows]


# A person search lists every segment they speak, so the whole record is
# choosable — capped only to keep the page usable for very large speakers.
SPEAKER_MAX = 3000


def speaker_segments(con, sid, name, only_song=False):
    """Every segment this speaker says, in order — time, words, service.
    only_song narrows to sung lines (the transcripts mark them with ♪)."""
    song = "AND r.text LIKE '%♪%'" if only_song else ""
    total = con.execute(
        f"SELECT COUNT(*) FROM RawSegments r WHERE r.speaker_id = ? {song}",
        (sid,),
    ).fetchone()[0]
    rows = con.execute(
        f"""
        SELECT MIN(r.ID) AS id, r.service_id, r.start, r.end, r.text,
               s.preach_date, s.title, s.media_path
        FROM RawSegments r
        JOIN Services s ON s.ID = r.service_id
        WHERE r.speaker_id = ? {song}
        GROUP BY r.service_id, r.start, r.text
        ORDER BY s.preach_date, r.start
        LIMIT ?
        """,
        (sid, SPEAKER_MAX),
    ).fetchall()
    return [hit_row(r, speaker=name) for r in rows], total


def speaker_text_search(con, sid, name, and_words):
    where = " AND ".join(["r.text LIKE ? ESCAPE '\\'"] * len(and_words))
    params = ["%" + like_escape(w) + "%" for w in and_words]
    rows = con.execute(
        f"""
        SELECT MIN(r.ID) AS id, r.service_id, r.start, r.end, r.text,
               s.preach_date, s.title, s.media_path
        FROM RawSegments r
        JOIN Services s ON s.ID = r.service_id
        WHERE r.speaker_id = ? AND {where}
        GROUP BY r.service_id, r.start, r.text
        ORDER BY s.preach_date, r.start
        LIMIT ?
        """,
        [sid] + params + [MAX_HITS],
    ).fetchall()
    return [hit_row(r, speaker=name) for r in rows]


def search(query):
    """Understand a plain question: a speaker's name finds where they speak;
    other words find where they were said; both together combine."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        qwords = words_of(query)
        found = find_speaker(con, qwords)
        if found:
            sid, name, nwords = found
            topic = [w for w in qwords
                     if w not in set(nwords) and w not in FILLER_WORDS]
            if topic and all(w in SING_WORDS for w in topic):
                hits, total = speaker_segments(con, sid, name, only_song=True)
                return hits, f"{name} — singing, {total} moments"
            if topic:
                hits = speaker_text_search(con, sid, name, topic)
                explain = f"{name} — moments with “{' '.join(topic)}”"
                # all words together found nothing — try the biggest word alone
                if not hits and len(topic) > 1:
                    for w in sorted(topic, key=len, reverse=True):
                        hits = speaker_text_search(con, sid, name, [w])
                        if hits:
                            explain = f"{name} — moments with “{w}”"
                            break
            else:
                hits, total = speaker_segments(con, sid, name)
                explain = f"{name} — all {total} segments"
                if total > len(hits):
                    explain = (f"{name} — first {len(hits)} of {total} segments "
                               f"(add a word to narrow)")
            return hits, explain

        hits = text_search(con, query)
        if hits:
            return hits, None
        # exact phrase not found — try all meaningful words in any order
        topic = [w for w in qwords if w not in FILLER_WORDS]
        if topic:
            hits = text_search(con, None, and_words=topic)
            if hits:
                return hits, f"moments with “{' '.join(topic)}”"
            for w in sorted(topic, key=len, reverse=True):
                hits = text_search(con, None, and_words=[w])
                if hits:
                    return hits, f"moments with “{w}”"
        return [], None
    finally:
        con.close()


def seconds_to_time(t):
    t = max(0.0, t)
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def service_context(con, service_id, t):
    """The service's entire transcript, in order — every line clickable in
    the display so any point of the sermon can be jumped to directly."""
    rows = con.execute(
        """
        SELECT r.start, r.text, COALESCE(sp.full_name, '') AS speaker
        FROM RawSegments r
        LEFT JOIN Speakers sp ON sp.ID = r.speaker_id
        WHERE r.service_id = ?
        GROUP BY r.start, r.text
        ORDER BY r.start
        """,
        (service_id,),
    ).fetchall()
    return [
        {"start": round(time_to_seconds(r["start"]), 2),
         "speaker": r["speaker"], "text": r["text"] or ""}
        for r in rows
    ]


def all_sermons():
    """Every sermon in the Parts table, exactly as stored — no retitling."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                           "AND name='Parts'").fetchone():
            return None
        rows = con.execute(
            """
            SELECT p.ID AS part_id, p.service_id, p.person, p.title,
                   p.start, p.end,
                   s.preach_date, s.title AS service_title, s.media_path
            FROM Parts p JOIN Services s ON s.ID = p.service_id
            WHERE p.kind = 'sermon'
            ORDER BY s.preach_date, p.start
            """).fetchall()
        return [
            {"part_id": r["part_id"], "service_id": r["service_id"],
             "person": r["person"] or "", "title": r["title"] or "",
             "date": r["preach_date"],
             "service_title": r["service_title"] or "",
             "start": round(time_to_seconds(r["start"]), 2),
             "end": round(time_to_seconds(r["end"]), 2),
             "has_video": bool(r["media_path"])
                          and os.path.exists(r["media_path"])}
            for r in rows
        ]
    finally:
        con.close()


def parts_of_service(service_id):
    """One service's parts (songs and sermons), as stored, in time order."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                           "AND name='Parts'").fetchone():
            return None
        rows = con.execute(
            "SELECT ID, kind, person, title, start, end FROM Parts "
            "WHERE service_id = ? ORDER BY start", (service_id,)).fetchall()
        return [
            {"part_id": r["ID"], "kind": r["kind"],
             "person": r["person"] or "", "title": r["title"] or "",
             "start": round(time_to_seconds(r["start"]), 2),
             "end": round(time_to_seconds(r["end"]), 2)}
            for r in rows
        ]
    finally:
        con.close()


def marks_con():
    """Marks are writes, so they live in Archive_Suggestions.db —
    Sermons.db stays read-only per the house law."""
    con = sqlite3.connect(SUGGESTIONS_DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS marks ("
        "  id INTEGER PRIMARY KEY,"
        "  service_id INTEGER NOT NULL,"
        "  seconds REAL NOT NULL,"
        "  note TEXT DEFAULT '',"
        "  created_at TEXT DEFAULT (datetime('now', 'localtime'))"
        ")"
    )
    return con


def save_mark(service_id, seconds, note):
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT preach_date, title FROM Services WHERE ID = ?",
        (service_id,)).fetchone()
    con.close()
    if not row:
        return None
    mcon = marks_con()
    cur = mcon.execute(
        "INSERT INTO marks (service_id, seconds, note) VALUES (?,?,?)",
        (service_id, seconds, note))
    mcon.commit()
    mark_id = cur.lastrowid
    mcon.close()
    return {"id": mark_id, "service_id": service_id,
            "seconds": seconds, "time": seconds_to_time(seconds),
            "date": row[0], "title": row[1] or "", "note": note}


def marks_of_service(service_id):
    mcon = marks_con()
    rows = mcon.execute(
        "SELECT id, seconds, note, created_at FROM marks "
        "WHERE service_id = ? ORDER BY seconds", (service_id,)).fetchall()
    mcon.close()
    return [{"id": r[0], "seconds": r[1], "time": seconds_to_time(r[1]),
             "note": r[2], "created_at": r[3]} for r in rows]


def media_path_for(service_id):
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT media_path FROM Services WHERE ID = ?", (service_id,)
    ).fetchone()
    con.close()
    if not row or not row[0]:
        return None
    path = os.path.realpath(row[0])
    if not path.startswith(os.path.realpath(VIDEO_ROOT) + os.sep):
        return None
    return path if os.path.exists(path) else None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    body = f.read()
            except OSError:
                self.send_error(500, "index.html missing next to viewer.py")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/screen":
            try:
                with open(os.path.join(HERE, "screen.html"), "rb") as f:
                    body = f.read()
            except OSError:
                self.send_error(500, "screen.html missing next to viewer.py")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/sermons":
            try:
                sermons = all_sermons()
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
                return
            if sermons is None:
                self.send_json({"error": "Parts table not found in the "
                                         "database."}, 500)
            else:
                self.send_json({"sermons": sermons})
            return

        if parsed.path == "/api/parts":
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                service_id = int(qs.get("service_id", ["0"])[0])
            except ValueError:
                self.send_json({"error": "bad service_id"}, 400)
                return
            try:
                parts = parts_of_service(service_id)
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
                return
            if parts is None:
                self.send_json({"error": "Parts table not found in the "
                                         "database."}, 500)
            else:
                self.send_json({"parts": parts})
            return

        if parsed.path == "/api/search":
            q = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
            if len(q) < 2:
                self.send_json({"query": q, "hits": []})
                return
            try:
                hits, explain = search(q)
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
                return
            self.send_json({"query": q, "hits": hits, "explain": explain})
            return

        if parsed.path == "/api/context":
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                service_id = int(qs.get("service_id", ["0"])[0])
                t = float(qs.get("t", ["0"])[0])
            except ValueError:
                self.send_json({"error": "bad parameters"}, 400)
                return
            con = sqlite3.connect(DB_PATH)
            con.row_factory = sqlite3.Row
            try:
                lines = service_context(con, service_id, t)
            finally:
                con.close()
            self.send_json({"lines": lines})
            return

        if parsed.path == "/api/marks":
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                service_id = int(qs.get("service_id", ["0"])[0])
            except ValueError:
                self.send_json({"error": "bad service_id"}, 400)
                return
            try:
                self.send_json({"marks": marks_of_service(service_id)})
            except sqlite3.Error as e:
                self.send_json({"error": str(e)}, 500)
            return

        m = re.fullmatch(r"/video/(\d+)", parsed.path)
        if m:
            self.serve_video(int(m.group(1)))
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/mark":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            service_id = int(data["service_id"])
            seconds = float(data["seconds"])
            note = str(data.get("note", ""))[:500]
        except (KeyError, ValueError, json.JSONDecodeError):
            self.send_json({"error": "bad mark"}, 400)
            return
        try:
            saved = save_mark(service_id, seconds, note)
        except sqlite3.Error as e:
            self.send_json({"error": str(e)}, 500)
            return
        if saved is None:
            self.send_json({"error": "no such service"}, 404)
        else:
            self.send_json({"saved": saved})

    def serve_video(self, service_id):
        path = media_path_for(service_id)
        if not path:
            self.send_error(404, "No video file for this service")
            return
        size = os.path.getsize(path)
        ctype = mimetypes.guess_type(path)[0] or "video/mp4"
        range_header = self.headers.get("Range")

        start, end = 0, size - 1
        status = 200
        if range_header:
            m = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    if m.group(2):
                        end = min(int(m.group(2)), size - 1)
                elif m.group(2):  # suffix range: last N bytes
                    start = max(0, size - int(m.group(2)))
                status = 206
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()

        try:
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(1024 * 512, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # browser scrubbed / closed the stream — normal


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Database not found: {DB_PATH} — is the Data drive mounted?")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Archive Viewer running — open http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
