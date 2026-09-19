#!/usr/bin/env python3
"""
SABA VOICE GATE

State machine:
  READY:
    F13 (global)              -> beep + start recording
    Return (Terminal fallback) -> beep + listen
    Esc    (Terminal fallback) -> quit

  RECORDING:
    F13 (global) -> stop recording (graceful SIGINT, never force-killed)

  REVIEW:
    F14 (global) -> RESTATE again from the ORIGINAL transcript
    F15 (global) -> discard utterance and reset to READY

Principles:
  - ORIGINAL transcript is preserved unchanged for every restatement attempt.
  - RESTATE determines what Saba meant and restates it clearly. It does not
    answer, act on, summarize, or add facts to what was said, and does not
    invent a destination or command. Genuine uncertainty is preserved rather
    than guessed away.
  - RESTATE runs through the Claude Code CLI already authenticated on this
    Mac — no Anthropic API key, no Ollama, no other separately billed API.
  - A successful restatement is copied to the clipboard automatically.
    Nothing is ever auto-pasted or executed; Saba pastes manually with
    Command-V, only after reviewing the RESTATED text.
  - If RESTATE cannot complete in time, the original transcript is shown
    and nothing is copied.
"""

import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import termios
import threading
import time
import tty
from pathlib import Path

try:
    from pynput import keyboard as _pynput_keyboard
except ImportError as exc:
    raise SystemExit(
        "The 'pynput' package is required for the F13 hotkey.\n"
        "Install it with: pip3 install pynput"
    ) from exc

# The Claude Code CLI already authenticated on this Mac (claude.ai / subscription
# login — never an ANTHROPIC_API_KEY). No Ollama, no OpenAI, no Gemini, no other
# separately billed API.
CLAUDE_BIN = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "/Users/saba/.local/bin/claude"
RESTATE_TIMEOUT = int(os.environ.get("RESTATE_TIMEOUT", "20"))

RESTATE_PROMPT = r"""
You are the RESTATE interpreter for Saba's voice gate.

You receive ONE raw transcript of something Saba actually said.

Your task is RESTATE, not rewrite:
- determine what Saba meant;
- restate it clearly;
- repair likely transcription errors only when context supports it.

You MUST NOT:
- answer it;
- act on it;
- summarize it;
- add facts;
- invent a destination or command.

If the meaning is genuinely uncertain, preserve that uncertainty rather than guessing.

Output only the restated text. No labels. No commentary.
"""

SWIFT_SPEECH_HELPER = r"""
import Foundation
import Speech
import AVFoundation

final class Listener {
    let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))!
    let audioEngine = AVAudioEngine()
    let request = SFSpeechAudioBufferRecognitionRequest()
    var task: SFSpeechRecognitionTask?
    var lastText = ""
    var lastChange = Date()
    var finished = false

    func permissions(_ done: @escaping (Bool) -> Void) {
        let group = DispatchGroup()
        var speechOK = false
        var micOK = false

        group.enter()
        SFSpeechRecognizer.requestAuthorization { status in
            speechOK = (status == .authorized)
            group.leave()
        }

        group.enter()
        AVCaptureDevice.requestAccess(for: .audio) { ok in
            micOK = ok
            group.leave()
        }

        group.notify(queue: .main) {
            done(speechOK && micOK)
        }
    }

    func start() throws {
        let node = audioEngine.inputNode
        let format = node.outputFormat(forBus: 0)
        request.shouldReportPartialResults = true

        node.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
            self.request.append(buffer)
        }

        audioEngine.prepare()
        try audioEngine.start()

        task = recognizer.recognitionTask(with: request) { result, error in
            if let result = result {
                let text = result.bestTranscription.formattedString
                if text != self.lastText {
                    self.lastText = text
                    self.lastChange = Date()
                }
                if result.isFinal {
                    self.finish()
                }
            }
            if error != nil {
                self.finish()
            }
        }

        let started = Date()
        Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { timer in
            if self.finished {
                timer.invalidate()
                return
            }

            let silentFor = Date().timeIntervalSince(self.lastChange)
            let total = Date().timeIntervalSince(started)

            if !self.lastText.isEmpty && silentFor > 1.2 {
                self.finish()
                timer.invalidate()
            } else if total > 15 {
                self.finish()
                timer.invalidate()
            }
        }
    }

    func finish() {
        guard !finished else { return }
        finished = true

        if audioEngine.isRunning {
            audioEngine.stop()
        }

        audioEngine.inputNode.removeTap(onBus: 0)
        request.endAudio()
        task?.cancel()

        print(lastText)
        fflush(stdout)
        exit(0)
    }
}

let listener = Listener()

// Graceful stop: a SIGINT (sent by the Python controller on the second
// F13 press) finishes the same way natural silence/timeout does, so the
// transcript captured so far is still printed. No force-kill.
let sigintSource = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
sigintSource.setEventHandler {
    listener.finish()
}
sigintSource.resume()
signal(SIGINT, SIG_IGN)

listener.permissions { ok in
    guard ok else {
        fputs("ERROR: Microphone or Speech Recognition permission was not granted.\n", stderr)
        exit(2)
    }
    do {
        try listener.start()
    } catch {
        fputs("ERROR: Could not start microphone: \(error)\n", stderr)
        exit(3)
    }
}
RunLoop.main.run()
"""


