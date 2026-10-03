"""Small local browser utility for generating clearly fictional demo IDs."""
import html
import io
import json
import threading
import uuid
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image, ImageDraw, ImageFont
from settings import ROOT


def font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def make_image(fields, file_path):
    image = Image.new("RGB", (1400, 850), "#faf8f2")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1400, 130), fill="#193e37")
    draw.text((60, 37), "PRAMAAN / PROTOTYPE ID", font=font(44), fill="white")
    draw.text((60, 157), "FICTIONAL SAMPLE - NOT A VALID IDENTITY DOCUMENT", font=font(29), fill="#a1392a")
    items = (("NAME", "name"), ("DATE OF BIRTH", "dob"), ("DOCUMENT NUMBER", "document_number"),
             ("ADDRESS", "address"), ("EXPIRY DATE", "expiry_date"))
    for i, (label, key) in enumerate(items):
        y = 235 + i * 105
        draw.text((60, y), label, font=font(21), fill="#54605b")
        draw.text((60, y + 31), fields[key] or "NOT SHOWN", font=font(36), fill="#152c26")
    draw.text((60, 785), "Synthetic hackathon sample | No government affiliation", font=font(25), fill="#63736b")
    image.save(file_path)


PAGE = """<!doctype html><html><head><meta charset='utf-8'><title>Pramaan Sample Builder</title>
<style>body{margin:0;background:#f5f5ef;color:#223731;font:14px Segoe UI,Arial}main{max-width:620px;margin:35px auto;background:white;border:1px solid #dce2d5;border-top:4px solid #244e41;border-radius:7px;padding:30px}h1{font:30px Georgia,serif;color:#244e41;margin:0 0 6px}p{color:#737c73;font-size:12px;line-height:1.6}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}label{font-size:11px;font-weight:600}input,textarea,select{display:block;width:100%;box-sizing:border-box;margin-top:6px;padding:10px;border:1px solid #d2dccb;border-radius:4px;font:12px Segoe UI}textarea{resize:vertical}.wide{grid-column:1/-1}button{width:100%;margin-top:20px;padding:13px;background:#244e41;color:#fff;border:0;border-radius:4px;cursor:pointer}.hint{font-size:10px;color:#8a6b2d;background:#fff8e8;padding:10px}.success{background:#edf3e6;color:#4c7248;padding:14px;margin-top:16px;font-size:12px}.success a{color:#244e41}</style></head>
<body><main><h1>pramaan</h1><p>FICTIONAL SAMPLE BUILDER / for prototype rehearsals only</p><p class='hint'>Every generated card is visibly marked fictional. Do not use government ID numbers or real personal data.</p>
<form method='post' action='/generate'><div class='grid'>
<label>Scenario<select name='scenario'><option value='standard'>Standard — matching evidence</option><option value='enhanced'>Enhanced — identity mismatch</option><option value='manual'>Manual — expired / conflicting evidence</option></select></label>
<label>Document type<input name='document_type' value='Prototype ID' maxlength='60' required></label>
<label>Full name<input name='name' value='Aarav Sharma' maxlength='100' required></label>
<label>Date of birth<input name='dob' value='1998-04-12' maxlength='20' required></label>
<label>Document number<input name='document_number' value='DEMO482901' maxlength='30' required></label>
<label>Expiry date<input name='expiry_date' value='2032-12-31' maxlength='20' required></label>
<label class='wide'>Address<textarea name='address' rows='2' maxlength='250' required>24 Lake Road, New Delhi 110001</textarea></label>
</div><button>Generate fictional sample</button></form></main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_html(self, body, status=200):
        body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            return self.send_html(PAGE)
        if path.startswith("/samples/"):
            file = ROOT / "data/demo" / Path(path.removeprefix("/samples/")).name
            if file.suffix.lower() == ".png" and file.exists():
                body = file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        self.send_html("Not found", 404)

    def do_POST(self):
        if urlsplit(self.path).path != "/generate":
            return self.send_html("Not found", 404)
        length = min(int(self.headers.get("Content-Length", 0)), 10000)
        values = {key: value[0].strip() for key, value in parse_qs(self.rfile.read(length).decode()).items()}
        required = ("name", "dob", "document_number", "address", "document_type", "expiry_date")
        if any(not values.get(key) for key in required) or values.get("scenario") not in ("standard", "enhanced", "manual"):
            return self.send_html("Please fill every field.", 400)
        fields = {key: values[key][:600] for key in required}
        scenario = values["scenario"]
        if scenario == "enhanced":
            applicant = {"name": "Arjun Sharma", "dob": fields["dob"], "address": fields["address"]}
            signals = {"device_known": False, "failed_attempts": 1, "previous_flags": 0, "duplicate_identity": False, "document_anomaly": False, "behavior_score": 0}
        elif scenario == "manual":
            applicant = {"name": fields["name"], "dob": "1995-08-21", "address": fields["address"]}
            fields["expiry_date"] = "2023-12-31"
            signals = {"device_known": False, "failed_attempts": 2, "previous_flags": 0, "duplicate_identity": False, "document_anomaly": False, "behavior_score": 0}
        else:
            applicant = {"name": fields["name"], "dob": fields["dob"], "address": fields["address"]}
            signals = {"device_known": True, "failed_attempts": 0, "previous_flags": 0, "duplicate_identity": False, "document_anomaly": False, "behavior_score": 0}
        folder = ROOT / "data/demo"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = f"custom_{scenario}_{stamp}_{uuid.uuid4().hex[:4]}"
        image_file = folder / f"{stem}.png"
        make_image(fields, image_file)
        json_file = folder / f"{stem}.json"
        json_file.write_text(json.dumps({"applicant": applicant, "fields": fields, "signals": signals, "image": image_file.name}, indent=2), encoding="utf-8")
        href = html.escape(f"/samples/{image_file.name}")
        result = f"<html><body style='font:14px Segoe UI;max-width:700px;margin:30px auto;color:#223731'><h2>Sample created</h2><p><b>{html.escape(image_file.name)}</b></p><img style='max-width:100%' src='{href}'><p>JSON saved beside the image in <code>data/demo</code>.</p><p>Copy the image into the KYC dashboard and enter the generated applicant details.</p><a href='/'>Create another sample</a></body></html>"
        self.send_html(result)


def main():
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        url = f"http://127.0.0.1:{server.server_port}"
        webbrowser.open(url)
        print(f"Sample Builder: {url}")
        threading.Timer(900, server.shutdown).start()
        server.serve_forever()


if __name__ == "__main__":
    main()
