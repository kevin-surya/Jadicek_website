"""Authenticated Vercel proxy for the Jadicek Hugging Face Space."""
from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


HF_SPACE_URL = os.environ.get(
    "HF_SPACE_URL", "https://kevin-surya04-jadicek-api.hf.space"
).strip().rstrip("/")
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()


def _request(url, *, data=None, timeout=25):
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    request = Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _parse_sse(stream):
    for block in re.split(r"\r?\n\r?\n", stream.strip()):
        event = None
        data_lines = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].strip())
        if event == "complete" and data_lines:
            result = json.loads("\n".join(data_lines))
            return result[0] if isinstance(result, list) else result
        if event == "error":
            detail = json.loads("\n".join(data_lines)) if data_lines else {}
            title = detail.get("title", "Hugging Face menolak prediksi.")
            raise RuntimeError(title)
    raise RuntimeError("Respons prediksi Hugging Face tidak lengkap.")


def predict(payload):
    start_body = json.dumps({"payload": payload}).encode("utf-8")
    start = json.loads(
        _request(f"{HF_SPACE_URL}/gradio_api/call/v2/predict", data=start_body)
    )
    event_id = start.get("event_id")
    if not event_id:
        raise RuntimeError("Hugging Face tidak mengembalikan event ID.")
    stream = _request(
        f"{HF_SPACE_URL}/gradio_api/call/predict/{quote(event_id, safe='')}",
        timeout=30,
    )
    result = _parse_sse(stream)
    if not isinstance(result, dict):
        raise RuntimeError("Format hasil prediksi Hugging Face tidak valid.")
    return result


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
        self._json(
            200,
            {
                "status": "ready" if HF_TOKEN else "configuration-required",
                "backend": "huggingface-space",
                "authenticated": bool(HF_TOKEN),
            },
        )

    def do_POST(self):
        if not HF_TOKEN:
            self._json(
                503,
                {
                    "error": "HF_TOKEN belum dikonfigurasi di Vercel.",
                    "code": "hf-token-missing",
                },
            )
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16_384:
                self._json(400, {"error": "Ukuran input tidak valid."})
                return
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError("Input harus berupa object JSON.")
            self._json(200, predict(payload))
        except (json.JSONDecodeError, ValueError) as exc:
            self._json(400, {"error": str(exc)})
        except HTTPError as exc:
            self._json(502, {"error": f"Hugging Face merespons HTTP {exc.code}."})
        except (URLError, TimeoutError):
            self._json(504, {"error": "Hugging Face tidak dapat dihubungi."})
        except RuntimeError as exc:
            self._json(503, {"error": str(exc)})
        except Exception:
            self._json(500, {"error": "Prediksi model gagal diproses."})
