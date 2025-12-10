#!/usr/bin/env python3
import http.server
import socketserver
from pathlib import Path
import urllib.parse
import json
import time
from threading import Thread
import sys
from pyvi import ViTokenizer
import re

PORT = 8888
TEMP_DIR = Path("temp_text")
TEMP_DIR.mkdir(exist_ok=True)
TEXT_FILE = TEMP_DIR / "selected.txt"
FULL_PDF_FILE = TEMP_DIR / "full_pdf.txt"

class TextHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/save-text':
            self._save_text(TEXT_FILE, "Selected text")
        elif self.path == '/save-full-pdf':
            self._save_text(FULL_PDF_FILE, "Full PDF text")
        else:
            self.send_response(404)
            self.end_headers()
    
    def _save_text(self, file_path, description):
        try:
            # Get content length
            content_length = int(self.headers['Content-Length'])
            
            # Read the text data
            text_data = self.rfile.read(content_length).decode('utf-8')
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_data)
            
            # Save metadata
            metadata = {
                'timestamp': time.time(),
                'length': len(text_data),
                'type': description,
                'preview': text_data[:100] + "..." if len(text_data) > 100 else text_data
            }
            
            metadata_file = TEMP_DIR / f"{file_path.stem}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            # Send success response
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                'status': 'success',
                'message': f'{description} saved ({len(text_data)} characters)',
                'timestamp': time.time(),
                'file': str(file_path.name)
            }
            
            self.wfile.write(json.dumps(response).encode())
            print(f"✅ {description}: {len(text_data)} characters → {file_path.name}")
            
        except Exception as e:
            print(f"❌ Error saving {description}: {e}")
            self.send_response(500)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            error_response = {
                'status': 'error',
                'message': str(e)
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_OPTIONS(self):
        # Handle CORS preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            status = {
                'server': 'running',
                'port': PORT,
                'selected_file_exists': TEXT_FILE.exists(),
                'full_pdf_file_exists': FULL_PDF_FILE.exists(),
                'timestamp': time.time()
            }
            
            # Add file info
            for file_path, key in [(TEXT_FILE, 'selected'), (FULL_PDF_FILE, 'full_pdf')]:
                if file_path.exists():
                    stat = file_path.stat()
                    status[f'{key}_file_size'] = stat.st_size
                    status[f'{key}_file_modified'] = stat.st_mtime
            
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def start_server():
    """Start the text server"""
    try:
        with socketserver.TCPServer(("", PORT), TextHandler) as httpd:
            print(f"🚀 Text server started at http://localhost:{PORT}")
            print(f"📁 Selected text → {TEXT_FILE.absolute()}")
            print(f"📄 Full PDF text → {FULL_PDF_FILE.absolute()}")
            httpd.serve_forever()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"⚠️  Port {PORT} already in use - server may already be running")
        else:
            print(f"❌ Error starting server: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")

def run_server_background():
    """Run server in background thread"""
    server_thread = Thread(target=start_server, daemon=True)
    server_thread.start()
    return server_thread


if __name__ == "__main__":
    start_server() 