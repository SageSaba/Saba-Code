#!/usr/bin/env python3
"""Simple HTTP server to serve transcripts from Sermons.db for the reader."""
import json
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

DB = Path.home() / "Archive/Sermons.db"
PORT = 8768

class TranscriptHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        path = urlparse(self.path).path

        # Serve static HTML files
        if path == '/' or path.endswith('.html'):
            if path == '/':
                path = '/sukkot-reader.html'
            html_file = Path(__file__).parent.parent / 'html' / path.lstrip('/')
            if html_file.exists() and html_file.suffix == '.html':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(html_file.read_bytes())
                return
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not found')
            return

        if path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            return

        if path.startswith('/transcript/'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                service_id = int(path.split('/')[-1])
                segments = self.get_segments(service_id)
                self.wfile.write(json.dumps(segments).encode())
            except (ValueError, sqlite3.Error) as e:
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        if path.startswith('/audio/'):
            try:
                service_id = int(path.split('/')[-1])
                conn = sqlite3.connect(DB)
                row = conn.execute("SELECT media_path FROM Services WHERE ID = ?", (service_id,)).fetchone()
                conn.close()

                if not row or not row[0]:
                    self.send_response(404)
                    self.end_headers()
                    return

                audio_file = Path(row[0])
                if not audio_file.exists():
                    self.send_response(404)
                    self.end_headers()
                    return

                self.send_response(200)
                self.send_header('Content-Type', 'audio/mpeg')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Length', str(audio_file.stat().st_size))
                self.end_headers()
                with open(audio_file, 'rb') as f:
                    self.wfile.write(f.read())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def get_segments(self, service_id):
        """Fetch segments from RawSegments table, convert to reader format."""
        conn = sqlite3.connect(DB)
        cursor = conn.cursor()

        rows = cursor.execute(
            "SELECT start, end, text FROM RawSegments WHERE service_id = ? ORDER BY start",
            (service_id,)
        ).fetchall()

        conn.close()

        segments = []
        for start, end, text in rows:
            # Convert timestamps if needed (they should be HH:MM:SS.mmm format already)
            segments.append({
                "start": start,
                "end": end,
                "text": text
            })

        return segments

if __name__ == '__main__':
    server = HTTPServer(('localhost', PORT), TranscriptHandler)
    print(f"Transcript server running on http://localhost:{PORT}")
    print(f"  GET /health — server status")
    print(f"  GET /transcript/<service_id> — transcript JSON")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown.")
