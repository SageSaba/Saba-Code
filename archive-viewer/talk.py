#!/usr/bin/env python3
"""talk.py -- a continuous voice conversation with your choice of AI.

Loop: press Enter to start recording, speak, press Enter to stop.
Your voice is transcribed locally with Whisper. The transcribed TEXT is
sent to whichever AI provider you choose; its answer prints back
immediately, with real access to the sermon archive as a tool. Say or
type "quit" to end.

Usage:  talk.py [claude|chatgpt|grok|gemini]
        (defaults to claude if no provider given)

This exists so no single AI provider is a single point of failure --
same archive, same voice pipeline, your choice of which AI answers.
"""

import json
import os
import subprocess
import sys
import tempfile

import httpx

WHISPER_MODEL = os.path.expanduser("~/ggml-large-v3-turbo.bin")
CONNECTOR_URL = os.environ.get("ARCHIVE_CONNECTOR_URL", "http://127.0.0.1:8766")

SYSTEM_PROMPT = """You're talking with Saba -- also Thomas A. Young, a retired \
pastor (~25 years) who keeps a church audio/video archive. His wife is \
Barbara; his daughter Elizabeth Doss is a song leader; his late best friend \
was Joe Nance. Saba speaks by voice through a dictation pipeline, so expect \
occasional transcription typos or garbled words -- ask for clarification \
rather than guessing if something doesn't parse. He leads the direction of \
any work; you help him think out loud, draft, and talk things through.

You have real tools that search his actual sermon archive (Sermons.db --
~2,600 services, ~3 million transcript lines). They return exact transcript
text and metadata -- they never answer on their own. Form your answer from
the evidence they return, quoting exact_text where it matters, rather than
paraphrasing or guessing. If the tools return nothing relevant, say so
honestly rather than inventing an answer."""

# Tool schemas, in Anthropic's shape. Converted to OpenAI's shape at call
# time for the providers that need it (chatgpt, grok, gemini all speak the
# OpenAI function-calling format over their APIs).
TOOLS_ANTHROPIC = [
    {
        "name": "search_transcripts",
        "description": "Find moments in the archive by words spoken, with optional speaker/date/type filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "words to search for"},
                "speaker": {"type": "string"},
                "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD"},
                "type": {"type": "string", "description": "Song, Prayer, Testimony, Scripture, Exhortation, or Sermon"},
                "match_all_words": {"type": "boolean"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_context",
        "description": "Get transcript lines immediately around a specific moment (by segment_id, or service_id + t seconds).",
        "input_schema": {
            "type": "object",
            "properties": {
                "segment_id": {"type": "integer"},
                "service_id": {"type": "integer"},
                "t": {"type": "number"},
                "before": {"type": "integer"},
                "after": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_service",
        "description": "Get one service's metadata (date, title, speakers, parts) and optionally its full transcript.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service_id": {"type": "integer"},
                "include_transcript": {"type": "boolean"},
            },
            "required": ["service_id"],
        },
    },
    {
        "name": "find_person",
        "description": "Find a name as a tracked speaker AND as words spoken about them in transcripts, kept separate.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "answer_question",
        "description": "Turn a natural-language question into a ready evidence package (best first tool to try).",
        "input_schema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
]


def tools_openai_format():
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOLS_ANTHROPIC
    ]


ENDPOINTS = {
    "search_transcripts": "/search",
    "get_context": "/context",
    "get_service": "/service",
    "find_person": "/person",
    "answer_question": "/answer-question",
}


def call_tool(name: str, tool_input: dict) -> str:
    path = ENDPOINTS.get(name)
    if not path:
        return json.dumps({"error": f"unknown tool {name}"})
    try:
        r = httpx.post(f"{CONNECTOR_URL}{path}", json=tool_input, timeout=30.0)
        r.raise_for_status()
        return r.text
    except Exception as e:
        return json.dumps({"error": f"connector unreachable: {e}"})


PROVIDERS = {
    "claude": {"key_file": "~/.anthropic_key", "model": "claude-sonnet-5", "kind": "anthropic"},
    "chatgpt": {"key_file": "~/.openai_key", "model": "gpt-5", "kind": "openai", "base_url": None},
    "grok": {"key_file": "~/.xai_key", "model": "grok-4", "kind": "openai", "base_url": "https://api.x.ai/v1"},
    "gemini": {"key_file": "~/.gemini_key", "model": "gemini-3.5-flash", "kind": "openai",
               "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"},
}


def looks_valid(key: str) -> bool:
    # A masked/placeholder value (bullets, asterisks from a password field)
    # won't be plain ascii text of reasonable length -- that's the real
    # thing this guards against, more than any specific prefix.
    return bool(key) and key.isascii() and len(key) >= 20


def get_key(provider: str) -> str:
    cfg = PROVIDERS[provider]
    key_file = os.path.expanduser(cfg["key_file"])
    if os.path.exists(key_file):
        with open(key_file) as f:
            key = f.read().strip()
        if looks_valid(key):
            return key
        print(f"Found {key_file} but it doesn't look like a real key")
        print("(too short, or non-ASCII -- likely a masked value was copied).")
    else:
        print(f"No key file found for {provider}.")
    print(f"Copy your {provider} key (after clicking reveal, if it's masked),")
    print(f"then run:  pbpaste > {cfg['key_file']}")
    sys.exit(1)


def record_and_transcribe() -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name

    input("Press Enter to start recording...")
    proc = subprocess.Popen(["rec", "-q", "-c", "1", "-r", "16000", wav_path])
    input("Recording -- press Enter to stop.")
    proc.terminate()
    proc.wait()

    result = subprocess.run(
        ["whisper-cli", "-m", WHISPER_MODEL, "-f", wav_path, "-np", "-nt"],
        capture_output=True, text=True,
    )
    os.unlink(wav_path)
    return result.stdout.strip()


def run_anthropic(provider: str):
    import anthropic
    cfg = PROVIDERS[provider]
    client = anthropic.Anthropic(api_key=get_key(provider))
    history = []

    while True:
        text = record_and_transcribe()
        if not text:
            print("(didn't catch anything -- try again)\n")
            continue
        print(f"\nYou said: {text}")
        if text.strip().lower().rstrip(".") in ("quit", "exit", "stop"):
            print("Ending conversation.")
            break

        history.append({"role": "user", "content": text})

        while True:
            response = client.messages.create(
                model=cfg["model"], max_tokens=1024, system=SYSTEM_PROMPT,
                tools=TOOLS_ANTHROPIC, messages=history,
            )
            history.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                print(f"  [searching the archive: {block.name}...]")
                result = call_tool(block.name, block.input)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
            history.append({"role": "user", "content": tool_results})

        reply = next((b.text for b in response.content if b.type == "text"), "(no text in response)")
        print(f"\n{provider.title()}: {reply}\n")
        print("-" * 60)


def run_openai_compatible(provider: str):
    from openai import OpenAI
    cfg = PROVIDERS[provider]
    client = OpenAI(api_key=get_key(provider), base_url=cfg.get("base_url"))
    tools = tools_openai_format()
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        text = record_and_transcribe()
        if not text:
            print("(didn't catch anything -- try again)\n")
            continue
        print(f"\nYou said: {text}")
        if text.strip().lower().rstrip(".") in ("quit", "exit", "stop"):
            print("Ending conversation.")
            break

        history.append({"role": "user", "content": text})

        while True:
            response = client.chat.completions.create(
                model=cfg["model"], messages=history, tools=tools,
            )
            msg = response.choices[0].message
            history.append(msg.model_dump(exclude_none=True))
            if not msg.tool_calls:
                break
            for tc in msg.tool_calls:
                print(f"  [searching the archive: {tc.function.name}...]")
                args = json.loads(tc.function.arguments or "{}")
                result = call_tool(tc.function.name, args)
                history.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        reply = msg.content or "(no text in response)"
        print(f"\n{provider.title()}: {reply}\n")
        print("-" * 60)


def main():
    provider = sys.argv[1].lower() if len(sys.argv) > 1 else "claude"
    if provider not in PROVIDERS:
        print(f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDERS)}")
        sys.exit(1)

    print(f"Talking to {provider.title()}. Say \"quit\" to end.\n")

    if PROVIDERS[provider]["kind"] == "anthropic":
        run_anthropic(provider)
    else:
        run_openai_compatible(provider)


if __name__ == "__main__":
    main()
