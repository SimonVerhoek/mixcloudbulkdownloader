"""Pytest configuration and fixtures for Mixcloud Bulk Downloader tests."""

import os
import sys
from pathlib import Path

import pytest

# Load test environment variables at import time, before any app modules are imported
from environs import Env


_project_root = Path(__file__).parent.parent
_test_env_file = _project_root / ".env.test"
if _test_env_file.exists():
    _env = Env()
    _env.read_env(str(_test_env_file))

from tests.stubs.api_stubs import StubMixcloudAPIService
from tests.stubs.file_stubs import StubFileService
from tests.stubs.github_api_stubs import FakeGitHubHTTPClient, StubGitHubUpdateService


def get_valid_threading_test_values():
    """Get valid threading values for the current test environment.

    Returns:
        tuple: (valid_parallel_downloads, valid_parallel_conversions)
    """
    from app.consts.settings import (
        DEFAULT_ENABLE_AUDIO_CONVERSION,
        DEFAULT_MAX_PARALLEL_CONVERSIONS,
        DEFAULT_MAX_PARALLEL_DOWNLOADS,
        PARALLEL_CONVERSIONS_OPTIONS,
        PARALLEL_DOWNLOADS_OPTIONS,
        SETTING_ENABLE_AUDIO_CONVERSION,
    )

    # Use defaults if they're valid, otherwise use first available option
    valid_downloads = (
        DEFAULT_MAX_PARALLEL_DOWNLOADS
        if DEFAULT_MAX_PARALLEL_DOWNLOADS in PARALLEL_DOWNLOADS_OPTIONS
        else PARALLEL_DOWNLOADS_OPTIONS[0]
    )
    valid_conversions = (
        DEFAULT_MAX_PARALLEL_CONVERSIONS
        if DEFAULT_MAX_PARALLEL_CONVERSIONS in PARALLEL_CONVERSIONS_OPTIONS
        else PARALLEL_CONVERSIONS_OPTIONS[0]
    )

    return valid_downloads, valid_conversions


def get_mock_settings_for_threading():
    """Get mock settings dict that works in current environment.

    Returns:
        dict: Mock settings with valid threading values
    """
    valid_downloads, valid_conversions = get_valid_threading_test_values()

    return {
        "default_download_directory": None,
        "default_audio_format": "MP3",
        SETTING_ENABLE_AUDIO_CONVERSION: DEFAULT_ENABLE_AUDIO_CONVERSION,
        "max_parallel_downloads": valid_downloads,
        "max_parallel_conversions": valid_conversions,
    }


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for the entire test session."""
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()

    yield app

    # Clean up
    if app:
        app.quit()


@pytest.fixture
def qtbot(qapp, request):
    """Provide qtbot for Qt widget testing."""
    from pytestqt.qtbot import QtBot

    result = QtBot(request)
    return result


@pytest.fixture
def stub_api_service():
    """Provide stub API service for testing."""
    service = StubMixcloudAPIService()
    yield service
    # Reset state after each test
    service.fake_client.request_count = 0
    service.fake_client.should_raise_network_error = False
    service.fake_client.should_raise_http_error = False


@pytest.fixture
def stub_file_service():
    """Provide stub file service for testing."""
    service = StubFileService()
    yield service
    # Reset state after each test
    service.reset()


@pytest.fixture
def stub_github_update_service():
    """Provide stub GitHub update service for testing."""
    fake_client = FakeGitHubHTTPClient()
    service = StubGitHubUpdateService(fake_client)
    yield service, fake_client
    # Reset state after each test
    fake_client.request_count = 0
    fake_client.should_raise_network_error = False
    fake_client.should_raise_http_error = False


@pytest.fixture
def sample_user():
    """Provide sample MixcloudUser for testing."""
    from app.data_classes import MixcloudUser

    return MixcloudUser(
        key="/testuser/",
        name="Test User",
        pictures={"large": "https://example.com/large.jpg"},
        url="https://www.mixcloud.com/testuser/",
        username="testuser",
    )


@pytest.fixture
def sample_cloudcast(sample_user):
    """Provide sample Cloudcast for testing."""
    from app.data_classes import Cloudcast

    return Cloudcast(
        name="Test Mix", url="https://www.mixcloud.com/testuser/test-mix/", user=sample_user
    )


@pytest.fixture
def sample_cloudcasts(sample_user):
    """Provide list of sample Cloudcasts for testing."""
    from app.data_classes import Cloudcast

    cloudcasts = []
    for i in range(5):
        cloudcast = Cloudcast(
            name=f"Test Mix {i+1}",
            url=f"https://www.mixcloud.com/testuser/test-mix-{i+1}/",
            user=sample_user,
        )
        cloudcasts.append(cloudcast)

    return cloudcasts


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "qt: Tests requiring Qt application")


# Test collection customization
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add qt marker to widget tests
        if "test_widgets" in str(item.fspath):
            item.add_marker(pytest.mark.qt)

        # Add unit marker to service tests
        if any(name in str(item.fspath) for name in ["test_api_service", "test_file_service"]):
            item.add_marker(pytest.mark.unit)

        # Add integration marker to thread tests
        if "test_threads" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# Skip tests that require specific conditions
def pytest_runtest_setup(item):
    """Setup function called before each test."""
    # Unit tests should never require Qt/GUI
    if item.get_closest_marker("unit"):
        # Unit tests should not require Qt fixtures
        if any(fixture in item.fixturenames for fixture in ["qapp", "qtbot"]):
            pytest.skip("Unit tests cannot use Qt fixtures")
        return
