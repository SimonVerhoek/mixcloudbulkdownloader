"""Integration tests for license API functionality."""

import time
from unittest.mock import Mock, PropertyMock, patch

import pytest

from app.consts.license import (
    DEFAULT_LICENSE_BACKOFF_RATE,
    DEFAULT_LICENSE_RETRY_COUNT,
    DEFAULT_LICENSE_TIMEOUT,
    LICENSE_SERVER_URL,
    OFFLINE_GRACE_PERIOD_DAYS,
)
from app.services.license_manager import LicenseManager, license_manager
from app.services.settings_manager import SettingsManager
from tests.stubs.license_server_stubs import FakeLicenseServerClient, StubLicenseServer


@pytest.fixture
def fresh_license_manager():
    """Create a fresh license manager instance for testing."""
    # Create a fresh settings manager
    with patch("app.services.settings_manager.QSettings") as mock_qsettings:
        mock_instance = Mock()
        mock_qsettings.return_value = mock_instance

        # Mock settings values with proper defaults
        def mock_value(key, default, **kwargs):
            if key == "last_successful_verification":
                return 0.0
            return default

        mock_instance.value.side_effect = mock_value

        fresh_settings = SettingsManager()
        fresh_settings._settings = mock_instance

        # Mock credential methods to return empty strings by default
        fresh_settings._retrieve_credential = Mock(return_value="")

        # Create license manager with fresh settings
        manager = LicenseManager()
        manager.settings = fresh_settings
        manager.is_pro = False

        return manager, fresh_settings, mock_instance


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client that can be configured for tests."""
    mock_client = Mock()
    mock_response = Mock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.request.return_value = mock_response
    return mock_client, mock_response


class TestLicenseAPIIntegration:
    """Test license API integration with real HTTP behavior."""

    def test_successful_license_verification(self, fresh_license_manager):
        """Test successful license verification flow."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential properties directly to return test credentials
        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
        ):

            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key-123"

            # Mock successful API response
            with patch("httpx.Client") as mock_client_class:
                mock_client = Mock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client_class.return_value.__exit__.return_value = None

                mock_response = Mock()
                mock_response.json.return_value = {
                    "valid": True,
                    "product_name": "mixcloud_bulk_downloader",
                    "product_title": "Mixcloud Bulk Downloader Pro",
                    "expires_at": None,
                    "error": None,
                }
                mock_client.request.return_value = mock_response

                # Test successful verification
                result = manager.verify_license()

                # Verify API call was made correctly
                mock_client.request.assert_called_once_with(
                    method="POST",
                    url=f"{LICENSE_SERVER_URL}/public/license/verify",
                    json={"email": "test@example.com", "license_key": "valid-key-123"},
                )

                # Verify results
                assert result is True
                assert manager.is_pro is True

                # Verify timestamp was updated
                assert any(
                    call[0][0] == "last_successful_verification"
                    for call in mock_qsettings.setValue.call_args_list
                )

    def test_invalid_license_verification(self, fresh_license_manager):
        """Test invalid license verification."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential retrieval to return test credentials
        def mock_retrieve_credential(key, default):
            if "email" in key:
                return "test@example.com"
            elif "license_key" in key:
                return "invalid-key"
            return default

        settings._retrieve_credential.side_effect = mock_retrieve_credential

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            mock_response = Mock()
            mock_response.json.return_value = {
                "valid": False,
                "product_name": None,
                "product_title": None,
                "expires_at": None,
                "error": "Invalid license credentials",
            }
            mock_client.request.return_value = mock_response

            result = manager.verify_license()

            assert result is False
            assert manager.is_pro is False

    def test_wrong_product_name(self, fresh_license_manager):
        """Test license for different product."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential retrieval to return test credentials
        def mock_retrieve_credential(key, default):
            if "email" in key:
                return "test@example.com"
            elif "license_key" in key:
                return "other-product-key"
            return default

        settings._retrieve_credential.side_effect = mock_retrieve_credential

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            mock_response = Mock()
            mock_response.json.return_value = {
                "valid": True,
                "product_name": "different_product",
                "product_title": "Different Product",
                "expires_at": None,
                "error": None,
            }
            mock_client.request.return_value = mock_response

            result = manager.verify_license()

            assert result is False
            assert manager.is_pro is False

    def test_missing_credentials(self, fresh_license_manager):
        """Test verification with missing credentials."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Test missing email
        def mock_retrieve_missing_email(key, default):
            if "email" in key:
                return ""
            elif "license_key" in key:
                return "some-key"
            return default

        settings._retrieve_credential.side_effect = mock_retrieve_missing_email
        result = manager.verify_license()
        assert result is False
        assert manager.is_pro is False

        # Test missing license key
        def mock_retrieve_missing_key(key, default):
            if "email" in key:
                return "test@example.com"
            elif "license_key" in key:
                return ""
            return default

        settings._retrieve_credential.side_effect = mock_retrieve_missing_key
        result = manager.verify_license()
        assert result is False
        assert manager.is_pro is False

        # Test both missing
        def mock_retrieve_both_missing(key, default):
            return ""

        settings._retrieve_credential.side_effect = mock_retrieve_both_missing
        result = manager.verify_license()
        assert result is False
        assert manager.is_pro is False

    def test_network_error_with_retry(self, fresh_license_manager):
        """Test network error handling with retry logic."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential properties directly to return test credentials
        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
            patch("httpx.Client") as mock_client_class,
            patch("time.sleep") as mock_sleep,
        ):  # Mock sleep to speed up test

            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key-123"

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            # Mock network error
            import httpx

            mock_client.request.side_effect = httpx.RequestError("Network connection failed")

            result = manager.verify_license(max_retries=2)

            # Verify retries were attempted
            assert mock_client.request.call_count == 3  # Initial + 2 retries
            assert result is False
            assert manager.is_pro is False

            # Verify exponential backoff delays
            expected_delays = [1.5**0, 1.5**1]  # backoff_rate ** attempt
            mock_sleep.assert_any_call(expected_delays[0])
            mock_sleep.assert_any_call(expected_delays[1])

    def test_timeout_error_handling(self, fresh_license_manager):
        """Test timeout error handling."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential properties directly to return test credentials
        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
            patch("httpx.Client") as mock_client_class,
            patch("time.sleep"),
        ):

            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key-123"

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            import httpx

            mock_client.request.side_effect = httpx.TimeoutException("Request timed out")

            result = manager.verify_license(max_retries=1)

            assert mock_client.request.call_count == 2  # Initial + 1 retry
            assert result is False
            assert manager.is_pro is False

    def test_http_error_handling(self, fresh_license_manager):
        """Test HTTP error handling."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential retrieval to return test credentials
        def mock_retrieve_credential(key, default):
            if "email" in key:
                return "test@example.com"
            elif "license_key" in key:
                return "valid-key-123"
            return default

        settings._retrieve_credential.side_effect = mock_retrieve_credential

        with patch("httpx.Client") as mock_client_class, patch("time.sleep"):

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            # Mock HTTP error
            import httpx

            mock_response = Mock()
            mock_response.status_code = 500
            mock_client.request.side_effect = httpx.HTTPStatusError(
                "Server error", request=Mock(), response=mock_response
            )

            result = manager.verify_license(max_retries=1)

            assert result is False
            assert manager.is_pro is False

    def test_malformed_json_response(self, fresh_license_manager):
        """Test handling of malformed JSON responses."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential retrieval to return test credentials
        def mock_retrieve_credential(key, default):
            if "email" in key:
                return "test@example.com"
            elif "license_key" in key:
                return "valid-key-123"
            return default

        settings._retrieve_credential.side_effect = mock_retrieve_credential

        with patch("httpx.Client") as mock_client_class, patch("time.sleep"):

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_client.request.return_value = mock_response

            result = manager.verify_license(max_retries=1)

            assert result is False
            assert manager.is_pro is False

    def test_offline_grace_period_fallback(self, fresh_license_manager):
        """Test offline grace period when verification fails."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Set up existing successful verification timestamp (within grace period)
        recent_timestamp = time.time() - (
            OFFLINE_GRACE_PERIOD_DAYS * 24 * 60 * 60 / 2
        )  # Half grace period ago

        def mock_value_with_timestamp(key, default, **kwargs):
            if key == "last_successful_verification":
                return recent_timestamp
            return default

        mock_qsettings.value.side_effect = mock_value_with_timestamp
        manager.is_pro = True  # Previously verified

        # Mock credential properties directly to return test credentials
        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
            patch("httpx.Client") as mock_client_class,
            patch("time.sleep"),
        ):

            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key-123"

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            # Mock network error
            import httpx

            mock_client.request.side_effect = httpx.RequestError("Network error")

            result = manager.verify_license(max_retries=1)

            # Should maintain pro status due to grace period
            assert result is True
            assert manager.is_pro is True

    def test_expired_grace_period(self, fresh_license_manager):
        """Test behavior when grace period has expired."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential retrieval to return test credentials
        def mock_retrieve_credential(key, default):
            if "email" in key:
                return "test@example.com"
            elif "license_key" in key:
                return "valid-key-123"
            return default

        settings._retrieve_credential.side_effect = mock_retrieve_credential

        # Set up old verification timestamp (outside grace period)
        old_timestamp = time.time() - (
            OFFLINE_GRACE_PERIOD_DAYS * 24 * 60 * 60 * 2
        )  # Double grace period ago

        def mock_value_with_old_timestamp(key, default, **kwargs):
            if key == "last_successful_verification":
                return old_timestamp
            return default

        mock_qsettings.value.side_effect = mock_value_with_old_timestamp
        manager.is_pro = True  # Previously verified

        with patch("httpx.Client") as mock_client_class, patch("time.sleep"):

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            import httpx

            mock_client.request.side_effect = httpx.RequestError("Network error")

            result = manager.verify_license(max_retries=1)

            # Should lose pro status due to expired grace period
            assert result is False
            assert manager.is_pro is False

    def test_credentials_from_settings(self, fresh_license_manager):
        """Test retrieving credentials from settings when not provided."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential properties directly to return test credentials
        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
            patch("httpx.Client") as mock_client_class,
        ):

            mock_email.return_value = "settings@example.com"
            mock_license_key.return_value = "settings-key-123"

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            mock_response = Mock()
            mock_response.json.return_value = {
                "valid": True,
                "product_name": "mixcloud_bulk_downloader",
                "product_title": "Mixcloud Bulk Downloader Pro",
                "expires_at": None,
                "error": None,
            }
            mock_client.request.return_value = mock_response

            # Call without providing credentials
            result = manager.verify_license()

            # Verify correct credentials were used from settings
            mock_client.request.assert_called_once_with(
                method="POST",
                url=f"{LICENSE_SERVER_URL}/public/license/verify",
                json={"email": "settings@example.com", "license_key": "settings-key-123"},
            )

            assert result is True
            assert manager.is_pro is True

    def test_timeout_parameter_conversion(self, fresh_license_manager):
        """Test that integer timeout is converted to httpx.Timeout."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential properties directly to return test credentials
        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
            patch("httpx.Client") as mock_client_class,
            patch("httpx.Timeout") as mock_timeout_class,
        ):

            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key"

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            mock_response = Mock()
            mock_response.json.return_value = {
                "valid": True,
                "product_name": "mixcloud_bulk_downloader",
                "product_title": "Mixcloud Bulk Downloader Pro",
                "expires_at": None,
                "error": None,
            }
            mock_client.request.return_value = mock_response

            custom_timeout = 30
            manager.verify_license(timeout=custom_timeout)

            # Verify httpx.Timeout was created with the integer value
            mock_timeout_class.assert_called_once_with(timeout=custom_timeout)

            # Verify client was created with the timeout object
            mock_client_class.assert_called_once_with(timeout=mock_timeout_class.return_value)

    def test_custom_retry_parameters(self, fresh_license_manager):
        """Test custom retry parameters are respected."""
        manager, settings, mock_qsettings = fresh_license_manager

        # Mock credential properties directly to return test credentials
        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
            patch("httpx.Client") as mock_client_class,
            patch("time.sleep") as mock_sleep,
        ):

            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key"

            mock_client = Mock()
            mock_client_class.return_value.__enter__.return_value = mock_client
            mock_client_class.return_value.__exit__.return_value = None

            import httpx

            mock_client.request.side_effect = httpx.RequestError("Network error")

            custom_retries = 3
            custom_backoff = 2.0

            result = manager.verify_license(max_retries=custom_retries, backoff_rate=custom_backoff)

            # Verify correct number of attempts (initial + retries)
            assert mock_client.request.call_count == custom_retries + 1

            # Verify exponential backoff with custom rate
            expected_delays = [custom_backoff**i for i in range(custom_retries)]
            for delay in expected_delays:
                mock_sleep.assert_any_call(delay)
