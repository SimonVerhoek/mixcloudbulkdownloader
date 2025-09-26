"""Tests for download service FFmpeg integration."""

import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from app.services.download_service import DownloadService
from tests.stubs.download_stubs import FFmpegAwareDownloadService
from tests.stubs.ffmpeg_stubs import StubFFmpegService
from tests.stubs.subprocess_stubs import patch_subprocess


class TestFFmpegPathResolution:
    """Test FFmpeg executable path resolution."""
    
    def test_get_ffmpeg_path_windows(self):
        """Test FFmpeg path resolution on Windows."""
        service = FFmpegAwareDownloadService()
        service.set_platform("windows")
        
        path = service._get_ffmpeg_path()
        
        assert "windows" in str(path)
        assert "ffmpeg.exe" in str(path)
        assert service.get_ffmpeg_path_calls() == ["windows"]
        
    def test_get_ffmpeg_path_macos(self):
        """Test FFmpeg path resolution on macOS."""
        service = FFmpegAwareDownloadService()
        service.set_platform("darwin")
        
        path = service._get_ffmpeg_path()
        
        assert "macos" in str(path)
        assert "ffmpeg" in str(path)
        assert not str(path).endswith(".exe")
        assert service.get_ffmpeg_path_calls() == ["darwin"]
        
    def test_get_ffmpeg_path_unsupported_platform(self):
        """Test FFmpeg path resolution on unsupported platform."""
        service = FFmpegAwareDownloadService()
        service.set_platform("freebsd")
        
        with pytest.raises(RuntimeError) as exc_info:
            service._get_ffmpeg_path()
            
        assert "Unsupported OS: freebsd" in str(exc_info.value)
        assert service.get_ffmpeg_path_calls() == ["freebsd"]
        
    def test_get_ffmpeg_path_default_platform(self):
        """Test FFmpeg path resolution with default platform detection."""
        service = FFmpegAwareDownloadService()
        
        # Should not raise exception and should call platform detection
        path = service._get_ffmpeg_path()
        
        assert isinstance(path, Path)
        assert service.get_ffmpeg_path_calls() == ["default"]


class TestFFmpegAvailabilityChecking:
    """Test FFmpeg availability verification."""
    
    def test_verify_ffmpeg_availability_available(self):
        """Test FFmpeg availability when executable exists."""
        service = FFmpegAwareDownloadService()
        service.set_ffmpeg_availability(True)
        service.set_ffmpeg_path_exists(True)
        
        result = service.verify_ffmpeg_availability()
        
        assert result is True
        checks = service.get_availability_checks()
        assert len(checks) == 1
        assert checks[0]["available"] is True
        assert checks[0]["platform"] == "default"
        
    def test_verify_ffmpeg_availability_unavailable(self):
        """Test FFmpeg availability when service is unavailable."""
        service = FFmpegAwareDownloadService()
        service.set_ffmpeg_availability(False)
        
        result = service.verify_ffmpeg_availability()
        
        assert result is False
        checks = service.get_availability_checks()
        assert len(checks) == 1
        assert checks[0]["available"] is False
        
    def test_verify_ffmpeg_availability_path_missing(self):
        """Test FFmpeg availability when executable doesn't exist."""
        service = FFmpegAwareDownloadService()
        service.set_ffmpeg_availability(True)
        service.set_ffmpeg_path_exists(False)
        
        result = service.verify_ffmpeg_availability()
        
        assert result is False
        
    def test_verify_ffmpeg_availability_unsupported_platform(self):
        """Test FFmpeg availability on unsupported platform."""
        service = FFmpegAwareDownloadService()
        service.set_platform("freebsd")
        
        result = service.verify_ffmpeg_availability()
        
        assert result is False
        checks = service.get_availability_checks()
        assert len(checks) == 1
        assert checks[0]["platform"] == "freebsd"
        assert checks[0]["available"] is False


