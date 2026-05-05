#!/usr/bin/env python3
"""
dashboard/server.py — local development server

Why this exists:
  Opening index.html directly as a file:// URL causes CORS errors when the
  dashboard tries to call the Google Sheets API. Browsers block cross-origin
  requests from file:// origins. Serving from localhost:3000 fixes this.

Usage:
  cd dashboard
  python server.py

Then open: http://localhost:3000
"""

import http.server
import socketserver
import os

PORT = 3000

# Change into the dashboard directory so index.html is served at /
os.chdir(os.path.dirname(os.path.abspath(__file__)))

handler = http.server.SimpleHTTPRequestHandler

# Suppress the default request logging (too noisy for dev)
handler.log_message = lambda *args: None

print(f"Dashboard running at http://localhost:{PORT}")
print("Press Ctrl+C to stop.\n")

with socketserver.TCPServer(("", PORT), handler) as httpd:
    httpd.serve_forever()
