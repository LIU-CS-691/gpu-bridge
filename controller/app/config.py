import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "")
    bootstrap_token: str = os.getenv("BOOTSTRAP_TOKEN", "")
    server_url: str = os.getenv("SERVER_URL", "http://localhost:8000")


settings = Settings()

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is required. Set it in .env or as an environment variable."
    )

if not settings.bootstrap_token:
    raise RuntimeError(
        "BOOTSTRAP_TOKEN is required. Set it in .env or as an environment variable."
    )
