PRAMAAN KYC — HACKATHON PROTOTYPE
================================

QUICK START — HOST LAPTOP (Windows x64)
1. Copy the entire release/SmartKYC folder to a writable location.
2. Install Ollama: https://ollama.com/download/windows
3. Double-click setup.bat. It checks Ollama and downloads qwen2.5vl:3b
   if absent (about 3.2 GB; internet needed for this initial download).
   Alternatively open a terminal and run: ollama pull qwen2.5vl:3b
4. Double-click SmartKYC_Server.exe or start_server.bat.
5. Your browser opens the dashboard. Keep the server console open.
   It prints the local address and available WiFi/LAN addresses.
6. Load a sample and click Extract & assess for REAL Ollama OCR.

This PC already has the chosen Ollama model downloaded during development.
Another host must install Ollama and download the model once.
After the download, document processing runs locally, without a cloud API.

SECOND PC — CLIENT ONLY
1. Copy the packaged SmartKYC folder (or just SmartKYC_Client.exe).
2. Run SmartKYC_Client.exe; enter the host's displayed IP:port.
3. Click Connect. The browser opens the complete upload/review dashboard.
4. Upload a document and submit details. AI processing happens on the host.
The client does NOT need Python, Ollama, or the vision model.
The EXE is a lightweight connection launcher; the actual interface runs in
the system browser. A browser alone can also visit http://HOST-IP:8000.
Both PCs must be on the same network. Guest WiFi may isolate devices.
If Windows asks, allow the host on your trusted PRIVATE network only.
No cloud deployment, Docker, Android build, or automatic discovery needed.

FICTIONAL SAMPLE BUILDER
Run SmartKYC_SampleBuilder.exe or start_sample_builder.bat.
Enter fictional fields, choose Standard / Enhanced / Manual, and submit.
It creates a clearly labelled PNG and matching JSON inside data/demo.
Use those fields and the PNG in the dashboard. Never enter real government
numbers or real personal data into this utility.

CONFIGURATION
Edit config.json beside the server EXE, then restart the server:
  server_port: 8000
  ollama_url: http://127.0.0.1:11434
  ollama_model: qwen2.5vl:3b
  ocr_timeout_seconds: 240
  standard_max: 35
  enhanced_max: 70
  max_upload_mb: 10
  open_browser: true
The client remembers its last host in this same file if it is writable.
No user-specific paths or fixed LAN IP addresses are baked into the app.

DEMO
See DEMO.txt for a short presentation script.
Three visibly fictional sample documents are in data/demo.
Sample buttons fill both the applicant form and the document selection.
Extract & assess always calls Ollama. There is NO silent OCR fallback.
Run labelled rehearsal explicitly skips OCR and uses cached sample fields;
the case is marked REHEARSAL / CACHED FIELDS in results and history.
The expected scores with these samples are 1 (Standard), 43 (Enhanced),
and 95 (Manual). Live OCR differences can change scores.

WHAT IS IMPLEMENTED
- JPG, PNG and WebP upload, image decoding, resizing, and EXIF orientation.
- Ollama vision -> structured JSON: name, DOB, number, address, type, expiry.
- Normalized name/address comparisons and parsed DOB comparisons.
- Basic document-number format and expiry checks; no issuer lookup.
- A logistic regression trained on 5,000 generated synthetic records.
- Identity, document, supplied device, behavior and history features.
- Risk score = 100 * sigmoid(intercept + coefficient contributions).
- Contributions shown in log-odds; they are NOT additive score points.
- Configurable routing with clear policy overrides: DOB conflict -> Manual;
  incomplete baseline checks can never receive the Standard route.
- Reviewer name + note required for approve / enhanced request / flag.
- Local SQLite case history, source image, review log and JSON export.
- Reassessment creates a NEW linked case and preserves the original.

