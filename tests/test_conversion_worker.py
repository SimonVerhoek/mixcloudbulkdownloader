"""Comprehensive tests for ConversionWorker using PyQt threading patterns."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from app.consts.audio import AudioFormat
from app.services.conversion_worker import ConversionCancelled, ConversionWorker
from app.services.settings_manager import SettingsManager
from tests.stubs.license_server_stubs import StubLicenseManager


class StubCallbackBridge:
    """Stub callback bridge for testing ConversionWorker signals."""

    def __init__(self):
        """Initialize stub callback bridge."""
        self.progress_calls = []
        self.completed_calls = []
        self.error_calls = []
        self.cancelled_calls = []

    def emit_progress(self, cloudcast_url: str, progress_text: str, task_type: str = "conversion"):
        """Record progress emission call."""
        self.progress_calls.append(
            {"cloudcast_url": cloudcast_url, "progress_text": progress_text, "task_type": task_type}
        )

    def emit_completed(self, cloudcast_url: str, file_path: str, task_type: str = "conversion"):
        """Record completion emission call."""
        self.completed_calls.append(
            {"cloudcast_url": cloudcast_url, "file_path": file_path, "task_type": task_type}
        )

    def emit_error(self, cloudcast_url: str, error_msg: str, task_type: str = "conversion"):
        """Record error emission call."""
        self.error_calls.append(
            {"cloudcast_url": cloudcast_url, "error_msg": error_msg, "task_type": task_type}
        )

    def emit_cancelled(self, cloudcast_url: str, task_type: str = "conversion"):
        """Record cancellation emission call."""
        self.cancelled_calls.append({"cloudcast_url": cloudcast_url, "task_type": task_type})

    def reset(self):
        """Reset call history."""
        self.progress_calls.clear()
        self.completed_calls.clear()
        self.error_calls.clear()
        self.cancelled_calls.clear()


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def test_input_file(temp_dir):
    """Create test input file."""
    input_file = temp_dir / "test_audio.webm"
    input_file.write_text("fake audio content")  # Minimal content for testing
    return str(input_file)


@pytest.fixture
def stub_callback_bridge():
    """Create stub callback bridge."""
    return StubCallbackBridge()


@pytest.fixture
def stub_license_manager():
    """Create stub license manager configured as Pro user."""
    manager = StubLicenseManager()
    manager.configure_as_pro_user()
    return manager


@pytest.fixture
def stub_settings_manager():
    """Create stub settings manager."""
    settings = Mock(spec=SettingsManager)
    settings.get.return_value = 192  # Default bitrate
    return settings


@pytest.fixture
def conversion_worker(
    test_input_file, temp_dir, stub_callback_bridge, stub_settings_manager, stub_license_manager
):
    """Create ConversionWorker instance for testing."""
    return ConversionWorker(
        cloudcast_url="https://mixcloud.com/test/mix",
        input_file=test_input_file,
        target_format="mp3",
        download_dir=str(temp_dir),
        callback_bridge=stub_callback_bridge,
        settings_manager=stub_settings_manager,
        license_manager=stub_license_manager,
    )


class TestConversionWorkerStructure:
    """Test ConversionWorker initialization and structure."""

    def test_conversion_worker_initialization(self, conversion_worker, test_input_file, temp_dir):
        """Test ConversionWorker initializes with correct attributes."""
        assert conversion_worker.cloudcast_url == "https://mixcloud.com/test/mix"
        assert conversion_worker.input_file == test_input_file
        assert conversion_worker.target_format == "mp3"
        assert conversion_worker.download_dir == str(temp_dir)
        assert not conversion_worker.cancelled
        assert conversion_worker.ffmpeg_process is None

    def test_conversion_worker_file_paths(self, conversion_worker, temp_dir):
        """Test ConversionWorker sets up correct file paths."""
        assert conversion_worker.final_filename == "test_audio.mp3"
        assert conversion_worker.temp_dir == Path(temp_dir) / ".converting"
        assert (
            conversion_worker.converting_file_path
            == Path(temp_dir) / ".converting" / "test_audio.mp3"
        )
        assert conversion_worker.final_file_path == Path(temp_dir) / "test_audio.mp3"


class TestConversionWorkerPrerequisites:
    """Test ConversionWorker prerequisite validation."""

    def test_pro_license_required(
        self, conversion_worker, stub_license_manager, stub_callback_bridge
    ):
        """Test conversion requires Pro license."""
        # Configure as free user
        stub_license_manager.configure_as_free_user()

        # Run conversion (should emit error signal instead of raising)
        conversion_worker.run()

        # Should emit error signal for Pro license requirement
        assert len(stub_callback_bridge.error_calls) == 1
        error = stub_callback_bridge.error_calls[0]
        assert "Audio conversion requires Pro license" in error["error_msg"]

    def test_ffmpeg_path_validation(self, conversion_worker, stub_callback_bridge):
        """Test FFmpeg path validation."""
        conversion_worker._ffmpeg_path = None

        # Run conversion (should emit error signal instead of raising)
        conversion_worker.run()

        # Should emit error signal for missing FFmpeg
        assert len(stub_callback_bridge.error_calls) == 1
        error = stub_callback_bridge.error_calls[0]
        assert "FFmpeg not found" in error["error_msg"]

    def test_input_file_validation(
        self, temp_dir, stub_callback_bridge, stub_settings_manager, stub_license_manager
    ):
        """Test input file validation."""
        # Non-existent input file
        worker = ConversionWorker(
            cloudcast_url="https://mixcloud.com/test/mix",
            input_file=str(temp_dir / "nonexistent.webm"),
            target_format="mp3",
            download_dir=str(temp_dir),
            callback_bridge=stub_callback_bridge,
            settings_manager=stub_settings_manager,
            license_manager=stub_license_manager,
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
        )

        # Run conversion (should emit error signal instead of raising)
        worker.run()

        # Should emit error signal for missing input file
        assert len(stub_callback_bridge.error_calls) == 1
        error = stub_callback_bridge.error_calls[0]
        assert "Input file does not exist" in error["error_msg"]

    def test_empty_input_file_validation(
        self, temp_dir, stub_callback_bridge, stub_settings_manager, stub_license_manager
    ):
        """Test empty input file validation."""
        # Create empty file
        empty_file = temp_dir / "empty.webm"
        empty_file.touch()

        worker = ConversionWorker(
            cloudcast_url="https://mixcloud.com/test/mix",
            input_file=str(empty_file),
            target_format="mp3",
            download_dir=str(temp_dir),
            callback_bridge=stub_callback_bridge,
            settings_manager=stub_settings_manager,
            license_manager=stub_license_manager,
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
        )

        # Run conversion (should emit error signal instead of raising)
        worker.run()

        # Should emit error signal for empty input file
        assert len(stub_callback_bridge.error_calls) == 1
        error = stub_callback_bridge.error_calls[0]
        assert "Input file is empty" in error["error_msg"]


@pytest.mark.unit
class TestFFmpegCommandBuilding:
    """Test FFmpeg command building for different formats."""

    def test_build_mp3_command(self, conversion_worker):
        """Test FFmpeg command for MP3 conversion."""
        cmd = conversion_worker._build_ffmpeg_command("/usr/bin/ffmpeg")

        expected_elements = [
            "/usr/bin/ffmpeg",
            "-y",  # Overwrite
            "-i",
            conversion_worker.input_file,  # Input
            "-vn",  # No video
            "-c:a",
            "libmp3lame",  # MP3 codec
            "-b:a",
            "192k",  # Bitrate for lossy
            "-progress",
            "pipe:1",  # Progress
            "-nostats",
            str(conversion_worker.converting_file_path),  # Output
        ]

        assert cmd == expected_elements

    def test_build_flac_command(
        self,
        test_input_file,
        temp_dir,
        stub_callback_bridge,
        stub_settings_manager,
        stub_license_manager,
    ):
        """Test FFmpeg command for FLAC conversion (lossless)."""
        worker = ConversionWorker(
            cloudcast_url="https://mixcloud.com/test/mix",
            input_file=test_input_file,
            target_format="flac",
            download_dir=str(temp_dir),
            callback_bridge=stub_callback_bridge,
            settings_manager=stub_settings_manager,
            license_manager=stub_license_manager,
        )

        cmd = worker._build_ffmpeg_command("/usr/bin/ffmpeg")

        # FLAC is lossless, so no bitrate should be specified
        assert "-b:a" not in cmd
        assert "flac" in cmd

    def test_unsupported_format_error(
        self,
        test_input_file,
        temp_dir,
        stub_callback_bridge,
        stub_settings_manager,
        stub_license_manager,
    ):
        """Test error for unsupported audio format."""
        worker = ConversionWorker(
            cloudcast_url="https://mixcloud.com/test/mix",
            input_file=test_input_file,
            target_format="unsupported",
            download_dir=str(temp_dir),
            callback_bridge=stub_callback_bridge,
            settings_manager=stub_settings_manager,
            license_manager=stub_license_manager,
        )

        with pytest.raises(KeyError, match="Audio format 'unsupported' not found"):
            worker._build_ffmpeg_command("/usr/bin/ffmpeg")


@pytest.mark.unit
class TestFFmpegProgressParsing:
    """Test FFmpeg progress parsing and signal emission."""

    def test_parse_progress_with_duration(self, conversion_worker, stub_callback_bridge):
        """Test progress parsing when duration is known."""
        conversion_worker._parse_progress("out_time_ms=30000000", 60.0)  # 30s of 60s = 50%

        assert len(stub_callback_bridge.progress_calls) == 1
        call = stub_callback_bridge.progress_calls[0]
        assert call["cloudcast_url"] == "https://mixcloud.com/test/mix"
        assert "MP3 50.0%" in call["progress_text"]
        assert call["task_type"] == "conversion"

    def test_parse_progress_without_duration(self, conversion_worker, stub_callback_bridge):
        """Test progress parsing when duration is unknown."""
        conversion_worker._parse_progress("out_time_ms=15000000", None)

        assert len(stub_callback_bridge.progress_calls) == 1
        call = stub_callback_bridge.progress_calls[0]
        assert "MP3..." in call["progress_text"]

    def test_parse_progress_malformed_line(self, conversion_worker, stub_callback_bridge):
        """Test handling of malformed progress lines."""
        conversion_worker._parse_progress("invalid=line", 60.0)
        conversion_worker._parse_progress("out_time_ms=invalid", 60.0)

        # Should not emit any progress signals for malformed lines
        assert len(stub_callback_bridge.progress_calls) == 0

    def test_parse_progress_na_value(self, conversion_worker, stub_callback_bridge):
        """Test handling of N/A progress values."""
        conversion_worker._parse_progress("out_time_ms=N/A", 60.0)

        # Should not emit progress signal for N/A values
        assert len(stub_callback_bridge.progress_calls) == 0


@pytest.mark.unit
class TestConversionCancellation:
    """Test conversion cancellation handling."""

    def test_cancel_before_start(self, conversion_worker, stub_callback_bridge):
        """Test cancellation before conversion starts emits emit_cancelled."""
        conversion_worker.cancel()
        conversion_worker._ffmpeg_path = Path("/usr/bin/ffmpeg")
        conversion_worker.run()

        # Must emit emit_cancelled, not a progress "Cancelled" message
        assert len(stub_callback_bridge.cancelled_calls) == 1
        assert (
            stub_callback_bridge.cancelled_calls[0]["cloudcast_url"]
            == "https://mixcloud.com/test/mix"
        )
        assert stub_callback_bridge.cancelled_calls[0]["task_type"] == "conversion"
        # No spurious progress signal
        cancelled_progress = [
            c
            for c in stub_callback_bridge.progress_calls
            if "Cancelled" in c.get("progress_text", "")
        ]
        assert len(cancelled_progress) == 0

    def test_cancel_during_process(self, conversion_worker):
        """Test cancellation during FFmpeg process."""
        # Mock a running process
        mock_process = Mock(spec=subprocess.Popen)
        conversion_worker.ffmpeg_process = mock_process

        conversion_worker.cancel()

        # Should terminate the process
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_with(timeout=2)
        assert conversion_worker.ffmpeg_process is None

    def test_cancel_with_stuck_process(self, conversion_worker):
        """Test cancellation when process won't terminate gracefully."""
        # Mock a process that times out on terminate
        mock_process = Mock(spec=subprocess.Popen)
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("ffmpeg", 2), None]
        conversion_worker.ffmpeg_process = mock_process

        conversion_worker.cancel()

        # Should terminate, then kill when timeout occurs
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_cancel_run_emits_cancelled_and_removes_source_file(
        self, conversion_worker, stub_callback_bridge, test_input_file
    ):
        """Cancelling run() emits emit_cancelled and deletes the source file."""
        conversion_worker.cancel()
        conversion_worker._ffmpeg_path = Path("/usr/bin/ffmpeg")
        conversion_worker.run()

        # emit_cancelled fired, not emit_progress
        assert len(stub_callback_bridge.cancelled_calls) == 1
        assert len(stub_callback_bridge.progress_calls) == 0 or all(
            "Cancelled" not in c.get("progress_text", "")
            for c in stub_callback_bridge.progress_calls
        )
        # Source file deleted
        assert not Path(test_input_file).exists()


