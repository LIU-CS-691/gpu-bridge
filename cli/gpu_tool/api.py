import httpx

from .config import settings


def client():
    return httpx.Client(
        base_url=settings.GPU_TOOL_SERVER,
        headers={"X-API-Token": settings.GPU_TOOL_TOKEN},
        timeout=10.0,
    )
