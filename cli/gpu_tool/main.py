import typer

from .api import client
from .config import settings

app = typer.Typer(help="GPUBridge CLI")


@app.command()
def login(token: str = typer.Option(...)):
    """Save controller server + token."""
    if token == settings.GPU_TOOL_TOKEN:
        typer.echo("Login successfull..")
    else:
        typer.echo("Invalid token. Please use a valid token")


@app.command()
def health():
    """Check controller health."""
    with client() as c:
        r = c.get("/health")
        r.raise_for_status()
        typer.echo(r.json())


@app.command("workers")
def workers_list():
    """List registered workers."""
    with client() as c:
        r = c.get("/workers")
        r.raise_for_status()
        for w in r.json():
            typer.echo(f'{w["name"]} - ID: {w["id"]}')


@app.command("job-create")
def job_create(
    gpu_id: str = typer.Option(..., "--gpu-id"),
    image: str = typer.Option("hello-image"),
    cmd: str = typer.Option("echo hello", "--cmd"),
):
    """Create a dummy job assigned to a worker."""
    with client() as c:
        r = c.post("/jobs", json={"worker_id": gpu_id,
                   "image": image, "command": cmd})
        r.raise_for_status()
        typer.echo(r.json())


@app.command("job-get")
def job_get(job_id: str = typer.Option(..., "--job-id")):
    """Get job status."""
    with client() as c:
        r = c.get(f"/jobs/{job_id}")
        r.raise_for_status()
        typer.echo(r.json())