@pytest.mark.unit
class TestCleanupSourceFile:
    """Test _cleanup_source_file behaviour."""

    def test_cleanup_source_file_removes_existing_file(self, conversion_worker, test_input_file):
        """_cleanup_source_file() deletes the source file when it exists."""
        assert Path(test_input_file).exists()
        conversion_worker._cleanup_source_file()
        assert not Path(test_input_file).exists()

    def test_cleanup_source_file_safe_when_file_missing(self, conversion_worker, test_input_file):
        """_cleanup_source_file() does not raise when source file is already gone."""
        Path(test_input_file).unlink()
        conversion_worker._cleanup_source_file()  # Must not raise

    def test_cleanup_source_file_not_called_on_error(
        self, conversion_worker, stub_callback_bridge, test_input_file
    ):
        """On conversion error the source file must be preserved for retry."""
        conversion_worker._ffmpeg_path = Path("/usr/bin/ffmpeg")

        class StubErrorProcess:
            """Stub process that simulates FFmpeg failing with exit code 1."""

            stdout = []
            returncode = 1

            def wait(self):
                pass

        stub_proc = StubErrorProcess()

        def stub_popen(cmd, **kwargs):
            return stub_proc

        conversion_worker._popen_fn = stub_popen

        with patch.object(conversion_worker, "_validate_conversion_prerequisites"):
            conversion_worker.run()

        # Error path: source file must still exist
        assert Path(test_input_file).exists()
        assert len(stub_callback_bridge.error_calls) == 1