def keypress() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        return os.read(fd, 1).decode("utf-8", errors="ignore")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def beep() -> None:
    # macOS system sound; terminal bell is fallback.
    try:
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Pop.aiff"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        print("\a", end="", flush=True)


def frontmost_app() -> str:
    script = (
        'tell application "System Events" to '
        'get name of first application process whose frontmost is true'
    )
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3
        )
        return r.stdout.strip()
    except Exception:
        return ""


def ensure_speech_helper() -> Path:
    d = Path(tempfile.gettempdir()) / "saba_voice_gate"
    d.mkdir(parents=True, exist_ok=True)
    swift = d / "saba_listen.swift"
    binary = d / "saba_listen_v4"

    if binary.exists():
        return binary

    swift.write_text(SWIFT_SPEECH_HELPER)
    which = subprocess.run(["which", "swiftc"], capture_output=True, text=True)
    if which.returncode != 0:
        raise RuntimeError("Swift compiler not found.")

    build = subprocess.run(
        [
            which.stdout.strip(), str(swift), "-o", str(binary),
            "-framework", "Speech", "-framework", "AVFoundation"
        ],
        capture_output=True, text=True
    )
    if build.returncode != 0:
        raise RuntimeError(build.stderr.strip() or "Could not build microphone helper.")
    return binary


def listen_once() -> str:
    helper = ensure_speech_helper()
    beep()
    print("\nLISTENING...")

    started = time.perf_counter()
    try:
        r = subprocess.run(
            [str(helper)], capture_output=True, text=True, timeout=20
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Listening timed out safely.") from exc

    elapsed = time.perf_counter() - started
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "Microphone failed.")

    raw = r.stdout.strip()
    if not raw:
        raise RuntimeError("No usable speech was heard.")

    print(f"[TIMER] Speech: {elapsed:.2f}s")
    return raw


