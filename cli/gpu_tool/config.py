import json
import os
from pathlib import Path

CONFIG_FILE = Path.home() / ".gpu-tool.json"


def _load_saved() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(server: str, token: str):
    CONFIG_FILE.write_text(json.dumps({"server": server, "token": token}, indent=2))


class Settings:
    def __init__(self, GPU_TOOL_SERVER: str, GPU_TOOL_TOKEN: str):
        self.GPU_TOOL_SERVER = GPU_TOOL_SERVER
        self.GPU_TOOL_TOKEN = GPU_TOOL_TOKEN


def _build_settings() -> Settings:
    saved = _load_saved()
    return Settings(
        GPU_TOOL_SERVER=saved.get("server", os.getenv("GPU_TOOL_SERVER", "http://localhost:8000")),
        GPU_TOOL_TOKEN=saved.get("token", os.getenv("GPU_TOOL_TOKEN", "devtoken")),
    )


settings = _build_settings()
