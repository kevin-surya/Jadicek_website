"""Vercel Python Function for the local Jadicek model artifacts."""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from model_service import ModelService
    model_repo = os.environ.get("HF_MODEL_REPO", "").strip()
    if model_repo:
        from huggingface_hub import snapshot_download

        downloaded_model_dir = snapshot_download(
            repo_id=model_repo,
            revision=os.environ.get("HF_MODEL_REVISION", "main"),
            allow_patterns=["*.joblib"],
            token=os.environ.get("HF_TOKEN") or None,
            cache_dir="/tmp/huggingface",
        )
        MODEL = ModelService(downloaded_model_dir)
        MODEL_SOURCE = f"huggingface:{model_repo}"
    else:
        MODEL = ModelService()
        MODEL_SOURCE = "bundled"
    MODEL_LOAD_ERROR = None
except Exception as exc:  # surfaced by the health endpoint without local paths
    MODEL = None
    MODEL_SOURCE = None
    MODEL_LOAD_ERROR = f"{type(exc).__name__}: {exc}"


class handler(BaseHTTPRequestHandler):
    def _json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if MODEL is None:
            self._json(503, {"status": "model-error", "detail": MODEL_LOAD_ERROR})
        else:
            self._json(200, {"status": "ready", "model": "notebook-lightgbm", "source": MODEL_SOURCE})

    def do_POST(self):
        if MODEL is None:
            self._json(503, {"error": "Model gagal dimuat.", "detail": MODEL_LOAD_ERROR})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16_384:
                self._json(400, {"error": "Ukuran input tidak valid."})
                return
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Input harus berupa object JSON.")
            self._json(200, MODEL.predict(payload))
        except (json.JSONDecodeError, ValueError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception:
            self._json(500, {"error": "Prediksi model gagal diproses."})
