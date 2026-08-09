"""Integration tests for license API functionality."""

import tempfile
import time
from pathlib import Path
from unittest.mock import PropertyMock, patch

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
from tests.stubs.license_server_stubs import (
    FakeHttpClientFactory,
    FakeLicenseServerClient,
    FakeLicenseServerResponse,
    RecordingSleepFn,
    StubLicenseServer,
)


def _make_settings(tmp_dir: Path) -> SettingsManager:
    """Create a real SettingsManager backed by a temporary directory.

    Args:
        tmp_dir: Temporary directory for settings storage.

    Returns:
        A fresh SettingsManager instance pointing at *tmp_dir*.
    """
    return SettingsManager(storage_path=tmp_dir)


def _make_manager(
    settings: SettingsManager,
    client: FakeLicenseServerClient | None = None,
    sleep_fn: RecordingSleepFn | None = None,
) -> LicenseManager:
    """Create a LicenseManager with injected fakes.

    Args:
        settings: SettingsManager to use.
        client: Optional fake HTTP client; when provided wraps it in a
            ``FakeHttpClientFactory``.  When *None* no client factory is injected
            (the manager will attempt real HTTP — only pass *None* in tests that
            short-circuit before any HTTP call is made).
        sleep_fn: Optional recording sleep callable; defaults to a new
            ``RecordingSleepFn`` so retry tests never actually sleep.

    Returns:
        A fresh LicenseManager instance.
    """
    factory = FakeHttpClientFactory(client) if client is not None else None
    effective_sleep = sleep_fn if sleep_fn is not None else RecordingSleepFn()
    manager = LicenseManager(
        settings=settings,
        http_client_factory=factory,
        sleep_fn=effective_sleep,
    )
    # Bypass lazy pro-status initialisation: the fresh manager has no stored
    # credentials so it should start as free.
    manager.is_pro = False
    return manager


@pytest.fixture
def mock_httpx_client():
    """Create a FakeLicenseServerClient that can be configured for tests."""
    client = FakeLicenseServerClient()
    return client


class TestLicenseAPIIntegration:
    """Test license API integration with real HTTP behaviour."""

    def test_successful_license_verification(self, tmp_path):
        """Test successful license verification flow."""
        settings = _make_settings(tmp_dir=tmp_path)

        # Inject credentials via property
        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
        ):
            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key-123"

            client = FakeLicenseServerClient()
            # Configure valid response
            client.add_valid_license("test@example.com", "valid-key-123")

            # Override the default response to include the full expected payload
            client.set_custom_response(
                "test@example.com",
                "valid-key-123",
                {
                    "valid": True,
                    "product_name": "mixcloud_bulk_downloader",
                    "product_title": "Mixcloud Bulk Downloader Pro",
                    "expires_at": None,
                    "error": None,
                },
            )

            manager = _make_manager(settings=settings, client=client)
            result = manager.verify_license()

            # Verify the request was made
            assert client.request_count == 1
            assert client.last_url == f"{LICENSE_SERVER_URL}/public/license/verify"
            assert client.last_data == {
                "email": "test@example.com",
                "license_key": "valid-key-123",
            }

            assert result is True
            assert manager.is_pro is True

    def test_invalid_license_verification(self, tmp_path):
        """Test invalid license verification."""
        settings = _make_settings(tmp_dir=tmp_path)
        settings.email = "test@example.com"
        settings.license_key = "invalid-key"

        client = FakeLicenseServerClient()
        # "invalid-key" is not in valid_licenses, so FakeLicenseServerClient
        # returns an invalid response automatically.

        manager = _make_manager(settings=settings, client=client)
        result = manager.verify_license()

        assert result is False
        assert manager.is_pro is False

    def test_wrong_product_name(self, tmp_path):
        """Test license for different product."""
        settings = _make_settings(tmp_dir=tmp_path)
        settings.email = "test@example.com"
        settings.license_key = "other-product-key"

        client = FakeLicenseServerClient()
        client.add_valid_license("test@example.com", "other-product-key")
        client.set_custom_response(
            "test@example.com",
            "other-product-key",
            {
                "valid": True,
                "product_name": "different_product",
                "product_title": "Different Product",
                "expires_at": None,
                "error": None,
            },
        )

        manager = _make_manager(settings=settings, client=client)
        result = manager.verify_license()

        assert result is False
        assert manager.is_pro is False

    def test_missing_credentials(self, tmp_path):
        """Test verification with missing credentials."""
        # Test missing email — no HTTP call is made, so no client needed.
        s1 = _make_settings(tmp_dir=tmp_path / "case1")
        s1.license_key = "some-key"  # email is "" by default
        manager = _make_manager(settings=s1)
        result = manager.verify_license()
        assert result is False
        assert manager.is_pro is False

        # Test missing license key
        s2 = _make_settings(tmp_dir=tmp_path / "case2")
        s2.email = "test@example.com"  # license_key is "" by default
        manager = _make_manager(settings=s2)
        result = manager.verify_license()
        assert result is False
        assert manager.is_pro is False

        # Test both missing
        s3 = _make_settings(tmp_dir=tmp_path / "case3")
        manager = _make_manager(settings=s3)
        result = manager.verify_license()
        assert result is False
        assert manager.is_pro is False

    def test_network_error_with_retry(self, tmp_path):
        """Test network error handling with retry logic."""
        settings = _make_settings(tmp_dir=tmp_path)

        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
        ):
            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key-123"

            client = FakeLicenseServerClient()
            client.set_network_error(should_error=True, message="Network connection failed")

            sleep_fn = RecordingSleepFn()
            manager = _make_manager(settings=settings, client=client, sleep_fn=sleep_fn)

            result = manager.verify_license(max_retries=2)

            # Verify retries were attempted
            assert client.request_count == 3  # Initial + 2 retries
            assert result is False
            assert manager.is_pro is False

            # Verify exponential backoff delays
            expected_delays = [1.5**0, 1.5**1]  # backoff_rate ** attempt
            assert sleep_fn.calls == expected_delays

    def test_timeout_error_handling(self, tmp_path):
        """Test timeout error handling."""
        settings = _make_settings(tmp_dir=tmp_path)

        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
        ):
            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key-123"

            client = FakeLicenseServerClient()
            client.set_timeout_error(should_error=True, message="Request timed out")

            sleep_fn = RecordingSleepFn()
            manager = _make_manager(settings=settings, client=client, sleep_fn=sleep_fn)

            result = manager.verify_license(max_retries=1)

            assert client.request_count == 2  # Initial + 1 retry
            assert result is False
            assert manager.is_pro is False

    def test_http_error_handling(self, tmp_path):
        """Test HTTP error handling."""
        settings = _make_settings(tmp_dir=tmp_path)
        settings.email = "test@example.com"
        settings.license_key = "valid-key-123"

        client = FakeLicenseServerClient()
        client.set_http_error(should_error=True, status_code=500)

        sleep_fn = RecordingSleepFn()
        manager = _make_manager(settings=settings, client=client, sleep_fn=sleep_fn)

        result = manager.verify_license(max_retries=1)

        assert result is False
        assert manager.is_pro is False

    def test_malformed_json_response(self, tmp_path):
        """Test handling of malformed JSON responses."""
        settings = _make_settings(tmp_dir=tmp_path)
        settings.email = "test@example.com"
        settings.license_key = "valid-key-123"

        # Use a custom client whose .json() raises ValueError
        class MalformedResponseClient:
            """Fake client returning a response whose .json() raises."""

            def __init__(self) -> None:
                self.request_count = 0

            def request(self, method, url, **kwargs):
                self.request_count += 1
                return _MalformedJsonResponse()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        class _MalformedJsonResponse:
            def json(self):
                raise ValueError("Invalid JSON")

            def raise_for_status(self):
                pass

        malformed_client = MalformedResponseClient()

        class _MalformedFactory:
            def __init__(self, c):
                self._c = c

            def __call__(self, *, timeout):
                return self._c

        sleep_fn = RecordingSleepFn()
        manager = LicenseManager(
            settings=settings,
            http_client_factory=_MalformedFactory(malformed_client),
            sleep_fn=sleep_fn,
        )
        manager.is_pro = False

        result = manager.verify_license(max_retries=1)

        assert result is False
        assert manager.is_pro is False

    def test_offline_grace_period_fallback(self, tmp_path):
        """Test offline grace period when verification fails."""
        settings = _make_settings(tmp_dir=tmp_path)

        # Set up existing successful verification timestamp (within grace period)
        recent_timestamp = time.time() - (
            OFFLINE_GRACE_PERIOD_DAYS * 24 * 60 * 60 / 2
        )  # Half grace period ago
        settings.last_successful_verification = recent_timestamp

        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
        ):
            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key-123"

            client = FakeLicenseServerClient()
            client.set_network_error(should_error=True, message="Network error")

            sleep_fn = RecordingSleepFn()
            manager = _make_manager(settings=settings, client=client, sleep_fn=sleep_fn)
            manager.is_pro = True  # Previously verified

            result = manager.verify_license(max_retries=1)

            # Should maintain pro status due to grace period
            assert result is True
            assert manager.is_pro is True

    def test_expired_grace_period(self, tmp_path):
        """Test behaviour when grace period has expired."""
        settings = _make_settings(tmp_dir=tmp_path)
        settings.email = "test@example.com"
        settings.license_key = "valid-key-123"

        # Set up old verification timestamp (outside grace period)
        old_timestamp = time.time() - (
            OFFLINE_GRACE_PERIOD_DAYS * 24 * 60 * 60 * 2
        )  # Double grace period ago
        settings.last_successful_verification = old_timestamp

        client = FakeLicenseServerClient()
        client.set_network_error(should_error=True, message="Network error")

        sleep_fn = RecordingSleepFn()
        manager = _make_manager(settings=settings, client=client, sleep_fn=sleep_fn)
        manager.is_pro = True  # Previously verified

        result = manager.verify_license(max_retries=1)

        # Should lose pro status due to expired grace period
        assert result is False
        assert manager.is_pro is False

    def test_credentials_from_settings(self, tmp_path):
        """Test retrieving credentials from settings when not provided."""
        settings = _make_settings(tmp_dir=tmp_path)

        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
        ):
            mock_email.return_value = "settings@example.com"
            mock_license_key.return_value = "settings-key-123"

            client = FakeLicenseServerClient()
            client.add_valid_license("settings@example.com", "settings-key-123")
            client.set_custom_response(
                "settings@example.com",
                "settings-key-123",
                {
                    "valid": True,
                    "product_name": "mixcloud_bulk_downloader",
                    "product_title": "Mixcloud Bulk Downloader Pro",
                    "expires_at": None,
                    "error": None,
                },
            )

            manager = _make_manager(settings=settings, client=client)
            result = manager.verify_license()

            # Verify correct credentials were used from settings
            assert client.last_data == {
                "email": "settings@example.com",
                "license_key": "settings-key-123",
            }
            assert result is True
            assert manager.is_pro is True

    def test_timeout_parameter_conversion(self, tmp_path):
        """Test that integer timeout is converted to httpx.Timeout."""
        import httpx

        settings = _make_settings(tmp_dir=tmp_path)

        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
        ):
            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key"

            # Record what timeout object the factory receives
            received_timeouts: list[httpx.Timeout] = []

            client = FakeLicenseServerClient()
            client.add_valid_license("test@example.com", "valid-key")
            client.set_custom_response(
                "test@example.com",
                "valid-key",
                {
                    "valid": True,
                    "product_name": "mixcloud_bulk_downloader",
                    "product_title": "Mixcloud Bulk Downloader Pro",
                    "expires_at": None,
                    "error": None,
                },
            )

            class _RecordingFactory:
                def __call__(self, *, timeout: httpx.Timeout):
                    received_timeouts.append(timeout)
                    return client

            manager = LicenseManager(
                settings=settings,
                http_client_factory=_RecordingFactory(),
                sleep_fn=RecordingSleepFn(),
            )
            manager.is_pro = False

            custom_timeout = 30
            manager.verify_license(timeout=custom_timeout)

            # Verify httpx.Timeout was created with the integer value
            assert len(received_timeouts) == 1
            assert isinstance(received_timeouts[0], httpx.Timeout)
            # httpx.Timeout stores the timeout value
            assert received_timeouts[0].read == custom_timeout

    def test_custom_retry_parameters(self, tmp_path):
        """Test custom retry parameters are respected."""
        settings = _make_settings(tmp_dir=tmp_path)

        with (
            patch.object(type(settings), "email", new_callable=PropertyMock) as mock_email,
            patch.object(
                type(settings), "license_key", new_callable=PropertyMock
            ) as mock_license_key,
        ):
            mock_email.return_value = "test@example.com"
            mock_license_key.return_value = "valid-key"

            client = FakeLicenseServerClient()
            client.set_network_error(should_error=True, message="Network error")

            sleep_fn = RecordingSleepFn()
            manager = _make_manager(settings=settings, client=client, sleep_fn=sleep_fn)

            custom_retries = 3
            custom_backoff = 2.0

            result = manager.verify_license(max_retries=custom_retries, backoff_rate=custom_backoff)

            # Verify correct number of attempts (initial + retries)
            assert client.request_count == custom_retries + 1

            # Verify exponential backoff with custom rate
            expected_delays = [custom_backoff**i for i in range(custom_retries)]
            assert sleep_fn.calls == expected_delays
