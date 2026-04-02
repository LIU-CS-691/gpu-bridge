import httpx
import typer

from .config import load_config

app = typer.Typer(help="GPUBridge Worker CLI")


@app.command()
def register(name: str = typer.Option("Unnamed GPU")):
    """Register this machine as a worker."""
    cfg = load_config()
    with httpx.Client(
        base_url=cfg["server"], headers={"X-API-Token": cfg["token"]}, timeout=30.0
    ) as c:
        r = c.post("/workers/register", json={"name": name})
        r.raise_for_status()
        worker = r.json()
        typer.echo(f"Registered worker_id={worker['id']}")
