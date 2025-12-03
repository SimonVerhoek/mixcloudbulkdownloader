"""yt-dlp utility functions for download progress and formatting."""


class QuietLogger:
    """Custom logger that suppresses yt-dlp output."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def get_stable_size_estimate(total_bytes_str: str) -> str:
    """Convert fluctuating size estimate to stable rounded estimate.

    Args:
        total_bytes_str: Raw size string like "  20.93MiB"

    Returns:
        Stable rounded estimate like "~21MB" or "~25MB"
    """
    try:
        # Extract numeric value and unit
        clean_str = total_bytes_str.strip()
        if "MiB" in clean_str:
            value = float(clean_str.replace("MiB", ""))
            # Round to nearest 1MB for stability
            rounded = round(value)
            return f"~{rounded:.0f}MB"
        elif "GiB" in clean_str:
            value = float(clean_str.replace("GiB", ""))
            # Round to nearest 0.1GB for larger files
            rounded = round(value, 1)
            return f"~{rounded:.1f}GB"
        elif "KiB" in clean_str:
            value = float(clean_str.replace("KiB", ""))
            # Convert to MB and round
            mb_value = value / 1024
            if mb_value < 1:
                return "<1MB"
            rounded = round(mb_value)
            return f"~{rounded:.0f}MB"
    except (ValueError, IndexError):
        pass

    return ""  # Return empty if parsing fails
