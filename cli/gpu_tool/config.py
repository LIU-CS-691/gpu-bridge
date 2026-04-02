import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from project root if present
env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings(BaseModel):
    GPU_TOOL_SERVER: str = os.getenv("GPU_TOOL_SERVER", "http://localhost:8000")
    GPU_TOOL_TOKEN: str = os.getenv("GPU_TOOL_TOKEN", "devtoken")


settings = Settings()
