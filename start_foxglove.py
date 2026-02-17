#!/usr/bin/env python3
"""
Foxglove Quick Start Helper
Starts HTTP server and opens browser automatically
"""

import http.server
import socketserver
import threading
import webbrowser
import time
import os
from pathlib import Path

HTTP_PORT = 8001

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()
    
    def log_message(self, format, *args):
        if "GET" in format:
            print(f"  📄 {args[0]} {args[1]}")

def start_server():
    """Start HTTP server"""
    os.chdir(Path(__file__).parent)
    
    print("\n" + "=" * 60)
    print("  🌐 Foxglove HTTP Server")
    print("=" * 60)
    
    with socketserver.TCPServer(("", HTTP_PORT), Handler) as httpd:
        print(f"  ✅ Server running on http://localhost:{HTTP_PORT}")
        print(f"  📍 Serving from: {os.getcwd()}")
        print()
        
        # Open browser
        time.sleep(1)
        url = f"http://localhost:{HTTP_PORT}/foxglove.html"
        print(f"  🌐 Opening browser: {url}")
        webbrowser.open(url)
        
        print()
        print("  📋 Make sure foxglove_server.py is running!")
        print("  💡 Press Ctrl+C to stop server")
        print("=" * 60 + "\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  🛑 Server stopped")

if __name__ == '__main__':
    start_server()
