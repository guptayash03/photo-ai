#!/bin/sh
# Start a minimal HTTP healthcheck server on PORT (default 8080) for Cloud Run
python -c "
import http.server, threading, os
port = int(os.environ.get('PORT', 8080))
handler = http.server.BaseHTTPRequestHandler
class H(handler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')
    def log_message(self, *a):
        pass
threading.Thread(target=http.server.HTTPServer(('', port), H).serve_forever, daemon=True).start()
" &

# Start Celery worker
exec celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
