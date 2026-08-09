"""Unit tests for LicenseManager singleton and stub functionality."""

import time
from unittest.mock import create_autospec, patch

import pytest

from app.consts.license import (
    DEFAULT_LICENSE_BACKOFF_RATE,
    DEFAULT_LICENSE_RETRY_COUNT,
    DEFAULT_LICENSE_TIMEOUT,
    OFFLINE_GRACE_PERIOD_DAYS,
)
from app.services.license_manager import LicenseManager, license_manager
from app.services.settings_manager import SettingsManager


def _make_settings(
    email: str = "",
    license_key: str = "",
    last_successful_verification: float = 0.0,
) -> SettingsManager:
    """Create a spec'd mock SettingsManager with sensible defaults."""
    mock_settings = create_autospec(spec=SettingsManager, instance=True)
    mock_settings.email = email
    mock_settings.license_key = license_key
    mock_settings.last_successful_verification = last_successful_verification
    return mock_settings


@pytest.fixture
def fresh_license_manager():
    """Create a fresh LicenseManager instance for testing."""
    mock_settings = _make_settings()
    manager = LicenseManager(settings=mock_settings)
    return manager, mock_settings


class TestLicenseManagerStructure:
    """Test LicenseManager basic structure and initialization."""

    def test_license_manager_initialization(self, fresh_license_manager):
        """Test LicenseManager initializes correctly."""
        manager, mock_settings = fresh_license_manager

        assert manager.settings is mock_settings
        assert manager.is_pro is False

    def test_license_manager_has_required_methods(self):
        """Test LicenseManager has all required methods."""
        assert callable(LicenseManager.verify_license)
        assert callable(LicenseManager._send_request_to_licensing_server)
        assert callable(LicenseManager.check_offline_status)
        assert callable(LicenseManager.update_verification_timestamp)
        assert callable(LicenseManager.get_license_status_info)

    def test_license_manager_has_required_attributes(self, fresh_license_manager):
        """Test LicenseManager has required attributes."""
        manager, mock_settings = fresh_license_manager

        _ = manager.is_pro
        _ = manager.settings
        assert isinstance(manager.is_pro, bool)


class TestVerifyLicenseAPI:
    """Test verify_license API implementation for Phase 2."""

    def test_verify_license_with_stored_credentials(self, fresh_license_manager):
        """Test verify_license with stored credentials in settings."""
        manager, mock_settings = fresh_license_manager

        # Set up stored credentials
        mock_settings.email = "test@example.com"
        mock_settings.license_key = "testkey123"

        # Inject a stub request_fn that simulates network failure
        manager._request_fn = lambda **kwargs: None

        result = manager.verify_license(max_retries=3, backoff_rate=2.0, timeout=60)

        assert result is False  # Network failure should return False
        assert manager.is_pro is False

    def test_verify_license_retrieves_from_settings(self, fresh_license_manager):
        """Test verify_license retrieves credentials from settings when not provided."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = "settings@example.com"
        mock_settings.license_key = "settingskey123"

        manager._request_fn = lambda **kwargs: None

        result = manager.verify_license()

        assert result is False
        assert manager.is_pro is False

    def test_verify_license_missing_credentials(self, fresh_license_manager):
        """Test verify_license returns False when credentials are missing."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = ""
        mock_settings.license_key = ""

        result = manager.verify_license()

        assert result is False
        assert manager.is_pro is False

    def test_verify_license_missing_email(self, fresh_license_manager):
        """Test verify_license returns False when email is missing."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = ""
        mock_settings.license_key = "haskey"

        result = manager.verify_license()

        assert result is False
        assert manager.is_pro is False

    def test_verify_license_missing_license_key(self, fresh_license_manager):
        """Test verify_license returns False when license key is missing."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = "has@email.com"
        mock_settings.license_key = ""

        result = manager.verify_license()

        assert result is False
        assert manager.is_pro is False

    def test_verify_license_default_parameters(self, fresh_license_manager):
        """Test verify_license uses default parameters correctly."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = "test@example.com"
        mock_settings.license_key = "testkey"

        received_kwargs: dict = {}

        def stub_request_fn(**kwargs):
            received_kwargs.update(kwargs)
            return None

        manager._request_fn = stub_request_fn

        result = manager.verify_license()

        assert received_kwargs["method"] == "POST"
        assert received_kwargs["uri"] == "/public/license/verify"
        assert received_kwargs["payload"] == {
            "email": "test@example.com",
            "license_key": "testkey",
        }
        assert received_kwargs["timeout"] == DEFAULT_LICENSE_TIMEOUT
        assert received_kwargs["max_retries"] == DEFAULT_LICENSE_RETRY_COUNT
        assert received_kwargs["backoff_rate"] == DEFAULT_LICENSE_BACKOFF_RATE
        assert result is False

    def test_verify_license_custom_parameters(self, fresh_license_manager):
        """Test verify_license with custom retry and timeout parameters."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = "settings@example.com"
        mock_settings.license_key = "settingskey"

        received_kwargs: dict = {}

        def stub_request_fn(**kwargs):
            received_kwargs.update(kwargs)
            return None

        manager._request_fn = stub_request_fn

        result = manager.verify_license(max_retries=5, backoff_rate=3.0, timeout=120)

        assert received_kwargs["method"] == "POST"
        assert received_kwargs["uri"] == "/public/license/verify"
        assert received_kwargs["payload"] == {
            "email": "settings@example.com",
            "license_key": "settingskey",
        }
        assert received_kwargs["timeout"] == 120
        assert received_kwargs["max_retries"] == 5
        assert received_kwargs["backoff_rate"] == 3.0
        assert result is False


