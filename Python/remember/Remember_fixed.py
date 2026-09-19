import sqlite3
import tkinter as tk
from threading import Thread
import time
from datetime import datetime
from pathlib import Path

# Use RawSegments.db by default if available, otherwise fall back to mymemory.db.
BASE_DIR = Path(__file__).resolve().parent
RAW_DB = BASE_DIR / "RawSegments.db"
MY_DB = BASE_DIR / "mymemory.db"
DB_PATH = RAW_DB if RAW_DB.exists() else MY_DB

running = False
worker_thread = None


def get_latest_entries(limit=10):
    if not DB_PATH.exists():
        return [("", "", f"Database not found:\n{DB_PATH}")]

    if DB_PATH.name == "RawSegments.db":
        query = "SELECT timestamp, speaker, text FROM RawSegments ORDER BY timestamp DESC LIMIT ?"
    else:
        query = "SELECT timestamp, '', content FROM memories ORDER BY timestamp DESC LIMIT ?"

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return cursor.fetchall()

    except Exception as e:
        return [("", "", f"DB error: {e}")]


def update_display():
    global running

    while running:
        entries = get_latest_entries()
        root.after(0, refresh_text_area, entries)
        time.sleep(1)


def refresh_text_area(entries):
    text_area.config(state="normal")
    text_area.delete("1.0", tk.END)

    shown_any = False

    for ts, speaker, content in entries:
        content_clean = str(content).strip()

        # Skip empty content and simple number-only test entries.
        if not content_clean or content_clean.isdigit():
            continue

        try:
            dt = datetime.strptime(str(ts), "%Y-%m-%d %H:%M:%S")
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            formatted = str(ts).strip()

        prefix = f"{speaker}: " if speaker else ""
        if formatted:
            text_area.insert(tk.END, f"{formatted}  ", "timestamp")

        text_area.insert(tk.END, f"{prefix}{content_clean}\n", "content")
        shown_any = True

    if not shown_any:
        text_area.insert(tk.END, "Waiting for new entries...\n")

    text_area.see(tk.END)


def clear_display():
    text_area.config(state="normal")
    text_area.delete("1.0", tk.END)
    text_area.insert(tk.END, "Cleared. Waiting...\n")


def stop_update():
    global running
    running = False

    text_area.config(state="normal")
    text_area.insert(tk.END, "\n--- Live feed stopped ---\n")


def start_update():
    global running, worker_thread

    if running:
        return

    running = True
    worker_thread = Thread(target=update_display, daemon=True)
    worker_thread.start()


def on_close():
    global running
    running = False
    root.destroy()


root = tk.Tk()
root.title("Memory Live View")
root.geometry("800x650")
root.protocol("WM_DELETE_WINDOW", on_close)

tk.Label(root, text="Live Memory Feed", font=("Arial", 16, "bold")).pack(pady=8)

button_frame = tk.Frame(root)
button_frame.pack(pady=5)

BTN_FONT = ("Arial", 13, "bold")

show_feed_var = tk.BooleanVar(value=False)

def toggle_feed():
    if show_feed_var.get():
        frame.pack(expand=True, fill="both", padx=10, pady=5)
    else:
        frame.pack_forget()

tk.Checkbutton(
    button_frame,
    text="Show feed",
    variable=show_feed_var,
    font=BTN_FONT,
    command=toggle_feed,
).pack(side="left", padx=15)

frame = tk.Frame(root)
# frame is not packed at startup — only shows when the "Show feed" checkbox is toggled on

scrollbar = tk.Scrollbar(frame)
scrollbar.pack(side="right", fill="y")

text_area = tk.Text(
    frame,
    wrap="word",
    font=("Arial", 12),
    yscrollcommand=scrollbar.set,
    spacing3=8,
)
text_area.pack(expand=True, fill="both", side="left")

scrollbar.config(command=text_area.yview)

text_area.tag_configure("timestamp", foreground="#555", font=("Arial", 10))
text_area.tag_configure("content", foreground="black")

text_area.config(state="disabled")


# --- speak/type input pair -----------------------------------------------

import re
try:
    from AppKit import NSSpellChecker
    _spell_checker = NSSpellChecker.sharedSpellChecker()
except Exception:
    _spell_checker = None


def clean_text(raw):
    """Fix misspellings word-by-word using macOS's built-in spell checker
    (same one every Mac app uses, on-device). Punctuation and whitespace
    are preserved exactly."""
    if not raw or _spell_checker is None:
        return raw or ""
    tokens = re.findall(r"[A-Za-z']+|[^A-Za-z']+", raw)
    out = []
    for tok in tokens:
        if not re.match(r"[A-Za-z']", tok):
            out.append(tok)
            continue
        r = _spell_checker.checkSpellingOfString_startingAt_(tok, 0)
        loc = r.location if hasattr(r, "location") else r[0]
        length = r.length if hasattr(r, "length") else r[1]
        if length > 0:
            guesses = _spell_checker.guessesForWordRange_inString_language_inSpellDocumentWithTag_(
                (loc, length), tok, "en", 0
            )
            if guesses:
                fixed = str(guesses[0])
                if tok[0].isupper() and fixed:
                    fixed = fixed[0].upper() + fixed[1:]
                out.append(fixed)
            else:
                out.append(tok)
        else:
            out.append(tok)
    return "".join(out)


def on_input_change(event=None):
    raw = input_box.get("1.0", tk.END).rstrip()
    heard = clean_text(raw)
    heard_box.config(state="normal")
    heard_box.delete("1.0", tk.END)
    heard_box.insert("1.0", heard)


def copy_and_clear(event=None):
    text = heard_box.get("1.0", tk.END).strip()
    if not text:
        return "break"
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()
    input_box.delete("1.0", tk.END)
    heard_box.delete("1.0", tk.END)
    return "break"


input_frame = tk.Frame(root)
input_frame.pack(fill="x", padx=10, pady=8)

tk.Label(input_frame, text="Type or dictate", font=("Arial", 11, "bold"), anchor="w").pack(fill="x")
input_box = tk.Text(input_frame, height=3, wrap="word", font=("Arial", 12))
input_box.pack(fill="x", pady=(2, 6))
input_box.bind("<KeyRelease>", on_input_change)

tk.Label(input_frame, text="What I heard  —  press Return to copy to clipboard", font=("Arial", 11, "bold"), fg="#557", anchor="w").pack(fill="x")
heard_box = tk.Text(input_frame, height=3, wrap="word", font=("Arial", 12), fg="#334", bg="#f4f4f8")
heard_box.pack(fill="x", pady=(2, 6))
heard_box.bind("<Return>", copy_and_clear)


start_update()

root.mainloop()
