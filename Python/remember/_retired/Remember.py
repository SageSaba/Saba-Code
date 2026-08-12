import sqlite3
import tkinter as tk
from threading import Thread
import time
from datetime import datetime

DB_PATH = "/Users/saba/Desktop/Saba Code/remember/mymemory.db"
running = True  # flag to control the loop

def get_latest_entries(limit=10):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, content FROM memories ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"DB error: {e}")
        return []

def update_display():
    global running
    while running:
        entries = get_latest_entries()
        root.after(0, refresh_text_area, entries)
        time.sleep(1)

def refresh_text_area(entries):
    text_area.config(state="normal")
    text_area.delete("1.0", tk.END)
    
    if not entries:
        text_area.insert(tk.END, "Waiting for new entries...\n")
    else:
        for ts, content in entries:
            content_clean = content.strip()
            if content_clean.isdigit():  # skip numbers
                continue
            try:
                dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted = ts.strip()
            
            text_area.insert(tk.END, f"{formatted}  ", "timestamp")
            text_area.insert(tk.END, f"{content_clean}\n", "content")
    
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
    global running
    running = True
    Thread(target=update_display, daemon=True).start()

root = tk.Tk()
root.title("Memory Live View")
root.geometry("800x650")

tk.Label(root, text="Live Memory Feed", font=("Arial", 16, "bold")).pack(pady=8)

button_frame = tk.Frame(root)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Clear Display", bg="#ff6666", fg="white", padx=15, pady=5,
          command=clear_display).pack(side="left", padx=5)

tk.Button(button_frame, text="Stop Live", bg="#666666", fg="white", padx=15, pady=5,
          command=stop_update).pack(side="left", padx=5)

tk.Button(button_frame, text="Start Live", bg="#44aa44", fg="white", padx=15, pady=5,
          command=start_update).pack(side="left", padx=5)

frame = tk.Frame(root)
frame.pack(expand=True, fill="both", padx=10, pady=5)

scrollbar = tk.Scrollbar(frame)
scrollbar.pack(side="right", fill="y")

text_area = tk.Text(frame, wrap="word", font=("Arial", 12),
                    yscrollcommand=scrollbar.set, spacing3=8)
text_area.pack(expand=True, fill="both", side="left")
scrollbar.config(command=text_area.yview)

text_area.tag_configure("timestamp", foreground="#555", font=("Arial", 10))
text_area.tag_configure("content", foreground="black")

text_area.config(state="disabled")

# Start live on launch
start_update()

root.mainloop()
