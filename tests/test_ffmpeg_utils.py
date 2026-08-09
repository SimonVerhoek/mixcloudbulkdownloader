"""Tests for app.utils.ffmpeg module."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from app.utils.ffmpeg import (
    _get_macos_architecture,
    get_ffmpeg_path,
    get_ffprobe_path,
    verify_ffmpeg_availability,
)


class TestGetFFmpegPath:
    """Test cases for get_ffmpeg_path function."""

    def test_get_ffmpeg_path_windows(self):
        """Test FFmpeg path generation for Windows."""
        result = get_ffmpeg_path(system="Windows")

        # Verify the path structure
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "windows" in path_parts
        assert "app" in str(result)
        assert result.name == "ffmpeg.exe"

    def test_get_ffmpeg_path_macos(self):
        """Test FFmpeg path generation for macOS."""
        result = get_ffmpeg_path(system="Darwin", machine="arm64")

        # Verify the path structure
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "macos" in path_parts
        assert "arm64" in path_parts
        assert "app" in str(result)
        assert result.name == "ffmpeg"

    def test_get_ffmpeg_path_case_insensitive(self):
        """Test that platform detection is case-insensitive."""
        # Test various capitalizations
        test_cases = [
            ("WINDOWS", "ffmpeg.exe"),
            ("windows", "ffmpeg.exe"),
            ("Windows", "ffmpeg.exe"),
            ("DARWIN", "ffmpeg"),
            ("darwin", "ffmpeg"),
            ("Darwin", "ffmpeg"),
        ]

        for platform_name, expected_filename in test_cases:
            result = get_ffmpeg_path(system=platform_name, machine="arm64")
            assert result.name == expected_filename

    def test_get_ffmpeg_path_unsupported_platform(self):
        """Test that unsupported platforms raise RuntimeError."""
        unsupported_platforms = ["Linux", "FreeBSD", "OpenBSD", "SunOS", "Unknown"]

        for platform_name in unsupported_platforms:
            with pytest.raises(RuntimeError) as exc_info:
                get_ffmpeg_path(system=platform_name)

            assert f"Unsupported OS: {platform_name.lower()}" in str(exc_info.value)

    def test_get_ffmpeg_path_base_directory_structure(self):
        """Test that the base directory structure is correct."""
        result = get_ffmpeg_path(system="Darwin", machine="arm64")

        # Verify parent directories in path
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "macos" in path_parts
        assert "arm64" in path_parts


class TestGetFFprobePath:
    """Test cases for get_ffprobe_path function."""

    def test_get_ffprobe_path_windows(self):
        """Test FFprobe path generation for Windows."""
        result = get_ffprobe_path(system="Windows")

        # Verify the path structure
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "windows" in path_parts
        assert "app" in str(result)
        assert result.name == "ffprobe.exe"

    def test_get_ffprobe_path_macos(self):
        """Test FFprobe path generation for macOS."""
        result = get_ffprobe_path(system="Darwin", machine="arm64")

        # Verify the path structure
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "macos" in path_parts
        assert "arm64" in path_parts
        assert "app" in str(result)
        assert result.name == "ffprobe"

    def test_get_ffprobe_path_case_insensitive(self):
        """Test that platform detection is case-insensitive."""
        test_cases = [
            ("WINDOWS", "ffprobe.exe"),
            ("windows", "ffprobe.exe"),
            ("Windows", "ffprobe.exe"),
            ("DARWIN", "ffprobe"),
            ("darwin", "ffprobe"),
            ("Darwin", "ffprobe"),
        ]

        for platform_name, expected_filename in test_cases:
            result = get_ffprobe_path(system=platform_name, machine="arm64")
            assert result.name == expected_filename

    def test_get_ffprobe_path_unsupported_platform(self):
        """Test that unsupported platforms raise RuntimeError."""
        unsupported_platforms = ["Linux", "FreeBSD", "OpenBSD", "SunOS", "Unknown"]

        for platform_name in unsupported_platforms:
            with pytest.raises(RuntimeError) as exc_info:
                get_ffprobe_path(system=platform_name)

            assert f"Unsupported OS: {platform_name.lower()}" in str(exc_info.value)

    def test_get_ffprobe_path_base_directory_structure(self):
        """Test that the base directory structure is correct."""
        result = get_ffprobe_path(system="Windows")

        # Verify parent directories in path
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "windows" in path_parts


class TestFFmpegFFprobePathConsistency:
    """Test consistency between FFmpeg and FFprobe path functions."""

    def test_ffmpeg_ffprobe_same_directory_windows(self):
        """Test that FFmpeg and FFprobe paths are in the same directory on Windows."""
        ffmpeg_path = get_ffmpeg_path(system="Windows")
        ffprobe_path = get_ffprobe_path(system="Windows")

        assert ffmpeg_path.parent == ffprobe_path.parent
        assert ffmpeg_path.parent.name == "windows"

    def test_ffmpeg_ffprobe_same_directory_macos(self):
        """Test that FFmpeg and FFprobe paths are in the same directory on macOS."""
        ffmpeg_path = get_ffmpeg_path(system="Darwin", machine="arm64")
        ffprobe_path = get_ffprobe_path(system="Darwin", machine="arm64")

        assert ffmpeg_path.parent == ffprobe_path.parent
        assert ffmpeg_path.parent.name == "arm64"

    def test_ffmpeg_ffprobe_same_base_path(self):
        """Test that both functions use the same base path logic."""
        for platform_name in ["Windows", "Darwin"]:
            ffmpeg_path = get_ffmpeg_path(system=platform_name, machine="arm64")
            ffprobe_path = get_ffprobe_path(system=platform_name, machine="arm64")

            # Should have same path up to the filename
            ffmpeg_parts = ffmpeg_path.parts[:-1]
            ffprobe_parts = ffprobe_path.parts[:-1]

            assert ffmpeg_parts == ffprobe_parts


class TestVerifyFFmpegAvailability:
    """Test cases for verify_ffmpeg_availability function."""

    def test_verify_ffmpeg_availability_exists_and_is_file(self):
        """Test verification when FFmpeg exists and is a file."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True

        result = verify_ffmpeg_availability(ffmpeg_path=mock_path)

        assert result is True
        mock_path.exists.assert_called_once()
        mock_path.is_file.assert_called_once()

    def test_verify_ffmpeg_availability_not_exists(self):
        """Test verification when FFmpeg does not exist."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False
        mock_path.is_file.return_value = False  # Won't be called, but set for completeness

        result = verify_ffmpeg_availability(ffmpeg_path=mock_path)

        assert result is False
        mock_path.exists.assert_called_once()
        # is_file should not be called if exists() returns False
        mock_path.is_file.assert_not_called()

    def test_verify_ffmpeg_availability_exists_but_not_file(self):
        """Test verification when path exists but is not a file (e.g., directory)."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = False

        result = verify_ffmpeg_availability(ffmpeg_path=mock_path)

        assert result is False
        mock_path.exists.assert_called_once()
        mock_path.is_file.assert_called_once()

    def test_verify_ffmpeg_availability_runtime_error(self):
        """Test verification when path operations raise RuntimeError."""
        mock_path = Mock(spec=Path)
        mock_path.exists.side_effect = RuntimeError("Unexpected error")

        result = verify_ffmpeg_availability(ffmpeg_path=mock_path)

        assert result is False

    def test_verify_ffmpeg_availability_os_error(self):
        """Test verification when path operations raise OSError."""
        mock_path = Mock(spec=Path)
        mock_path.exists.side_effect = OSError("Permission denied")

        result = verify_ffmpeg_availability(ffmpeg_path=mock_path)

        assert result is False

    def test_verify_ffmpeg_availability_permission_error_on_is_file(self):
        """Test verification when is_file() raises PermissionError."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.side_effect = PermissionError("Access denied")

        result = verify_ffmpeg_availability(ffmpeg_path=mock_path)

        assert result is False


class TestFFmpegUtilsIntegration:
    """Integration tests for FFmpeg utility functions."""

    def test_integration_with_real_platform_detection(self):
        """Test integration between platform detection and verification."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True

        result = verify_ffmpeg_availability(ffmpeg_path=mock_path)
        assert result is True

        mock_path.exists.assert_called_once()
        mock_path.is_file.assert_called_once()

    def test_path_construction_logic(self):
        """Test the internal path construction logic."""
        path = get_ffmpeg_path(system="Darwin", machine="arm64")

        # Verify path construction
        assert isinstance(path, Path)
        assert path.name == "ffmpeg"

        # Test that the path has expected structure
        path_str = str(path)
        assert "resources" in path_str
        assert "ffmpeg" in path_str
        assert "macos" in path_str
        assert "arm64" in path_str

    def test_platform_specific_extensions(self):
        """Test that correct file extensions are used per platform."""
        platform_extensions = {
            "Windows": (".exe", ".exe"),  # (ffmpeg, ffprobe)
            "Darwin": ("", ""),  # No extensions on macOS
        }

        for platform, (ffmpeg_ext, ffprobe_ext) in platform_extensions.items():
            ffmpeg_path = get_ffmpeg_path(system=platform, machine="arm64")
            ffprobe_path = get_ffprobe_path(system=platform, machine="arm64")

            if ffmpeg_ext:
                assert ffmpeg_path.name.endswith(ffmpeg_ext)
                assert ffprobe_path.name.endswith(ffprobe_ext)
            else:
                assert not ffmpeg_path.name.endswith(".exe")
                assert not ffprobe_path.name.endswith(".exe")


class TestFFmpegUtilsEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_platform_string(self):
        """Test behavior with empty platform string."""
        with pytest.raises(RuntimeError) as exc_info:
            get_ffmpeg_path(system="")

        assert "Unsupported OS:" in str(exc_info.value)

    def test_numeric_platform_string(self):
        """Test behavior with numeric platform string."""
        with pytest.raises(RuntimeError) as exc_info:
            get_ffmpeg_path(system="123")

        assert "Unsupported OS: 123" in str(exc_info.value)

    def test_path_object_type(self):
        """Test that functions return proper Path objects."""
        ffmpeg_path = get_ffmpeg_path(system="Darwin", machine="arm64")
        ffprobe_path = get_ffprobe_path(system="Darwin", machine="arm64")

        assert isinstance(ffmpeg_path, Path)
        assert isinstance(ffprobe_path, Path)

        # Path objects always have these methods (guaranteed by isinstance check above)
        assert callable(ffmpeg_path.exists)
        assert callable(ffmpeg_path.is_file)
        _ = ffmpeg_path.parent
        _ = ffmpeg_path.name


# Performance and behavior tests
class TestFFmpegUtilsPerformance:
    """Test performance and behavioral characteristics."""

    def test_function_calls_are_pure(self):
        """Test that functions are pure (same input -> same output)."""
        # Call functions multiple times
        paths1 = (get_ffmpeg_path(system="Windows"), get_ffprobe_path(system="Windows"))
        paths2 = (get_ffmpeg_path(system="Windows"), get_ffprobe_path(system="Windows"))
        paths3 = (get_ffmpeg_path(system="Windows"), get_ffprobe_path(system="Windows"))

        # Results should be identical
        assert paths1 == paths2 == paths3

    def test_no_side_effects(self):
        """Test that functions don't have side effects."""
        original_cwd = Path.cwd()

        get_ffmpeg_path(system="Darwin", machine="arm64")
        get_ffprobe_path(system="Darwin", machine="arm64")
        verify_ffmpeg_availability(ffmpeg_path=Mock(spec=Path))

        # Working directory should be unchanged
        assert Path.cwd() == original_cwd


