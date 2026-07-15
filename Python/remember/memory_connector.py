#!/usr/bin/env python3
"""Memory AI Connector — read-only API over mymemory.db.

The memory file is untouchable: the database is opened in SQLite
READ-ONLY mode (mode=ro) on every request, so this connector can
NEVER modify, delete, or corrupt your minutes. It serves them.

Run:   python3 memory_connector.py
Then from any device on your home Wi-Fi (iPhone, iPad, another Mac):

    http://10.0.0.30:8767        <- the "Ask My Memory" page in Safari

The page gathers the minutes that bear on your question and forms a
paste-ready text block for other AIs (ChatGPT, Claude, ...) — or, with
the "Ask here" button, has your local Ollama model form the answer
privately on the Mac, so nothing ever leaves the house.

Endpoints (for AI tool systems — Open WebUI, Claude, anything HTTP):
  GET  /health           is everything reachable (database, Ollama)
  GET  /openapi.json     machine-readable description of this API
  GET  /                 the phone-friendly Ask My Memory page
  POST /search           find minutes by words        {"words": "...", "limit": 25}
  POST /recent           the latest minutes           {"limit": 10}
  POST /on-day           minutes captured on a date   {"date": "2026-07-15"}
  POST /answer-question  paste-ready evidence block   {"question": "..."}
  POST /ask-local        Ollama forms the answer      {"question": "..."}

Install as always-on (starts when the Mac starts):
    python3 memory_connector.py --install
Remove the always-on agent:
    python3 memory_connector.py --uninstall

Serves on the home network only. Your router does not forward this
port to the internet, so nothing outside the house can reach it.
"""

import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DB_PATH = os.path.expanduser("~/Documents/mymemory.db")
HOST = "0.0.0.0"                # every device on the home network
PORT = 8767                     # next door to the archive connector (8766)

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3:4b"

DEFAULT_LIMIT = 25
MAX_LIMIT = 200
EVIDENCE_MINUTES = 12           # strongest matches carried into the block

LAUNCH_AGENT_LABEL = "com.sabacode.memoryconnector"


class ConnectorError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------------------------------------------------------------- database

def connect_ro():
    """Open the memory file read-only. Writing is impossible by design."""
    if not os.path.exists(DB_PATH):
        raise ConnectorError(503, f"Memory file not found at {DB_PATH}.")
    con = sqlite3.connect(f"file:{urllib.parse.quote(DB_PATH)}?mode=ro",
                          uri=True)
    con.row_factory = sqlite3.Row
    return con


def fetch_minutes():
    """All minutes, newest first. The memory file is small; this is cheap."""
    con = connect_ro()
    try:
        rows = con.execute(
            "SELECT id, timestamp, content, "
            "       COALESCE(source,'') AS source, "
            "       COALESCE(audio_path,'') AS audio_path "
            "FROM memories "
            "WHERE content IS NOT NULL AND TRIM(content) <> '' "
            "ORDER BY timestamp DESC, id DESC").fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


def clamp_limit(value, fallback=DEFAULT_LIMIT):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(1, min(n, MAX_LIMIT))


# ---------------------------------------------------------------- searching

def words_of(text):
    return [w for w in re.findall(r"[a-z0-9']+", (text or "").lower())
            if len(w) > 1]


def score_minute(minute, query_words):
    """How strongly one minute bears on the question: word hits."""
    content = minute["content"].lower()
    hits = 0
    for w in query_words:
        hits += content.count(w)
    return hits


def search_minutes(query, limit=DEFAULT_LIMIT):
    query_words = words_of(query)
    if not query_words:
        return []
    scored = []
    for m in fetch_minutes():
        s = score_minute(m, query_words)
        if s > 0:
            scored.append((s, m))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["timestamp"]),
                reverse=False)
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [dict(m, score=s) for s, m in scored[:limit]]


