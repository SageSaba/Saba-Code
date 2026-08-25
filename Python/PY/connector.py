#!/usr/bin/env python3
"""Archive AI Connector — read-only evidence API over Sermons.db.

Run:  python3 connector.py
Then an AI client (Open WebUI, or any tool that speaks HTTP) can ask
questions at  http://127.0.0.1:8766  and receive grounded evidence.

The connector NEVER answers questions itself and NEVER writes to the
database. It returns exact transcript text plus metadata; the AI model
forms the final answer from that evidence.

Endpoints:
  GET  /health           is everything reachable (drive, database, tables)
  GET  /openapi.json     machine-readable description of this API
  GET  /                 a small browser test page
  POST /search           search_transcripts: words + optional filters
  POST /context          get_context: transcript lines around a moment
  POST /service          get_service: one service's metadata and transcript
  POST /person           find_person: a name, as speaker and as spoken words
  POST /answer-question  evidence package for a natural-language question

The database is opened in SQLite read-only mode (mode=ro) on every
request — inserts, updates, and schema changes are impossible.
"""

import json
import os
import re
import sqlite3
import time
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = "/Users/saba/Archive/Sermons.db"
VIDEO_ROOT = "/Volumes/Data/Video Archive"
VIEWER_URL = "http://localhost:8765"   # the Archive Viewer, when it is running
HOST = "127.0.0.1"                     # local only — never exposed to the internet
PORT = 8766

DEFAULT_LIMIT = 25
MAX_LIMIT = 200
EVIDENCE_SEGMENTS = 8                  # strongest matches carried into evidence
CONTEXT_LINES = 3                      # transcript lines kept around each match


# ---------------------------------------------------------------- database

def connect_ro():
    """Open the database read-only. Raises helpful errors when unreachable."""
    if not os.path.exists("/Volumes/Data"):
        raise ConnectorError(503, "Data drive not connected — plug in the "
                                  "Data drive and try again.")
    if not os.path.exists(DB_PATH):
        raise ConnectorError(503, f"Database not found at {DB_PATH} — the "
                                  "drive is mounted but the file is missing.")
    con = sqlite3.connect(f"file:{urllib.parse.quote(DB_PATH)}?mode=ro",
                          uri=True)
    con.row_factory = sqlite3.Row
    return con


class ConnectorError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


REQUIRED = {
    "Services": {"ID", "preach_date", "title", "media_path"},
    "RawSegments": {"ID", "service_id", "start", "end", "speaker_id",
                    "type_id", "text"},
    "Speakers": {"ID", "full_name"},
    "Types": {"ID", "type_name"},
}


def check_schema(con):
    """Confirm the tables and columns this code relies on really exist."""
    problems = []
    for table, cols in REQUIRED.items():
        try:
            have = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
        except sqlite3.Error:
            have = set()
        if not have:
            problems.append(f"table {table} is missing")
        else:
            missing = cols - have
            if missing:
                problems.append(f"table {table} lacks columns: "
                                + ", ".join(sorted(missing)))
    if problems:
        raise ConnectorError(500, "Unexpected database schema — "
                             + "; ".join(problems))


def has_parts_table(con):
    return bool(con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='Parts'"
    ).fetchone())


# ------------------------------------------------------------- small tools

def time_to_seconds(t):
    """'01:59:10.520' -> 7150.52"""
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