HONEST LIMITATIONS
This is a prototype, not certified KYC or proven fraud detection.
The model's labels come from a hand-designed formula plus random sampling.
The held-out metrics in ml/model.json describe synthetic data only.
They do not establish accuracy on actual applicants or fraudulent IDs.
The ocr_confidence dataset column is a field-completeness proxy, NOT a
measured or calibrated OCR confidence probability. UI calls it completeness.
Device, behavioral, anomaly, duplicate and history signals are supplied
demo inputs, not automatic tracking, forensic detection or issuer checks.
Normalization is simple exact comparison after punctuation/case removal.
Review original evidence where spelling, date format or address differs.
PAN/Aadhaar document types allow absent expiry; other types with absent
expiry require further evidence. Number checking is generic, not official.
The local host uses HTTP, no login, and an unencrypted local case database.
Use fictional samples on a trusted demo LAN. Anyone who can reach this
prototype host can access cases and reviewer actions. No production claims.
The reviewer name is a label, not authenticated identity.
Only the most recent 100 cases appear in the queue; older records remain
in the database. Case decisions persist until the database is removed.

TROUBLESHOOTING
- Ollama missing: install it, open Ollama, then run setup.bat.
- Model missing: ollama pull qwen2.5vl:3b (or your configured model).
- Model too slow / memory error: close heavy apps; keep the document sharp
  and tightly cropped; check the Ollama console. Increase timeout if needed.
  A different vision model can be selected in config.json.
- First OCR call loads the model; allow up to four minutes by default.
- Wrong host: use the current address from the server console, not an old
  IP. Check same WiFi, firewall and port. Client reports connection errors.
- Port in use: close the previous host or change server_port.
- Missing files: copy the WHOLE packaged SmartKYC folder, not server EXE only.
- Server cannot save: move the folder out of a read-only/protected directory.
- OCR failed / unreadable fields: upload a clear full document and retry.
  The app reports the error and does not invent an OCR result.
- Local records: data/cases.sqlite3. To start a fresh demo, stop the server
  and MOVE this file to a backup location, then restart.

DEVELOPMENT (only on a development PC; not needed on client/host EXE PCs)
From the repository directory:
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -r SmartKYC\requirements.txt
  .venv\Scripts\python.exe SmartKYC\server.py
  .venv\Scripts\python.exe -m unittest discover -s SmartKYC\tests -v
To regenerate the synthetic dataset/model:
  .venv\Scripts\python.exe SmartKYC\train_model.py
To regenerate fictional sample cards:
  .venv\Scripts\python.exe SmartKYC\make_demo.py
To package on Windows:
  powershell -ExecutionPolicy Bypass -File SmartKYC\build.ps1
Build outputs are in release/SmartKYC. Build never copies the case database.
Packaging and local EXE smoke tests were performed on this Windows PC.
A separate physical clean Windows PC was not available for validation.

SIMPLE API
GET /api/health                    Ollama/model health and thresholds
GET /api/samples                   Sample applicant/field fixtures
POST /api/ocr                      {image: base64} -> extracted fields
POST /api/verify (or /verify)       {image: base64, applicant, signals}
GET /api/cases                     Latest 100 case summaries
GET /api/cases/CASE_ID              Full case with image and review log
POST /api/review                   {id, action, reviewer, note}
POST /api/rehearsal                {scenario: standard|enhanced|manual}

REFERENCE ALIGNMENT
Built from the supplied Smart KYC problem statement and Pramaan PPT.
Kept: local host, OCR, checks, synthetic ML, explanation, adaptive policy,
reviewer decisions, evidence and reassessment.
Simplified: vanilla HTML/CSS/JS instead of React; one Python HTTP host
instead of a framework stack; direct Ollama vision instead of Tesseract.
Used the user's requested inclusive 0-35 / 36-70 / 71-100 thresholds in
place of the PPT's illustrative <30 / 30-69 / 70+ values.
Deferred: Android, face matching, HTTPS/roles/encryption, production fraud
detection. The presentation's illustrative 18/48/82 are not measured scores.
The original reference PPT was not modified.

MODEL / API REFERENCES
https://ollama.com/library/qwen2.5vl:3b
https://docs.ollama.com/api/chat
Qwen2.5-VL 3B was selected as one practical local vision model supporting
document understanding and structured output. No agent/RAG/vector store.