class F13Recorder:
    """First F13 starts the helper; second F13 sends SIGINT (never kills) and hands the transcript to review()."""

    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self.started = 0.0

    def toggle(self) -> None:
        try:
            if self.process is None:
                self._start()
            else:
                self._stop()
        except Exception as exc:
            print(f"\n[F13] RESET — {exc}")
            self.process = None

    def _start(self) -> None:
        helper = ensure_speech_helper()
        beep()
        print("\n[F13] LISTENING... (press F13 again to stop)")
        self.started = time.perf_counter()
        self.process = subprocess.Popen(
            [str(helper)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _stop(self) -> None:
        proc = self.process
        self.process = None
        print("\n[F13] STOPPING...")

        proc.send_signal(signal.SIGINT)
        out, err = proc.communicate()  # waits for graceful finish(); never killed
        elapsed = time.perf_counter() - self.started

        if proc.returncode != 0:
            print(f"\n[F13] RESET — {err.strip() or 'Microphone failed.'}")
            return

        raw = out.strip()
        if not raw:
            print("\n[F13] RESET — No usable speech was heard.")
            return

        print(f"[TIMER] Speech: {elapsed:.2f}s")
        review(raw)


CONTROL_QUEUE: "queue.Queue[str]" = queue.Queue()

_HOTKEY_MAP = {
    _pynput_keyboard.Key.f13: "F13",
    _pynput_keyboard.Key.f14: "TAB",
    _pynput_keyboard.Key.f15: "ESC",
}


def start_hotkeys(recorder: F13Recorder) -> None:
    """Global F13/F14/F15 capture; listener thread only enqueues so the OS event tap is never blocked."""

    def on_press(key) -> None:
        tag = _HOTKEY_MAP.get(key)
        if tag:
            CONTROL_QUEUE.put(tag)

    def worker() -> None:
        while True:
            tag = CONTROL_QUEUE.get()
            if tag == "F13":
                recorder.toggle()
            # TAB/ESC with no review() waiting on them: nothing to do, drop.

    threading.Thread(target=worker, daemon=True).start()
    listener = _pynput_keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()


def wait_review_control() -> str:
    """Block until F14 (restate) or F15 (discard); ignore anything else (e.g. a stray F13)."""
    while True:
        tag = CONTROL_QUEUE.get()
        if tag in ("TAB", "ESC"):
            return tag


def listen_more(existing: str) -> str:
    """
    Give Saba another speaking turn and append it to the ORIGINAL transcript.
    Nothing already captured is discarded.
    """
    print("\nADD TO ORIGINAL — press Return, then speak more.")
    print("[RETURN = ADD SPEECH]   [ESC = KEEP WHAT I HAVE]")
    print("Choice: ", end="", flush=True)

    while True:
        k = keypress()

        if k == "\x1b":
            print("KEEP ORIGINAL")
            return existing

        if k in {"\r", "\n"}:
            print("ADD SPEECH")
            more = listen_once()
            if not more.strip():
                return existing
            combined = (existing.rstrip() + " " + more.strip()).strip()
            print("\nORIGINAL IS NOW:")
            print(combined)
            return combined



def restate(original: str) -> tuple[str, float, bool]:
    """Call the already-authenticated Claude Code CLI, non-interactively, as the RESTATE interpreter."""
    started = time.perf_counter()
    try:
        r = subprocess.run(
            [
                CLAUDE_BIN, "-p",
                "--output-format", "json",
                "--tools", "",              # no tool access: RESTATE must not act on anything
                "--strict-mcp-config",      # no MCP servers either
                "--no-session-persistence",
                "--system-prompt", RESTATE_PROMPT,
                original,
            ],
            capture_output=True, text=True, timeout=RESTATE_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError):
        return original, time.perf_counter() - started, False

    elapsed = time.perf_counter() - started

    if r.returncode != 0:
        return original, elapsed, False

    try:
        data = json.loads(r.stdout)
    except ValueError:
        return original, elapsed, False

    if data.get("is_error") or data.get("subtype") != "success":
        return original, elapsed, False

    restated = str(data.get("result", "")).strip()
    if not restated:
        return original, elapsed, False

    return restated, elapsed, True


def copy_to_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text, text=True, check=True)


def paste_to_app(text: str, app_name: str) -> None:
    copy_to_clipboard(text)

    # If the recorded frontmost app was Terminal, ChatGPT is the useful default
    # for our present test. Otherwise return to the actual prior app.
    target = app_name
    if not target or target in {"Terminal", "iTerm2", "Python"}:
        target = "ChatGPT"

    activate = f'tell application "{target}" to activate'
    subprocess.run(
        ["osascript", "-e", activate],
        capture_output=True, text=True, check=True
    )
    time.sleep(0.6)

    paste = 'tell application "System Events" to keystroke "v" using command down'
    subprocess.run(
        ["osascript", "-e", paste],
        capture_output=True, text=True, check=True
    )


def review(original: str) -> None:
    while True:
        current, elapsed, restated = restate(original)

        print("\n" + "=" * 72)
        print("ORIGINAL:")
        print(original)

        if restated:
            print("\nRESTATED:")
            print(current)
            print(f"\n[TIMER] Restate: {elapsed:.2f}s")
            copy_to_clipboard(current)
            print("COPIED TO CLIPBOARD — paste yourself with Command-V.")
        else:
            print(f"\n[TIMER] Restate stopped at {elapsed:.2f}s.")
            print("Nothing was restated. Nothing was copied.")

        print("=" * 72)
        print("[F14 = RESTATE FROM ORIGINAL]   [F15 = DISCARD / RESET]")

        action = wait_review_control()

        if action == "ESC":
            print("DISCARD")
            return

        print("RESTATE")
        # Always restates from the full, untouched ORIGINAL.

def main() -> None:
    print("SABA VOICE GATE — 1.1")
    print("F13 (global) = start / stop recording")
    print("F14 (global) = restate again from ORIGINAL")
    print("F15 (global) = discard, reset to READY")
    print("A successful restatement is copied to the clipboard automatically — paste yourself with Command-V.")
    print("(A focused Terminal can still use RETURN to speak / ESC to quit.)\n")

    start_hotkeys(F13Recorder())

    while True:
        print("\nREADY — [RETURN = SPEAK]   [ESC = QUIT]")
        print("Saba: ", end="", flush=True)

        k = keypress()

        if k == "\x1b":
            print("QUIT")
            break

        if k not in {"\r", "\n"}:
            continue

        print("SPEAK")

        try:
            original = listen_once()
            review(original)
        except Exception as exc:
            print(f"\nRESET — {exc}")


if __name__ == "__main__":
    main()