def hms(seconds):
    s = max(0, int(round(seconds)))
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def like_escape(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def words_of(s):
    return [w.strip("'") for w in re.split(r"[^\w']+", (s or "").lower())
            if w.strip("'")]


# Words that carry no meaning in a spoken question — dropped before search.
FILLER_WORDS = {
    "show", "me", "where", "when", "did", "i", "want", "to", "hear", "who",
    "spoke", "speak", "speaks", "speaking", "said", "say", "says", "talk",
    "talked", "talking", "play", "find", "search", "for", "all", "times",
    "every", "time", "the", "a", "an", "clip", "clips", "video", "videos",
    "see", "watch", "listen", "his", "her", "him", "them", "was", "is",
    "please", "can", "you", "everything", "anything", "moments", "places",
    "about", "on", "of", "in", "at", "and", "or", "with", "what", "how",
    "look", "looking", "ask", "asking", "asked", "she", "he", "we", "us",
    "that", "this", "it", "are", "be", "why", "over", "years", "year",
    "sharing", "share", "shared", "need", "needs", "needed",
}


def find_speaker(con, query_words):
    """(id, name, name_words) when a tracked speaker's name is in the words.
    Full name always wins; a lone first/last name works when unambiguous."""
    qset = set(query_words)
    partial = []
    for r in con.execute("SELECT ID, full_name FROM Speakers"):
        nwords = words_of(r["full_name"])
        if not nwords:
            continue
        if all(w in qset for w in nwords):
            return r["ID"], r["full_name"], nwords
        matched = [w for w in nwords if len(w) > 2 and w in qset]
        if matched:
            partial.append((r["ID"], r["full_name"], matched))
    if len({sid for sid, _, _ in partial}) == 1:
        return partial[0]
    return None


def segment_dict(r, extra=None):
    start = time_to_seconds(r["start"])
    end = time_to_seconds(r["end"])
    media = r["media_path"] if "media_path" in r.keys() else None
    d = {
        "segment_id": r["id"],
        "service_id": r["service_id"],
        "date": r["preach_date"],
        "title": r["title"] or "",
        "speaker": (r["speaker"] or "") if "speaker" in r.keys() else "",
        "start_seconds": round(start, 2),
        "end_seconds": round(end, 2),
        "start": hms(start),
        "end": hms(end),
        "exact_text": r["text"] or "",
        "video_path": media or "",
        "video_file_exists": bool(media) and os.path.exists(media),
        "video_stream_url": f"{VIEWER_URL}/video/{r['service_id']}",
        "viewer_note": "video_stream_url works while the Archive Viewer "
                       "(viewer.py, port 8765) is running",
    }
    if extra:
        d.update(extra)
    return d


SEGMENT_SELECT = """
    SELECT MIN(r.ID) AS id, r.service_id, r.start, r.end, r.text,
           s.preach_date, s.title, s.media_path,
           COALESCE(sp.full_name, '') AS speaker
    FROM RawSegments r
    JOIN Services s ON s.ID = r.service_id
    LEFT JOIN Speakers sp ON sp.ID = r.speaker_id
"""
SEGMENT_GROUP = " GROUP BY r.service_id, r.start, r.text "


def run_segment_query(con, where, params, limit):
    rows = con.execute(
        SEGMENT_SELECT + " WHERE " + where + SEGMENT_GROUP
        + " ORDER BY s.preach_date, r.start LIMIT ?",
        params + [limit],
    ).fetchall()
    return [segment_dict(r) for r in rows]


# ---------------------------------------------------------------- searches

def search_transcripts(body):
    """Words + optional speaker / date range / content type filters."""
    query = (body.get("query") or "").strip()
    limit = min(int(body.get("limit") or DEFAULT_LIMIT), MAX_LIMIT)
    con = connect_ro()
    try:
        check_schema(con)
        where, params, interpretation = [], [], {}

        if query:
            if body.get("match_all_words"):
                topic = [w for w in words_of(query) if w not in FILLER_WORDS] \
                        or words_of(query)
                where += ["r.text LIKE ? ESCAPE '\\'"] * len(topic)
                params += ["%" + like_escape(w) + "%" for w in topic]
                interpretation["matched"] = "all of: " + ", ".join(topic)
            else:
                where.append("r.text LIKE ? ESCAPE '\\'")
                params.append("%" + like_escape(query) + "%")
                interpretation["matched"] = f"exact phrase “{query}”"

        speaker_name = (body.get("speaker") or "").strip()
        if speaker_name:
            found = find_speaker(con, words_of(speaker_name))
            if not found:
                known = [r["full_name"] for r in
                         con.execute("SELECT full_name FROM Speakers")]
                raise ConnectorError(404, f"No tracked speaker matches "
                                     f"“{speaker_name}”. Known speakers: "
                                     + ", ".join(known))
            where.append("r.speaker_id = ?")
            params.append(found[0])
            interpretation["speaker"] = found[1]

        if body.get("date_from"):
            where.append("s.preach_date >= ?")
            params.append(str(body["date_from"]))
        if body.get("date_to"):
            where.append("s.preach_date <= ?")
            params.append(str(body["date_to"]))

        ctype = (body.get("type") or "").strip()
        if ctype:
            row = con.execute(
                "SELECT ID, type_name FROM Types WHERE lower(type_name)=?",
                (ctype.lower(),)).fetchone()
            if not row:
                names = [r["type_name"] for r in
                         con.execute("SELECT type_name FROM Types")]
                raise ConnectorError(404, f"Unknown content type “{ctype}”. "
                                     "Types in this archive: " + ", ".join(names))
            if row["type_name"] == "Song":
                # The type tag misses most songs; transcripts mark sung
                # lines with ♪ — accept either signal.
                where.append("(r.type_id = ? OR r.text LIKE '%♪%')")
            else:
                where.append("r.type_id = ?")
            params.append(row["ID"])
            interpretation["type"] = row["type_name"]

        if not where:
            raise ConnectorError(400, "Give at least a query, a speaker, "
                                      "a date range, or a type.")

        hits = run_segment_query(con, " AND ".join(where), params, limit)
        return {"interpretation": interpretation, "count": len(hits),
                "limit": limit, "hits": hits,
                "message": None if hits else "No transcript match."}
    finally:
        con.close()


def service_lines(con, service_id):
    return con.execute(
        """
        SELECT MIN(r.ID) AS id, r.start, r.end, r.text,
               COALESCE(sp.full_name, '') AS speaker
        FROM RawSegments r
        LEFT JOIN Speakers sp ON sp.ID = r.speaker_id
        WHERE r.service_id = ?
        GROUP BY r.start, r.text
        ORDER BY r.start
        """, (service_id,)).fetchall()


def context_lines(con, service_id, t, before, after):
    """Transcript lines around second t, in chronological order."""
    rows = service_lines(con, service_id)
    if not rows:
        return []
    starts = [time_to_seconds(r["start"]) for r in rows]
    idx = min(range(len(starts)), key=lambda i: abs(starts[i] - t))
    lo, hi = max(0, idx - before), min(len(rows), idx + after + 1)
    return [
        {"segment_id": r["id"], "start": hms(time_to_seconds(r["start"])),
         "start_seconds": round(time_to_seconds(r["start"]), 2),
         "speaker": r["speaker"], "exact_text": r["text"] or "",
         "is_the_match": i == idx}
        for i, r in zip(range(lo, hi), rows[lo:hi])
    ]


def get_context(body):
    before = int(body.get("before") or CONTEXT_LINES)
    after = int(body.get("after") or CONTEXT_LINES)
    before, after = min(before, 50), min(after, 50)
    con = connect_ro()
    try:
        check_schema(con)
        if body.get("segment_id"):
            row = con.execute(
                "SELECT service_id, start FROM RawSegments WHERE ID = ?",
                (int(body["segment_id"]),)).fetchone()
            if not row:
                raise ConnectorError(404, "No segment with that segment_id.")
            service_id = row["service_id"]
            t = time_to_seconds(row["start"])
        elif body.get("service_id") is not None:
            service_id = int(body["service_id"])
            t = float(body.get("t") or 0)
        else:
            raise ConnectorError(400, "Send segment_id, or service_id plus t "
                                      "(seconds).")
        lines = context_lines(con, service_id, t, before, after)
        if not lines:
            raise ConnectorError(404, "No transcript for that service.")
        return {"service_id": service_id, "around_seconds": t, "lines": lines}
    finally:
        con.close()


def get_service(body):
    if body.get("service_id") is None:
        raise ConnectorError(400, "Send service_id.")
    service_id = int(body["service_id"])
    con = connect_ro()
    try:
        check_schema(con)
        svc = con.execute(
            "SELECT ID, preach_date, title, sermon_giver, notes, media_path "
            "FROM Services WHERE ID = ?", (service_id,)).fetchone()
        if not svc:
            raise ConnectorError(404, f"No service with ID {service_id}.")
        speakers = [r["full_name"] for r in con.execute(
            """SELECT DISTINCT sp.full_name FROM RawSegments r
               JOIN Speakers sp ON sp.ID = r.speaker_id
               WHERE r.service_id = ? ORDER BY sp.full_name""", (service_id,))]
        parts = []
        if has_parts_table(con):
            parts = [{"part_id": r["ID"], "kind": r["kind"],
                      "person": r["person"], "title": r["title"],
                      "start": hms(time_to_seconds(r["start"])),
                      "end": hms(time_to_seconds(r["end"]))}
                     for r in con.execute(
                         "SELECT * FROM Parts WHERE service_id = ? "
                         "ORDER BY start", (service_id,))]
        media = svc["media_path"] or ""
        out = {
            "service_id": svc["ID"], "date": svc["preach_date"],
            "title": svc["title"] or "",
            "sermon_giver": svc["sermon_giver"] or "",
            "notes": svc["notes"] or "", "speakers": speakers,
            "parts": parts, "video_path": media,
            "video_file_exists": bool(media) and os.path.exists(media),
            "video_stream_url": f"{VIEWER_URL}/video/{service_id}",
        }
        if body.get("include_transcript"):
            out["transcript"] = [
                {"segment_id": r["id"],
                 "start": hms(time_to_seconds(r["start"])),
                 "start_seconds": round(time_to_seconds(r["start"]), 2),
                 "speaker": r["speaker"], "exact_text": r["text"] or ""}
                for r in service_lines(con, service_id)]
        return out
    finally:
        con.close()


def find_person(body):
    """A name, looked up two honest ways: as a tracked speaker, and as
    words spoken inside transcripts. The two are clearly separated."""
    name = (body.get("name") or "").strip()
    if not name:
        raise ConnectorError(400, "Send name.")
    con = connect_ro()
    try:
        check_schema(con)
        out = {"name": name, "as_tracked_speaker": None,
               "mentioned_in_transcripts": None}

        found = find_speaker(con, words_of(name))
        if found:
            sid, full_name, _ = found
            services = con.execute(
                """SELECT s.ID, s.preach_date, s.title, COUNT(*) AS segs
                   FROM RawSegments r JOIN Services s ON s.ID = r.service_id
                   WHERE r.speaker_id = ?
                   GROUP BY s.ID ORDER BY s.preach_date""", (sid,)).fetchall()
            out["as_tracked_speaker"] = {
                "speaker_id": sid, "full_name": full_name,
                "services": [{"service_id": r["ID"], "date": r["preach_date"],
                              "title": r["title"] or "",
                              "segments_spoken": r["segs"]} for r in services],
            }

        mentions = run_segment_query(
            con, "r.text LIKE ? ESCAPE '\\'",
            ["%" + like_escape(name) + "%"], MAX_LIMIT)
        out["mentioned_in_transcripts"] = {
            "count": len(mentions), "hits": mentions[:DEFAULT_LIMIT]}
        if not found and not mentions:
            out["message"] = (f"“{name}” is not a tracked speaker and those "
                              "words were not found in any transcript.")
        elif not found:
            out["message"] = (f"“{name}” is not a tracked speaker in this "
                              "archive, but the words are spoken in "
                              f"{len(mentions)} transcript moments — see "
                              "mentioned_in_transcripts.")
        return out
    finally:
        con.close()


# ------------------------------------------------------ answer_question

def answer_question(body):
    """Turn a natural question into an evidence package. The connector never
    forms an answer; it gathers exact transcript text for the AI model."""
    question = (body.get("question") or "").strip()
    if len(question) < 3:
        raise ConnectorError(400, "Send question.")
    con = connect_ro()
    try:
        check_schema(con)
        qwords = words_of(question)
        notes = []

        speaker = find_speaker(con, qwords)
        speaker_words = set(speaker[2]) if speaker else set()
        topic = [w for w in qwords
                 if w not in FILLER_WORDS and w not in speaker_words]

        # Phrases to try, strongest first: adjacent word pairs (often names
        # or set phrases), then every meaningful word on its own.
        pairs = [f"{a} {b}" for a, b in zip(topic, topic[1:])]
        singles = sorted(set(topic), key=len, reverse=True)
        phrases_tried, scored = [], {}

        def collect(phrase, weight, where_extra="", params_extra=()):
            phrases_tried.append(phrase)
            hits = run_segment_query(
                con, "r.text LIKE ? ESCAPE '\\'" + where_extra,
                ["%" + like_escape(phrase) + "%", *params_extra], MAX_LIMIT)
            for h in hits:
                key = h["segment_id"]
                if key not in scored:
                    scored[key] = {"segment": h, "score": 0.0,
                                   "matched_phrases": []}
                scored[key]["score"] += weight
                scored[key]["matched_phrases"].append(phrase)

        for p in pairs:
            collect(p, 10.0)
        for w in singles:
            collect(w, len(w) / 3.0)

        # A tracked speaker in the question narrows nothing by itself but
        # boosts their own segments to the top.
        if speaker:
            for v in scored.values():
                if v["segment"]["speaker"] == speaker[1]:
                    v["score"] += 8.0
            notes.append(f"“{speaker[1]}” is a tracked speaker in this "
                         "archive; their own segments were boosted.")

        # Names asked about but not tracked as speakers get an honest note.
        for p in pairs:
            if any(p in v["segment"]["exact_text"].lower()
                   for v in scored.values()):
                if not speaker or p not in " ".join(speaker[2]):
                    notes.append(f"“{p}” matched transcript words. It is NOT "
                                 "a tracked speaker name — treat these as "
                                 "moments where the words were spoken, not "
                                 "necessarily that person speaking. "
                                 "(inferred relationship)")

        # Strongest first, but no single service may flood the evidence —
        # at most 3 segments each, so different moments get their say.
        best, per_service = [], {}
        for v in sorted(scored.values(), key=lambda v: -v["score"]):
            sid = v["segment"]["service_id"]
            if per_service.get(sid, 0) >= 3:
                continue
            per_service[sid] = per_service.get(sid, 0) + 1
            best.append(v)
            if len(best) >= EVIDENCE_SEGMENTS:
                break
        evidence = []
        for rank, v in enumerate(best, 1):
            seg = v["segment"]
            evidence.append({
                "rank": rank, "score": round(v["score"], 2),
                "matched_phrases": v["matched_phrases"],
                "segment": seg,
                "context": context_lines(con, seg["service_id"],
                                         seg["start_seconds"],
                                         CONTEXT_LINES, CONTEXT_LINES),
            })

        return {
            "question": question,
            "interpretation": {
                "tracked_speaker_match": speaker[1] if speaker else None,
                "topic_words": topic,
                "phrases_tried": phrases_tried,
                "notes": notes,
            },
            "evidence": evidence,
            "evidence_count": len(evidence),
            "message": None if evidence else
                "No transcript match for any phrase tried.",
            "instructions_for_ai": (
                "Form your answer ONLY from exact_text in evidence segments "
                "and their context lines. Cite date, speaker, and start time "
                "for every claim. interpretation and notes tell you how the "
                "search was read — they are not transcript content. If the "
                "evidence is weak or absent, say so plainly; do not invent."),
        }
    finally:
        con.close()


# ----------------------------------------------------------- OpenAPI spec

def openapi_spec():
    def op(summary, props, required):
        return {"summary": summary, "requestBody": {"required": True,
                "content": {"application/json": {"schema": {
                    "type": "object", "properties": props,
                    "required": required}}}},
                "responses": {"200": {"description": "JSON result"}}}
    S = {"type": "string"}
    I = {"type": "integer"}
    B = {"type": "boolean"}
    N = {"type": "number"}
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Archive AI Connector",
            "version": "1.0.0",
            "description": ("Read-only evidence API over a sermon archive "
                            "(724 services, ~595k transcript segments). "
                            "Returns exact transcript text with timestamps; "
                            "the AI client forms the final answer."),
        },
        "servers": [{"url": f"http://{HOST}:{PORT}"}],
        "paths": {
            "/health": {"get": {"summary": "Connector and database status",
                        "responses": {"200": {"description": "status"}}}},
            "/search": {"post": op(
                "search_transcripts: find moments by words, with optional "
                "speaker, date range, and content-type filters",
                {"query": S, "speaker": S, "date_from": S, "date_to": S,
                 "type": {**S, "description":
                          "Song, Prayer, Testimony, Scripture, "
                          "Exhortation, or Sermon"},
                 "match_all_words": B, "limit": I}, [])},
            "/context": {"post": op(
                "get_context: transcript lines around a moment",
                {"segment_id": I, "service_id": I,
                 "t": {**N, "description": "seconds into the service"},
                 "before": I, "after": I}, [])},
            "/service": {"post": op(
                "get_service: one service's metadata, speakers, parts, "
                "and optionally its full transcript",
                {"service_id": I, "include_transcript": B}, ["service_id"])},
            "/person": {"post": op(
                "find_person: a name as tracked speaker AND as words "
                "spoken in transcripts, clearly separated",
                {"name": S}, ["name"])},
            "/answer-question": {"post": op(
                "answer_question: turn a natural question into an evidence "
                "package (exact transcript text, metadata, interpretation)",
                {"question": S}, ["question"])},
            "/suggest": {"post": op(
                "submit_suggestion: propose a correction or added "
                "knowledge (speaker, transcript, event_context, "
                "content_type, scripture, location, person, service_title, "
                "meaning, other). NEVER alters the archive — lands as a "
                "pending suggestion for trusted review.",
                {"suggestion_type": S, "proposed_value": S,
                 "current_value": S, "explanation": S, "evidence": S,
                 "service_id": I, "segment_id": I, "service_date": S,
                 "timestamp_start": N, "timestamp_end": N,
                 "source_title": S, "submitted_by": S,
                 "submitted_email": S, "question_id": I},
                ["suggestion_type", "proposed_value"])},
            "/suggestions": {"post": op(
                "list_suggestions: list suggestions by status (pending | "
                "approved | rejected | needs_more_information | all)",
                {"status": S, "limit": I}, [])},
            "/review": {"post": op(
                "review_suggestion: a trusted reviewer rules on a "
                "suggestion — approved, rejected, or "
                "needs_more_information; the ruling carries their name",
                {"suggestion_id": I, "status": S, "reviewed_by": S,
                 "reviewer_note": S}, ["suggestion_id", "status",
                                       "reviewed_by"])},
            "/log-question": {"post": op(
                "log_question: journal a question asked of the archive "
                "(question, asker, AI used, answer, confidence, receipts)",
                {"question_text": S, "asked_by": S, "ai_provider": S,
                 "answer_text": S, "confidence": S, "receipts": S},
                ["question_text"])},
        },
    }


