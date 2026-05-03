import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

env_path = Path.cwd() / ".env"
if env_path.exists():
    load_dotenv(env_path, override=False)


class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL", "")
    api_token: str = os.getenv("API_TOKEN", "devtoken")


settings = Settings()

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is required. Set it in .env or as an environment variable."
    )
