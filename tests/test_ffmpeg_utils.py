"""Tests for app.utils.ffmpeg module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.utils.ffmpeg import (
    _get_macos_architecture,
    get_ffmpeg_path,
    get_ffprobe_path,
    verify_ffmpeg_availability,
)


class TestGetFFmpegPath:
    """Test cases for get_ffmpeg_path function."""

    @patch("platform.system")
    def test_get_ffmpeg_path_windows(self, mock_system):
        """Test FFmpeg path generation for Windows."""
        mock_system.return_value = "Windows"

        result = get_ffmpeg_path()

        # Verify the path structure
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "windows" in path_parts
        assert "app" in str(result)
        assert result.name == "ffmpeg.exe"

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_ffmpeg_path_macos(self, mock_system, mock_machine):
        """Test FFmpeg path generation for macOS."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        result = get_ffmpeg_path()

        # Verify the path structure
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "macos" in path_parts
        assert "arm64" in path_parts
        assert "app" in str(result)
        assert result.name == "ffmpeg"

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_ffmpeg_path_case_insensitive(self, mock_system, mock_machine):
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

        mock_machine.return_value = "arm64"  # Set architecture for macOS tests

        for platform_name, expected_filename in test_cases:
            mock_system.return_value = platform_name
            result = get_ffmpeg_path()
            assert result.name == expected_filename

    @patch("platform.system")
    def test_get_ffmpeg_path_unsupported_platform(self, mock_system):
        """Test that unsupported platforms raise RuntimeError."""
        unsupported_platforms = ["Linux", "FreeBSD", "OpenBSD", "SunOS", "Unknown"]

        for platform_name in unsupported_platforms:
            mock_system.return_value = platform_name

            with pytest.raises(RuntimeError) as exc_info:
                get_ffmpeg_path()

            assert f"Unsupported OS: {platform_name.lower()}" in str(exc_info.value)

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_ffmpeg_path_base_directory_structure(self, mock_system, mock_machine):
        """Test that the base directory structure is correct."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        result = get_ffmpeg_path()

        # Verify parent directories in path
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "macos" in path_parts
        assert "arm64" in path_parts


class TestGetFFprobePath:
    """Test cases for get_ffprobe_path function."""

    @patch("platform.system")
    def test_get_ffprobe_path_windows(self, mock_system):
        """Test FFprobe path generation for Windows."""
        mock_system.return_value = "Windows"

        result = get_ffprobe_path()

        # Verify the path structure
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "windows" in path_parts
        assert "app" in str(result)
        assert result.name == "ffprobe.exe"

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_ffprobe_path_macos(self, mock_system, mock_machine):
        """Test FFprobe path generation for macOS."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        result = get_ffprobe_path()

        # Verify the path structure
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "macos" in path_parts
        assert "arm64" in path_parts
        assert "app" in str(result)
        assert result.name == "ffprobe"

    @patch("platform.machine")
    @patch("platform.system")
    def test_get_ffprobe_path_case_insensitive(self, mock_system, mock_machine):
        """Test that platform detection is case-insensitive."""
        test_cases = [
            ("WINDOWS", "ffprobe.exe"),
            ("windows", "ffprobe.exe"),
            ("Windows", "ffprobe.exe"),
            ("DARWIN", "ffprobe"),
            ("darwin", "ffprobe"),
            ("Darwin", "ffprobe"),
        ]

        mock_machine.return_value = "arm64"  # Set architecture for macOS tests

        for platform_name, expected_filename in test_cases:
            mock_system.return_value = platform_name
            result = get_ffprobe_path()
            assert result.name == expected_filename

    @patch("platform.system")
    def test_get_ffprobe_path_unsupported_platform(self, mock_system):
        """Test that unsupported platforms raise RuntimeError."""
        unsupported_platforms = ["Linux", "FreeBSD", "OpenBSD", "SunOS", "Unknown"]

        for platform_name in unsupported_platforms:
            mock_system.return_value = platform_name

            with pytest.raises(RuntimeError) as exc_info:
                get_ffprobe_path()

            assert f"Unsupported OS: {platform_name.lower()}" in str(exc_info.value)

    @patch("platform.system")
    def test_get_ffprobe_path_base_directory_structure(self, mock_system):
        """Test that the base directory structure is correct."""
        mock_system.return_value = "Windows"

        result = get_ffprobe_path()

        # Verify parent directories in path
        path_parts = result.parts
        assert "resources" in path_parts
        assert "ffmpeg" in path_parts
        assert "windows" in path_parts


