# Pramaan KYC prototype

Run the packaged [server](release/SmartKYC/SmartKYC_Server.exe) or [client](release/SmartKYC/SmartKYC_Client.exe).

- Portable application: `release/SmartKYC/` — copy the entire folder.
- Source code: `SmartKYC/`.
- Setup and limitations: [README](SmartKYC/README.txt).
- Presentation walkthrough: [DEMO](SmartKYC/DEMO.txt).

Host: Ollama vision → extracted fields → checks → synthetic logistic risk model → adaptive routing → reviewer decision.

The source runs with `.venv\Scripts\python.exe SmartKYC\server.py`.
