"""Tree widget for displaying and managing cloudcasts."""

import re
import unicodedata
from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from app.consts.audio import AUDIO_FORMATS
from app.consts.ui import (
    CANCELLED_ICON,
    COMPLETE_ICON,
    ERROR_ICON,
    TREE_SELECT_COLUMN_WIDTH,
    TREE_STATUS_COLUMN_WIDTH,
    TREE_TITLE_COLUMN_WIDTH,
)
from app.custom_widgets.cloudcast_q_tree_widget_item import CloudcastQTreeWidgetItem
from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.custom_widgets.dialogs.get_pro_persuasion_dialog import GetProPersuasionDialog
from app.data_classes import Cloudcast, MixcloudUser
from app.services.api_service import MixcloudAPIService, api_service
from app.services.download_manager import DownloadManager
from app.services.file_service import FileService, file_service
from app.services.license_manager import LicenseManager, license_manager
from app.services.settings_manager import SettingsManager, settings
from app.threads.get_cloudcasts_thread import GetCloudcastsThread


class CloudcastQTreeWidget(QTreeWidget):
    """Tree widget for displaying cloudcasts with selection and download functionality.

    This widget shows a list of cloudcasts from a selected user, allows selection
    of multiple items, and provides download functionality with progress tracking.
    """

    def __init__(
        self,
        api_service: MixcloudAPIService = api_service,
        file_service: FileService = file_service,
        license_manager: LicenseManager = license_manager,
        settings_manager: SettingsManager = settings,
    ) -> None:
        """Initialize the cloudcast tree widget with columns and background threads.

        Args:
            api_service: Service for API operations.
            file_service: Service for file operations.
            license_manager: License manager for Pro status checking.
            settings_manager: Settings manager for preference persistence.
        """
        super().__init__()

        # Store services
        self.api_service = api_service
        self.file_service = file_service
        self.license_manager = license_manager
        self.settings_manager = settings_manager

        # Configure tree widget columns
        self.setColumnCount(3)
        self.setHeaderLabels(["select", "title", "download status"])
        self.header().resizeSection(0, TREE_SELECT_COLUMN_WIDTH)
        self.header().resizeSection(1, TREE_TITLE_COLUMN_WIDTH)
        self.header().resizeSection(2, TREE_STATUS_COLUMN_WIDTH)
        self.setHeaderHidden(True)

        # Initialize and connect cloudcast fetching thread
        self.get_cloudcasts_thread = GetCloudcastsThread(api_service=self.api_service)
        self.get_cloudcasts_thread.error_signal.connect(self.show_error)
        self.get_cloudcasts_thread.new_result.connect(self.add_result)
        self.get_cloudcasts_thread.interrupt_signal.connect(self.clear)

        self.download_manager = DownloadManager(
            settings_manager=self.settings_manager, license_manager=self.license_manager
        )

        # Connect download manager signals to existing handlers
        self.download_manager.task_progress.connect(self.handle_task_progress)
        self.download_manager.task_result.connect(self.handle_task_result)
        self.download_manager.task_error.connect(self.handle_task_error)
        self.download_manager.task_cancelled.connect(self.handle_task_cancelled)
        self.download_manager.task_finished.connect(self.handle_task_finished)

    def _get_download_dir(self) -> Path | None:
        """Get download directory using Pro-aware directory selection.

        Returns:
            Selected directory path, or None if cancelled
        """
        # Use file service's Pro-aware directory selection
        directory_str = self.file_service.get_pro_download_directory(
            self.license_manager, self.settings_manager, self
        )
        return Path(directory_str) if directory_str else None

    def _get_tree_items(self) -> list[QTreeWidgetItem]:
        """Get all top-level items in the tree.

        Returns:
            List of all tree widget items
        """
        root = self.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount())]

    def get_selected_cloudcasts(self) -> list[CloudcastQTreeWidgetItem]:
        """Get all checked/selected cloudcast items.

        Returns:
            List of selected cloudcast tree items
        """
        return [
            sc
            for sc in self._get_tree_items()
            if isinstance(sc, CloudcastQTreeWidgetItem)
            and sc.checkState(0) == Qt.CheckState.Checked
        ]

    @Slot(MixcloudUser)
    def get_cloudcasts(self, user: MixcloudUser) -> None:
        """Start fetching cloudcasts for the specified user.

        Args:
            user: MixcloudUser whose cloudcasts to fetch
        """
        self.get_cloudcasts_thread.user = user
        self.clear()

        if self.get_cloudcasts_thread.isRunning():
            self.get_cloudcasts_thread.stop()
        self.get_cloudcasts_thread.start()

    @Slot()
    def show_error(self, msg: str) -> None:
        """Display error dialog with the given message.

        Args:
            msg: Error message to display
        """
        ErrorDialog(self.parent(), message=msg)

    @Slot()
    def show_pro_persuasion_dialog(self) -> None:
        """Display Pro persuasion dialog after successful download completion."""
        if GetProPersuasionDialog.should_show():
            dialog = GetProPersuasionDialog(self.parent())
            dialog.exec()

    @Slot()
    def select_all(self) -> None:
        """Select all cloudcast items in the tree."""
        for item in self._get_tree_items():
            item.setCheckState(0, Qt.CheckState.Checked)

    @Slot()
    def unselect_all(self) -> None:
        """Unselect all cloudcast items in the tree."""
        for item in self._get_tree_items():
            item.setCheckState(0, Qt.CheckState.Unchecked)

    @Slot()
    def download_selected_cloudcasts(self) -> None:
        """Download selected cloudcasts using DownloadManager system.

        This method uses the new PyQt threading patterns with proper signal
        emission and resource management.
        """
        download_dir = self._get_download_dir()
        if not download_dir:  # User cancelled directory selection
            return

        items = self.get_selected_cloudcasts()
        if not items:  # No items selected
            return

        # Extract cloudcasts from tree items
        cloudcasts = [item.cloudcast for item in items]

        # Start downloads using download manager
        self.download_manager.start_downloads(cloudcasts=cloudcasts, download_dir=str(download_dir))

    @Slot(Cloudcast)
    def add_result(self, cloudcast: Cloudcast) -> None:
        """Add a new cloudcast item to the tree.

        Args:
            cloudcast: Cloudcast data to add as a tree item
        """
        item = CloudcastQTreeWidgetItem(cloudcast=cloudcast)
        self.addTopLevelItem(item)

    @Slot()
    def cancel_cloudcasts_download(self) -> None:
        """Cancel all active downloads using DownloadManager system."""
        self.download_manager.cancel_all()

    def _normalize_filename(self, name: str) -> str:
        """Normalize a filename for consistent matching using comprehensive Unicode handling.

        This method systematically transforms Unicode characters to ASCII equivalents
        for reliable filename matching between expected names and yt-dlp filenames.
        It also removes known file extensions to focus on the content name.

        Args:
            name: Raw filename to normalize

        Returns:
            Normalized filename with Unicode characters properly handled and extensions removed
        """
        # Step 1: Unicode normalization (NFKC converts compatibility characters to standard forms)
        # This handles characters like BIG SOLIDUS (⧸) -> SOLIDUS (/)
        normalized = unicodedata.normalize("NFKC", name)

        # Step 2: Handle accented characters by decomposing them and keeping base characters
        # This converts characters like "á" to "a", "ñ" to "n", "ó" to "o", etc.
        ascii_normalized = ""
        for char in normalized:
            if ord(char) < 128:
                # Already ASCII, keep as-is
                ascii_normalized += char
            else:
                # Try to decompose the character and extract the base character
                decomposed = unicodedata.normalize("NFD", char)
                base_char = ""
                for component in decomposed:
                    if ord(component) < 128:
                        base_char += component
                        break  # Take only the first ASCII component

                # If we found a base character, use it; otherwise skip the character entirely
                if base_char:
                    ascii_normalized += base_char
                # Characters that can't be decomposed to ASCII are simply removed

        # Step 3: Clean up the result
        # Remove only truly problematic filesystem characters
        # Keep safe punctuation like colons, asterisks, hyphens, periods, parentheses
        cleaned = re.sub(r'[<>"/\\|?]', "", ascii_normalized)

        # Replace multiple spaces with single space (AFTER removing special chars)
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Step 4: Remove actual file extensions (not date parts like .17)
        # Only strip known audio/video file extensions
        result = cleaned.lower().strip()
        for audio_format in AUDIO_FORMATS.values():
            extension = audio_format.extension  # Already has dot like ".mp3"
            if result.endswith(extension):
                result = result[: -len(extension)]
                break

        return result

    def _get_normalized_expected_name(self, item: CloudcastQTreeWidgetItem) -> str:
        """Get normalized expected name for a cloudcast item for matching with yt-dlp filenames.

        Args:
            item: CloudcastQTreeWidgetItem to get expected name for

        Returns:
            Normalized expected name in format "username - cloudcast_name"
        """
        expected_name = f"{item.cloudcast.user.name} - {item.cloudcast.name}"
        return self._normalize_filename(expected_name)

    @Slot(str, str)
    def update_item_download_progress(self, name: str, progress: str) -> None:
        """Update download progress for a specific cloudcast item.

        Args:
            name: Name of the cloudcast being downloaded (from yt-dlp filename)
            progress: Progress information string
        """
        # Normalize the incoming name from yt-dlp (this also removes file extensions)
        name_normalized = self._normalize_filename(name)

        selected_items = self.get_selected_cloudcasts()

        # Find exact match using normalized names
        for item in selected_items:
            expected_normalized = self._get_normalized_expected_name(item)

            # Try exact match first
            if name_normalized == expected_normalized:
                item.update_download_progress(progress)
                return

            # Try matching without username prefix (yt-dlp sometimes omits it)
            # Extract just the cloudcast name part from expected
            username_prefix = self._normalize_filename(item.cloudcast.user.name) + " - "
            if expected_normalized.startswith(username_prefix):
                expected_without_username = expected_normalized[len(username_prefix) :]
                if name_normalized == expected_without_username:
                    item.update_download_progress(progress)
                    return

    # TaskManager signal handlers for URL-based progress tracking

    @Slot(str, str)
    def handle_task_progress(self, task_id: str, progress_text: str) -> None:
        """Handle progress updates from TaskManager using URL-based lookup.

        Args:
            task_id: Cloudcast URL (task identifier)
            progress_text: Progress information to display
        """
        item = self._find_item_by_url(task_id)
        if item:
            item.update_download_progress(progress_text)

    @Slot(str, str, bool)
    def handle_task_result(self, task_id: str, result_path: str, will_convert: bool) -> None:
        """Handle task completion with result.

        Args:
            task_id: Cloudcast URL (task identifier)
            result_path: Path to completed file
            will_convert: Whether conversion will happen after this download
        """
        item = self._find_item_by_url(task_id)
        if item:
            if will_convert:
                item.update_download_progress("Download complete, preparing conversion...")
            else:
                item.update_download_progress(f"{COMPLETE_ICON} Complete")

    @Slot(str, str)
    def handle_task_error(self, task_id: str, error_message: str) -> None:
        """Handle task error.

        Args:
            task_id: Cloudcast URL (task identifier)
            error_message: Error details
        """
        item = self._find_item_by_url(task_id)
        if item:
            item.update_download_progress(f"{ERROR_ICON} Failed")

        # Show error via existing error handling
        self.show_error(f"Download failed: {error_message}")

    @Slot(str)
    def handle_task_cancelled(self, task_id: str) -> None:
        """Handle task cancellation.

        Args:
            task_id: Cloudcast URL (task identifier)
        """
        item = self._find_item_by_url(task_id)
        if item:
            item.update_download_progress(f"{CANCELLED_ICON} Cancelled")

    @Slot(str)
    def handle_task_finished(self, task_id: str) -> None:
        """Handle task finished (cleanup).

        Args:
            task_id: Cloudcast URL (task identifier)
        """
        # Task cleanup if needed in the future
        pass

    def _find_item_by_url(self, cloudcast_url: str) -> CloudcastQTreeWidgetItem | None:
        """Find tree item by matching cloudcast URL.

        Args:
            cloudcast_url: URL to search for

        Returns:
            Matching CloudcastQTreeWidgetItem or None if not found
        """
        # Search through all items, not just selected ones
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if isinstance(item, CloudcastQTreeWidgetItem) and item.cloudcast.url == cloudcast_url:
                return item
        return None
