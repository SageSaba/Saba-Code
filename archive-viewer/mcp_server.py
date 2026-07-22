#!/usr/bin/env python3
"""Archive MCP Bridge — speaks the Model Context Protocol in front of the
Archive AI Connector (connector.py, port 8766).

Why this exists: Claude's custom connectors (claude.ai Settings -> Customize
-> Add custom connector) need a "Remote MCP server URL" -- an endpoint that
speaks MCP itself, not a plain REST/OpenAPI API. connector.py is deliberately
stdlib-only REST (so Open WebUI and curl can use it directly); this bridge
is the thin adapter that lets Claude's connector system do the same.

This bridge touches the database NOT AT ALL -- it only forwards HTTP calls
to the already-read-only connector. Exposes only the evidence-returning
tools (search, context, service, person, answer-question); the suggestion/
review/log-question endpoints are deliberately left out of this surface so
anything reachable through Claude stays strictly read-only, per house law.

Run:  python3 mcp_server.py
Then point Claude's custom connector at this process's URL (once it is
reachable from wherever Claude is calling from -- locally that's
http://127.0.0.1:8769/mcp, over Streamable HTTP).
"""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

CONNECTOR_URL = os.environ.get("ARCHIVE_CONNECTOR_URL", "http://127.0.0.1:8766")
HOST = os.environ.get("MCP_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_BRIDGE_PORT", "8769"))

mcp = FastMCP(
    "Archive Well",
    host=HOST,
    port=PORT,
    instructions=(
        "Read-only evidence API over a sermon/service archive. "
        "These tools return exact transcript text plus metadata -- they "
        "never answer on their own. Form your answer from the evidence "
        "returned, and prefer quoting exact_text over paraphrasing."
    ),
)


async def _post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{CONNECTOR_URL}{path}", json=payload)
        r.raise_for_status()
        return r.json()


async def _get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{CONNECTOR_URL}{path}")
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def archive_health() -> dict:
    """Check whether the archive connector and database are reachable right
    now. Call this first if other tools start failing."""
    return await _get("/health")


@mcp.tool()
async def search_transcripts(
    query: Optional[str] = None,
    speaker: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    type: Optional[str] = None,
    match_all_words: Optional[bool] = None,
    limit: Optional[int] = None,
) -> dict:
    """Find moments in the archive by words spoken, with optional filters.

    query: words to search for in the transcript text.
    speaker: restrict to a tracked speaker's name.
    date_from / date_to: ISO date strings (YYYY-MM-DD) to bound the range.
    type: one of Song, Prayer, Testimony, Scripture, Exhortation, Sermon.
    match_all_words: require every word in query to match (default: any).
    limit: max hits to return (connector default 25, max 200).
    """
    payload = {
        k: v
        for k, v in {
            "query": query,
            "speaker": speaker,
            "date_from": date_from,
            "date_to": date_to,
            "type": type,
            "match_all_words": match_all_words,
            "limit": limit,
        }.items()
        if v is not None
    }
    return await _post("/search", payload)


@mcp.tool()
async def get_context(
    segment_id: Optional[int] = None,
    service_id: Optional[int] = None,
    t: Optional[float] = None,
    before: Optional[int] = None,
    after: Optional[int] = None,
) -> dict:
    """Get the transcript lines immediately around a specific moment.

    Identify the moment either by segment_id, or by service_id + t (seconds
    into that service). before/after control how many lines of context on
    each side (connector default: 3)."""
    payload = {
        k: v
        for k, v in {
            "segment_id": segment_id,
            "service_id": service_id,
            "t": t,
            "before": before,
            "after": after,
        }.items()
        if v is not None
    }
    return await _post("/context", payload)


@mcp.tool()
async def get_service(service_id: int, include_transcript: Optional[bool] = None) -> dict:
    """Get one service's metadata (date, title, speakers, parts) and,
    optionally, its full transcript.

    service_id: required, the archive's numeric service ID.
    include_transcript: pass true to also receive the whole transcript
    (can be long -- prefer search/context for a targeted moment)."""
    payload = {"service_id": service_id}
    if include_transcript is not None:
        payload["include_transcript"] = include_transcript
    return await _post("/service", payload)


@mcp.tool()
async def find_person(name: str) -> dict:
    """Find a name in the archive both as a tracked speaker AND as words
    spoken about them in transcripts -- the two are kept clearly separate
    in the result so you don't confuse someone being spoken OF with them
    speaking."""
    return await _post("/person", {"name": name})


@mcp.tool()
async def answer_question(question: str) -> dict:
    """Turn a natural-language question into a ready-made evidence package:
    exact transcript text, metadata, and the connector's interpretation of
    what was asked -- clearly separated so you can see how the question was
    parsed. This is usually the best first tool to reach for; fall back to
    search_transcripts for a more targeted follow-up."""
    return await _post("/answer-question", {"question": question})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