class TestOfflineStatus:
    """Test offline status checking functionality."""

    def test_check_offline_status_never_verified(self, fresh_license_manager):
        """Test offline status when never successfully verified."""
        manager, mock_settings = fresh_license_manager
        mock_settings.last_successful_verification = 0.0

        result = manager.check_offline_status()

        assert result is False

    def test_check_offline_status_within_grace_period(self, fresh_license_manager):
        """Test offline status when within grace period."""
        manager, mock_settings = fresh_license_manager
        recent_time = time.time() - (
            OFFLINE_GRACE_PERIOD_DAYS * 24 * 60 * 60 / 2
        )  # Half the grace period ago
        mock_settings.last_successful_verification = recent_time

        result = manager.check_offline_status()

        assert result is True

    def test_check_offline_status_outside_grace_period(self, fresh_license_manager):
        """Test offline status when outside grace period."""
        manager, mock_settings = fresh_license_manager
        old_time = time.time() - (
            OFFLINE_GRACE_PERIOD_DAYS * 24 * 60 * 60 * 2
        )  # Double the grace period ago
        mock_settings.last_successful_verification = old_time

        result = manager.check_offline_status()

        assert result is False

    def test_check_offline_status_exactly_at_boundary(self, fresh_license_manager):
        """Test offline status exactly at grace period boundary."""
        manager, mock_settings = fresh_license_manager
        # Use a slightly more recent time to account for floating point precision
        boundary_time = time.time() - (OFFLINE_GRACE_PERIOD_DAYS * 24 * 60 * 60 - 1)
        mock_settings.last_successful_verification = boundary_time

        result = manager.check_offline_status()

        # Should be True (within grace period) due to <= comparison
        assert result is True


class TestVerificationTimestamp:
    """Test verification timestamp management."""

    def test_update_verification_timestamp(self, fresh_license_manager):
        """Test updating verification timestamp."""
        manager, mock_settings = fresh_license_manager

        before_time = time.time()
        manager.update_verification_timestamp()
        after_time = time.time()

        # Check that timestamp was set to current time
        set_time = mock_settings.last_successful_verification
        assert before_time <= set_time <= after_time


class TestLicenseStatusInfo:
    """Test license status information gathering."""

    def test_get_license_status_info_complete(self, fresh_license_manager):
        """Test get_license_status_info returns complete information."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = "test@example.com"
        mock_settings.license_key = "testkey123"
        mock_settings.last_successful_verification = 1234567890.0
        manager.is_pro = True

        with patch.object(manager, "check_offline_status", return_value=True) as mock_offline:
            result = manager.get_license_status_info()

        expected = {
            "is_pro": True,
            "email": "test@example.com",
            "has_license_key": True,
            "last_verification": 1234567890.0,
            "within_offline_period": True,
            "offline_grace_days": OFFLINE_GRACE_PERIOD_DAYS,
        }

        assert result == expected
        mock_offline.assert_called_once()

    def test_get_license_status_info_no_credentials(self, fresh_license_manager):
        """Test get_license_status_info with no credentials."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = ""
        mock_settings.license_key = ""
        mock_settings.last_successful_verification = 0.0
        manager.is_pro = False

        with patch.object(manager, "check_offline_status", return_value=False) as mock_offline:
            result = manager.get_license_status_info()

        expected = {
            "is_pro": False,
            "email": "",
            "has_license_key": False,
            "last_verification": 0.0,
            "within_offline_period": False,
            "offline_grace_days": OFFLINE_GRACE_PERIOD_DAYS,
        }

        assert result == expected
        mock_offline.assert_called_once()

    def test_get_license_status_info_has_email_no_key(self, fresh_license_manager):
        """Test get_license_status_info with email but no license key."""
        manager, mock_settings = fresh_license_manager
        mock_settings.email = "test@example.com"
        mock_settings.license_key = ""
        mock_settings.last_successful_verification = 0.0
        manager.is_pro = False

        with patch.object(manager, "check_offline_status", return_value=False) as mock_offline:
            result = manager.get_license_status_info()

        assert result["email"] == "test@example.com"
        assert result["has_license_key"] is False
        mock_offline.assert_called_once()


class TestLicenseManagerSingleton:
    """Test LicenseManager singleton pattern."""

    def test_license_manager_singleton_exists(self):
        """Test that license_manager singleton instance exists."""
        assert license_manager is not None
        assert isinstance(license_manager, LicenseManager)

    def test_license_manager_singleton_is_same_instance(self):
        """Test that importing license_manager gives the same instance."""
        from app.services.license_manager import license_manager as license_manager2

        assert license_manager is license_manager2

    def test_license_manager_singleton_initial_state(self):
        """Test that license_manager singleton has correct initial state."""
        # Note: This test interacts with the real singleton, so it might affect other tests
        # In a real scenario, you might want to reset the singleton state in a fixture
        _ = license_manager.is_pro
        _ = license_manager.settings
        assert isinstance(license_manager.is_pro, bool)
