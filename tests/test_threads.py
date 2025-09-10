"""Tests for thread classes."""

import pytest
from unittest.mock import Mock
from PySide6.QtCore import QCoreApplication, QTimer

from app.threads.download_thread import DownloadThread
from app.threads.get_cloudcasts_thread import GetCloudcastsThread
from app.threads.search_artist_thread import SearchArtistThread
from app.data_classes import MixcloudUser, Cloudcast
from tests.stubs.api_stubs import StubMixcloudAPIService
from tests.stubs.download_stubs import StubDownloadService


class TestDownloadThread:
    """Test cases for DownloadThread."""

    def test_init_with_service(self):
        """Test initialization with custom download service."""
        mock_service = Mock()
        thread = DownloadThread(download_service=mock_service)
        
        assert thread.download_service is mock_service

    def test_init_without_service(self):
        """Test initialization without custom service."""
        thread = DownloadThread()
        
        assert thread.download_service is not None

    def test_run_success(self):
        """Test successful download execution."""
        stub_service = StubDownloadService()
        thread = DownloadThread(download_service=stub_service)
        
        thread.urls = ["https://example.com/mix1/", "https://example.com/mix2/"]
        thread.download_dir = "/fake/downloads"
        
        thread.run()
        
        assert stub_service.downloaded_urls == thread.urls
        assert stub_service.download_directory == thread.download_dir

    def test_run_emits_completion_signal(self):
        """Test that completion signal is emitted on successful download."""
        stub_service = StubDownloadService()
        thread = DownloadThread(download_service=stub_service)
        
        completion_signals = []
        thread.completion_signal.connect(lambda: completion_signals.append(True))
        
        thread.urls = ["https://example.com/mix1/"]
        thread.download_dir = "/fake/downloads"
        
        thread.run()
        
        assert len(completion_signals) == 1

    def test_run_with_error(self):
        """Test download execution with error."""
        stub_service = StubDownloadService()
        stub_service.set_download_error(True, "Network error")
        
        error_signals = []
        thread = DownloadThread(download_service=stub_service)
        thread.error_signal.connect(lambda error: error_signals.append(error))
        
        thread.urls = ["https://example.com/mix/"]
        thread.download_dir = "/fake/downloads"
        
        thread.run()
        
        assert len(error_signals) >= 1
        assert "Network error" in error_signals[0]

    def test_stop(self):
        """Test stopping download thread."""
        stub_service = StubDownloadService()
        thread = DownloadThread(download_service=stub_service)
        
        interrupt_signals = []
        thread.interrupt_signal.connect(lambda: interrupt_signals.append(True))
        
        thread.stop()
        
        assert stub_service.is_cancelled
        assert len(interrupt_signals) == 1


class TestGetCloudcastsThread:
    """Test cases for GetCloudcastsThread."""

    def test_init_with_service(self):
        """Test initialization with custom API service."""
        mock_service = Mock()
        thread = GetCloudcastsThread(api_service=mock_service)
        
        assert thread.api_service is mock_service

    def test_init_without_service(self):
        """Test initialization without custom service."""
        thread = GetCloudcastsThread()
        
        assert thread.api_service is not None

    def test_run_success(self):
        """Test successful cloudcast fetching."""
        stub_service = StubMixcloudAPIService()
        thread = GetCloudcastsThread(api_service=stub_service)
        
        test_user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser"
        )
        thread.user = test_user
        
        results = []
        thread.new_result.connect(lambda cloudcast: results.append(cloudcast))
        
        thread.run()
        
        # Should get results from first page
        assert len(results) >= 2
        assert all(isinstance(result, Cloudcast) for result in results)
        assert results[0].name == "Test Mix 1"

    def test_run_without_user(self):
        """Test run without user set."""
        thread = GetCloudcastsThread()
        
        error_signals = []
        thread.error_signal.connect(lambda error: error_signals.append(error))
        
        thread.run()
        
        assert len(error_signals) == 1
        assert "no user provided" in error_signals[0].lower()

    def test_run_with_api_error(self):
        """Test run with API error."""
        stub_service = StubMixcloudAPIService()
        stub_service.set_network_error(True)
        
        thread = GetCloudcastsThread(api_service=stub_service)
        test_user = MixcloudUser(
            key="/testuser/",
            name="Test User", 
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser"
        )
        thread.user = test_user
        
        error_signals = []
        thread.error_signal.connect(lambda error: error_signals.append(error))
        
        thread.run()
        
        assert len(error_signals) == 1

    def test_stop(self):
        """Test stopping cloudcast fetching thread."""
        thread = GetCloudcastsThread()
        
        interrupt_signals = []
        thread.interrupt_signal.connect(lambda: interrupt_signals.append(True))
        
        thread.stop()
        
        assert len(interrupt_signals) == 1


class TestSearchArtistThread:
    """Test cases for SearchArtistThread."""

    def test_init_with_service(self):
        """Test initialization with custom API service."""
        mock_service = Mock()
        thread = SearchArtistThread(api_service=mock_service)
        
        assert thread.api_service is mock_service

    def test_init_without_service(self):
        """Test initialization without custom service."""
        thread = SearchArtistThread()
        
        assert thread.api_service is not None

    def test_run_success(self):
        """Test successful user search."""
        stub_service = StubMixcloudAPIService()
        thread = SearchArtistThread(api_service=stub_service)
        thread.phrase = "test"
        
        results = []
        thread.new_result.connect(lambda user: results.append(user))
        
        thread.run()
        
        assert len(results) == 2
        assert all(isinstance(result, MixcloudUser) for result in results)
        assert results[0].username == "testuser"
        assert results[1].username == "anotheruser"

    def test_run_without_phrase(self):
        """Test run without search phrase."""
        thread = SearchArtistThread()
        
        error_signals = []
        thread.error_signal.connect(lambda error: error_signals.append(error))
        
        thread.run()
        
        assert len(error_signals) == 1
        assert "no search phrase provided" in error_signals[0].lower()

    def test_run_with_api_error(self):
        """Test run with API error."""
        stub_service = StubMixcloudAPIService()
        stub_service.set_network_error(True)
        
        thread = SearchArtistThread(api_service=stub_service)
        thread.phrase = "test"
        
        error_signals = []
        thread.error_signal.connect(lambda error: error_signals.append(error))
        
        thread.run()
        
        assert len(error_signals) == 1

    def test_show_suggestions_with_results(self):
        """Test show_suggestions method with results."""
        stub_service = StubMixcloudAPIService()
        thread = SearchArtistThread(api_service=stub_service)
        
        results = []
        thread.new_result.connect(lambda user: results.append(user))
        
        thread.show_suggestions("test")
        
        assert len(results) == 2

    def test_show_suggestions_with_error(self):
        """Test show_suggestions method with error."""
        stub_service = StubMixcloudAPIService()
        thread = SearchArtistThread(api_service=stub_service)
        
        error_signals = []
        thread.error_signal.connect(lambda error: error_signals.append(error))
        
        thread.show_suggestions("nonexistent")
        
        assert len(error_signals) == 1

    def test_stop(self):
        """Test stopping search thread."""
        thread = SearchArtistThread()
        
        thread.stop()
        
        # Thread should be requested to interrupt
        assert thread.isInterruptionRequested() or not thread.isRunning()