def minutes_on_day(date_text, limit=MAX_LIMIT):
    day = (date_text or "").strip()[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ConnectorError(400, "Give the date as YYYY-MM-DD, "
                                  "e.g. 2026-07-15.")
    return [m for m in fetch_minutes()
            if str(m["timestamp"]).startswith(day)][:limit]


# ---------------------------------------------------------------- the block

def format_minute(m):
    """One minute as a line that keeps its whole trail: the clock time,
    how it was captured, and the recording it came from — so any answer
    can always be traced back to the sound of Saba saying it."""
    ts = str(m["timestamp"])[:16]
    src = m.get("source") or ""
    rec = m.get("audio_path") or ""
    if src and rec:
        tag = f" ({src} — recording: {rec})"
    elif src:
        tag = f" ({src})"
    else:
        tag = ""
    return f"[{ts}]{tag} {m['content'].strip()}"


def build_block(question):
    """The paste-ready text block: Saba's relevant minutes, formed for an AI."""
    matches = search_minutes(question, EVIDENCE_MINUTES)
    lines = []
    lines.append("MEMORY BRIEFING — from Saba's personal memory file")
    lines.append(f"Prepared: {datetime.now():%Y-%m-%d %H:%M}")
    lines.append(f"Question: {question.strip()}")
    lines.append("")
    if matches:
        lines.append("These are Saba's own captured notes (his minutes), "
                     "strongest match first:")
        for m in matches:
            lines.append("  - " + format_minute(m))
    else:
        recents = fetch_minutes()[:5]
        lines.append("No minutes matched the question directly. "
                     "For context, his most recent minutes are:")
        for m in recents:
            lines.append("  - " + format_minute(m))
    lines.append("")
    lines.append("Please answer the question using only these notes as the "
                 "source of what Saba said and did. If the notes do not "
                 "contain the answer, say so plainly.")
    return "\n".join(lines), matches


# ---------------------------------------------------------------- ollama

def ollama_available():
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def ask_ollama(question):
    """Have the local model form the answer from the evidence block.
    Private by construction: the model runs on this Mac."""
    block, matches = build_block(question)
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "stream": False,
        "think": False,
        "messages": [{"role": "user", "content": block}],
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL + "/api/chat", data=payload,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise ConnectorError(503, f"Ollama isn't answering ({e}). Is the "
                                  "Ollama app running on the Mac?")
    answer = (data.get("message") or {}).get("content", "")
    # Some models narrate their thinking in <think> tags (sometimes without
    # the opening tag); keep only what comes after the thinking.
    answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S)
    if "</think>" in answer:
        answer = answer.rsplit("</think>", 1)[-1]
    return answer.strip(), block, matches


# ---------------------------------------------------------------- openapi

def openapi_spec():
    def op(op_id, summary, props, required):
        return {
            "operationId": op_id,
            "summary": summary,
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                }}},
            },
            "responses": {"200": {"description": "JSON result"}},
        }

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Saba Memory Connector",
            "version": "1.0",
            "description": "Read-only access to Saba's personal memory "
                           "file (mymemory.db). Returns his captured "
                           "minutes as evidence; never writes.",
        },
        "servers": [{"url": f"http://10.0.0.30:{PORT}"}],
        "paths": {
            "/search": {"post": op(
                "search_minutes",
                "Find Saba's minutes containing the given words.",
                {"words": {"type": "string"},
                 "limit": {"type": "integer", "default": DEFAULT_LIMIT}},
                ["words"])},
            "/recent": {"post": op(
                "recent_minutes",
                "Saba's most recent minutes, newest first.",
                {"limit": {"type": "integer", "default": 10}}, [])},
            "/on-day": {"post": op(
                "minutes_on_day",
                "Every minute Saba captured on a date (YYYY-MM-DD).",
                {"date": {"type": "string"}}, ["date"])},
            "/answer-question": {"post": op(
                "answer_question",
                "An evidence package for a natural-language question: "
                "the relevant minutes formed into a paste-ready block.",
                {"question": {"type": "string"}}, ["question"])},
        },
    }


