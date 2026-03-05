from fastapi import Header, HTTPException

from .config import settings


def require_token(x_api_token: str | None = Header(default=None)):
    # Simple dev auth for milestone; replace with proper auth later.
    print(x_api_token)
    print(settings.api_token)
    if x_api_token != settings.api_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
