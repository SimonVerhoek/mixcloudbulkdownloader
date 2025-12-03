"""Update notification dialog with download progress integration."""

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.qt_logger import log_error_with_traceback
from app.services.update_service import UpdateService, update_service
from app.threads.update_download_thread import UpdateDownloadThread


class UpdateProgressDialog(QDialog):
    """Custom progress dialog for update downloads following ErrorDialog pattern.

    Provides a modal dialog with progress bar and dynamic button management
    for download cancellation and completion actions.
    """

    canceled = Signal()  # Emitted when user cancels

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the progress dialog.

        Args:
            parent: Parent widget for the dialog
        """
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Downloading Update")
        self.setFixedSize(400, 150)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        layout = QVBoxLayout(self)

        # Status label
        self.status_label = QLabel("Downloading update...")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Button layout
        button_layout = QHBoxLayout()

        # Cancel button (shown during download)
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.cancel_button)

        # Close button (shown after completion/cancellation)
        self.close_button = QPushButton("Close")
        self.close_button.setVisible(False)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """Connect button signals."""
        self.cancel_button.clicked.connect(self._handle_cancel)
        self.close_button.clicked.connect(self.close)

    def show_cancel_only(self) -> None:
        """Show only cancel button during download."""
        self.cancel_button.setVisible(True)
        self.close_button.setVisible(False)

    def show_completion_buttons(self) -> None:
        """Replace cancel with close button."""
        self.status_label.setText("Download completed!")
        self.progress_bar.setValue(100)

        self.cancel_button.setVisible(False)
        self.close_button.setVisible(True)

    def show_cancellation_buttons(self) -> None:
        """Show only close button on cancellation."""
        self.status_label.setText("Download cancelled")
        self.cancel_button.setVisible(False)
        self.close_button.setVisible(True)

    def _handle_cancel(self) -> None:
        """Handle cancel button click."""
        self.canceled.emit()


class UpdateDialog(QDialog):
    """Main update notification dialog with release information and download trigger.

    Displays release information and provides options to download the update
    with integrated progress tracking.
    """

    def __init__(
        self,
        current_version: str,
        latest_version: str,
        download_url: str,
        release_notes: str,
        update_service_instance: UpdateService = update_service,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the update dialog.

        Args:
            current_version: Current application version
            latest_version: Latest available version
            download_url: URL to download the update
            release_notes: Release notes/changelog
            update_service_instance: Service for update operations
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_version = current_version
        self.latest_version = latest_version
        self.download_url = download_url
        self.release_notes = release_notes
        self.update_service = update_service_instance

        self.download_thread: UpdateDownloadThread | None = None
        self.progress_dialog: UpdateProgressDialog | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the dialog UI components."""
        self.setWindowTitle("Update Available")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # Version information
        version_label = QLabel(
            f"<h2>Update Available</h2>"
            f"<p>Current version: <b>{self.current_version}</b></p>"
            f"<p>Latest version: <b>{self.latest_version}</b></p>"
        )
        version_label.setTextFormat(Qt.RichText)
        layout.addWidget(version_label)

        # Release notes
        notes_label = QLabel("Release Notes:")
        layout.addWidget(notes_label)

        self.release_notes_text = QTextEdit()
        self.release_notes_text.setPlainText(self.release_notes)
        self.release_notes_text.setReadOnly(True)
        self.release_notes_text.setMaximumHeight(200)
        layout.addWidget(self.release_notes_text)

        # Button box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.download_button = QPushButton("Download Now")
        self.button_box.addButton(self.download_button, QDialogButtonBox.AcceptRole)
        layout.addWidget(self.button_box)

    def _connect_signals(self) -> None:
        """Connect dialog signals."""
        self.button_box.rejected.connect(self.reject)
        self.download_button.clicked.connect(self._start_download)

    def _start_download(self) -> None:
        """Start the download process with progress dialog."""
        try:
            # Determine file extension based on platform
            file_extension = ".dmg" if sys.platform == "darwin" else ".zip"
            default_filename = f"MixcloudBulkDownloader-{self.latest_version}{file_extension}"

            # Set file filter for dialog
            if sys.platform == "darwin":
                file_filter = "Disk Images (*.dmg);;All Files (*)"
            else:
                file_filter = "ZIP Archives (*.zip);;All Files (*)"

            # Prompt user for save location
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Update File",
                str(Path.home() / "Downloads" / default_filename),
                file_filter,
            )

            # User cancelled the dialog
            if not save_path:
                return

            # Create and configure progress dialog (with parent for proper window relationship)
            self.progress_dialog = UpdateProgressDialog(self)
            self.progress_dialog.show_cancel_only()

            # Create download thread with full target path (no parent to prevent Qt cleanup issues)
            self.download_thread = UpdateDownloadThread(
                self.download_url, save_path, self.update_service
            )

            # Connect thread signals
            self.download_thread.download_progress.connect(self._on_download_progress)
            self.download_thread.download_finished.connect(self._on_download_finished)
            self.download_thread.error_occurred.connect(self._on_download_error)

            # Connect progress dialog cancellation
            self.progress_dialog.canceled.connect(self._cancel_download)

            # Start download
            self.progress_dialog.show()
            self.download_thread.start()

            # Disable main dialog buttons during download (keep dialog visible but non-interactive)
            self.button_box.setEnabled(False)

        except Exception as e:
            log_error_with_traceback(f"Failed to start download: {e}")
            ErrorDialog(self, f"Failed to start download: {str(e)}")

    def _on_download_progress(self, value: int) -> None:
        """Handle download progress updates.

        Args:
            value: Progress value (0-100)
        """
        if self.progress_dialog:
            self.progress_dialog.progress_bar.setValue(value)

    def _on_download_finished(self, path: str) -> None:
        """Handle download completion.

        Args:
            path: Path to the downloaded file
        """
        if self.progress_dialog:
            self.progress_dialog.show_completion_buttons()

        # Re-enable main dialog buttons
        self.button_box.setEnabled(True)

        # Show enhanced completion message with reveal option
        self._show_download_complete_dialog(path)

        # Close the main update dialog after successful completion
        self.accept()

    def _show_download_complete_dialog(self, file_path: str) -> None:
        """Show enhanced download completion dialog with reveal option.

        Args:
            file_path: Path to the downloaded file
        """
        msgBox = QMessageBox(self)
        msgBox.setIcon(QMessageBox.Icon.Information)
        msgBox.setWindowTitle("Download Complete")
        msgBox.setText("The installer has been downloaded successfully!")
        msgBox.setInformativeText(f"The installer has been downloaded to:\n{file_path}")

        # Add custom "Show in Finder" button based on platform
        if sys.platform == "darwin":
            reveal_button = msgBox.addButton("Show in Finder", QMessageBox.ButtonRole.ActionRole)
        else:
            reveal_button = msgBox.addButton("Open folder", QMessageBox.ButtonRole.ActionRole)

        # Add standard OK button
        ok_button = msgBox.addButton(QMessageBox.StandardButton.Ok)
        msgBox.setDefaultButton(ok_button)

        # Execute dialog and handle button clicks
        result = msgBox.exec()

        # Handle reveal button click
        if msgBox.clickedButton() == reveal_button:
            self._reveal_file(file_path)

    def _reveal_file(self, file_path: str) -> None:
        """Reveal downloaded file in system file manager.

        Args:
            file_path: Path to the file to reveal
        """
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", "-R", file_path], check=True)
            elif sys.platform.startswith("win"):
                subprocess.run(["explorer", "/select,", file_path], check=True)
            # Note: Linux support could be added here if needed
        except subprocess.CalledProcessError:
            # If reveal fails, just ignore it - it's not critical
            pass

    def _on_download_error(self, error_message: str) -> None:
        """Handle download errors.

        Args:
            error_message: Error description
        """
        if self.progress_dialog:
            self.progress_dialog.close()

        # Re-enable main dialog buttons
        self.button_box.setEnabled(True)

        ErrorDialog(self, f"Download failed: {error_message}")

    def _cancel_download(self) -> None:
        """Cancel the ongoing download."""
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()

        # Re-enable main dialog buttons
        self.button_box.setEnabled(True)

        if self.progress_dialog:
            self.progress_dialog.show_cancellation_buttons()

    def closeEvent(self, event) -> None:
        """Handle dialog close event with thread cleanup."""
        if self.download_thread and self.download_thread.isRunning():
            # Disconnect signals first to prevent access to destroyed objects
            self.download_thread.download_progress.disconnect()
            self.download_thread.download_finished.disconnect()
            self.download_thread.error_occurred.disconnect()

            # Stop thread with proper cleanup
            self.download_thread.stop()

        if self.progress_dialog:
            self.progress_dialog.close()

        super().closeEvent(event)
