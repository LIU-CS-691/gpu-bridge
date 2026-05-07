from collections.abc import Generator

import docker
from docker.errors import ContainerError, ImageNotFound, APIError


def run_container_streaming(
    image: str, command: str, timeout: int = 300, gpu: bool = False
) -> Generator[tuple[str | None, bool | None], None, None]:
    """Run a Docker container, yielding (log_chunk, None) during execution
    and (None, succeeded) at the end."""
    yield "[gpu-worker] Connecting to Docker daemon...\n", None
    client = docker.from_env()

    kwargs = {
        "image": image,
        "command": command,
        "detach": True,
        "stdout": True,
        "stderr": True,
    }

    if gpu:
        kwargs["device_requests"] = [docker.types.DeviceRequest(count=-1, capabilities=[["gpu"]])]
        yield "[gpu-worker] GPU passthrough enabled\n", None

    container = None
    try:
        try:
            client.images.get(image)
            yield f"[gpu-worker] Image '{image}' found locally\n", None
        except docker.errors.ImageNotFound:
            yield f"[gpu-worker] Pulling image: {image} (this may take a few minutes)...\n", None
            last_status = ""
            for line in client.api.pull(image, stream=True, decode=True):
                status = line.get("status", "")
                layer_id = line.get("id", "")
                progress = line.get("progress", "")
                if status == "Downloading" and progress:
                    msg = f"[pull] {layer_id}: {progress}\n"
                    yield msg, None
                elif status == "Extracting" and progress:
                    msg = f"[pull] {layer_id} extracting: {progress}\n"
                    yield msg, None
                elif status != last_status:
                    if layer_id:
                        yield f"[pull] {layer_id}: {status}\n", None
                    elif status:
                        yield f"[pull] {status}\n", None
                    last_status = status
            yield "[gpu-worker] Pull complete.\n", None

        yield "[gpu-worker] Starting container...\n", None
        container = client.containers.run(**kwargs)
        yield "[gpu-worker] Container started. Streaming output:\n", None
        yield "─" * 60 + "\n", None

        for chunk in container.logs(stream=True, follow=True):
            text = chunk.decode("utf-8", errors="replace")
            yield text, None

        yield "─" * 60 + "\n", None
        yield "[gpu-worker] Container finished. Checking exit code...\n", None

        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", -1)
        if exit_code == 0:
            yield "[gpu-worker] Exit code: 0 (success)\n", None
        else:
            yield f"[gpu-worker] Exit code: {exit_code} (failure)\n", None
        yield None, exit_code == 0
    except ContainerError as e:
        yield f"[gpu-worker] Container error: {e}\n", None
        yield None, False
    except ImageNotFound:
        yield f"[gpu-worker] ERROR: Image not found: {image}\n", None
        yield None, False
    except APIError as e:
        yield f"[gpu-worker] Docker API error: {e}\n", None
        yield None, False
    except Exception as e:
        yield f"[gpu-worker] Unexpected error: {e}\n", None
        yield None, False
    finally:
        if container:
            try:
                container.remove(force=True)
                yield "[gpu-worker] Container cleaned up.\n", None
            except Exception:
                pass
