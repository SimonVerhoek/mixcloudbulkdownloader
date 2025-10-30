"""System service for hardware detection and system information."""

import multiprocessing


def get_cpu_count() -> int:
    """Get logical CPU core count with fallback.

    Returns:
        Number of logical CPU cores, or 4 as safe fallback
    """
    try:
        return multiprocessing.cpu_count()
    except (NotImplementedError, OSError, Exception):
        return 4  # Safe fallback


# Module singleton
cpu_count = get_cpu_count()
