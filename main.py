"""Main application entry point for Mixcloud Bulk Downloader."""

import logging
import sys
from pathlib import Path

import sentry_sdk
from PySide6.QtWidgets import QApplication
from sentry_sdk.integrations.logging import LoggingIntegration

from app._version import __version__
from app.consts.settings import DEVELOPMENT, SENTRY_DSN
from app.custom_widgets.dialogs.error_reporting_consent_dialog import ErrorReportingConsentDialog
from app.logger import log_ui
from app.main_window import MainWindow
from app.qt_logger import QtLogger
from app.services.sentry_service import before_breadcrumb, before_send
from app.services.settings_manager import settings
from app.styles import load_application_styles
from app.utils.version import set_current_version


def _on_consent_accepted() -> None:
    """Persist the user's choice to enable error reporting."""
    settings.error_reporting_enabled = True
    settings.error_reporting_consent_shown = True


def _on_consent_rejected() -> None:
    """Persist the user's choice to disable error reporting."""
    settings.error_reporting_enabled = False
    settings.error_reporting_consent_shown = True



def main() -> None:
    """Main application entry point."""
    try:
        application = QApplication(sys.argv)

        # Initialize Qt logging system after QApplication
        qt_logger = QtLogger()
        log_ui("Application starting up", "INFO")

        # Initialize Sentry after QApplication so QSettings (SettingsManager) are accessible.
        # A blank DSN disables Sentry entirely. Environment is derived from the DEVELOPMENT flag.
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment="development" if DEVELOPMENT else "production",
            before_send=before_send,
            before_breadcrumb=before_breadcrumb,
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,        # INFO+ records become breadcrumbs (no quota cost)
                    event_level=logging.ERROR, # ERROR+ records become events (count toward quota)
                ),
            ],
            release=__version__,
            sample_rate=1.0,       # lower this if the 5k/month free limit is regularly hit
            traces_sample_rate=0.0,
            max_breadcrumbs=50,    # halves default breadcrumb payload; does not affect event quota
        )

        # Initialize application version
        version = set_current_version()
        log_ui(f"Application version ({version}) initialized", "INFO")

        # Load application stylesheets
        log_ui("Loading application styles", "INFO")
        load_application_styles(application)

        log_ui("Creating main window", "INFO")
        window = MainWindow()
        window.show()
        window.activateWindow()
        window.raise_()

        # Show first-run consent dialog if the user hasn't seen it yet.
        # Use show() (non-blocking) instead of exec() to avoid a nested event loop.
        # setModal(True) on the dialog still prevents interaction with the main window.
        if not settings.error_reporting_consent_shown:
            _consent_dialog = ErrorReportingConsentDialog(parent=window)
            _consent_dialog.accepted.connect(_on_consent_accepted)
            _consent_dialog.rejected.connect(_on_consent_rejected)
            _consent_dialog.show()

        log_ui("Application ready", "INFO")

        sys.exit(application.exec())
    except Exception as e:
        # Fallback error handling for bundled apps
        import traceback

        error_msg = f"""
            Application startup error: {e}\n
            {traceback.format_exc()}
        """

        # Try to write to log file directly if Qt logging fails
        try:
            log_dir = Path.home() / "Library" / "Logs" / "MixcloudBulkDownloader"
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / "crash.log", "w") as f:
                f.write(error_msg)
        except:
            pass

        # Also output to stderr
        sys.stderr.write(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()
