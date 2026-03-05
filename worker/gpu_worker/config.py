import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from repo root or working directory
for p in [Path.cwd() / ".env", Path.cwd().parent / ".env"]:
    if p.exists():
        load_dotenv(p)
        break


def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"Missing required env var: {name}. "
            f"Create a .env file or export the variable."
        )
    return val


def load_config() -> dict:
    return {
        "server": require_env("GPU_TOOL_SERVER"),
        "token": require_env("GPU_TOOL_TOKEN"),
        "worker_name": os.getenv("GPU_WORKER_NAME", "dev-worker"),
    }