"""Settings management for Mixcloud Bulk Downloader using QSettings."""

from PySide6.QtCore import QSettings

from app.consts import FF_SETTINGS_PANE_ENABLED


class MBDSettings:
    """Settings manager for Mixcloud Bulk Downloader application.

    This class provides a centralized interface for reading and writing
    application settings using Qt's QSettings for cross-platform persistence.
    Settings are automatically stored in platform-appropriate locations.
    """

    def __init__(self) -> None:
        """Initialize settings manager with QSettings backend.

        QSettings automatically handles platform-specific storage locations:
        - macOS: ~/Library/Preferences/com.mixcloud-bulk-downloader.plist
        - Windows: HKEY_CURRENT_USER\Software\mixcloud-bulk-downloader
        - Linux: ~/.config/mixcloud-bulk-downloader.conf
        """
        self._settings = QSettings("mixcloud-bulk-downloader", "Mixcloud Bulk Downloader")
        self._initialize_from_env()

    @property
    def settings_pane_enabled(self) -> bool:
        """Get whether the settings pane should be accessible to users.

        Returns:
            bool: True if settings pane should be shown, False otherwise.
                 Defaults to False for new installations.
        """
        return bool(self._settings.value("settings_pane_enabled", False, type=bool))

    @settings_pane_enabled.setter
    def settings_pane_enabled(self, enabled: bool) -> None:
        """Set whether the settings pane should be accessible to users.

        Args:
            enabled: True to enable settings pane access, False to disable.
        """
        self._settings.setValue("settings_pane_enabled", enabled)

    def _initialize_from_env(self) -> None:
        """Initialize settings from environment variables at application startup.

        This should be called once during application initialization to set
        default values from environment variables if they are defined.
        """
        self.settings_pane_enabled = FF_SETTINGS_PANE_ENABLED

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
