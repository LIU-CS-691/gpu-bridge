import base64
import os
from pathlib import Path

from dotenv import load_dotenv

for p in [Path.cwd() / ".env", Path.cwd().parent / ".env"]:
    if p.exists():
        load_dotenv(p)
        break


def _decode_invite(token: str) -> tuple[str, str]:
    decoded = base64.urlsafe_b64decode(token).decode()
    server, key = decoded.split("|", 1)
    return server, key


def load_config() -> dict:
    invite = os.getenv("GPU_BRIDGE_INVITE")
    if invite:
        server, token = _decode_invite(invite)
    else:
        server = os.getenv("GPU_TOOL_SERVER")
        token = os.getenv("GPU_TOOL_TOKEN")
        if not server or not token:
            raise RuntimeError("Set GPU_BRIDGE_INVITE or both GPU_TOOL_SERVER and GPU_TOOL_TOKEN.")
    return {
        "server": server,
        "token": token,
        "worker_name": os.getenv("GPU_WORKER_NAME", "dev-worker"),
    }
