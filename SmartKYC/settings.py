import json
import sys
from pathlib import Path

ROOT = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


def load_config():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    if not 0 <= config["standard_max"] < config["enhanced_max"] < 100:
        raise ValueError("config.json: thresholds must satisfy 0 <= standard_max < enhanced_max < 100")
    if not 1 <= int(config["server_port"]) <= 65535:
        raise ValueError("config.json: server_port must be between 1 and 65535")
    return config
