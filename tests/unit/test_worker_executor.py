from unittest.mock import MagicMock, patch

from worker.gpu_worker.executor import run_container_streaming


def _mock_container(logs_output, exit_code=0):
    container = MagicMock()
    container.logs.return_value = iter([chunk.encode() for chunk in logs_output])
    container.wait.return_value = {"StatusCode": exit_code}
    return container


def test_successful_run():
    container = _mock_container(["hello\n", "world\n"], exit_code=0)

    with patch("worker.gpu_worker.executor.docker") as mock_docker:
        mock_docker.from_env.return_value.containers.run.return_value = container
        mock_docker.from_env.return_value.images.get.return_value = True

        chunks = list(run_container_streaming("alpine", "echo hello"))

    log_chunks = [c for c, d in chunks if c is not None]
    done = [d for c, d in chunks if d is not None]

    assert "hello\n" in log_chunks
    assert "world\n" in log_chunks
    assert any("Connecting to Docker" in c for c in log_chunks)
    assert any("Container started" in c for c in log_chunks)
    assert any("Exit code: 0" in c for c in log_chunks)
    assert done == [True]
    container.remove.assert_called_once_with(force=True)


def test_failed_run():
    container = _mock_container(["error output\n"], exit_code=1)

    with patch("worker.gpu_worker.executor.docker") as mock_docker:
        mock_docker.from_env.return_value.containers.run.return_value = container
        mock_docker.from_env.return_value.images.get.return_value = True

        chunks = list(run_container_streaming("alpine", "false"))

    done = [d for c, d in chunks if d is not None]
    assert done == [False]


def test_image_not_found():
    from docker.errors import ImageNotFound as DockerImageNotFound

    with patch("worker.gpu_worker.executor.docker") as mock_docker:
        mock_docker.from_env.return_value.images.get.side_effect = DockerImageNotFound(
            "nope"
        )
        mock_docker.errors.ImageNotFound = DockerImageNotFound
        mock_docker.from_env.return_value.api.pull.return_value = iter([])
        mock_docker.from_env.return_value.containers.run.side_effect = (
            DockerImageNotFound("nope")
        )

        chunks = list(run_container_streaming("nonexistent", "echo hi"))

    log_chunks = [c for c, d in chunks if c is not None]
    done = [d for c, d in chunks if d is not None]

    assert any("not found" in c.lower() or "nope" in c.lower() for c in log_chunks)
    assert done == [False]


def test_gpu_passthrough_flag():
    container = _mock_container(["gpu ok\n"], exit_code=0)

    with patch("worker.gpu_worker.executor.docker") as mock_docker:
        mock_docker.from_env.return_value.containers.run.return_value = container
        mock_docker.from_env.return_value.images.get.return_value = True
        mock_docker.types.DeviceRequest = MagicMock()

        list(run_container_streaming("nvidia/cuda", "nvidia-smi", gpu=True))

    call_kwargs = mock_docker.from_env.return_value.containers.run.call_args
    assert "device_requests" in call_kwargs.kwargs


def test_container_cleanup_on_error():
    container = MagicMock()
    container.logs.side_effect = RuntimeError("connection lost")

    with patch("worker.gpu_worker.executor.docker") as mock_docker:
        mock_docker.from_env.return_value.containers.run.return_value = container
        mock_docker.from_env.return_value.images.get.return_value = True

        chunks = list(run_container_streaming("alpine", "echo hi"))

    done = [d for c, d in chunks if d is not None]
    assert done == [False]
    container.remove.assert_called_once_with(force=True)
