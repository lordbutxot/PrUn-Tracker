#!/usr/bin/env python3
"""
Simple HTTP server to serve CSV files for the arbitrage app.
Run this script from the PrUn-Tracker directory to serve the cache files.
"""

import http.server
import socketserver
import os
from urllib.parse import unquote

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With')
        super().end_headers()

    def do_GET(self):
        # Handle requests for cache files
        if self.path.startswith('/pu-tracker/cache/'):
            file_path = unquote(self.path[1:])  # Remove leading slash
            if os.path.exists(file_path):
                self.send_response(200)
                if file_path.endswith('.csv'):
                    self.send_header('Content-Type', 'text/csv')
                super().end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        else:
            super().do_GET()

if __name__ == '__main__':
    PORT = 8000

    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print("Press Ctrl+C to stop the server")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")