@pytest.mark.unit
class TestConversionErrorHandling:
    """Test conversion error handling and user-friendly messages."""

    def test_ffmpeg_error_parsing_permission_denied(self, conversion_worker):
        """Test parsing of permission denied errors."""
        error_msg = conversion_worker._parse_ffmpeg_error("Permission denied", 1)
        assert "Permission denied" in error_msg
        assert "exit code 1" in error_msg

    def test_ffmpeg_error_parsing_no_space(self, conversion_worker):
        """Test parsing of disk space errors."""
        error_msg = conversion_worker._parse_ffmpeg_error("No space left on device", 1)
        assert "Not enough disk space" in error_msg

    def test_ffmpeg_error_parsing_unknown_error(self, conversion_worker):
        """Test parsing of unknown errors."""
        error_msg = conversion_worker._parse_ffmpeg_error("Some random error", 42)
        assert "Unknown conversion error" in error_msg
        assert "exit code 42" in error_msg

    def test_ffmpeg_error_parsing_exit_code_specific(self, conversion_worker):
        """Test exit code specific error messages."""
        error_msg = conversion_worker._parse_ffmpeg_error("", 127)
        assert "FFmpeg executable not found" in error_msg
        assert "exit code 127" in error_msg

    def test_ffmpeg_error_no_double_prefix(self, conversion_worker):
        """Regression guard: _parse_ffmpeg_error must not include 'Conversion failed:' prefix.

        The run() method wraps the result in f"Conversion failed: {str(e)}".
        If _parse_ffmpeg_error already adds the prefix, the user sees it twice.
        """
        msg_known = conversion_worker._parse_ffmpeg_error("", 127)
        msg_unknown = conversion_worker._parse_ffmpeg_error("Some random error", 42)

        assert not msg_known.startswith("Conversion failed:")
        assert not msg_unknown.startswith("Conversion failed:")

    def test_ffmpeg_error_windows_antivirus_exit_code(self, conversion_worker):
        """Regression guard: exit code 3221225786 (0xC000013A) must map to an antivirus message."""
        msg = conversion_worker._parse_ffmpeg_error("", 3221225786)

        assert "antivirus" in msg.lower() or "security software" in msg.lower()


