#!/bin/bash
set -e

# Celery app lives in app.tasks.celery_app (not app.celery_app)
CELERY_APP="app.tasks.celery_app"

# Start Celery worker in background
celery -A "$CELERY_APP" worker --loglevel=info --concurrency=2 &

# Beat drains ingest:events queue every 5s (see celery_app.conf beat_schedule)
celery -A "$CELERY_APP" beat --loglevel=info &

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