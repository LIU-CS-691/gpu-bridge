import time

import httpx
import typer

from .config import load_config
from .executor import run_container

app = typer.Typer(help="GPUBridge Worker CLI")

POLL_INTERVAL = 5
HEARTBEAT_INTERVAL = 30


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


@app.command()
def start(
    worker_id: str = typer.Option(..., "--worker-id"),
    gpu: bool = typer.Option(False, "--gpu", help="Enable GPU passthrough"),
    timeout: int = typer.Option(300, "--timeout", help="Container timeout in seconds"),
):
    """Start polling for jobs and executing them."""
    cfg = load_config()
    headers = {"X-API-Token": cfg["token"]}
    base_url = cfg["server"]
    last_heartbeat = 0.0

    typer.echo(f"Worker {worker_id} starting — polling {base_url} every {POLL_INTERVAL}s")

    with httpx.Client(base_url=base_url, headers=headers, timeout=30.0) as c:
        while True:
            now = time.time()

            if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                try:
                    c.post(f"/workers/{worker_id}/heartbeat")
                    last_heartbeat = now
                except httpx.HTTPError:
                    typer.echo("Heartbeat failed, retrying next cycle")

            try:
                r = c.get("/jobs", params={"worker_id": worker_id, "status": "PENDING"})
                r.raise_for_status()
                jobs = r.json()
            except httpx.HTTPError as e:
                typer.echo(f"Poll failed: {e}")
                time.sleep(POLL_INTERVAL)
                continue

            for job in jobs:
                job_id = job["id"]
                typer.echo(f"Claiming job {job_id}")

                try:
                    claim = c.patch(f"/jobs/{job_id}/claim")
                    if claim.status_code == 409:
                        typer.echo(f"Job {job_id} already claimed, skipping")
                        continue
                    claim.raise_for_status()
                except httpx.HTTPError as e:
                    typer.echo(f"Claim failed for {job_id}: {e}")
                    continue

                typer.echo(f"Running job {job_id}: {job['image']} — {job['command']}")
                logs, succeeded = run_container(
                    image=job["image"],
                    command=job["command"],
                    timeout=timeout,
                    gpu=gpu,
                )

                status = "SUCCEEDED" if succeeded else "FAILED"
                typer.echo(f"Job {job_id} {status}")

                try:
                    c.patch(
                        f"/jobs/{job_id}/complete",
                        json={"status": status, "logs": logs},
                    )
                except httpx.HTTPError as e:
                    typer.echo(f"Failed to report completion for {job_id}: {e}")

            time.sleep(POLL_INTERVAL)
