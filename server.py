"""Static website + optional server-side proxy to the existing Jadicek API."""
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
try:
    from model_service import ModelService
    MODEL_SERVICE = ModelService()
    MODEL_ERROR = None
except Exception as exc:
    MODEL_SERVICE = None
    MODEL_ERROR = str(exc)


class Handler(SimpleHTTPRequestHandler):
    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != '/api/predict':
            self.reply(404, {'error': 'Endpoint tidak ditemukan.'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16384:
                self.reply(400, {'error': 'Ukuran input tidak valid.'})
                return
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError('Input harus berupa object.')
        except (ValueError, json.JSONDecodeError):
            self.reply(400, {'error': 'Input JSON tidak valid.'})
            return
        if MODEL_SERVICE is None:
            self.reply(503, {'error': 'Model lokal belum tersedia.', 'detail': MODEL_ERROR})
            return
        try:
            self.reply(200, MODEL_SERVICE.predict(payload))
        except ValueError as exc:
            self.reply(400, {'error': str(exc)})
        except Exception:
            self.reply(500, {'error': 'Prediksi model gagal diproses.'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '3000'))
    server = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(ROOT)))
    print(f'Jadicek berjalan di http://localhost:{port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
