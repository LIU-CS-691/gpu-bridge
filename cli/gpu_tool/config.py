import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path)

CONFIG_FILE = Path.home() / ".gpu-tool.json"


def _load_saved() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(server: str, token: str):
    CONFIG_FILE.write_text(json.dumps({"server": server, "token": token}, indent=2))


class Settings(BaseModel):
    GPU_TOOL_SERVER: str = "http://localhost:8000"
    GPU_TOOL_TOKEN: str = "devtoken"


def _build_settings() -> Settings:
    saved = _load_saved()
    return Settings(
        GPU_TOOL_SERVER=os.getenv("GPU_TOOL_SERVER", saved.get("server", "http://localhost:8000")),
        GPU_TOOL_TOKEN=os.getenv("GPU_TOOL_TOKEN", saved.get("token", "devtoken")),
    )


settings = _build_settings()
