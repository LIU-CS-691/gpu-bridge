from collections.abc import Generator

import docker
from docker.errors import ContainerError, ImageNotFound, APIError


def run_container_streaming(
    image: str, command: str, timeout: int = 300, gpu: bool = False
) -> Generator[tuple[str | None, bool | None], None, None]:
    """Run a Docker container, yielding (log_chunk, None) during execution
    and (None, succeeded) at the end."""
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

        for chunk in container.logs(stream=True, follow=True):
            text = chunk.decode("utf-8", errors="replace")
            yield text, None

        result = container.wait(timeout=timeout)
        exit_code = result.get("StatusCode", -1)
        yield None, exit_code == 0
    except ContainerError as e:
        yield str(e) + "\n", None
        yield None, False
    except ImageNotFound:
        yield f"Image not found: {image}\n", None
        yield None, False
    except APIError as e:
        yield f"Docker API error: {e}\n", None
        yield None, False
    except Exception as e:
        yield f"Unexpected error: {e}\n", None
        yield None, False
    finally:
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass
