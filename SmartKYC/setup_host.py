"""Used by the frozen server's --setup command."""
import os
import shutil
import subprocess
import time
from pathlib import Path
from ocr import health


def setup(config):
    print("PRAMAAN | Host setup\n")
    executable = shutil.which("ollama")
    if not executable:
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe"
        if candidate.exists():
            executable = str(candidate)
    if not executable:
        print("Install Ollama from https://ollama.com/download/windows, then run setup.bat again.")
        return 1
    if not health(config)["reachable"]:
        print("Starting Ollama locally...")
        subprocess.Popen([executable, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(20):
            time.sleep(.5)
            if health(config)["reachable"]:
                break
    status = health(config)
    if not status["reachable"]:
        print(status["message"])
        return 1
    if not status["ready"]:
        print(f"Downloading {config['ollama_model']} (default model is about 3.2 GB).")
        if subprocess.call([executable, "pull", config["ollama_model"]]) != 0:
            print("Download failed. Check your connection and run setup.bat again.")
            return 1
    print("Ollama ready. Model ready. Run start_server.bat.")
    return 0
