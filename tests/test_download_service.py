"""Tests for DownloadService."""

import pytest
from typing import Callable

from app.services.download_service import DownloadService
from tests.stubs import StubDownloadService


class TestDownloadService:
    """Test cases for DownloadService."""

    def test_init_with_callbacks(self):
        """Test initialization with callback functions."""
        progress_calls = []
        error_calls = []
        
        def progress_callback(item: str, progress: str) -> None:
            progress_calls.append((item, progress))
            
        def error_callback(error: str) -> None:
            error_calls.append(error)
        
        service = DownloadService(
            progress_callback=progress_callback,
            error_callback=error_callback
        )
        
        assert service.progress_callback is progress_callback
        assert service.error_callback is error_callback

    def test_init_without_callbacks(self):
        """Test initialization without callback functions."""
        service = DownloadService()
        
        assert service.progress_callback is None
        assert service.error_callback is None

    def test_download_cloudcasts_success(self):
        """Test successful cloudcast downloads."""
        service = StubDownloadService()
        urls = [
            "https://www.mixcloud.com/user1/mix1/",
            "https://www.mixcloud.com/user1/mix2/"
        ]
        directory = "/fake/downloads"
        
        service.download_cloudcasts(urls, directory)
        
        assert service.downloaded_urls == urls
        assert service.download_directory == directory
        assert not service.is_cancelled

    def test_download_cloudcasts_no_directory(self):
        """Test download with missing directory."""
        service = StubDownloadService()
        
        with pytest.raises(ValueError) as exc:
            service.download_cloudcasts(["https://example.com/mix/"], "")
            
        assert "No download directory provided" in str(exc.value)

    def test_download_cloudcasts_with_error(self):
        """Test download with simulated error."""
        service = StubDownloadService()
        service.set_download_error(True, "Network timeout")
        
        with pytest.raises(Exception) as exc:
            service.download_cloudcasts(["https://example.com/mix/"], "/fake/path")
            
        assert "Network timeout" in str(exc.value)

    def test_download_single_cloudcast(self):
        """Test downloading a single cloudcast."""
        service = StubDownloadService()
        url = "https://www.mixcloud.com/user1/mix1/"
        directory = "/fake/downloads"
        
        service.download_single_cloudcast(url, directory)
        
        assert service.downloaded_urls == [url]
        assert service.download_directory == directory

    def test_cancel_downloads(self):
        """Test cancelling downloads."""
        service = StubDownloadService()
        
        service.cancel_downloads()
        
        assert service.is_cancelled

    def test_set_callbacks_after_init(self):
        """Test setting callbacks after initialization."""
        service = DownloadService()
        
        progress_calls = []
        error_calls = []
        
        def progress_callback(item: str, progress: str) -> None:
            progress_calls.append((item, progress))
            
        def error_callback(error: str) -> None:
            error_calls.append(error)
        
        service.set_progress_callback(progress_callback)
        service.set_error_callback(error_callback)
        
        assert service.progress_callback is progress_callback
        assert service.error_callback is error_callback

    def test_progress_callback_invocation(self):
        """Test that progress callback is invoked during downloads."""
        progress_calls = []
        
        def progress_callback(item: str, progress: str) -> None:
            progress_calls.append((item, progress))
        
        service = StubDownloadService()
        service.set_progress_callback(progress_callback)
        
        urls = ["https://www.mixcloud.com/user1/test-mix/"]
        service.download_cloudcasts(urls, "/fake/path")
        
        # Should have received progress updates
        assert len(progress_calls) > 0
        assert any("test mix" in call[0] for call in progress_calls)
        assert any("Done" in call[1] for call in progress_calls)

    def test_error_callback_invocation(self):
        """Test that error callback is invoked on errors."""
        error_calls = []
        
        def error_callback(error: str) -> None:
            error_calls.append(error)
        
        service = StubDownloadService()
        service.set_error_callback(error_callback)
        service.set_download_error(True, "Test error")
        
        with pytest.raises(Exception):
            service.download_cloudcasts(["https://example.com/mix/"], "/fake/path")
        
        assert len(error_calls) == 1
        assert "Test error" in error_calls[0]

    def test_create_download_options_default(self):
        """Test creating download options with default template."""
        service = DownloadService()
        directory = "/fake/downloads"
        
        options = service.create_download_options(directory)
        
        assert "outtmpl" in options
        assert directory in options["outtmpl"]
        assert "%(uploader)s - %(title)s.%(ext)s" in options["outtmpl"]
        assert "progress_hooks" in options
        assert options["verbose"] is False

    def test_create_download_options_custom_template(self):
        """Test creating download options with custom template."""
        service = DownloadService()
        directory = "/fake/downloads"
        custom_template = "%(title)s.%(ext)s"
        
        options = service.create_download_options(directory, custom_template)
        
        assert custom_template in options["outtmpl"]
        assert directory in options["outtmpl"]

    def test_track_progress_with_cancelled_download(self):
        """Test progress tracking when download is cancelled."""
        progress_calls = []
        
        def progress_callback(item: str, progress: str) -> None:
            progress_calls.append((item, progress))
        
        service = DownloadService()
        service.set_progress_callback(progress_callback)
        service.cancel_downloads()  # Cancel before tracking
        
        # Simulate progress data
        progress_data = {
            "filename": "/fake/downloads/User - Track.mp3",
            "status": "downloading",
            "_percent_str": "50%",
            "_total_bytes_estimate_str": "10MB",
            "_speed_str": "500KB/s"
        }
        
        service._track_progress(progress_data)
        
        # Should not call progress callback when cancelled
        assert len(progress_calls) == 0

    def test_track_progress_malformed_data(self):
        """Test progress tracking with malformed progress data."""
        progress_calls = []
        
        def progress_callback(item: str, progress: str) -> None:
            progress_calls.append((item, progress))
        
        service = DownloadService()
        service.set_progress_callback(progress_callback)
        
        # Simulate malformed progress data
        progress_data = {}  # Missing all expected fields
        
        service._track_progress(progress_data)
        
        # Should handle gracefully without calling callback for malformed data
        assert len(progress_calls) == 0