class TestFFmpegFFprobePathConsistency:
    """Test consistency between FFmpeg and FFprobe path functions."""

    @patch("platform.system")
    def test_ffmpeg_ffprobe_same_directory_windows(self, mock_system):
        """Test that FFmpeg and FFprobe paths are in the same directory on Windows."""
        mock_system.return_value = "Windows"

        ffmpeg_path = get_ffmpeg_path()
        ffprobe_path = get_ffprobe_path()

        assert ffmpeg_path.parent == ffprobe_path.parent
        assert ffmpeg_path.parent.name == "windows"

    @patch("platform.machine")
    @patch("platform.system")
    def test_ffmpeg_ffprobe_same_directory_macos(self, mock_system, mock_machine):
        """Test that FFmpeg and FFprobe paths are in the same directory on macOS."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        ffmpeg_path = get_ffmpeg_path()
        ffprobe_path = get_ffprobe_path()

        assert ffmpeg_path.parent == ffprobe_path.parent
        assert ffmpeg_path.parent.name == "arm64"

    @patch("platform.machine")
    @patch("platform.system")
    def test_ffmpeg_ffprobe_same_base_path(self, mock_system, mock_machine):
        """Test that both functions use the same base path logic."""
        mock_machine.return_value = "arm64"  # Set architecture for macOS tests

        for platform_name in ["Windows", "Darwin"]:
            mock_system.return_value = platform_name

            ffmpeg_path = get_ffmpeg_path()
            ffprobe_path = get_ffprobe_path()

            # Should have same path up to the filename
            ffmpeg_parts = ffmpeg_path.parts[:-1]
            ffprobe_parts = ffprobe_path.parts[:-1]

            assert ffmpeg_parts == ffprobe_parts


class TestVerifyFFmpegAvailability:
    """Test cases for verify_ffmpeg_availability function."""

    @patch("app.utils.ffmpeg.get_ffmpeg_path")
    def test_verify_ffmpeg_availability_exists_and_is_file(self, mock_get_path):
        """Test verification when FFmpeg exists and is a file."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_get_path.return_value = mock_path

        result = verify_ffmpeg_availability()

        assert result is True
        mock_path.exists.assert_called_once()
        mock_path.is_file.assert_called_once()

    @patch("app.utils.ffmpeg.get_ffmpeg_path")
    def test_verify_ffmpeg_availability_not_exists(self, mock_get_path):
        """Test verification when FFmpeg does not exist."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False
        mock_path.is_file.return_value = False  # Won't be called, but set for completeness
        mock_get_path.return_value = mock_path

        result = verify_ffmpeg_availability()

        assert result is False
        mock_path.exists.assert_called_once()
        # is_file should not be called if exists() returns False
        mock_path.is_file.assert_not_called()

    @patch("app.utils.ffmpeg.get_ffmpeg_path")
    def test_verify_ffmpeg_availability_exists_but_not_file(self, mock_get_path):
        """Test verification when path exists but is not a file (e.g., directory)."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = False
        mock_get_path.return_value = mock_path

        result = verify_ffmpeg_availability()

        assert result is False
        mock_path.exists.assert_called_once()
        mock_path.is_file.assert_called_once()

    @patch("app.utils.ffmpeg.get_ffmpeg_path")
    def test_verify_ffmpeg_availability_runtime_error(self, mock_get_path):
        """Test verification when get_ffmpeg_path raises RuntimeError."""
        mock_get_path.side_effect = RuntimeError("Unsupported OS: linux")

        result = verify_ffmpeg_availability()

        assert result is False

    @patch("app.utils.ffmpeg.get_ffmpeg_path")
    def test_verify_ffmpeg_availability_os_error(self, mock_get_path):
        """Test verification when path operations raise OSError."""
        mock_path = Mock(spec=Path)
        mock_path.exists.side_effect = OSError("Permission denied")
        mock_get_path.return_value = mock_path

        result = verify_ffmpeg_availability()

        assert result is False

    @patch("app.utils.ffmpeg.get_ffmpeg_path")
    def test_verify_ffmpeg_availability_permission_error_on_is_file(self, mock_get_path):
        """Test verification when is_file() raises PermissionError."""
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.side_effect = PermissionError("Access denied")
        mock_get_path.return_value = mock_path

        result = verify_ffmpeg_availability()

        assert result is False


