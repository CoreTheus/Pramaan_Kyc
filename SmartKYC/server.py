"""Small LAN HTTP server. Start with: python server.py"""
import base64
import binascii
import json
import logging
import math
import mimetypes
import socket
import sqlite3
import sys
import threading
import uuid
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from settings import ROOT, load_config
from ocr import OCRError, extract, health, prepare_image
from verification import verify
from risk import predict
import cases

CONFIG = load_config()
OCR_LOCK = threading.Lock()


def validate_inputs(data):
    applicant, signals = data.get("applicant", {}), data.get("signals", {})
    if not isinstance(applicant, dict) or not isinstance(signals, dict):
        raise ValueError("Applicant and signals must be objects")
    applicant = {k: str(applicant.get(k) or "").strip()[:600] for k in ("name", "dob", "address")}
    if not applicant["name"] or not applicant["dob"]:
        raise ValueError("Enter applicant name and date of birth before verification.")
    from verification import parse_date
    if not parse_date(applicant["dob"]) or parse_date(applicant["dob"]) > datetime.now().date():
        raise ValueError("Enter a valid date of birth that is not in the future.")
    clean = {}
    for key in ("device_known", "document_anomaly", "duplicate_identity"):
        val = signals.get(key, False)
        if not isinstance(val, bool):
            raise ValueError(f"{key} must be true or false")
        clean[key] = val
    for key, maximum in (("failed_attempts", 5), ("previous_flags", 3), ("behavior_score", 100)):
        val = float(signals.get(key, 0))
        if not math.isfinite(val) or not 0 <= val <= maximum or val != int(val):
            raise ValueError(f"{key} must be a whole number between 0 and {maximum}")
        clean[key] = int(val)
    return applicant, clean


def create_case(applicant, fields, signals, image, source, parent_id=None):
    if parent_id and not cases.get(parent_id):
        raise ValueError("Original case not found.")
    result = verify(applicant, fields, signals)
    case = {"id": uuid.uuid4().hex[:12].upper(), "created_at": datetime.now(timezone.utc).isoformat(),
            "applicant": applicant, "fields": fields, "signals": signals, "source": source,
            "image": base64.b64encode(image).decode(), "verification": result,
            "risk": predict(result["features"], CONFIG, result), "status": "Awaiting review", "reviews": [],
            "parent_id": parent_id}
    cases.save(case)
    return case


class Handler(BaseHTTPRequestHandler):
    def reply(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == "/api/health":
                return self.reply({"app": "Pramaan KYC", "ollama": health(CONFIG), "port": CONFIG["server_port"],
                                   "thresholds": {"standard_max": CONFIG["standard_max"], "enhanced_max": CONFIG["enhanced_max"]}})
            if path == "/api/cases":
                return self.reply(cases.list_cases())
            if path.startswith("/api/cases/"):
                case = cases.get(path.split("/")[-1])
                return self.reply(case if case else {"error": "Case not found"}, 200 if case else 404)
            if path == "/api/samples":
                return self.reply(json.loads((ROOT / "data/demo/cases.json").read_text()))
            static = {"/": ROOT / "ui/index.html", "/app.js": ROOT / "ui/app.js", "/style.css": ROOT / "ui/style.css"}
            for name in ("standard", "enhanced", "manual"):
                static[f"/samples/{name}.png"] = ROOT / f"data/demo/{name}.png"
            if path in static:
                file = static[path]
                body = file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(str(file))[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
                return
            self.reply({"error": "Not found"}, 404)
        except (OSError, sqlite3.Error):
            self.reply({"error": "Cannot read local files. Keep config, ui, ml and data folders beside the server."}, 500)

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", 0))
            if size <= 0 or size > CONFIG["max_upload_mb"] * 1024 * 1024 * 1.4:
                return self.reply({"error": "Upload is empty or too large (10 MB maximum)."}, 413)
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Request must be an object")
            if self.path in ("/api/ocr", "/api/verify", "/verify"):
                applicant, signals = validate_inputs(data) if self.path != "/api/ocr" else ({}, {})
                raw = base64.b64decode(data.get("image", ""), validate=True)
                if len(raw) > CONFIG["max_upload_mb"] * 1024 * 1024:
                    raise ValueError("Image exceeds the upload limit.")
                image = prepare_image(raw)
                if not OCR_LOCK.acquire(blocking=False):
                    return self.reply({"error": "Host is processing another document. Please retry shortly."}, 409)
                try:
                    fields = extract(image, CONFIG)
                finally:
                    OCR_LOCK.release()
                if self.path == "/api/ocr":
                    return self.reply({"fields": fields, "source": "live_ollama"})
                return self.reply(create_case(applicant, fields, signals, image, "live_ollama", data.get("parent_id")))
            if self.path == "/api/rehearsal":
                key = data.get("scenario")
                demos = json.loads((ROOT / "data/demo/cases.json").read_text())
                if key not in demos:
                    raise ValueError("Choose a valid rehearsal scenario.")
                demo = demos[key]
                image = prepare_image((ROOT / "data/demo" / demo["image"]).read_bytes())
                return self.reply(create_case(demo["applicant"], demo["fields"], demo["signals"], image, "rehearsal_cached_fields"))
            if self.path == "/api/review":
                if data.get("action") not in ("Approved", "Enhanced requested", "Flagged for manual review"):
                    raise ValueError("Choose a review action.")
                note, reviewer = str(data.get("note", "")).strip(), str(data.get("reviewer", "")).strip()
                if not note or not reviewer or len(note) > 2000 or len(reviewer) > 80:
                    raise ValueError("Enter your name and a review note (maximum 2,000 characters).")
                return self.reply(cases.review(str(data.get("id", "")), data["action"], note, reviewer))
            self.reply({"error": "Not found"}, 404)
        except OCRError as exc:
            self.reply({"error": str(exc)}, 422)
        except (ValueError, TypeError, binascii.Error) as exc:
            self.reply({"error": str(exc) or "Invalid request. Check the fields and image."}, 400)
        except (OSError, sqlite3.Error, KeyError):
            logging.exception("Request failed")
            self.reply({"error": "The host could not complete this request. Check its console and local data files."}, 500)


def main():
    try:
        server = ThreadingHTTPServer(("0.0.0.0", CONFIG["server_port"]), Handler)
    except OSError as exc:
        print(f"Cannot start server: {exc}. Change server_port in config.json or close the other server.")
        input("Press Enter to close.")
        return
    status = health(CONFIG)
    print("PRAMAAN KYC | Local prototype")
    print(status["message"])
    print(f"Local: http://127.0.0.1:{CONFIG['server_port']}")
    try:
        for address in sorted(set(socket.gethostbyname_ex(socket.gethostname())[2])):
            if not address.startswith("127."):
                print(f"WiFi / LAN: http://{address}:{CONFIG['server_port']}")
    except OSError:
        pass
    print("Keep this window open. Ctrl+C stops the host.", flush=True)
    if CONFIG.get("open_browser") and "--no-browser" not in sys.argv:
        threading.Timer(1, lambda: webbrowser.open(f"http://127.0.0.1:{CONFIG['server_port']}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    if "--setup" in sys.argv:
        from setup_host import setup
        sys.exit(setup(CONFIG))
    else:
        main()
