"""Main application entry point for Mixcloud Bulk Downloader."""

import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.qt_logger import log_ui, QtLogger
from app.styles import load_application_styles
from app.utils.version import set_current_version


def main() -> None:
    """Main application entry point."""
    try:
        application = QApplication(sys.argv)

        # Initialize Qt logging system after QApplication
        qt_logger = QtLogger()
        log_ui("Application starting up", "INFO")

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
            from pathlib import Path

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