class TestMacOSArchitectureDetection:
    """Test cases for _get_macos_architecture function."""

    def test_get_macos_architecture_arm64(self):
        """Test detection of ARM64 architecture."""
        result = _get_macos_architecture(machine="arm64")

        assert result == "arm64"

    def test_get_macos_architecture_intel_x86_64(self):
        """Test detection of Intel x86_64 architecture."""
        result = _get_macos_architecture(machine="x86_64")

        assert result == "intel"

    def test_get_macos_architecture_intel_i386(self):
        """Test detection of Intel i386 architecture."""
        result = _get_macos_architecture(machine="i386")

        assert result == "intel"

    def test_get_macos_architecture_case_insensitive(self):
        """Test that architecture detection is case-insensitive."""
        test_cases = [
            ("ARM64", "arm64"),
            ("arm64", "arm64"),
            ("Arm64", "arm64"),
            ("X86_64", "intel"),
            ("x86_64", "intel"),
            ("I386", "intel"),
            ("i386", "intel"),
        ]

        for machine_value, expected_result in test_cases:
            result = _get_macos_architecture(machine=machine_value)
            assert result == expected_result

    def test_get_macos_architecture_unsupported(self):
        """Test that unsupported architectures raise RuntimeError."""
        unsupported_architectures = ["sparc", "ppc", "mips", "unknown", ""]

        for arch in unsupported_architectures:
            with pytest.raises(RuntimeError) as exc_info:
                _get_macos_architecture(machine=arch)

            assert f"Unsupported macOS architecture: {arch}" in str(exc_info.value)

    def test_architecture_integration_with_path_functions(self):
        """Test that architecture detection integrates properly with path functions."""
        # Test ARM64
        ffmpeg_path = get_ffmpeg_path(system="Darwin", machine="arm64")
        ffprobe_path = get_ffprobe_path(system="Darwin", machine="arm64")
        assert "arm64" in str(ffmpeg_path)
        assert "arm64" in str(ffprobe_path)

        # Test Intel
        ffmpeg_path = get_ffmpeg_path(system="Darwin", machine="x86_64")
        ffprobe_path = get_ffprobe_path(system="Darwin", machine="x86_64")
        assert "intel" in str(ffmpeg_path)
        assert "intel" in str(ffprobe_path)
