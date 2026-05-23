#!/bin/bash
set -e

# Start Celery worker in background
celery -A app.celery_app worker --loglevel=info --concurrency=2 &

# Start Celery Beat in background (redbeat stores schedule in Redis)
celery -A app.celery_app beat --loglevel=info --scheduler redbeat.RedBeatScheduler &

# Keep a tiny HTTP server alive so Render doesn't kill the service
# This just responds 200 OK to health checks on $PORT
python -c "
import os, http.server, socketserver
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')
    def log_message(self, *args): pass
port = int(os.environ.get('PORT', 8001))
with socketserver.TCPServer(('', port), H) as s:
    s.serve_forever()
"