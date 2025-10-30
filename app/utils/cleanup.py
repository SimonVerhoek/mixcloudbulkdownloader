"""Cleanup utilities for partial download and conversion files."""

import time
from pathlib import Path


class PartialFileCleanup:
    """Utility for cleaning up partial download and conversion files."""

    @staticmethod
    def cleanup_partial_files(directory: Path, max_age_minutes: int = 60) -> dict[str, int]:
        """Clean up partial files (.downloading, .converting) older than specified age.

        Args:
            directory: Directory to scan for partial files
            max_age_minutes: Maximum age in minutes for partial files before cleanup

        Returns:
            Dictionary with cleanup statistics: {"downloading": count, "converting": count}
        """
        if not directory.exists() or not directory.is_dir():
            return {"downloading": 0, "converting": 0}

        current_time = time.time()
        max_age_seconds = max_age_minutes * 60
        stats = {"downloading": 0, "converting": 0}

        # Clean up .downloading files
        for downloading_file in directory.glob("*.downloading"):
            try:
                if downloading_file.is_file():
                    file_age = current_time - downloading_file.stat().st_mtime
                    if file_age > max_age_seconds:
                        downloading_file.unlink()
                        stats["downloading"] += 1
            except (OSError, PermissionError):
                continue  # Skip files that can't be accessed or deleted

        # Clean up .converting files
        for converting_file in directory.glob("*.converting"):
            try:
                if converting_file.is_file():
                    file_age = current_time - converting_file.stat().st_mtime
                    if file_age > max_age_seconds:
                        converting_file.unlink()
                        stats["converting"] += 1
            except (OSError, PermissionError):
                continue  # Skip files that can't be accessed or deleted

        return stats

    @staticmethod
    def list_partial_files(directory: Path) -> dict[str, list[str]]:
        """List all partial files in a directory.

        Args:
            directory: Directory to scan for partial files

        Returns:
            Dictionary with lists of partial files: {"downloading": [...], "converting": [...]}
        """
        if not directory.exists() or not directory.is_dir():
            return {"downloading": [], "converting": []}

        result = {"downloading": [], "converting": []}

        # Find .downloading files
        for downloading_file in directory.glob("*.downloading"):
            if downloading_file.is_file():
                result["downloading"].append(str(downloading_file))

        # Find .converting files
        for converting_file in directory.glob("*.converting"):
            if converting_file.is_file():
                result["converting"].append(str(converting_file))

        return result

    @staticmethod
    def cleanup_fragment_files(directory: Path) -> int:
        """Clean up yt-dlp fragment files (.part, .part-Frag*, etc.).

        Args:
            directory: Directory to scan for fragment files

        Returns:
            Number of fragment files cleaned up
        """
        if not directory.exists() or not directory.is_dir():
            return 0

        cleaned_count = 0
        fragment_patterns = ["*.part", "*.part-Frag*", "*.webm.part*", "*.mp4.part*"]

        for pattern in fragment_patterns:
            for fragment_file in directory.glob(pattern):
                try:
                    if fragment_file.is_file():
                        fragment_file.unlink()
                        cleaned_count += 1
                except (OSError, PermissionError):
                    continue  # Skip files that can't be deleted

        return cleaned_count

    @staticmethod
    def get_partial_file_info(file_path: Path) -> dict[str, str] | None:
        """Get information about a partial file.

        Args:
            file_path: Path to the partial file

        Returns:
            Dictionary with file info or None if not a partial file
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        name = file_path.name

        if name.endswith(".downloading"):
            # Extract base name and target extension
            base_name_with_ext = name[:-12]  # Remove ".downloading"
            if "." in base_name_with_ext:
                base_name, target_extension = base_name_with_ext.rsplit(".", 1)
                return {
                    "type": "downloading",
                    "base_name": base_name,
                    "target_extension": target_extension,
                    "final_name": base_name_with_ext,
                }
            else:
                return {
                    "type": "downloading",
                    "base_name": base_name_with_ext,
                    "target_extension": "",
                    "final_name": base_name_with_ext,
                }
        elif name.endswith(".converting"):
            # Extract base name and target extension
            base_name_with_ext = name[:-11]  # Remove ".converting"
            if "." in base_name_with_ext:
                base_name, target_extension = base_name_with_ext.rsplit(".", 1)
                return {
                    "type": "converting",
                    "base_name": base_name,
                    "target_extension": target_extension,
                    "final_name": base_name_with_ext,
                }
            else:
                return {
                    "type": "converting",
                    "base_name": base_name_with_ext,
                    "target_extension": "",
                    "final_name": base_name_with_ext,
                }

        return None