@pytest.mark.integration
class TestConversionWorkerIntegration:
    """Integration tests for ConversionWorker with stub subprocess."""

    def test_successful_conversion_workflow(
        self, conversion_worker, stub_callback_bridge, temp_dir
    ):
        """Test complete successful conversion workflow."""
        conversion_worker._ffmpeg_path = Path("/usr/bin/ffmpeg")

        captured_calls = []

        class StubSuccessProcess:
            """Stub process that simulates a successful FFmpeg conversion."""

            stdout = [
                "  Duration: 00:02:30.00, start: 0.000000",
                "out_time_ms=75000000",
                "out_time_ms=150000000",
            ]
            returncode = 0

            def wait(self):
                pass

        stub_proc = StubSuccessProcess()

        def stub_popen(cmd, **kwargs):
            captured_calls.append(cmd)
            return stub_proc

        conversion_worker._popen_fn = stub_popen

        with patch.object(conversion_worker, "_validate_conversion_prerequisites"):
            # Create temp conversion directory and file to simulate FFmpeg output
            conversion_worker.temp_dir.mkdir(parents=True, exist_ok=True)
            conversion_worker.converting_file_path.write_text("converted audio content")

            # Run conversion
            conversion_worker.run()

        # Verify FFmpeg was called correctly
        assert len(captured_calls) == 1
        cmd = captured_calls[0]
        # Check that the FFmpeg path appears in the command (platform-agnostic)
        assert str(conversion_worker._ffmpeg_path) in cmd
        assert conversion_worker.input_file in cmd
        assert str(conversion_worker.converting_file_path) in cmd

        # Verify progress signals were emitted
        assert len(stub_callback_bridge.progress_calls) >= 1

        # Verify completion signal was emitted
        assert len(stub_callback_bridge.completed_calls) == 1
        completion = stub_callback_bridge.completed_calls[0]
        assert completion["cloudcast_url"] == "https://mixcloud.com/test/mix"
        assert completion["file_path"] == str(conversion_worker.final_file_path)
        assert completion["task_type"] == "conversion"

        # Verify file was moved to final location
        assert conversion_worker.final_file_path.exists()
        assert conversion_worker.final_file_path.read_text() == "converted audio content"

    def test_conversion_failure_handling(self, conversion_worker, stub_callback_bridge):
        """Test handling of FFmpeg conversion failure."""
        conversion_worker._ffmpeg_path = Path("/usr/bin/ffmpeg")

        class StubFailProcess:
            """Stub process that simulates FFmpeg failing with exit code 1."""

            stdout = ["Some error output"]
            returncode = 1

            def wait(self):
                pass

        stub_proc = StubFailProcess()

        def stub_popen(cmd, **kwargs):
            return stub_proc

        conversion_worker._popen_fn = stub_popen

        # Run conversion (should handle error gracefully)
        conversion_worker.run()

        # Verify error signal was emitted
        assert len(stub_callback_bridge.error_calls) == 1
        error = stub_callback_bridge.error_calls[0]
        assert error["cloudcast_url"] == "https://mixcloud.com/test/mix"
        assert "Conversion failed" in error["error_msg"]
        assert error["task_type"] == "conversion"

    def test_full_error_message_single_conversion_failed_prefix(
        self, conversion_worker, stub_callback_bridge
    ):
        """Regression guard: end-to-end error for exit code 3221225786 must have exactly one prefix.

        Before the fix, _parse_ffmpeg_error returned "Conversion failed: ..." which run()
        then wrapped again as f"Conversion failed: {str(e)}", producing a double prefix.
        This test also verifies the antivirus message reaches the user.
        """
        conversion_worker._ffmpeg_path = Path("/usr/bin/ffmpeg")

        class StubAntivirusExitProcess:
            """Stub process that simulates the Windows antivirus exit code."""

            stdout = []
            returncode = 3221225786

            def wait(self):
                pass

        stub_proc = StubAntivirusExitProcess()

        def stub_popen(cmd, **kwargs):
            return stub_proc

        conversion_worker._popen_fn = stub_popen

        with patch.object(conversion_worker, "_validate_conversion_prerequisites"):
            conversion_worker.run()

        assert len(stub_callback_bridge.error_calls) == 1
        error_msg = stub_callback_bridge.error_calls[0]["error_msg"]

        # Exactly one "Conversion failed: " prefix — not two
        assert error_msg.startswith("Conversion failed: ")
        assert not error_msg.startswith("Conversion failed: Conversion failed: ")

        # Must surface the antivirus explanation to the user
        assert "antivirus" in error_msg.lower() or "security software" in error_msg.lower()

    def test_cleanup_operations(self, conversion_worker, temp_dir):
        """Test file cleanup operations."""
        # Create files to test cleanup
        conversion_worker.temp_dir.mkdir(parents=True, exist_ok=True)
        conversion_worker.converting_file_path.write_text("partial conversion")

        # Test cleanup of partial conversion
        conversion_worker._cleanup_partial_conversion()

        # Verify files were cleaned up
        assert not conversion_worker.converting_file_path.exists()


