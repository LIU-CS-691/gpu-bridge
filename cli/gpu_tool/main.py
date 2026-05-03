import time

import typer

from .api import client
from .config import save_config, settings

app = typer.Typer(help="GPUBridge CLI")

FOLLOW_POLL_INTERVAL = 1


@app.command()
def login(
    server: str = typer.Option(settings.GPU_TOOL_SERVER, "--server"),
    token: str = typer.Option(..., "--token", prompt=True, hide_input=True),
):
    """Save controller server + token to ~/.gpu-tool.json."""
    save_config(server, token)
    typer.echo(f"Credentials saved for {server}")


@app.command()
def health():
    """Check controller health."""
    with client() as c:
        r = c.get("/health")
        r.raise_for_status()
        typer.echo(r.json())


@app.command("workers")
def workers_list():
    """List registered workers with online/offline status and GPU info."""
    with client() as c:
        r = c.get("/workers")
        r.raise_for_status()
        for w in r.json():
            status = w.get("status", "unknown")
            line = f'[{status.upper()}] {w["name"]} - ID: {w["id"]}'
            gpus = w.get("gpu_info")
            if gpus:
                gpu_strs = [f'{g["name"]} ({g["memory_total_mb"]}MB)' for g in gpus]
                line += f' — GPUs: {", ".join(gpu_strs)}'
            else:
                line += " — No GPUs"
            typer.echo(line)


@app.command("jobs")
def jobs_list(
    gpu_id: str = typer.Option(None, "--gpu-id"),
    status: str = typer.Option(None, "--status"),
):
    """List jobs with optional filters."""
    with client() as c:
        params = {}
        if gpu_id:
            params["worker_id"] = gpu_id
        if status:
            params["status"] = status
        r = c.get("/jobs", params=params)
        r.raise_for_status()
        jobs = r.json()
        if not jobs:
            typer.echo("No jobs found.")
            return
        for j in jobs:
            worker = j["worker_id"] or "unassigned"
            prio = f' P{j["priority"]}' if j.get("priority") else ""
            typer.echo(f'[{j["status"]}{prio}] {j["id"]} — worker:{worker} image:{j["image"]}')


@app.command("job-create")
def job_create(
    gpu_id: str = typer.Option(None, "--gpu-id", help="Worker ID. Omit for auto-assignment."),
    image: str = typer.Option("hello-image"),
    cmd: str = typer.Option("echo hello", "--cmd"),
    priority: int = typer.Option(0, "--priority", "-p", help="Priority 0-10, higher runs first"),
):
    """Create a job. Omit --gpu-id to let the controller auto-assign."""
    with client() as c:
        payload = {"image": image, "command": cmd, "priority": priority}
        if gpu_id:
            payload["worker_id"] = gpu_id
        r = c.post("/jobs", json=payload)
        r.raise_for_status()
        j = r.json()
        status_msg = f'{j["status"]}'
        if j.get("worker_id"):
            status_msg += f' → worker:{j["worker_id"]}'
        else:
            status_msg += " (queued, waiting for worker)"
        typer.echo(f'Job {j["id"]} [{status_msg}]')


@app.command("job-get")
def job_get(job_id: str = typer.Option(..., "--job-id")):
    """Get job status."""
    with client() as c:
        r = c.get(f"/jobs/{job_id}")
        r.raise_for_status()
        typer.echo(r.json())


@app.command("job-logs")
def job_logs(
    job_id: str = typer.Option(..., "--job-id"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Tail logs in real-time"),
):
    """Fetch job output logs. Use --follow to stream live."""
    with client() as c:
        offset = 0

        while True:
            r = c.get(f"/jobs/{job_id}/logs", params={"offset": offset})
            r.raise_for_status()
            data = r.json()
            chunk = data.get("logs", "")

            if chunk:
                typer.echo(chunk, nl=False)
                offset += len(chunk)

            if not follow:
                if not offset:
                    typer.echo(f'No logs available (status: {data["status"]})')
                break

            if data["status"] in ("SUCCEEDED", "FAILED"):
                if not offset:
                    typer.echo(f'No logs available (status: {data["status"]})')
                break

            time.sleep(FOLLOW_POLL_INTERVAL)