class TestAudioConversion:
    """Test audio conversion functionality."""
    
    def test_convert_audio_success(self):
        """Test successful audio conversion."""
        progress_calls = []
        
        def progress_callback(item_name: str, message: str) -> None:
            progress_calls.append((item_name, message))
            
        service = FFmpegAwareDownloadService(progress_callback=progress_callback)
        
        input_path = "/test/input.mp3"
        output_path = "/test/output.flac"
        target_format = "flac"
        bitrate = 192
        
        service.convert_audio(input_path, output_path, target_format, bitrate)
        
        # Verify conversion was recorded
        conversions = service.get_conversions()
        assert len(conversions) == 1
        conversion = conversions[0]
        assert conversion["input_path"] == input_path
        assert conversion["output_path"] == output_path
        assert conversion["target_format"] == target_format
        assert conversion["bitrate_k"] == bitrate
        
        # Verify progress callbacks were made
        progress_calls_from_service = service.get_conversion_progress_calls()
        assert len(progress_calls_from_service) > 0
        assert any("Converting to flac" in msg for _, msg in progress_calls_from_service)
        assert any("Conversion finished!" in msg for _, msg in progress_calls_from_service)
        
        # Verify progress callback was called
        assert len(progress_calls) > 0
        
    def test_convert_audio_failure(self):
        """Test audio conversion failure."""
        error_calls = []
        
        def error_callback(message: str) -> None:
            error_calls.append(message)
            
        service = FFmpegAwareDownloadService(error_callback=error_callback)
        service.set_conversion_failure(True, "FFmpeg failed with code 1")
        
        with pytest.raises(RuntimeError) as exc_info:
            service.convert_audio("/test/input.mp3", "/test/output.flac", "flac")
            
        assert "FFmpeg failed with code 1" in str(exc_info.value)
        
        # Verify conversion was still recorded
        conversions = service.get_conversions()
        assert len(conversions) == 1
        
    def test_convert_audio_multiple_formats(self):
        """Test conversion to multiple audio formats."""
        service = FFmpegAwareDownloadService()
        
        test_cases = [
            ("/test/input.mp3", "/test/output.flac", "flac", 0),  # Lossless
            ("/test/input.mp3", "/test/output.mp3", "mp3", 192),
            ("/test/input.mp3", "/test/output.aac", "aac", 128),
            ("/test/input.mp3", "/test/output.wav", "wav", 0),  # Lossless
        ]
        
        for input_path, output_path, target_format, bitrate in test_cases:
            service.convert_audio(input_path, output_path, target_format, bitrate)
            
        conversions = service.get_conversions()
        assert len(conversions) == 4
        
        # Verify all formats were handled
        formats = [conv["target_format"] for conv in conversions]
        assert set(formats) == {"flac", "mp3", "aac", "wav"}
        
    def test_convert_audio_with_progress_tracking(self):
        """Test audio conversion with detailed progress tracking."""
        service = FFmpegAwareDownloadService()
        
        service.convert_audio("/test/song.mp3", "/test/song.flac", "flac")
        
        progress_calls = service.get_conversion_progress_calls()
        
        # Verify progress sequence
        assert len(progress_calls) >= 6  # At least 6 progress updates
        
        # Check for specific progress patterns
        progress_messages = [msg for _, msg in progress_calls]
        assert any("0.00%" in msg for msg in progress_messages)
        assert any("25.50%" in msg for msg in progress_messages)
        assert any("50.00%" in msg for msg in progress_messages)
        assert any("75.25%" in msg for msg in progress_messages)
        assert any("100.00%" in msg for msg in progress_messages)
        assert any("Conversion finished!" in msg for msg in progress_messages)
        
        # Verify item names are extracted correctly
        item_names = [name for name, _ in progress_calls]
        assert all(name == "song" for name in item_names)