@pytest.mark.unit
class TestConversionWorkerEdgeCases:
    """Test edge cases and error conditions."""

    def test_conversion_with_special_characters_in_filename(
        self, temp_dir, stub_callback_bridge, stub_settings_manager, stub_license_manager
    ):
        """Test conversion with special characters in filename."""
        # Create input file with special characters
        special_filename = "test audio [2024] (remix).webm"
        input_file = temp_dir / special_filename
        input_file.write_text("audio content")

        worker = ConversionWorker(
            cloudcast_url="https://mixcloud.com/test/special-mix",
            input_file=str(input_file),
            target_format="mp3",
            download_dir=str(temp_dir),
            callback_bridge=stub_callback_bridge,
            settings_manager=stub_settings_manager,
            license_manager=stub_license_manager,
        )

        # Should handle special characters in filename
        assert worker.final_filename == "test audio [2024] (remix).mp3"

    def test_conversion_with_very_long_filename(
        self, temp_dir, stub_callback_bridge, stub_settings_manager, stub_license_manager
    ):
        """Test conversion with very long filename."""
        # Create input file with long filename
        long_name = "a" * 200 + ".webm"
        input_file = temp_dir / long_name
        input_file.write_text("audio content")

        worker = ConversionWorker(
            cloudcast_url="https://mixcloud.com/test/long-mix",
            input_file=str(input_file),
            target_format="mp3",
            download_dir=str(temp_dir),
            callback_bridge=stub_callback_bridge,
            settings_manager=stub_settings_manager,
            license_manager=stub_license_manager,
        )

        # Should handle long filenames
        expected_filename = "a" * 200 + ".mp3"
        assert worker.final_filename == expected_filename
