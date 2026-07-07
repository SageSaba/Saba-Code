import sqlite3
import tkinter as tk
from threading import Thread
import time
from datetime import datetime
from pathlib import Path

# Change this path on your Mac if needed.
DB_PATH = Path("/Users/saba/Desktop/Saba Code/remember/mymemory.db")

running = False
worker_thread = None


def get_latest_entries(limit=10):
    if not DB_PATH.exists():
        return [("", f"Database not found:\n{DB_PATH}")]

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, content
                FROM memories
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            return cursor.fetchall()

    except Exception as e:
        return [("", f"DB error: {e}")]


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

    for ts, content in entries:
        content_clean = str(content).strip()

        # Skip empty content and simple number-only test entries.
        if not content_clean or content_clean.isdigit():
            continue

        try:
            dt = datetime.strptime(str(ts), "%Y-%m-%d %H:%M:%S")
            formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            formatted = str(ts).strip()

        if formatted:
            text_area.insert(tk.END, f"{formatted}  ", "timestamp")

        text_area.insert(tk.END, f"{content_clean}\n", "content")
        shown_any = True

    if not shown_any:
        text_area.insert(tk.END, "Waiting for new entries...\n")

    text_area.config(state="disabled")
    text_area.see(tk.END)


def clear_display():
    text_area.config(state="normal")
    text_area.delete("1.0", tk.END)
    text_area.insert(tk.END, "Cleared. Waiting...\n")
    text_area.config(state="disabled")


def stop_update():
    global running
    running = False

    text_area.config(state="normal")
    text_area.insert(tk.END, "\n--- Live feed stopped ---\n")
    text_area.config(state="disabled")


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

tk.Button(
    button_frame,
    text="Clear Display",
    bg="#ff6666",
    fg="white",
    padx=15,
    pady=5,
    command=clear_display,
).pack(side="left", padx=5)

tk.Button(
    button_frame,
    text="Stop Live",
    bg="#666666",
    fg="white",
    padx=15,
    pady=5,
    command=stop_update,
).pack(side="left", padx=5)

tk.Button(
    button_frame,
    text="Start Live",
    bg="#44aa44",
    fg="white",
    padx=15,
    pady=5,
    command=start_update,
).pack(side="left", padx=5)

frame = tk.Frame(root)
frame.pack(expand=True, fill="both", padx=10, pady=5)

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

start_update()

root.mainloop()
