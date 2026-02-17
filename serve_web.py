#!/usr/bin/env python3
"""
Simple HTTP server for CARLA visualization
Serves HTML, CSS, and JS files while main.py handles WebSocket on port 8765
"""

import http.server
import socketserver
import threading
import os
from pathlib import Path

PORT = 8000
HOST = "localhost"

# Allow port to be reused immediately (SO_REUSEADDR)
socketserver.TCPServer.allow_reuse_address = True

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler with CORS headers"""
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Custom logging format
        if "GET" in format or "POST" in format:
            print(f"🌐 HTTP: {args[0]} {args[1]} {args[2]}")

def start_server():
    """Start HTTP server"""
    os.chdir(Path(__file__).parent)
    
    port = PORT
    max_retries = 5
    
    for attempt in range(max_retries):
        try:
            with socketserver.TCPServer(("", port), MyHTTPRequestHandler) as httpd:
                print("=" * 60)
                print("🌐 HTTP Server Started")
                print("=" * 60)
                print(f"📍 URL: http://localhost:{port}")
                print(f"📄 Serving files from: {os.getcwd()}")
                print("\n💡 Open http://localhost:{} in your browser".format(port))
                print("⚠️  Make sure main.py is running (WebSocket on :8765)")
                print("\nPress Ctrl+C to stop the server\n")
                
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\n\n🛑 HTTP Server stopped")
                break
        except OSError as e:
            if attempt < max_retries - 1:
                port += 1
                print(f"⚠️  Port {port-1} in use, trying {port}...")
            else:
                print(f"❌ ERROR: Could not find available port after {max_retries} attempts")
                print(f"Try: netstat -ano | findstr :{PORT}")
                raise

if __name__ == '__main__':
    start_server()
