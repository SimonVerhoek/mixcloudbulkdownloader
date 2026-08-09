"""System service for hardware detection and system information."""

import multiprocessing
from collections.abc import Callable


def get_cpu_count(cpu_count_fn: Callable[[], int] | None = None) -> int:
    """Get logical CPU core count with fallback.

    Args:
        cpu_count_fn: Optional callable that returns the CPU count. Defaults to
            ``multiprocessing.cpu_count``. Allows injection for testing without patching.

    Returns:
        Number of logical CPU cores, or 4 as safe fallback
    """
    _fn = cpu_count_fn if cpu_count_fn is not None else multiprocessing.cpu_count
    try:
        return _fn()
    except (NotImplementedError, OSError, Exception):
        return 4  # Safe fallback


# Module singleton
cpu_count = get_cpu_count()
