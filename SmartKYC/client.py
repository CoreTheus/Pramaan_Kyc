"""Tiny Windows connector: the host serves the complete client interface."""
import json
import sys
import threading
import urllib.request
import urllib.error
import webbrowser
from urllib.parse import urlsplit


def host_url(value):
    value = value.strip()
    if not value:
        raise ValueError("Enter the host address shown in the server window.")
    url = urlsplit(value if "://" in value else "http://" + value)
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
        raise ValueError("Enter just a host IP or hostname and port, for example HOST-IP:8000.")
    port = url.port or 8000
    host = f"[{url.hostname}]" if ":" in url.hostname else url.hostname
    return f"{url.scheme}://{host}:{port}"


def check_host(value):
    url = host_url(value)
    try:
        with urllib.request.urlopen(url + "/api/health", timeout=5) as response:
            data = json.load(response)
        if data.get("app") != "Pramaan KYC":
            raise ValueError("This address is not a Pramaan KYC host.")
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Cannot reach the host. Check its IP and port, the server window, WiFi, and Windows Firewall.") from exc
    return url, data


def main():
    import html
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from settings import ROOT
    saved = ""
    try:
        saved = json.loads((ROOT / "config.json").read_text()).get("client_host", "")
    except (OSError, ValueError):
        pass
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pramaan | Connect to host</title>
<style>*{box-sizing:border-box}body{background:#f5f5ef;color:#223731;font:14px 'Segoe UI',sans-serif;display:grid;place-items:center;min-height:95vh;margin:0}main{width:480px;max-width:94vw;background:#fff;border:1px solid #dce2d5;border-top:4px solid #244e41;padding:38px;border-radius:7px}.brand{font:36px Georgia,serif;color:#244e41;margin:0 0 8px}small{font-size:9px;letter-spacing:2px;color:#718267}h1{font:25px Georgia,serif;margin-top:30px}p{font-size:12px;line-height:1.7;color:#73806c}label{font-size:12px;display:block;margin:25px 0 8px}input{width:100%;border:1px solid #ccd7c2;border-radius:4px;padding:13px;font:14px 'Segoe UI',sans-serif;color:#244e41}button{width:100%;border:0;border-radius:4px;background:#244e41;color:white;padding:14px;cursor:pointer;margin-top:15px;font-size:12px}button:disabled{opacity:.5}#status{min-height:35px}footer{border-top:1px solid #e5e9df;padding-top:16px;margin-top:20px;font-size:10px;color:#7a8870}</style>
<main><div class="brand">pramaan</div><small>LOCAL KYC / PC CLIENT</small><h1>Connect to your verification host.</h1><p>Enter the address displayed on the host laptop.<br>Both computers should be on the same WiFi or LAN.</p><form id="connect"><label for="host">Host IP or hostname, with port</label><input id="host" placeholder="HOST-IP:8000" value="SAVED_HOST" autocomplete="off" required autofocus><button id="button">Connect & open verification desk →</button></form><p id="status" role="status">The client does not need Ollama or Python.</p><footer>Hackathon prototype · Local document processing</footer></main>
<script>document.getElementById('connect').onsubmit=async e=>{e.preventDefault();const b=document.getElementById('button'),s=document.getElementById('status');b.disabled=true;s.textContent='Checking host…';try{const r=await fetch('/connect',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:document.getElementById('host').value}),signal:AbortSignal.timeout(10000)});const d=await r.json();if(!r.ok)throw Error(d.error);s.textContent='Connected. Opening your verification desk…';location.href=d.url;}catch(e){s.textContent=e.message==='Failed to fetch'?'Connection page closed. Launch SmartKYC_Client.exe again.':e.message;b.disabled=false;}};</script></html>'''.replace('SAVED_HOST', html.escape(saved, quote=True)).encode('utf-8')

    class Connector(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 4096:
                    raise ValueError("Enter a valid host address.")
                body = json.loads(self.rfile.read(length))
                url, _ = check_host(str(body.get("host", "")))
                try:
                    file = ROOT / "config.json"
                    config = json.loads(file.read_text()) if file.exists() else {}
                    config["client_host"] = url
                    file.write_text(json.dumps(config, indent=2))
                except (OSError, ValueError):
                    pass
                data, status = {"url":url}, 200
            except (ValueError, TypeError, AttributeError) as exc:
                data, status = {"error":str(exc)}, 400
            result = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(result)))
            self.end_headers()
            self.wfile.write(result)
            if status == 200:
                timer = threading.Timer(2, self.server.shutdown)
                timer.daemon = True
                timer.start()

    port = int(sys.argv[sys.argv.index("--port")+1]) if "--port" in sys.argv else 0
    with ThreadingHTTPServer(("127.0.0.1", port), Connector) as server:
        url = f"http://127.0.0.1:{server.server_port}"
        if "--no-browser" not in sys.argv:
            webbrowser.open(url)
        timer = threading.Timer(600, server.shutdown)
        timer.daemon = True
        timer.start()
        server.serve_forever()
        timer.cancel()


if __name__ == "__main__":
    if "--check-url" in sys.argv:
        try:
            url, state = check_host(sys.argv[-1])
            print(json.dumps({"url": url, "state": state}))
        except ValueError as exc:
            print(str(exc))
            sys.exit(1)
    else:
        main()