class TestFFmpegUtilsIntegration:
    """Integration tests for FFmpeg utility functions."""

    @patch("platform.system")
    @patch("app.utils.ffmpeg.get_ffmpeg_path")
    def test_integration_with_real_platform_detection(self, mock_get_path, mock_system):
        """Test integration between platform detection and verification."""
        # Simulate Windows platform
        mock_system.return_value = "Windows"

        # Create a mock path that behaves like a real Path object
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_get_path.return_value = mock_path

        # Test verification function
        result = verify_ffmpeg_availability()
        assert result is True

        # Verify that get_ffmpeg_path was called
        mock_get_path.assert_called_once()
        mock_path.exists.assert_called_once()
        mock_path.is_file.assert_called_once()

    def test_path_construction_logic(self):
        """Test the internal path construction logic."""
        with (
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="arm64"),
        ):
            path = get_ffmpeg_path()

            # Verify path construction
            assert isinstance(path, Path)
            assert path.name == "ffmpeg"

            # Test that the path has expected structure
            path_str = str(path)
            assert "resources" in path_str
            assert "ffmpeg" in path_str
            assert "macos" in path_str
            assert "arm64" in path_str

    @patch("platform.machine")
    @patch("platform.system")
    def test_platform_specific_extensions(self, mock_system, mock_machine):
        """Test that correct file extensions are used per platform."""
        platform_extensions = {
            "Windows": (".exe", ".exe"),  # (ffmpeg, ffprobe)
            "Darwin": ("", ""),  # No extensions on macOS
        }

        mock_machine.return_value = "arm64"  # Set architecture for macOS tests

        for platform, (ffmpeg_ext, ffprobe_ext) in platform_extensions.items():
            mock_system.return_value = platform

            ffmpeg_path = get_ffmpeg_path()
            ffprobe_path = get_ffprobe_path()

            if ffmpeg_ext:
                assert ffmpeg_path.name.endswith(ffmpeg_ext)
                assert ffprobe_path.name.endswith(ffprobe_ext)
            else:
                assert not ffmpeg_path.name.endswith(".exe")
                assert not ffprobe_path.name.endswith(".exe")


class TestFFmpegUtilsEdgeCases:
    """Test edge cases and error conditions."""

    @patch("platform.system")
    def test_empty_platform_string(self, mock_system):
        """Test behavior with empty platform string."""
        mock_system.return_value = ""

        with pytest.raises(RuntimeError) as exc_info:
            get_ffmpeg_path()

        assert "Unsupported OS:" in str(exc_info.value)

    @patch("platform.system")
    def test_none_platform_string(self, mock_system):
        """Test behavior when platform.system() returns None."""
        mock_system.return_value = None

        # This will fail when we try to call .lower() on None
        with pytest.raises(AttributeError):
            get_ffmpeg_path()

    @patch("platform.system")
    def test_numeric_platform_string(self, mock_system):
        """Test behavior with numeric platform string."""
        mock_system.return_value = "123"

        with pytest.raises(RuntimeError) as exc_info:
            get_ffmpeg_path()

        assert "Unsupported OS: 123" in str(exc_info.value)

    def test_path_object_type(self):
        """Test that functions return proper Path objects."""
        with (
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="arm64"),
        ):
            ffmpeg_path = get_ffmpeg_path()
            ffprobe_path = get_ffprobe_path()

            assert isinstance(ffmpeg_path, Path)
            assert isinstance(ffprobe_path, Path)

            # Test that Path objects have expected methods
            assert hasattr(ffmpeg_path, "exists")
            assert hasattr(ffmpeg_path, "is_file")
            assert hasattr(ffmpeg_path, "parent")
            assert hasattr(ffmpeg_path, "name")


