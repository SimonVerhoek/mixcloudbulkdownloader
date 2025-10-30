"""Settings management for Mixcloud Bulk Downloader using QSettings."""

import json
import os
import sys
from pathlib import Path

import keyring
from PySide6.QtCore import QSettings

from app.consts.license import LOG_KEYRING_ERROR
from app.consts.settings import (
    CUSTOM_SETTINGS_PATH,
    DEFAULT_MAX_PARALLEL_CONVERSIONS,
    DEFAULT_MAX_PARALLEL_DOWNLOADS,
    DEVELOPMENT,
    KEYRING_EMAIL_KEY,
    KEYRING_LICENSE_KEY,
    KEYRING_SERVICE_NAME,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    SETTING_MAX_PARALLEL_DOWNLOADS,
)


class SettingsManager:
    """Settings manager for Mixcloud Bulk Downloader application.

    This class provides a centralized interface for reading and writing
    application settings using Qt's QSettings for cross-platform persistence.
    Settings are automatically stored in platform-appropriate locations.
    """

    def __init__(self) -> None:
        """Initialize settings manager with QSettings backend.

        If DEVELOPMENT environment variable is True and CUSTOM_SETTINGS_PATH is set,
        uses that directory for both QSettings and local file-based secrets storage.
        Otherwise, uses platform defaults:
        - macOS: ~/Library/Preferences/com.mixcloud-bulk-downloader.plist + system keyring
        - Windows: HKEY_CURRENT_USER\Software\mixcloud-bulk-downloader + system keyring
        - Linux: ~/.config/mixcloud-bulk-downloader.conf + system keyring
        """
        self._shutting_down = False  # Flag to prevent keyring access during shutdown

        # Provide ability to override path for dev purposes
        custom_path = None
        if DEVELOPMENT and CUSTOM_SETTINGS_PATH:
            custom_path = self._resolve_custom_path(CUSTOM_SETTINGS_PATH)

        self._custom_path = custom_path
        self._configure_keyring_backend()
        self._settings = self._create_qsettings()
        self._initialize_from_env()

    @property
    def email(self) -> str:
        """Get the stored license email.

        Returns:
            str: The license email or empty string if not set.
        """
        return self._retrieve_credential(KEYRING_EMAIL_KEY, "")

    @email.setter
    def email(self, value: str) -> None:
        """Set the license email.

        Args:
            value: The email address to store.
        """
        self._store_credential(KEYRING_EMAIL_KEY, value)

    @property
    def license_key(self) -> str:
        """Get the stored license key.

        Returns:
            str: The license key or empty string if not set.
        """
        return self._retrieve_credential(KEYRING_LICENSE_KEY, "")

    @license_key.setter
    def license_key(self, value: str) -> None:
        """Set the license key.

        Args:
            value: The license key to store.
        """
        self._store_credential(KEYRING_LICENSE_KEY, value)

    @property
    def last_successful_verification(self) -> float:
        """Get the timestamp of the last successful license verification.

        Returns:
            float: Unix timestamp or 0.0 if never verified successfully.
        """
        return float(self._settings.value("last_successful_verification", 0.0, type=float))

    @last_successful_verification.setter
    def last_successful_verification(self, timestamp: float) -> None:
        """Set the timestamp of the last successful license verification.

        Args:
            timestamp: Unix timestamp of successful verification.
        """
        self._settings.setValue("last_successful_verification", timestamp)

    def _store_credential(self, key: str, value: str) -> None:
        """Store a credential securely using keyring, local file, or fallback to QSettings.

        Args:
            key: The credential key to store.
            value: The credential value to store.
        """
        # Skip keyring operations during shutdown to prevent crashes
        if self._shutting_down:
            return

        # Use local file-based storage for custom paths
        if self._custom_path:
            try:
                self._store_credential_local_file(key, value)
                # Clear from QSettings if successfully stored in local file
                self._settings.remove(key)
                return
            except Exception as e:
                # Log local file error, fallback to QSettings
                print(LOG_KEYRING_ERROR.format(error=f"Local file storage failed: {e}"))
                self._settings.setValue(key, value)
                return

        try:
            service_name = self._get_keyring_service_name()
            keyring.set_password(service_name, key, value)
            # Clear from QSettings if successfully stored in keyring
            self._settings.remove(key)
        except Exception as e:
            # Log keyring error, fallback to QSettings
            print(LOG_KEYRING_ERROR.format(error=e))
            self._settings.setValue(key, value)

    def _retrieve_credential(self, key: str, default: str = "") -> str:
        """Retrieve a credential from keyring, local file, or fallback to QSettings.

        Args:
            key: The credential key to retrieve.
            default: Default value if credential not found.

        Returns:
            str: The credential value or default if not found.
        """
        # Skip keyring operations during shutdown to prevent crashes
        if self._shutting_down:
            return self._settings.value(key, default, type=str)

        # Use local file-based storage for custom paths
        if self._custom_path:
            try:
                credential = self._retrieve_credential_local_file(key)
                if credential is not None:
                    return credential
            except Exception as e:
                # Log local file error, fallback to QSettings
                print(LOG_KEYRING_ERROR.format(error=f"Local file retrieval failed: {e}"))

            # Fallback to QSettings for custom path
            return self._settings.value(key, default, type=str)

        try:
            service_name = self._get_keyring_service_name()
            credential = keyring.get_password(service_name, key)
            if credential is not None:
                return credential
        except Exception as e:
            # Log keyring error, fallback to QSettings
            print(LOG_KEYRING_ERROR.format(error=e))

        # Fallback to QSettings
        return self._settings.value(key, default, type=str)

    def _create_qsettings(self) -> QSettings:
        """Create QSettings instance with custom path support.

        Returns:
            QSettings: Configured QSettings instance using custom path if specified.
        """
        if self._custom_path:
            # Ensure the custom directory exists
            self._custom_path.mkdir(parents=True, exist_ok=True)

            # Create settings file in custom directory
            settings_file = self._custom_path / "mixcloud-bulk-downloader.conf"
            return QSettings(str(settings_file), QSettings.Format.IniFormat)
        else:
            # Use default platform-specific storage
            return QSettings("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")

    def _get_keyring_service_name(self) -> str:
        """Get the keyring service name, customized for custom path if used.

        Returns:
            str: Service name for keyring operations.
        """
        if self._custom_path:
            # Use custom path in service name to isolate credentials
            safe_path = str(self._custom_path).replace(os.sep, "_").replace(":", "_")
            return f"{KEYRING_SERVICE_NAME}-{safe_path}"
        else:
            return KEYRING_SERVICE_NAME

    def _resolve_custom_path(self, path: str) -> Path:
        """Resolve a custom path to an absolute path with proper expansions.

        Args:
            path: The custom path which may be relative or contain ~ references.

        Returns:
            str: Absolute path with user home and relative paths resolved.
        """
        # Use pathlib for cross-platform path handling
        path_obj = Path(path).expanduser().resolve()

        return path_obj

    def _configure_keyring_backend(self) -> None:
        """Configure the appropriate keyring backend for the current platform.

        This method sets up platform-specific keyring backends to avoid the
        "No recommended backend was available" error. Fallback gracefully
        if platform-specific backend is not available.
        """
        try:
            if sys.platform == "darwin":  # macOS
                from keyring.backends.macOS import Keyring as MacOSKeyring

                keyring.set_keyring(MacOSKeyring())
            elif sys.platform == "win32":  # Windows
                from keyring.backends.Windows import WinVaultKeyring

                keyring.set_keyring(WinVaultKeyring())
            elif sys.platform.startswith("linux"):  # Linux
                try:
                    from keyring.backends.SecretService import Keyring as SecretServiceKeyring

                    keyring.set_keyring(SecretServiceKeyring())
                except ImportError:
                    # Fallback to libsecret if SecretService not available
                    from keyring.backends.libsecret import Keyring as LibSecretKeyring

                    keyring.set_keyring(LibSecretKeyring())

        except (ImportError, Exception) as e:
            # Platform-specific backend not available, keyring will use default fallback
            print(LOG_KEYRING_ERROR.format(error=f"Backend configuration failed: {e}"))

    def _get_secrets_file_path(self) -> Path:
        """Get the path to the local secrets file.

        Returns:
            Path: Path to the secrets file in the custom settings directory.
        """
        if not self._custom_path:
            raise ValueError("Custom path not set - local secrets file not available")

        return self._custom_path / ".secrets.json"

    def _store_credential_local_file(self, key: str, value: str) -> None:
        """Store a credential in local file-based storage for development.

        Args:
            key: The credential key to store.
            value: The credential value to store.
        """
        secrets_file = self._get_secrets_file_path()

        # Load existing secrets or create empty dict
        secrets = {}
        if secrets_file.exists():
            try:
                with open(secrets_file, "r", encoding="utf-8") as f:
                    secrets = json.load(f)
            except (json.JSONDecodeError, ValueError) as e:
                # If file is corrupted, start fresh (but log the error)
                print(f"Warning: Corrupted secrets file, creating new one: {e}")
                secrets = {}

        # Update the credential
        secrets[key] = value

        # Ensure directory exists
        secrets_file.parent.mkdir(parents=True, exist_ok=True)

        # Write to file as plain JSON for development convenience
        with open(secrets_file, "w", encoding="utf-8") as f:
            json.dump(secrets, f, indent=2)

        # Set restrictive file permissions (readable only by owner)
        try:
            secrets_file.chmod(0o600)  # rw------- (owner read/write only)
        except OSError:
            # Windows may not support chmod, continue anyway
            pass

    def _retrieve_credential_local_file(self, key: str) -> str | None:
        """Retrieve a credential from local file-based storage for development.

        Args:
            key: The credential key to retrieve.

        Returns:
            str | None: The credential value or None if not found.
        """
        secrets_file = self._get_secrets_file_path()

        if not secrets_file.exists():
            return None

        try:
            with open(secrets_file, "r", encoding="utf-8") as f:
                secrets = json.load(f)
                return secrets.get(key)

        except (json.JSONDecodeError, ValueError):
            # If file is corrupted, treat as if credential doesn't exist
            return None

    def _initialize_from_env(self) -> None:
        """Initialize settings from environment variables at application startup.

        This should be called once during application initialization to set
        default values from environment variables if they are defined.
        """
        # currently not in use
        pass

    def initialize_threading_settings(self, is_pro: bool) -> None:
        """Initialize threading settings with defaults if not present.

        Args:
            is_pro: Whether user has Pro status to determine appropriate defaults
        """
        if is_pro:
            if self.get(SETTING_MAX_PARALLEL_DOWNLOADS) is None:
                self.set(SETTING_MAX_PARALLEL_DOWNLOADS, DEFAULT_MAX_PARALLEL_DOWNLOADS)
            if self.get(SETTING_MAX_PARALLEL_CONVERSIONS) is None:
                self.set(SETTING_MAX_PARALLEL_CONVERSIONS, DEFAULT_MAX_PARALLEL_CONVERSIONS)
        else:
            self.set(SETTING_MAX_PARALLEL_DOWNLOADS, 1)
            self.set(SETTING_MAX_PARALLEL_CONVERSIONS, 0)  # conversions is a pro-only feature

        self.sync()

    def get(self, key: str, default=None):
        """Get a setting value by key with automatic type conversion.

        Args:
            key: Setting key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Setting value with proper type conversion, or default if not found
        """
        value = self._settings.value(key, default)

        # If we got the default value, return it as-is (it's already the correct type)
        if value == default:
            return default

        # Handle type conversion based on default type if provided
        if default is not None:
            try:
                # Convert to the same type as the default value
                if isinstance(default, int):
                    return int(value) if value is not None else default
                elif isinstance(default, float):
                    return float(value) if value is not None else default
                elif isinstance(default, bool):
                    # QSettings stores bools as strings "true"/"false"
                    if isinstance(value, str):
                        return value.lower() in ("true", "1", "yes", "on")
                    return bool(value) if value is not None else default
            except (ValueError, TypeError):
                # If conversion fails, return the default
                return default

        return value

    def set(self, key: str, value) -> None:
        """Set a setting value by key.

        Args:
            key: Setting key to set
            value: Value to store
        """
        self._settings.setValue(key, value)

    def sync(self) -> None:
        """Force synchronization of settings to persistent storage.

        This is typically called automatically by QSettings, but can be
        called manually to ensure settings are immediately written to disk.
        """
        self._settings.sync()

    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values.

        This will clear all stored settings and restore default values
        for all configuration options. Use with caution.
        """
        self._settings.clear()


# Create module-level singleton instance
settings = SettingsManager()