# ---------------------------------------------------------- test page

TEST_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Archive AI Connector — test</title>
<style>
 body{font-family:-apple-system,sans-serif;max-width:1180px;margin:20px auto;
      padding:0 12px;line-height:1.45}
 textarea{font:inherit;padding:8px;box-sizing:border-box;
      border:1px solid #bbb;border-radius:8px}
 #q{width:100%;font-size:17px;min-height:70px}
 button{font:inherit;padding:8px 14px;cursor:pointer;border-radius:8px;
      border:1px solid #bbb;background:#f4f4f2}
 button.primary{font-weight:600;background:#2456c8;border-color:#2456c8;color:#fff}
 button.small{font-size:12px;padding:3px 8px}
 .btnrow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
 .cols{display:grid;grid-template-columns:1fr;gap:16px}
 @media(min-width:920px){.cols{grid-template-columns:3fr 2fr;align-items:start}}
 .hit{border:1px solid #ccc;border-radius:8px;padding:10px;margin:10px 0}
 .meta{color:#666;font-size:13px}
 .ctx{margin:6px 0 0 12px;font-size:14px}
 .ctx b{background:#fff3b0}
 .note{background:#eef;padding:8px;border-radius:6px;font-size:14px}
 a{color:#2456c8}
 #notes{width:100%;min-height:320px;font-size:14px}
 .notes-panel h3{margin:0 0 6px}
 .hint{color:#666;font-size:12px}
</style></head><body>
<h2>Archive AI Connector — test page</h2>
<p>This asks the connector for <em>evidence</em> (exact transcript text).
It does not form answers — that is the AI model's job.</p>
<textarea id="q" rows="3" autofocus
 placeholder="Type your question about the archive here… (Escape clears the box)"></textarea>
<div class="btnrow">
 <button class="primary" onclick="go()">Get evidence</button>
 <button onclick="resetQuestion()">New question</button>
 <button class="small" onclick="useExample()">Example: Robert Morgan</button>
 <span id="st"></span>
</div>
<div class="cols">
 <div id="out"></div>
 <div class="notes-panel">
  <h3>Notes</h3>
  <div class="btnrow">
   <button class="small" onclick="copySelectionToNotes()">Copy selection to Notes</button>
   <button class="small" onclick="copyAllToNotes()">Copy all results to Notes</button>
  </div>
  <textarea id="notes"
   placeholder="Evidence you keep lands here. Type freely — nothing here ever touches the archive."></textarea>
  <div class="btnrow">
   <button class="small" onclick="copyNotesToClipboard()">Copy Notes to clipboard</button>
   <button class="small" onclick="downloadNotes()">Download .txt</button>
   <button class="small" onclick="clearNotes()">Clear Notes</button>
   <span class="hint" id="nst"></span>
  </div>
 </div>
</div>
<script>
const EXAMPLE='Find Robert Morgan sharing about the need for theology to change over the years.';
const qEl=document.getElementById('q'),st=document.getElementById('st'),
      out=document.getElementById('out'),notes=document.getElementById('notes'),
      nst=document.getElementById('nst');
let lastData=null;

// Notes survive a page reload (kept in this browser only, never in the DB).
notes.value=localStorage.getItem('archive-notes')||'';
notes.addEventListener('input',()=>localStorage.setItem('archive-notes',notes.value));

qEl.addEventListener('keydown',e=>{if(e.key==='Escape')qEl.value='';});
function useExample(){qEl.value=EXAMPLE;qEl.focus();}
function resetQuestion(){                 // Notes stay untouched, on purpose
  qEl.value='';out.innerHTML='';st.textContent='';lastData=null;qEl.focus();
}

const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const viewerLink=e=>'http://localhost:8765/?q='
      +encodeURIComponent((e.matched_phrases&&e.matched_phrases[0])||'');

function resultText(e){
  const s=e.segment;
  let t='#'+e.rank+' · '+s.date+(s.title?' · '+s.title:'')
       +(s.speaker?' · '+s.speaker:'')+' · at '+s.start+'\n';
  t+='Said: '+s.exact_text+'\n';
  if(e.context&&e.context.length){
    t+='Around it:\n';
    for(const c of e.context)
      t+='  '+c.start+' — '+c.exact_text+(c.speaker?' ('+c.speaker+')':'')+'\n';
  }
  t+=s.video_file_exists?('Video: '+viewerLink(e)+'\n'):'(no video file on the drive)\n';
  return t;
}
function noteSaved(msg){nst.textContent=msg;setTimeout(()=>nst.textContent='',2500);}
function addToNotes(text){
  if(!text)return;
  notes.value=(notes.value?notes.value.replace(/\s+$/,'')+'\n\n':'')
              +text.replace(/\s+$/,'')+'\n';
  localStorage.setItem('archive-notes',notes.value);
}
function copyResultToNotes(i){
  if(!lastData)return;
  addToNotes(resultText(lastData.evidence[i]));
  noteSaved('Added result #'+(i+1)+' to Notes.');
}
function copyAllToNotes(){
  if(!lastData||!lastData.evidence||!lastData.evidence.length){
    noteSaved('No results yet.');return;
  }
  addToNotes('QUESTION: '+lastData.question+'\n\n'
             +lastData.evidence.map(resultText).join('\n'));
  noteSaved('Added all '+lastData.evidence.length+' results.');
}
function copySelectionToNotes(){
  const sel=String(window.getSelection());
  if(!sel.trim()){noteSaved('Select some text in the results first.');return;}
  addToNotes(sel);noteSaved('Added selection to Notes.');
}
async function copyNotesToClipboard(){
  try{await navigator.clipboard.writeText(notes.value);}
  catch(e){notes.select();document.execCommand('copy');}
  noteSaved('Notes copied to clipboard.');
}
function downloadNotes(){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([notes.value],{type:'text/plain'}));
  a.download='archive-notes.txt';a.click();URL.revokeObjectURL(a.href);
  noteSaved('Notes downloaded as archive-notes.txt.');
}
function clearNotes(){
  if(!notes.value)return;
  if(confirm('Clear all Notes? This cannot be undone.')){
    notes.value='';localStorage.removeItem('archive-notes');
    noteSaved('Notes cleared.');
  }
}

async function go(){
  const question=qEl.value.trim();
  if(question.length<3){st.textContent='Type a question first.';qEl.focus();return;}
  st.textContent='searching…';out.innerHTML='';lastData=null;
  let d;
  try{
    const r=await fetch('/answer-question',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question})});
    d=await r.json();
  }catch(e){ st.textContent='Connector not reachable.'; return; }
  if(d.error){st.textContent=d.error;return;}
  lastData=d;
  st.textContent=(d.evidence_count||0)+' evidence segments';
  let h='';
  if(d.interpretation&&d.interpretation.notes.length)
    h+='<div class="note">'+d.interpretation.notes.map(esc).join('<br>')+'</div>';
  (d.evidence||[]).forEach((e,i)=>{
    const s=e.segment;
    h+='<div class="hit"><div class="meta">#'+e.rank+' · '+esc(s.date)+
       (s.title?' · '+esc(s.title):'')+(s.speaker?' · '+esc(s.speaker):'')+
       ' · at '+s.start+' · matched: '+e.matched_phrases.map(esc).join(', ')+
       (s.video_file_exists?' · <a target="_blank" href="'+viewerLink(e)+
        '">open in viewer</a>':' · (no video file)')+
       ' · <button class="small" onclick="copyResultToNotes('+i+')">Copy to Notes</button>'+
       '</div>';
    for(const c of e.context)
      h+='<div class="ctx">'+(c.is_the_match?'<b>':'')+c.start+' — '+
         esc(c.exact_text)+(c.is_the_match?'</b>':'')+'</div>';
    h+='</div>';
  });
  out.innerHTML=h||'<p>No evidence found.</p>';
}
</script></body></html>"""


# ---------------------------------------------------------------- server

# ---------------------------------------------- the suggestion door
# Corrections and added knowledge NEVER touch Sermons.db. They land in
# a separate database as pending suggestions, walk a review workflow
# (pending -> approved / rejected / needs_more_information), and only
# APPROVED rulings ride into answers. Raw stays raw; the teacher's
# word outranks the machine only after review.

SUG_DB = "/Users/saba/Archive/Archive_Suggestions.db"

SUGGESTION_TYPES = ("speaker", "transcript", "event_context",
                    "content_type", "scripture", "location", "person",
                    "service_title", "meaning", "other")


def connect_sug():
    if not os.path.exists(SUG_DB):
        raise ConnectorError(503, f"Suggestions database not found: {SUG_DB}")
    con = sqlite3.connect(SUG_DB, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def submit_suggestion(body):
    stype = (body.get("suggestion_type") or "").strip()
    proposed = (body.get("proposed_value") or "").strip()
    if stype not in SUGGESTION_TYPES:
        raise ConnectorError(400, f"suggestion_type must be one of "
                                  f"{', '.join(SUGGESTION_TYPES)}")
    if not proposed:
        raise ConnectorError(400, "proposed_value is required.")
    con = connect_sug()
    try:
        cur = con.execute(
            "INSERT INTO suggestions (service_id, segment_id, service_date,"
            " timestamp_start, timestamp_end, source_title,"
            " suggestion_type, current_value, proposed_value, explanation,"
            " evidence, submitted_by, submitted_email, question_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (body.get("service_id"), body.get("segment_id"),
             body.get("service_date"), body.get("timestamp_start"),
             body.get("timestamp_end"), body.get("source_title"),
             stype, body.get("current_value"), proposed,
             body.get("explanation"), body.get("evidence"),
             body.get("submitted_by"), body.get("submitted_email"),
             body.get("question_id")))
        con.commit()
        return {"ok": True, "suggestion_id": cur.lastrowid,
                "status": "pending"}
    finally:
        con.close()


def list_suggestions(body):
    status = (body.get("status") or "pending").strip()
    limit = min(int(body.get("limit") or 50), 200)
    con = connect_sug()
    try:
        rows = con.execute(
            "SELECT id, service_id, segment_id, service_date, source_title,"
            " suggestion_type, current_value, proposed_value, explanation,"
            " evidence, submitted_by, submitted_at, status, reviewer_note,"
            " reviewed_by, reviewed_at FROM suggestions"
            " WHERE (?='all' OR status=?) ORDER BY submitted_at LIMIT ?",
            (status, status, limit)).fetchall()
        return {"count": len(rows), "suggestions": [dict(r) for r in rows]}
    finally:
        con.close()


def review_suggestion(body):
    sid = body.get("suggestion_id")
    new_status = (body.get("status") or "").strip()
    reviewer = (body.get("reviewed_by") or "").strip()
    if not sid or new_status not in ("approved", "rejected",
                                    "needs_more_information"):
        raise ConnectorError(400, "suggestion_id and status (approved | "
                             "rejected | needs_more_information) required.")
    if not reviewer:
        raise ConnectorError(400, "reviewed_by is required — rulings carry "
                             "the reviewer's name.")
    con = connect_sug()
    try:
        n = con.execute(
            "UPDATE suggestions SET status=?, reviewer_note=?,"
            " reviewed_by=?, reviewed_at=datetime('now') WHERE id=?",
            (new_status, body.get("reviewer_note"), reviewer, sid)).rowcount
        con.commit()
        if not n:
            raise ConnectorError(404, f"No suggestion with id {sid}.")
        return {"ok": True, "suggestion_id": sid, "status": new_status,
                "reviewed_by": reviewer}
    finally:
        con.close()


def log_question(body):
    q = (body.get("question_text") or "").strip()
    if not q:
        raise ConnectorError(400, "question_text is required.")
    con = connect_sug()
    try:
        cur = con.execute(
            "INSERT INTO questions (question_text, asked_by, ai_provider,"
            " answer_text, confidence, receipts) VALUES (?,?,?,?,?,?)",
            (q, body.get("asked_by"), body.get("ai_provider"),
             body.get("answer_text"), body.get("confidence"),
             body.get("receipts")))
        con.commit()
        return {"ok": True, "question_id": cur.lastrowid}
    finally:
        con.close()


ROUTES = {
    "/search": search_transcripts,
    "/context": get_context,
    "/service": get_service,
    "/person": find_person,
    "/answer-question": answer_question,
    "/suggest": submit_suggestion,
    "/suggestions": list_suggestions,
    "/review": review_suggestion,
    "/log-question": log_question,
}


def health():
    try:
        con = connect_ro()
    except ConnectorError as e:
        return {"ok": False, "error": e.message}
    try:
        check_schema(con)
        counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("Services", "RawSegments", "Speakers")}
        return {"ok": True, "read_only": True, "database": DB_PATH,
                "services": counts["Services"],
                "segments": counts["RawSegments"],
                "speakers": counts["Speakers"],
                "parts_table": has_parts_table(con)}
    except ConnectorError as e:
        return {"ok": False, "error": e.message}
    finally:
        con.close()


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # our own log() lines instead

    # CORS for local AI clients (Open WebUI) only — localhost origins.
    def cors_headers(self):
        origin = self.headers.get("Origin", "")
        if origin.startswith("http://localhost") \
                or origin.startswith("http://127.0.0.1"):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods",
                             "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers",
                             "Content-Type, Authorization")

    def reply(self, obj, status=200, ctype="application/json"):
        body = (obj if isinstance(obj, bytes)
                else json.dumps(obj, ensure_ascii=False).encode())
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.cors_headers()
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/health":
            self.reply(health())
        elif path == "/openapi.json":
            self.reply(openapi_spec())
        elif path in ("/", "/test"):
            self.reply(TEST_PAGE.encode(), ctype="text/html; charset=utf-8")
        else:
            self.reply({"error": "Unknown path. See /openapi.json"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        fn = ROUTES.get(path)
        if not fn:
            self.reply({"error": "Unknown path. See /openapi.json"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            self.reply({"error": "Body must be a JSON object."}, 400)
            return
        t0 = time.time()
        try:
            result = fn(body)
            log(f"POST {path} ok in {time.time()-t0:.2f}s — "
                + json.dumps({k: body[k] for k in list(body)[:3]},
                             ensure_ascii=False)[:120])
            self.reply(result)
        except ConnectorError as e:
            log(f"POST {path} -> {e.status}: {e.message}")
            self.reply({"error": e.message}, e.status)
        except sqlite3.Error as e:
            log(f"POST {path} -> database error: {e}")
            self.reply({"error": f"Database error: {e}"}, 500)


def main():
    status = health()
    if not status.get("ok"):
        raise SystemExit(f"Cannot start: {status.get('error')}")
    log(f"Archive AI Connector running — http://{HOST}:{PORT}")
    log(f"Read-only over {DB_PATH}")
    log(f"{status['services']} services · {status['segments']} segments · "
        f"{status['speakers']} speakers · Parts table: "
        f"{'yes' if status['parts_table'] else 'no'}")
    log("Test page: open the address above in a browser. Ctrl+C stops.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Stopped.")


if __name__ == "__main__":
    main()
