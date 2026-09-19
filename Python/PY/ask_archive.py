#!/usr/bin/env python3
"""Ask the Archive — one page where Saba asks a question and an AI answers
from his own data.

Run:  python3 ask_archive.py     (or double-click Start Ask the Archive.command)
Then the page lives at  http://127.0.0.1:8768

How an answer happens, in plain words:
  1. The question is heard two ways: by MEANING (its numbers, from the
     local Ollama model, matched against the Meanings index — finds the
     teaching even when the words differ) and by WORDS (exact matching,
     still best for names and phrases). Read-only, mode=ro — writing is
     impossible.
  2. The strongest moments, with surrounding lines, become the EVIDENCE.
  3. The Claude command already installed on this Mac is asked to answer
     the question using ONLY that evidence, citing date and time.
  4. The page shows the answer, with the evidence receipts underneath.
If Ollama is not running, word-search alone answers, and the page says so.

Separate, exterior tool: shares nothing with the Archive Viewer (8765),
the AI Connector (8766), or the Transcript Exporter (8767).
"""

import json
import os
import re
import shutil
import sqlite3
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Typo-forgiving search: correct a search word against the archive's own
# vocabulary (spell_correct.py). Optional — if unavailable, searches run
# exactly as before.
try:
    import spell_correct as _spell
except Exception:
    _spell = None

DB_PATH = "/Users/saba/Archive/Sermons.db"
HOST = "127.0.0.1"
PORT = 8768
HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = "Ask the Archive.html"

CLAUDE = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
EVIDENCE_SEGMENTS = 8
CONTEXT_LINES = 3
MAX_HITS = 200

OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "nomic-embed-text"   # must match what meanings_build.py used
MEANING_HITS = 12

# The ruling layer: approved suggestions (and ONLY approved) ride into
# answers — the teacher's word outranks the machine, after review.
SUG_DB = "/Users/saba/Archive/Archive_Suggestions.db"


def approved_rulings(service_ids):
    """Approved rulings touching these services -> (notes, speaker_map)."""
    if not service_ids or not os.path.exists(SUG_DB):
        return [], {}
    try:
        con = sqlite3.connect(SUG_DB, timeout=10)
        con.row_factory = sqlite3.Row
        marks = ",".join("?" * len(service_ids))
        rows = con.execute(
            f"SELECT * FROM suggestions WHERE status='approved' "
            f"AND service_id IN ({marks})", list(service_ids)).fetchall()
        con.close()
    except sqlite3.Error:
        return [], {}
    notes, speakers = [], {}
    for r in rows:
        if r["suggestion_type"] == "speaker" and r["segment_id"] is None:
            speakers[r["service_id"]] = r["proposed_value"]
        notes.append(
            f"- [{r['suggestion_type']}] service {r['service_id']}"
            + (f" seg {r['segment_id']}" if r["segment_id"] else "")
            + f": {r['proposed_value']}"
            + (f" — {r['explanation']}" if r["explanation"] else "")
            + f" (ruled by {r['reviewed_by']})")
    return notes, speakers


def log_question(question, answer, receipts):
    try:
        con = sqlite3.connect(SUG_DB, timeout=10)
        con.execute(
            "INSERT INTO questions (question_text, ai_provider,"
            " answer_text, receipts) VALUES (?,?,?,?)",
            (question, "claude (ask-the-archive 8768)", answer,
             json.dumps(receipts, ensure_ascii=False)[:8000]))
        con.commit()
        con.close()
    except sqlite3.Error:
        pass   # journaling must never break an answer


class AskError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def connect_ro():
    if not os.path.exists(DB_PATH):
        raise AskError(503, f"Database not found at {DB_PATH}.")
    con = sqlite3.connect(f"file:{urllib.parse.quote(DB_PATH)}?mode=ro",
                          uri=True)
    con.row_factory = sqlite3.Row
    return con


# ------------------------------------------------ finding the evidence

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


def hms(seconds):
    s = max(0, int(round(seconds)))
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def like_escape(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def words_of(s):
    return [w.strip("'") for w in re.split(r"[^\w']+", (s or "").lower())
            if w.strip("'")]


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
    "sharing", "share", "shared", "need", "needs", "needed", "tell",
    "often", "much", "many", "does", "do", "archive",
}


def find_speaker(con, query_words):
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


SEGMENT_SELECT = """
    SELECT MIN(r.ID) AS id, r.service_id, r.start, r.end, r.text,
           s.preach_date, s.title,
           COALESCE(sp.full_name, '') AS speaker
    FROM RawSegments r
    JOIN Services s ON s.ID = r.service_id
    LEFT JOIN Speakers sp ON sp.ID = r.speaker_id
"""


def phrase_hits(con, phrase):
    rows = con.execute(
        SEGMENT_SELECT + " WHERE r.text LIKE ? ESCAPE '\\' "
        " GROUP BY r.service_id, r.start, r.text "
        " ORDER BY s.preach_date, r.start LIMIT ?",
        ["%" + like_escape(phrase) + "%", MAX_HITS]).fetchall()
    return [
        {"segment_id": r["id"], "service_id": r["service_id"],
         "date": r["preach_date"], "title": r["title"] or "",
         "speaker": r["speaker"],
         "start_seconds": round(time_to_seconds(r["start"]), 2),
         "start": hms(time_to_seconds(r["start"])),
         "text": r["text"] or ""}
        for r in rows
    ]


def context_lines(con, service_id, t):
    rows = con.execute(
        """
        SELECT r.start, r.text, COALESCE(sp.full_name,'') AS speaker
        FROM RawSegments r
        LEFT JOIN Speakers sp ON sp.ID = r.speaker_id
        WHERE r.service_id = ?
        GROUP BY r.start, r.text ORDER BY r.start
        """, (service_id,)).fetchall()
    if not rows:
        return []
    starts = [time_to_seconds(r["start"]) for r in rows]
    idx = min(range(len(starts)), key=lambda i: abs(starts[i] - t))
    lo, hi = max(0, idx - CONTEXT_LINES), min(len(rows), idx + CONTEXT_LINES + 1)
    return [
        {"start": hms(time_to_seconds(r["start"])),
         "speaker": r["speaker"], "text": r["text"] or ""}
        for r in rows[lo:hi]
    ]


# ------------------------------------------------ hearing the meaning

_MEANINGS_CACHE = {"mat": None, "rows": None}


def load_meanings(con):
    """The passage index, loaded once per run and kept in memory."""
    if _MEANINGS_CACHE["mat"] is not None:
        return _MEANINGS_CACHE["mat"], _MEANINGS_CACHE["rows"]
    try:
        import numpy as np
    except ImportError:
        return None, None
    rows = con.execute(
        "SELECT seg_first, seg_last, service_id, start, end, text "
        "FROM Meanings WHERE kind='passage' ORDER BY ID").fetchall()
    if not rows:
        return None, None
    blobs = con.execute(
        "SELECT embedding FROM Meanings WHERE kind='passage' ORDER BY ID"
    ).fetchall()
    mat = np.frombuffer(b"".join(b[0] for b in blobs),
                        dtype=np.float32).reshape(len(rows), -1)
    mat = mat / np.linalg.norm(mat, axis=1, keepdims=True)
    _MEANINGS_CACHE["mat"], _MEANINGS_CACHE["rows"] = mat, rows
    return mat, rows


def embed_question(question):
    """The question's numbers, from local Ollama. None if Ollama is away."""
    try:
        import urllib.request
        import numpy as np
        req = urllib.request.Request(
            OLLAMA_URL,
            json.dumps({"model": EMBED_MODEL,
                        "input": [question]}).encode(),
            {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            vec = np.array(json.load(r)["embeddings"][0], dtype=np.float32)
        return vec / (np.linalg.norm(vec) or 1.0)
    except Exception:
        return None


def passage_lines(con, service_id, seg_first, seg_last):
    rows = con.execute(
        """
        SELECT r.start, r.text, COALESCE(sp.full_name,'') AS speaker
        FROM RawSegments r
        LEFT JOIN Speakers sp ON sp.ID = r.speaker_id
        WHERE r.service_id = ? AND r.ID BETWEEN ? AND ?
        GROUP BY r.start, r.text ORDER BY r.start
        """, (service_id, seg_first, seg_last)).fetchall()
    return [
        {"start": hms(time_to_seconds(r["start"])),
         "speaker": r["speaker"], "text": r["text"] or ""}
        for r in rows[:12]
    ]


def ruled_speaker_services(query_words):
    """Services whose APPROVED speaker ruling names someone the question
    asks about -> {service_id: ruled name}. Ruled names are findable."""
    if not os.path.exists(SUG_DB):
        return {}
    qset = set(query_words)
    out = {}
    try:
        con = sqlite3.connect(SUG_DB, timeout=10)
        rows = con.execute(
            "SELECT service_id, proposed_value FROM suggestions "
            "WHERE status='approved' AND suggestion_type='speaker' "
            "AND service_id IS NOT NULL").fetchall()
        con.close()
    except sqlite3.Error:
        return {}
    for sid, name in rows:
        words = [w for w in words_of(name) if len(w) > 2]
        if words and all(w in qset for w in words):
            out[sid] = name
    return out


def meaning_hits(con, question, boost_services=None):
    """The passages whose meaning sits closest to the question's."""
    q = embed_question(question)
    if q is None:
        return None                       # Ollama not reachable
    mat, rows = load_meanings(con)
    if mat is None:
        return None                       # index absent — not built yet
    sims = mat @ q
    order = list(sims.argsort()[::-1][:MEANING_HITS])
    if boost_services:
        # a ruled name was asked about: that person's own services join
        # the evidence hunt — their closest passages, question-ranked
        for sid in boost_services:
            idxs = [i for i, r in enumerate(rows) if r["service_id"] == sid]
            idxs.sort(key=lambda i: -sims[i])
            for i in idxs[:3]:
                if i not in order:
                    order.append(i)
    hits = []
    for i in order:
        r = rows[int(i)]
        svc = con.execute(
            "SELECT s.preach_date, s.title, "
            "COALESCE(sp.full_name,'') AS speaker "
            "FROM RawSegments rs "
            "JOIN Services s ON s.ID = rs.service_id "
            "LEFT JOIN Speakers sp ON sp.ID = rs.speaker_id "
            "WHERE rs.ID = ?", (r["seg_first"],)).fetchone()
        if not svc:
            continue
        hits.append(
            {"segment_id": r["seg_first"], "seg_last": r["seg_last"],
             "service_id": r["service_id"],
             "date": svc["preach_date"], "title": svc["title"] or "",
             "speaker": svc["speaker"],
             "start_seconds": round(time_to_seconds(r["start"]), 2),
             "start": hms(time_to_seconds(r["start"])),
             "text": r["text"] or "", "sim": float(sims[int(i)])})
    return hits


def gather_evidence(question):
    """The strongest matching moments for the question, with context."""
    con = connect_ro()
    try:
        qwords = words_of(question)
        speaker = find_speaker(con, qwords)
        speaker_words = set(speaker[2]) if speaker else set()
        topic = [w for w in qwords
                 if w not in FILLER_WORDS and w not in speaker_words]
        # typo tolerance: nudge each search word toward the archive's own
        # vocabulary (isreal -> israel) before the LIKE search. correct_word
        # returns the word unchanged if it's already known or has no clear match.
        if _spell is not None:
            try:
                topic = [_spell.correct_word(w) for w in topic]
            except Exception:
                pass
        pairs = [f"{a} {b}" for a, b in zip(topic, topic[1:])]
        singles = sorted(set(topic), key=len, reverse=True)

        scored = {}
        def collect(phrase, weight):
            for h in phrase_hits(con, phrase):
                v = scored.setdefault(h["segment_id"],
                                      {"segment": h, "score": 0.0,
                                       "matched": []})
                v["score"] += weight
                v["matched"].append(phrase)

        for p in pairs:
            collect(p, 10.0)
        for w in singles:
            collect(w, len(w) / 3.0)

        ruled = ruled_speaker_services(qwords)
        heard_meaning = meaning_hits(con, question, set(ruled) or None)
        for h in (heard_meaning or []):
            v = scored.setdefault(h["segment_id"],
                                  {"segment": h, "score": 0.0,
                                   "matched": []})
            v["score"] += 22.0 * h["sim"]
            v["matched"].append("meaning")
            if h["service_id"] in ruled:
                v["score"] += 15.0          # the asked-about person's own service
                v["matched"].append("ruled speaker")
                if not h.get("speaker"):
                    h["speaker"] = ruled[h["service_id"]] + " (ruled)"

        if speaker:
            for v in scored.values():
                if v["segment"]["speaker"] == speaker[1]:
                    v["score"] += 8.0

        best, per_service = [], {}
        for v in sorted(scored.values(), key=lambda v: -v["score"]):
            sid = v["segment"]["service_id"]
            if per_service.get(sid, 0) >= 3:
                continue
            per_service[sid] = per_service.get(sid, 0) + 1
            seg = v["segment"]
            if "seg_last" in seg:      # a meaning passage — its own lines
                v["context"] = passage_lines(con, sid, seg["segment_id"],
                                             seg["seg_last"])
            else:
                v["context"] = context_lines(con, sid, seg["start_seconds"])
            best.append(v)
            if len(best) >= EVIDENCE_SEGMENTS:
                break

        note = None
        if heard_meaning is None:
            note = ("Meaning-search was unavailable this time (Ollama not "
                    "running, or the Meanings index not built) — this "
                    "answer used word-matching only.")
        if speaker:
            note = f"“{speaker[1]}” is a tracked speaker in this archive."
        elif pairs and best:
            for p in pairs:
                if any(p in v["segment"]["text"].lower() for v in best):
                    note = (f"“{p}” matches words spoken in transcripts but "
                            "is NOT a tracked speaker — these are moments "
                            "where the words were said.")
                    break
        return best, note
    finally:
        con.close()


# ------------------------------------------------ asking the AI voice

PROMPT = """You are answering a question about a church sermon archive
of thirty years of recorded services. Answer ONLY from the evidence
below — exact
transcript quotes with their dates, speakers, and timestamps.

Rules:
- Plain, warm, direct language. No headers, no bullet lists unless natural.
- Cite the date and time for every claim, like (2016-12-03 at 0:00).
- If the evidence is thin or doesn't really answer the question, say so
  honestly — never fill gaps with guesses.
- Quote the transcript's own words where they carry the answer.

QUESTION: {question}

{note}

{rulings}

EVIDENCE:
{evidence}
"""


def format_evidence(best):
    parts = []
    for i, v in enumerate(best, 1):
        s = v["segment"]
        parts.append(f"--- Moment {i} · {s['date']}"
                     + (f" · {s['title']}" if s['title'] else "")
                     + (f" · {s['speaker']}" if s['speaker'] else "")
                     + f" · at {s['start']}")
        for c in v["context"]:
            mark = ">>" if c["text"] == s["text"] else "  "
            who = f" ({c['speaker']})" if c["speaker"] else ""
            parts.append(f"{mark} [{c['start']}]{who} {c['text']}")
    return "\n".join(parts)


def ask_ai(question, best, note, rulings=None):
    rtext = ""
    if rulings:
        rtext = ("HOUSE RULINGS (approved by trusted reviewers — these "
                 "OUTRANK anything contrary in the transcripts):\n"
                 + "\n".join(rulings))
    prompt = PROMPT.format(question=question,
                           note=("NOTE: " + note) if note else "",
                           rulings=rtext,
                           evidence=format_evidence(best))
    # The API key lives in ~/.zshrc, which is only sourced by an interactive
    # shell. When this server is started by the Book of Remembrance .app
    # (macOS `do shell script` = non-interactive), the key is absent and every
    # question fails with "not signed in". So supply it ourselves.
    env = os.environ.copy()
    if not env.get("ANTHROPIC_API_KEY"):
        keyfile = os.path.expanduser("~/.anthropic_key")
        try:
            if os.path.exists(keyfile):
                k = open(keyfile).read().strip()
                if k:
                    env["ANTHROPIC_API_KEY"] = k
        except OSError:
            pass
    try:
        run = subprocess.run(
            [CLAUDE, "-p", "--output-format", "text", prompt],
            capture_output=True, text=True, timeout=240, env=env)
    except FileNotFoundError:
        raise AskError(500, "The Claude command was not found on this Mac.")
    except subprocess.TimeoutExpired:
        raise AskError(504, "Claude took too long to answer — try again.")
    if run.returncode != 0:
        said = (run.stderr or run.stdout or "unknown error").strip()
        if "Not logged in" in said or "/login" in said:
            raise AskError(401, "Claude on this Mac isn't signed in yet — "
                           "a one-time step only you can do. Open the "
                           "Terminal app, type  claude  and press return, "
                           "follow the sign-in it offers (a browser window "
                           "opens — approve it), then come back and ask "
                           "again. You never need to do it twice.")
        raise AskError(502, "Claude could not answer: " + said[:300])
    return run.stdout.strip()


# ------------------------------------------------------------- server

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        # the page may live on xwalls.net; the browser asks permission
        # before POSTing across sites — this is the yes
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
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
        self.send_error(404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/ask":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            question = (body.get("question") or "").strip()
            if len(question) < 3:
                raise AskError(400, "Type a question first.")
            best, note = gather_evidence(question)
            if not best:
                self.send_json({"answer": "I searched every transcript and "
                                "found no moment matching those words. Try "
                                "different words, or fewer of them.",
                                "receipts": [], "note": None})
                return
            svc_ids = {v["segment"]["service_id"] for v in best}
            rulings, ruled_speakers = approved_rulings(svc_ids)
            for v in best:
                seg = v["segment"]
                if not seg["speaker"] and seg["service_id"] in ruled_speakers:
                    seg["speaker"] = (ruled_speakers[seg["service_id"]]
                                      + " (ruled)")
            answer = ask_ai(question, best, note, rulings)
            receipts = [
                {"date": v["segment"]["date"],
                 "title": v["segment"]["title"],
                 "speaker": v["segment"]["speaker"],
                 "start": v["segment"]["start"],
                 "text": v["segment"]["text"]}
                for v in best
            ]
            log_question(question, answer, receipts)
            self.send_json({"answer": answer, "receipts": receipts,
                            "note": note})
        except AskError as e:
            self.send_json({"error": e.message}, e.status)
        except sqlite3.Error as e:
            self.send_json({"error": f"Database error: {e}"}, 500)


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Database not found: {DB_PATH} — is the Data "
                         "drive mounted?")
    print(f"Ask the Archive — open http://{HOST}:{PORT}")
    print("Read-only over", DB_PATH)
    print("Press Ctrl+C to stop.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
