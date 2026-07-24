#!/usr/bin/env python3
"""MCP stdio bridge for the Archive AI Connector.

Raycast (and other MCP clients) speak the Model Context Protocol, not
plain REST/OpenAPI — so they can't call connector.py (port 8766) directly
the way Open WebUI's tool-server integration does. This wraps the same
five read-only evidence endpoints as MCP tools, translating each tool
call into an HTTP request against the already-running connector.

Read-only: every tool here is a GET-shaped lookup against a connector
that opens the database "mode=ro". This file adds no new access and no
writes — it only changes which protocol the archive can be asked in.
"""
import json
import urllib.error
import urllib.request

from mcp.server.fastmcp import FastMCP

CONNECTOR = "http://127.0.0.1:8766"

mcp = FastMCP("archive")


def _post(path, payload):
    req = urllib.request.Request(
        CONNECTOR + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        return {"error": f"Could not reach the archive connector at {CONNECTOR}: {e}"}


@mcp.tool()
def search_transcripts(query: str = "", speaker: str = "", date_from: str = "",
                        date_to: str = "", type: str = "",
                        match_all_words: bool = False, limit: int = 20) -> dict:
    """Find moments in the sermon archive by words, with optional speaker,
    date range, and content-type (Song, Prayer, Testimony, Scripture,
    Exhortation, Sermon) filters. Returns exact transcript text with
    dates, speakers, and timestamps — evidence, not an answer."""
    body = {k: v for k, v in {
        "query": query, "speaker": speaker, "date_from": date_from,
        "date_to": date_to, "type": type, "match_all_words": match_all_words,
        "limit": limit,
    }.items() if v not in ("", False, None)}
    return _post("/search", body)


@mcp.tool()
def get_context(service_id: int, t: float, before: int = 5, after: int = 5) -> dict:
    """Transcript lines around one moment (service_id + seconds into the
    service), for reading what was said just before and after a hit."""
    return _post("/context", {"service_id": service_id, "t": t,
                               "before": before, "after": after})


@mcp.tool()
def get_service(service_id: int, include_transcript: bool = False) -> dict:
    """One service's metadata (date, title, speakers, parts) and,
    optionally, its full transcript."""
    return _post("/service", {"service_id": service_id,
                               "include_transcript": include_transcript})


@mcp.tool()
def find_person(name: str) -> dict:
    """A name, looked up two ways: as a tracked speaker (their sermons and
    songs) AND as words spoken about them in transcripts — clearly
    separated so the two are never confused."""
    return _post("/person", {"name": name})


@mcp.tool()
def answer_question(question: str) -> dict:
    """Turn a natural-language question into an evidence package: exact
    transcript text, metadata, and the connector's own reading of the
    question. Never invents an answer — forms it from the evidence only."""
    return _post("/answer-question", {"question": question})


if __name__ == "__main__":
    mcp.run()