# ---------------------------------------------------------------- the page

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>Ask My Memory</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Helvetica Neue", sans-serif;
         background: #f4f0fa; color: #1d1a26; }
  @media (prefers-color-scheme: dark) {
    body { background: #1d1a26; color: #efeaf7; }
    textarea, .card { background: #2a2438 !important; color: #efeaf7 !important; }
  }
  .wrap { max-width: 560px; margin: 0 auto; padding: 18px 16px 40px; }
  h1 { font-size: 1.35rem; margin: 8px 0 2px; }
  h1 .dot { color: #d0342c; }
  .sub { margin: 0 0 14px; font-size: .85rem; opacity: .65; }
  textarea { width: 100%; min-height: 88px; font-size: 1.05rem; padding: 12px;
             border: 1.5px solid #b9a5e3; border-radius: 12px; background: #fff;
             -webkit-appearance: none; }
  .row { display: flex; gap: 10px; margin-top: 12px; }
  button { flex: 1; padding: 13px 8px; font-size: 1rem; font-weight: 600;
           border: 0; border-radius: 12px; cursor: pointer; }
  #formBtn { background: #7a5cc4; color: #fff; }
  #localBtn { background: #e4dbf5; color: #43317a; }
  @media (prefers-color-scheme: dark) { #localBtn { background:#3a3153; color:#d9ccf5; } }
  .card { margin-top: 16px; background: #fff; border-radius: 12px; padding: 14px;
          white-space: pre-wrap; font-size: .95rem; line-height: 1.45;
          box-shadow: 0 1px 4px rgba(60,40,110,.12); display: none; }
  #copyBtn { display: none; margin-top: 10px; width: 100%; background: #43317a;
             color: #fff; }
  .status { margin-top: 12px; font-size: .9rem; opacity: .75; min-height: 1.2em; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Ask My Memory <span class="dot">&#9679;</span></h1>
  <p class="sub">Your minutes are read-only &mdash; asking can never change them.</p>
  <textarea id="q" placeholder="What do you want to remember?"></textarea>
  <div class="row">
    <button id="formBtn">Form text to paste</button>
    <button id="localBtn">Ask here (private)</button>
  </div>
  <div class="status" id="status"></div>
  <div class="card" id="out"></div>
  <button id="copyBtn">Copy &mdash; ready for ChatGPT / Claude</button>
</div>
<script>
var q = document.getElementById('q'), out = document.getElementById('out'),
    st = document.getElementById('status'), copyBtn = document.getElementById('copyBtn');

function show(text, copyable) {
  out.textContent = text; out.style.display = 'block';
  copyBtn.style.display = copyable ? 'block' : 'none';
}
function post(path, body, onOk) {
  st.textContent = 'Working...';
  fetch(path, { method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body) })
    .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
    .then(function (res) {
      if (!res.ok) { st.textContent = res.j.error || 'Something went wrong.'; return; }
      st.textContent = ''; onOk(res.j);
    })
    .catch(function () { st.textContent = 'Could not reach the Mac. Same Wi-Fi?'; });
}
document.getElementById('formBtn').onclick = function () {
  if (!q.value.trim()) { st.textContent = 'Type a question first.'; return; }
  post('/answer-question', { question: q.value }, function (j) {
    show(j.block, true);
    st.textContent = j.matches + ' minute(s) matched.';
  });
};
document.getElementById('localBtn').onclick = function () {
  if (!q.value.trim()) { st.textContent = 'Type a question first.'; return; }
  st.textContent = 'Asking the Mac privately (can take a minute)...';
  post('/ask-local', { question: q.value }, function (j) {
    show(j.answer, false);
  });
};
copyBtn.onclick = function () {
  var done = function () { st.textContent = 'Copied. Paste it into any AI.'; };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(out.textContent).then(done);
  } else {
    var ta = document.createElement('textarea');
    ta.value = out.textContent; document.body.appendChild(ta);
    ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
    done();
  }
};
</script>
</body>
</html>"""


# ---------------------------------------------------------------- server

class Handler(BaseHTTPRequestHandler):

    server_version = "MemoryConnector/1.0"

    def log_message(self, fmt, *args):
        print(f"{datetime.now():%H:%M:%S}  {self.client_address[0]}  "
              f"{fmt % args}")

    # -- plumbing ---------------------------------------------------------

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_page(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError:
            raise ConnectorError(400, "The request body must be JSON.")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # -- GET --------------------------------------------------------------

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == "/":
                self.send_page(PAGE)
            elif path == "/health":
                db_ok, count = False, 0
                try:
                    count = len(fetch_minutes())
                    db_ok = True
                except ConnectorError:
                    pass
                self.send_json({
                    "database": "ok" if db_ok else "unreachable",
                    "memory_file": DB_PATH,
                    "minutes": count,
                    "ollama": "ok" if ollama_available() else "not running",
                    "read_only": True,
                })
            elif path == "/openapi.json":
                self.send_json(openapi_spec())
            else:
                self.send_json({"error": "Unknown path."}, 404)
        except ConnectorError as e:
            self.send_json({"error": e.message}, e.status)

    # -- POST -------------------------------------------------------------

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            body = self.read_body()
            if path == "/search":
                words = (body.get("words") or "").strip()
                if not words:
                    raise ConnectorError(400, "Give some words to search for.")
                found = search_minutes(words, clamp_limit(body.get("limit")))
                self.send_json({"minutes": found, "count": len(found)})
            elif path == "/recent":
                limit = clamp_limit(body.get("limit"), 10)
                found = fetch_minutes()[:limit]
                self.send_json({"minutes": found, "count": len(found)})
            elif path == "/on-day":
                found = minutes_on_day(body.get("date"))
                self.send_json({"minutes": found, "count": len(found)})
            elif path == "/answer-question":
                question = (body.get("question") or "").strip()
                if not question:
                    raise ConnectorError(400, "Ask a question.")
                block, matches = build_block(question)
                self.send_json({"block": block, "matches": len(matches)})
            elif path == "/ask-local":
                question = (body.get("question") or "").strip()
                if not question:
                    raise ConnectorError(400, "Ask a question.")
                answer, block, matches = ask_ollama(question)
                self.send_json({"answer": answer, "matches": len(matches),
                                "model": OLLAMA_MODEL})
            else:
                self.send_json({"error": "Unknown path."}, 404)
        except ConnectorError as e:
            self.send_json({"error": e.message}, e.status)


# ---------------------------------------------------------------- always-on

def launch_agent_path():
    return os.path.expanduser(
        f"~/Library/LaunchAgents/{LAUNCH_AGENT_LABEL}.plist")


def install_agent():
    """Start the connector at login and keep it running."""
    script = os.path.abspath(__file__)
    log = os.path.expanduser("~/Library/Logs/memory_connector.log")
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>{LAUNCH_AGENT_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>{script}</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>{log}</string>
  <key>StandardErrorPath</key><string>{log}</string>
</dict>
</plist>
"""
    path = launch_agent_path()
    with open(path, "w") as f:
        f.write(plist)
    subprocess.run(["launchctl", "unload", path], capture_output=True)
    subprocess.run(["launchctl", "load", path], check=True)
    print(f"Installed and started. The connector now runs whenever the Mac "
          f"is on.\n  Agent: {path}\n  Log:   {log}")


def uninstall_agent():
    path = launch_agent_path()
    subprocess.run(["launchctl", "unload", path], capture_output=True)
    if os.path.exists(path):
        os.remove(path)
    print("Always-on agent removed. You can still run the connector by "
          "hand any time.")


# ---------------------------------------------------------------- main

def main():
    if "--install" in sys.argv:
        install_agent()
        return
    if "--uninstall" in sys.argv:
        uninstall_agent()
        return

    print("Memory AI Connector — read-only over", DB_PATH)
    print(f"On this Mac:        http://127.0.0.1:{PORT}")
    print(f"On the home Wi-Fi:  http://10.0.0.30:{PORT}   (iPhone / iPad)")
    print("The memory file is opened read-only on every request; "
          "writing is impossible.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
