def detect_gpus() -> list[dict] | None:
    """Detect NVIDIA GPUs via pynvml. Returns None if no GPUs or driver not available."""
    try:
        import pynvml

        pynvml.nvmlInit()
    except Exception:
        return None

    try:
        count = pynvml.nvmlDeviceGetCount()
        if count == 0:
            return None

        gpus = []
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode()
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)

            gpus.append(
                {
                    "index": i,
                    "name": name,
                    "memory_total_mb": mem.total // (1024 * 1024),
                    "memory_free_mb": mem.free // (1024 * 1024),
                    "utilization_pct": util.gpu,
                }
            )
        return gpus
    except Exception:
        return None
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