class TestFFmpegServiceIntegration:
    """Test integration with real DownloadService (using mocks)."""
    
    @patch('app.services.download_service.platform.system')
    def test_real_service_ffmpeg_path_windows(self, mock_system):
        """Test real service FFmpeg path resolution on Windows."""
        mock_system.return_value = "Windows"
        
        service = DownloadService()
        path = service._get_ffmpeg_path()
        
        assert "windows" in str(path)
        assert "ffmpeg.exe" in str(path)
        
    @patch('app.services.download_service.platform.system')
    def test_real_service_ffmpeg_path_macos(self, mock_system):
        """Test real service FFmpeg path resolution on macOS."""
        mock_system.return_value = "Darwin"
        
        service = DownloadService()
        path = service._get_ffmpeg_path()
        
        assert "macos" in str(path)
        assert path.name == "ffmpeg"
        
    @patch('app.services.download_service.platform.system')
    def test_real_service_ffmpeg_path_unsupported(self, mock_system):
        """Test real service FFmpeg path resolution on unsupported platform."""
        mock_system.return_value = "Linux"
        
        service = DownloadService()
        
        with pytest.raises(RuntimeError) as exc_info:
            service._get_ffmpeg_path()
            
        assert "Unsupported OS: linux" in str(exc_info.value)
        
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('app.services.download_service.platform.system')
    def test_real_service_verify_ffmpeg_availability_exists(self, mock_system, mock_is_file, mock_exists):
        """Test real service FFmpeg availability when file exists."""
        mock_system.return_value = "Darwin"
        mock_exists.return_value = True
        mock_is_file.return_value = True
        
        service = DownloadService()
        result = service.verify_ffmpeg_availability()
        
        assert result is True
        
    @patch('pathlib.Path.exists')
    @patch('app.services.download_service.platform.system')
    def test_real_service_verify_ffmpeg_availability_missing(self, mock_system, mock_exists):
        """Test real service FFmpeg availability when file doesn't exist."""
        mock_system.return_value = "Darwin"
        mock_exists.return_value = False
        
        service = DownloadService()
        result = service.verify_ffmpeg_availability()
        
        assert result is False
        
    @patch('app.services.download_service.platform.system')
    def test_real_service_verify_ffmpeg_availability_unsupported_os(self, mock_system):
        """Test real service FFmpeg availability on unsupported OS."""
        mock_system.return_value = "Linux"
        
        service = DownloadService()
        result = service.verify_ffmpeg_availability()
        
        assert result is False


class TestFFmpegWithSubprocessStub:
    """Test FFmpeg integration with subprocess stubbing."""
    
    @pytest.mark.parametrize("mock_platform", ["Darwin", "Windows"])
    @patch('app.services.download_service.platform.system')
    @patch('subprocess.Popen')
    def test_convert_audio_with_subprocess_stub(self, mock_popen, mock_platform_system, mock_platform):
        """Test audio conversion using subprocess mock."""
        from tests.stubs.ffmpeg_stubs import StubFFmpegProcess
        
        # Configure platform mock
        mock_platform_system.return_value = mock_platform
        
        progress_calls = []
        
        def progress_callback(item_name: str, message: str) -> None:
            progress_calls.append((item_name, message))
        
        # Create a stub FFmpeg process
        def create_stub_process(cmd, **kwargs):
            process = StubFFmpegProcess(cmd, **kwargs)
            return process
            
        mock_popen.side_effect = create_stub_process
        service = DownloadService(progress_callback=progress_callback)
        
        # The mock will handle the FFmpeg process simulation
        service.convert_audio("/test/input.mp3", "/test/output.flac", "flac", 192)
        
        # Verify subprocess was called
        assert mock_popen.called
        call_args = mock_popen.call_args[0][0]  # First positional argument (cmd)
        
        # Verify FFmpeg command structure
        assert any("ffmpeg" in str(arg) for arg in call_args)
        assert "-i" in call_args
        assert "/test/input.mp3" in call_args
        assert "/test/output.flac" in call_args
        assert "-c:a" in call_args
        
    @pytest.mark.parametrize("mock_platform", ["Darwin", "Windows"])
    @patch('app.services.download_service.platform.system')
    @patch('subprocess.Popen')
    def test_convert_audio_subprocess_failure(self, mock_popen, mock_platform_system, mock_platform):
        """Test audio conversion failure with subprocess mock."""
        from tests.stubs.ffmpeg_stubs import StubFFmpegProcess
        
        # Configure platform mock
        mock_platform_system.return_value = mock_platform
        
        # Configure subprocess to return failing FFmpeg process
        def create_failing_process(cmd, **kwargs):
            process = StubFFmpegProcess(cmd, **kwargs)
            process.should_fail = True
            process.failure_code = 1
            process.failure_message = "FFmpeg conversion failed"
            return process
            
        mock_popen.side_effect = create_failing_process
        service = DownloadService()
        
        with pytest.raises(RuntimeError) as exc_info:
            service.convert_audio("/test/input.mp3", "/test/output.flac", "flac")
            
        assert "FFmpeg failed with code 1" in str(exc_info.value)


