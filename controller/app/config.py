import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env from project root if present
env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Settings(BaseModel):
    database_url: str = os.getenv(
        "DATABASE_URL", "sqlite+pysqlite:///./dev.db")
    api_token: str = os.getenv("API_TOKEN", "devtoken")


settings = Settings()
