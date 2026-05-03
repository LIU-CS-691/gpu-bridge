import docker
from docker.errors import ContainerError, ImageNotFound, APIError


def run_container(
    image: str, command: str, timeout: int = 300, gpu: bool = False
) -> tuple[str, bool]:
    """Run a Docker container and return (logs, succeeded)."""
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

    container = None
    try:
        container = client.containers.run(**kwargs)
        result = container.wait(timeout=timeout)
        logs = container.logs().decode("utf-8", errors="replace")
        exit_code = result.get("StatusCode", -1)
        return logs, exit_code == 0
    except ContainerError as e:
        return str(e), False
    except ImageNotFound:
        return f"Image not found: {image}", False
    except APIError as e:
        return f"Docker API error: {e}", False
    except Exception as e:
        return f"Unexpected error: {e}", False
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass
