"""Settings management for Mixcloud Bulk Downloader using encrypted INI files."""

import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings

from app.consts.settings import (
    DEFAULT_CHECK_UPDATES_ON_STARTUP,
    DEFAULT_ENABLE_AUDIO_CONVERSION,
    DEFAULT_MAX_PARALLEL_CONVERSIONS,
    DEFAULT_MAX_PARALLEL_DOWNLOADS,
    DEVELOPMENT,
    KEYRING_EMAIL_KEY,
    KEYRING_LICENSE_KEY,
    SETTING_CHECK_UPDATES_ON_STARTUP,
    SETTING_ENABLE_AUDIO_CONVERSION,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    SETTING_MAX_PARALLEL_DOWNLOADS,
)
from app.qt_logger import log_error, log_ui
from app.services.credential_encryptor import CredentialEncryptor


class SettingsManager:
    """Enhanced settings manager with encrypted credential storage and threading.

    This class provides:
    - Property-based interface for all settings including credentials
    - Encrypted storage of sensitive data using device-specific keys
    - Thread-safe operations with concurrent read support
    - Cross-platform file protection
    - Comprehensive error handling with user notifications
    - Development mode support with ./local_settings/
    """

    def __init__(self) -> None:
        """Initialize settings manager with encrypted INI storage.

        Creates a cross-platform settings manager that stores application settings
        and encrypted credentials in platform-appropriate directories.

        Storage Locations:
        ==================

        Production Mode (DEVELOPMENT=False):
        - macOS: ~/Library/Application Support/mixcloud-bulk-downloader/settings.conf
        - Windows: %APPDATA%/mixcloud-bulk-downloader/settings.conf
          (typically C:\\Users\\{username}\\AppData\\Roaming\\mixcloud-bulk-downloader\\settings.conf)
        - Linux: $XDG_CONFIG_HOME/mixcloud-bulk-downloader/settings.conf
          (defaults to ~/.config/mixcloud-bulk-downloader/settings.conf)

        Development Mode (DEVELOPMENT=True):
        - All platforms: ./local_settings/settings.conf

        Custom Override:
        - Set CUSTOM_SETTINGS_PATH environment variable to any directory
        - Example: CUSTOM_SETTINGS_PATH="/opt/mixcloud-settings"
        - Results in: {CUSTOM_SETTINGS_PATH}/mixcloud-bulk-downloader.conf
        - Useful for portable installations, multi-user environments, testing

        Features:
        =========
        - Encrypted credential storage using device-specific keys
        - Thread-safe operations with concurrent read support
        - Cross-platform file protection (chmod 700 on Unix, ACLs on Windows)
        - Automatic directory creation with appropriate permissions
        - Comprehensive error handling with user notifications
        - Legacy credential migration support

        Note:
        =====
        The settings manager follows platform conventions for application data storage:
        - macOS: Apple's Application Support guidelines
        - Windows: Microsoft's APPDATA roaming profile standard
        - Linux: XDG Base Directory Specification

        Credentials are encrypted and stored separately from regular settings for
        enhanced security. The storage directory permissions are restricted to the
        current user only.
        """
        self._shutting_down = False
        self._read_write_lock = threading.RLock()  # Allow recursive acquisition
        self._thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="settings")

        # Initialize storage location and encryption
        self._storage_path = self._get_storage_path()
        self._encryptor = CredentialEncryptor()
        self._settings = self._create_qsettings()

        # Test encryption functionality at startup
        self._test_encryption_functionality()

        # Ensure storage directory permissions are secure
        self._secure_storage_directory()

    # Property-based interface for all settings

    @property
    def email(self) -> str:
        """Get the stored license email.

        Returns:
            str: The license email or empty string if not set.
        """
        return self._get_secret(key=KEYRING_EMAIL_KEY, default="")

    @email.setter
    def email(self, value: str) -> None:
        """Set the license email.

        Args:
            value: The email address to store.
        """
        self._set_secret(key=KEYRING_EMAIL_KEY, value=value)

    @property
    def license_key(self) -> str:
        """Get the stored license key.

        Returns:
            str: The license key or empty string if not set.
        """
        return self._get_secret(key=KEYRING_LICENSE_KEY, default="")

    @license_key.setter
    def license_key(self, value: str) -> None:
        """Set the license key.

        Args:
            value: The license key to store.
        """
        self._set_secret(key=KEYRING_LICENSE_KEY, value=value)

    @property
    def last_successful_verification(self) -> float:
        """Get the timestamp of the last successful license verification.

        Returns:
            float: Unix timestamp or 0.0 if never verified successfully.
        """
        return self._get(key="last_successful_verification", default=0.0)

    @last_successful_verification.setter
    def last_successful_verification(self, timestamp: float) -> None:
        """Set the timestamp of the last successful license verification.

        Args:
            timestamp: Unix timestamp of successful verification.
        """
        self._set(key="last_successful_verification", value=timestamp)

    @property
    def max_parallel_downloads(self) -> int:
        """Get the maximum number of parallel downloads.

        Returns:
            int: Maximum parallel downloads setting.
        """
        return self._get(key=SETTING_MAX_PARALLEL_DOWNLOADS, default=DEFAULT_MAX_PARALLEL_DOWNLOADS)

    @max_parallel_downloads.setter
    def max_parallel_downloads(self, value: int) -> None:
        """Set the maximum number of parallel downloads.

        Args:
            value: Maximum parallel downloads to allow.
        """
        self._set(key=SETTING_MAX_PARALLEL_DOWNLOADS, value=value)

    @property
    def max_parallel_conversions(self) -> int:
        """Get the maximum number of parallel conversions.

        Returns:
            int: Maximum parallel conversions setting.
        """
        return self._get(
            key=SETTING_MAX_PARALLEL_CONVERSIONS, default=DEFAULT_MAX_PARALLEL_CONVERSIONS
        )

    @max_parallel_conversions.setter
    def max_parallel_conversions(self, value: int) -> None:
        """Set the maximum number of parallel conversions.

        Args:
            value: Maximum parallel conversions to allow.
        """
        self._set(key=SETTING_MAX_PARALLEL_CONVERSIONS, value=value)

    @property
    def check_updates_on_startup(self) -> bool:
        """Get the check updates on startup setting.

        Returns:
            bool: Whether to check for updates on startup.
        """
        return self._get(
            key=SETTING_CHECK_UPDATES_ON_STARTUP, default=DEFAULT_CHECK_UPDATES_ON_STARTUP
        )

    @check_updates_on_startup.setter
    def check_updates_on_startup(self, value: bool) -> None:
        """Set the check updates on startup setting.

        Args:
            value: Whether to check for updates on startup.
        """
        self._set(key=SETTING_CHECK_UPDATES_ON_STARTUP, value=value)

    @property
    def default_download_directory(self) -> str | None:
        """Get the default download directory.

        Returns:
            str | None: Default download directory path or None if not set.
        """
        return self._get(key="default_download_directory", default=None)

    @default_download_directory.setter
    def default_download_directory(self, value: str | None) -> None:
        """Set the default download directory.

        Args:
            value: Default download directory path or None to unset.
        """
        self._set(key="default_download_directory", value=value)

    @property
    def enable_audio_conversion(self) -> bool:
        """Get the audio conversion enabled setting.

        Returns:
            bool: Whether audio conversion is enabled.
        """
        return self._get(
            key=SETTING_ENABLE_AUDIO_CONVERSION, default=DEFAULT_ENABLE_AUDIO_CONVERSION
        )

    @enable_audio_conversion.setter
    def enable_audio_conversion(self, value: bool) -> None:
        """Set the audio conversion enabled setting.

        Args:
            value: Whether to enable audio conversion.
        """
        self._set(key=SETTING_ENABLE_AUDIO_CONVERSION, value=value)

    @property
    def preferred_audio_format(self) -> str:
        """Get the default audio format.

        Returns:
            str: Default audio format (e.g., 'MP3', 'FLAC').
        """
        return self._get(key="preferred_audio_format", default="MP3")

    @preferred_audio_format.setter
    def preferred_audio_format(self, value: str) -> None:
        """Set the default audio format.

        Args:
            value: Default audio format to use.
        """
        self._set(key="preferred_audio_format", value=value)

    # Private implementation methods

    def _get_storage_path(self) -> Path:
        """Get the storage directory path for settings and credentials.

        Returns:
            Path: Directory path for storing application data.
        """
        if DEVELOPMENT:
            # Development mode: use local_settings directory
            return Path("./local_settings").resolve()
        else:
            # Production mode: platform-specific directories
            if sys.platform == "darwin":  # macOS
                return Path.home() / "Library" / "Application Support" / "mixcloud-bulk-downloader"
            elif sys.platform == "win32":  # Windows
                app_data = os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
                return Path(app_data) / "mixcloud-bulk-downloader"
            else:  # Linux
                xdg_config_home = os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))
                return Path(xdg_config_home) / "mixcloud-bulk-downloader"

    def _create_qsettings(self) -> QSettings:
        """Create QSettings instance with INI format in storage directory.

        Returns:
            QSettings: Configured QSettings instance.
        """
        # Ensure storage directory exists
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # Create settings file in storage directory
        settings_file = self._storage_path / "settings.conf"
        return QSettings(str(settings_file), QSettings.Format.IniFormat)

    def _test_encryption_functionality(self) -> None:
        """Test encryption functionality at startup and log results."""
        try:
            if self._encryptor.test_encryption_cycle():
                log_ui(
                    message="Credential encryption system initialized successfully", level="INFO"
                )
            else:
                log_error(
                    message="Credential encryption test failed - credentials may not be secure"
                )
        except Exception as e:
            log_error(message=f"Failed to initialize credential encryption: {e}")

    def _secure_storage_directory(self) -> None:
        """Apply platform-specific security permissions to storage directory."""
        try:
            if sys.platform == "win32":
                # Windows: Use ACL to restrict access to current user
                self._secure_directory_windows()
            else:
                # Unix-like: Use chmod to set restrictive permissions
                self._storage_path.chmod(0o700)  # rwx------ (owner only)

            log_ui(
                message=f"Applied security permissions to storage directory: {self._storage_path}",
                level="INFO",
            )
        except Exception as e:
            log_error(message=f"Failed to secure storage directory: {e}")

    def _secure_directory_windows(self) -> None:
        """Apply Windows-specific ACL permissions to storage directory."""
        try:
            import ntsecuritycon
            import win32security

            # Get current user SID
            user_sid = win32security.GetTokenInformation(
                win32security.GetCurrentProcessToken(), win32security.TokenUser
            )[0]

            # Create ACL with only current user having full control
            acl = win32security.ACL()
            acl.AddAccessAllowedAce(
                win32security.ACL_REVISION, ntsecuritycon.FILE_ALL_ACCESS, user_sid
            )

            # Create security descriptor and apply to directory
            security_descriptor = win32security.SECURITY_DESCRIPTOR()
            security_descriptor.SetSecurityDescriptorDacl(1, acl, 0)

            win32security.SetFileSecurity(
                str(self._storage_path),
                win32security.DACL_SECURITY_INFORMATION,
                security_descriptor,
            )
        except ImportError:
            # pywin32 not available in development, skip Windows ACL
            log_ui(
                message="pywin32 not available - skipping Windows ACL configuration",
                level="WARNING",
            )
        except Exception as e:
            log_error(message=f"Failed to apply Windows ACL permissions: {e}")

    def _get(self, key: str, default: Any = None) -> Any:
        """Private method for retrieving regular settings with thread safety.

        Args:
            key: Setting key to retrieve.
            default: Default value if key doesn't exist.

        Returns:
            Any: Setting value with type conversion, or default if not found.
        """

        def _read_operation():
            with self._read_write_lock:
                value = self._settings.value(key, default)

                # Handle type conversion based on default type
                if value == default or default is None:
                    return value

                try:
                    # ALWAYS check for bool type _before_ int type to prevent booleans from being identified
                    # as ints! More info: https://stackoverflow.com/a/37888668
                    if isinstance(default, bool):
                        if isinstance(value, str):
                            return value.lower() in ("true", "1", "yes", "on")
                        return bool(value) if value is not None else default
                    elif isinstance(default, int):
                        return int(value) if value is not None else default
                    elif isinstance(default, float):
                        return float(value) if value is not None else default

                except (ValueError, TypeError) as e:
                    log_error(message=f"Failed to identify type of setting '{key}': {e}")
                    return default

                return value

        # Execute in thread pool for non-blocking access
        try:
            future = self._thread_pool.submit(_read_operation)
            return future.result(timeout=2.0)  # 2-second timeout for reads
        except Exception as e:
            log_error(message=f"Failed to read setting '{key}': {e}")
            return default

    def _set(self, key: str, value: Any) -> None:
        """Private method for storing regular settings in background thread.

        Args:
            key: Setting key to store.
            value: Value to store.
        """

        def _write_operation():
            with self._read_write_lock:
                self._settings.setValue(key, value)
                self._settings.sync()
                return True

        try:
            future = self._thread_pool.submit(_write_operation)
            future.result(timeout=5.0)  # 5-second timeout for writes
        except Exception as e:
            log_error(message=f"Failed to write setting '{key}': {e}")

    def _get_secret(self, key: str, default: str = "") -> str:
        """Private method for retrieving encrypted credentials with thread safety.

        Args:
            key: Credential key to retrieve.
            default: Default value if credential not found.

        Returns:
            str: Decrypted credential value or default if not found.
        """

        def _read_operation():
            with self._read_write_lock:
                # Try to read from secrets section
                encrypted_value = self._settings.value(f"secrets/{key}", None)

                if encrypted_value:
                    try:
                        return self._encryptor.decrypt(encrypted_data=encrypted_value)
                    except Exception as e:
                        log_error(message=f"Failed to decrypt credential '{key}': {e}")
                        # Fall back to regular settings for migration compatibility
                        return self._settings.value(key, default, type=str)

                # Check regular settings for legacy credentials
                legacy_value = self._settings.value(key, None)
                if legacy_value:
                    log_ui(
                        message=f"Migrating legacy credential '{key}' to encrypted storage",
                        level="INFO",
                    )
                    # Migrate to encrypted storage
                    try:
                        encrypted_data = self._encryptor.encrypt(plaintext=legacy_value)
                        self._settings.setValue(f"secrets/{key}", encrypted_data)
                        self._settings.remove(key)  # Remove legacy value
                        self._settings.sync()
                        return legacy_value
                    except Exception as e:
                        log_error(message=f"Failed to migrate credential '{key}': {e}")
                        return legacy_value

                return default

        try:
            future = self._thread_pool.submit(_read_operation)
            return future.result(timeout=3.0)  # 3-second timeout for credential reads
        except Exception as e:
            log_error(message=f"Failed to read credential '{key}': {e}")
            return default

    def _set_secret(self, key: str, value: str) -> None:
        """Private method for storing encrypted credentials in background thread.

        Args:
            key: Credential key to store.
            value: Credential value to encrypt and store.
        """

        def _write_operation():
            with self._read_write_lock:
                if not value:
                    # Remove credential if empty value
                    self._settings.remove(f"secrets/{key}")
                else:
                    try:
                        encrypted_data = self._encryptor.encrypt(plaintext=value)
                        self._settings.setValue(f"secrets/{key}", encrypted_data)
                    except Exception as e:
                        log_error(message=f"Failed to encrypt credential '{key}': {e}")
                        # Fallback to unencrypted storage with warning
                        log_error(
                            message=f"Storing credential '{key}' unencrypted due to encryption failure"
                        )
                        self._settings.setValue(key, value)

                # Remove any legacy unencrypted version
                self._settings.remove(key)
                self._settings.sync()
                return True

        try:
            future = self._thread_pool.submit(_write_operation)
            future.result(timeout=5.0)  # 5-second timeout for credential writes
        except Exception as e:
            log_error(message=f"Failed to write credential '{key}': {e}")

    # Legacy compatibility methods (deprecated, use properties instead)

    def get(self, key: str, default=None):
        """Get a setting value by key with automatic type conversion.

        DEPRECATED: Use property-based access instead.

        Args:
            key: Setting key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Setting value with proper type conversion, or default if not found
        """
        return self._get(key=key, default=default)

    def set(self, key: str, value) -> None:
        """Set a setting value by key.

        DEPRECATED: Use property-based access instead.

        Args:
            key: Setting key to set
            value: Value to store
        """
        self._set(key=key, value=value)

    def sync(self) -> None:
        """Force synchronization of settings to persistent storage."""

        def _sync_operation():
            with self._read_write_lock:
                self._settings.sync()
                return True

        try:
            future = self._thread_pool.submit(_sync_operation)
            future.result(timeout=5.0)
        except Exception as e:
            log_error(message=f"Failed to sync settings: {e}")

    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values."""

        def _reset_operation():
            with self._read_write_lock:
                self._settings.clear()
                self._settings.sync()
                return True

        try:
            future = self._thread_pool.submit(_reset_operation)
            future.result(timeout=10.0)  # Longer timeout for reset operation
            log_ui(message="Settings reset to defaults", level="INFO")
        except Exception as e:
            log_error(message=f"Failed to reset settings: {e}")

    def initialize_threading_settings(self, is_pro: bool) -> None:
        """Initialize threading settings with defaults if not present.

        Args:
            is_pro: Whether user has Pro status to determine appropriate defaults
        """
        if is_pro:
            if self._get(key=SETTING_MAX_PARALLEL_DOWNLOADS) is None:
                self.max_parallel_downloads = DEFAULT_MAX_PARALLEL_DOWNLOADS
            if self._get(key=SETTING_MAX_PARALLEL_CONVERSIONS) is None:
                self.max_parallel_conversions = DEFAULT_MAX_PARALLEL_CONVERSIONS
        else:
            self.max_parallel_downloads = 1
            self.max_parallel_conversions = 0  # conversions is a pro-only feature

        self.sync()

    def shutdown(self) -> None:
        """Shutdown the settings manager and cleanup resources."""
        self._shutting_down = True

        try:
            # Wait for pending operations to complete
            self._thread_pool.shutdown(wait=True, timeout=10.0)
            log_ui(message="Settings manager shutdown completed", level="INFO")
        except Exception as e:
            log_error(message=f"Error during settings manager shutdown: {e}")


# Create module-level singleton instance
settings = SettingsManager()
