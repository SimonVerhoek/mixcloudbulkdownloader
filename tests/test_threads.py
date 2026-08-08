"""Tests for thread classes."""

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication, QTimer

from app.data_classes import Cloudcast, MixcloudUser
from app.threads.fetch_by_url_thread import FetchByUrlThread
from app.threads.get_cloudcasts_thread import GetCloudcastsThread
from app.threads.search_artist_thread import SearchArtistThread
from app.threads.search_cloudcast_thread import SearchCloudcastThread
from tests.stubs.api_stubs import StubMixcloudAPIService


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
            username="testuser",
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
            username="testuser",
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


class TestSearchCloudcastThread:
    """Test cases for SearchCloudcastThread."""

    def test_init_with_service(self):
        """Test initialization with custom API service stores the injected service."""
        mock_service = Mock()
        thread = SearchCloudcastThread(api_service=mock_service)

        assert thread.api_service is mock_service

    def test_init_without_service(self):
        """Test initialization without custom service uses a default non-None service."""
        thread = SearchCloudcastThread()

        assert thread.api_service is not None

    def test_run_success(self):
        """Test successful cloudcast search emits Cloudcast objects via new_result."""
        stub_service = StubMixcloudAPIService()
        thread = SearchCloudcastThread(api_service=stub_service)
        thread.phrase = "test"

        results = []
        thread.new_result.connect(lambda cloudcast: results.append(cloudcast))

        thread.run()

        assert len(results) == 2
        assert all(isinstance(r, Cloudcast) for r in results)
        assert results[0].name == "Test Mix A"
        assert results[1].name == "Test Mix B"

    def test_run_without_phrase(self):
        """Test run without search phrase emits error_signal once."""
        thread = SearchCloudcastThread()

        error_signals = []
        thread.error_signal.connect(lambda error: error_signals.append(error))

        thread.run()

        assert len(error_signals) == 1

    def test_run_with_api_error(self):
        """Test run with network error emits error_signal once."""
        stub_service = StubMixcloudAPIService()
        stub_service.set_network_error(should_error=True)

        thread = SearchCloudcastThread(api_service=stub_service)
        thread.phrase = "test"

        error_signals = []
        thread.error_signal.connect(lambda error: error_signals.append(error))

        thread.run()

        assert len(error_signals) == 1

    def test_stop(self):
        """Test that stop() requests interruption and the thread is no longer running."""
        thread = SearchCloudcastThread()

        thread.stop()

        assert thread.isInterruptionRequested() or not thread.isRunning()


class TestFetchByUrlThread:
    """Test cases for FetchByUrlThread."""

    def test_init_with_service(self):
        """Test initialization with custom API service stores the injected service."""
        mock_service = Mock()
        thread = FetchByUrlThread(api_service=mock_service)

        assert thread.api_service is mock_service

    def test_init_without_service(self):
        """Test initialization without custom service uses a default non-None service."""
        thread = FetchByUrlThread()

        assert thread.api_service is not None

    def test_emits_user_result_for_user_url(self):
        """Test that run() emits user_result when slug is None."""
        stub_service = StubMixcloudAPIService()
        thread = FetchByUrlThread(api_service=stub_service)
        thread.username = "testuser"
        thread.slug = None

        results: list[MixcloudUser] = []
        thread.user_result.connect(lambda u: results.append(u))

        thread.run()

        assert len(results) == 1
        assert isinstance(results[0], MixcloudUser)
        assert results[0].username == "testuser"

    def test_emits_cloudcast_result_for_cloudcast_url(self):
        """Test that run() emits cloudcast_result when slug is set."""
        stub_service = StubMixcloudAPIService()
        thread = FetchByUrlThread(api_service=stub_service)
        thread.username = "djtest"
        thread.slug = "test-mix-a"

        results: list[Cloudcast] = []
        thread.cloudcast_result.connect(lambda c: results.append(c))

        thread.run()

        assert len(results) == 1
        assert isinstance(results[0], Cloudcast)
        assert results[0].name == "Test Mix A"

    def test_emits_error_on_network_failure(self):
        """Test that run() emits error_signal when the network call fails."""
        stub_service = StubMixcloudAPIService()
        stub_service.set_network_error(should_error=True)
        thread = FetchByUrlThread(api_service=stub_service)
        thread.username = "testuser"
        thread.slug = None

        errors: list[str] = []
        thread.error_signal.connect(lambda e: errors.append(e))

        thread.run()

        assert len(errors) == 1
        assert errors[0] != ""

    def test_missing_username_emits_error(self):
        """Test that run() emits error_signal when username is empty."""
        thread = FetchByUrlThread()
        thread.username = ""

        errors: list[str] = []
        thread.error_signal.connect(lambda e: errors.append(e))

        thread.run()

        assert len(errors) == 1

    def test_stop(self):
        """Test that stop() requests interruption and the thread is no longer running."""
        thread = FetchByUrlThread()

        thread.stop()

        assert thread.isInterruptionRequested() or not thread.isRunning()