# Performance and behavior tests
class TestFFmpegUtilsPerformance:
    """Test performance and behavioral characteristics."""

    def test_function_calls_are_pure(self):
        """Test that functions are pure (same input -> same output)."""
        with patch("platform.system", return_value="Windows"):
            # Call functions multiple times
            paths1 = (get_ffmpeg_path(), get_ffprobe_path())
            paths2 = (get_ffmpeg_path(), get_ffprobe_path())
            paths3 = (get_ffmpeg_path(), get_ffprobe_path())

            # Results should be identical
            assert paths1 == paths2 == paths3

    def test_no_side_effects(self):
        """Test that functions don't have side effects."""
        original_cwd = Path.cwd()

        with (
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="arm64"),
        ):
            get_ffmpeg_path()
            get_ffprobe_path()
            verify_ffmpeg_availability()

        # Working directory should be unchanged
        assert Path.cwd() == original_cwd


class TestMacOSArchitectureDetection:
    """Test cases for _get_macos_architecture function."""

    @patch("platform.machine")
    def test_get_macos_architecture_arm64(self, mock_machine):
        """Test detection of ARM64 architecture."""
        mock_machine.return_value = "arm64"

        result = _get_macos_architecture()

        assert result == "arm64"

    @patch("platform.machine")
    def test_get_macos_architecture_intel_x86_64(self, mock_machine):
        """Test detection of Intel x86_64 architecture."""
        mock_machine.return_value = "x86_64"

        result = _get_macos_architecture()

        assert result == "intel"

    @patch("platform.machine")
    def test_get_macos_architecture_intel_i386(self, mock_machine):
        """Test detection of Intel i386 architecture."""
        mock_machine.return_value = "i386"

        result = _get_macos_architecture()

        assert result == "intel"

    @patch("platform.machine")
    def test_get_macos_architecture_case_insensitive(self, mock_machine):
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
            mock_machine.return_value = machine_value
            result = _get_macos_architecture()
            assert result == expected_result

    @patch("platform.machine")
    def test_get_macos_architecture_unsupported(self, mock_machine):
        """Test that unsupported architectures raise RuntimeError."""
        unsupported_architectures = ["sparc", "ppc", "mips", "unknown", ""]

        for arch in unsupported_architectures:
            mock_machine.return_value = arch

            with pytest.raises(RuntimeError) as exc_info:
                _get_macos_architecture()

            assert f"Unsupported macOS architecture: {arch}" in str(exc_info.value)

    @patch("platform.machine")
    def test_get_macos_architecture_none_value(self, mock_machine):
        """Test behavior when platform.machine() returns None."""
        mock_machine.return_value = None

        # This will fail when we try to call .lower() on None
        with pytest.raises(AttributeError):
            _get_macos_architecture()

    @patch("platform.machine")
    @patch("platform.system")
    def test_architecture_integration_with_path_functions(self, mock_system, mock_machine):
        """Test that architecture detection integrates properly with path functions."""
        mock_system.return_value = "Darwin"

        # Test ARM64
        mock_machine.return_value = "arm64"
        ffmpeg_path = get_ffmpeg_path()
        ffprobe_path = get_ffprobe_path()
        assert "arm64" in str(ffmpeg_path)
        assert "arm64" in str(ffprobe_path)

        # Test Intel
        mock_machine.return_value = "x86_64"
        ffmpeg_path = get_ffmpeg_path()
        ffprobe_path = get_ffprobe_path()
        assert "intel" in str(ffmpeg_path)
        assert "intel" in str(ffprobe_path)