class TestFFmpegStubConfiguration:
    """Test FFmpeg stub configuration and state management."""
    
    def test_ffmpeg_stub_reset(self):
        """Test FFmpeg stub state reset."""
        service = FFmpegAwareDownloadService()
        
        # Make some calls
        service.verify_ffmpeg_availability()
        service.convert_audio("/test/input.mp3", "/test/output.flac", "flac")
        service.set_platform("windows")
        
        # Verify state exists
        assert len(service.get_availability_checks()) == 1
        assert len(service.get_conversions()) == 1
        assert len(service.get_ffmpeg_path_calls()) == 0  # No path calls yet
        
        # Reset and verify clean state
        service.reset()
        
        assert len(service.get_availability_checks()) == 0
        assert len(service.get_conversions()) == 0
        assert len(service.get_ffmpeg_path_calls()) == 0
        assert len(service.get_conversion_progress_calls()) == 0
        
    def test_ffmpeg_stub_advanced_configuration(self):
        """Test advanced FFmpeg stub configuration."""
        service = FFmpegAwareDownloadService()
        ffmpeg_stub = service.get_ffmpeg_stub()
        
        # Configure complex scenario
        ffmpeg_stub.set_availability(False)
        ffmpeg_stub.set_path_exists(True)  # Path exists but service unavailable
        ffmpeg_stub.set_conversion_failure(True, "Custom error message")
        
        # Test availability (should be False due to service unavailable)
        assert service.verify_ffmpeg_availability() is False
        
        # Test conversion failure
        with pytest.raises(RuntimeError) as exc_info:
            service.convert_audio("/test/input.mp3", "/test/output.flac", "flac")
            
        assert "Custom error message" in str(exc_info.value)
        
    def test_multiple_service_instances_independence(self):
        """Test that multiple service instances don't interfere."""
        service1 = FFmpegAwareDownloadService()
        service2 = FFmpegAwareDownloadService()
        
        # Configure differently
        service1.set_platform("windows")
        service1.set_ffmpeg_availability(True)
        
        service2.set_platform("darwin")
        service2.set_ffmpeg_availability(False)
        
        # Test independence
        service1._get_ffmpeg_path()  # Should work
        assert service1.get_ffmpeg_path_calls() == ["windows"]
        assert service2.get_ffmpeg_path_calls() == []
        
        assert service1.verify_ffmpeg_availability() is True
        assert service2.verify_ffmpeg_availability() is False
        
        # Verify no cross-contamination
        assert len(service1.get_availability_checks()) == 1
        assert len(service2.get_availability_checks()) == 1
        assert service1.get_availability_checks()[0]["platform"] == "windows"
        assert service2.get_availability_checks()[0]["platform"] == "darwin"