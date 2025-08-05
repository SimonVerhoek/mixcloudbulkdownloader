"""Tree widget for displaying and managing cloudcasts."""

import re
import unicodedata
from os.path import expanduser

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QFileDialog, QTreeWidget, QTreeWidgetItem

from app.consts import (
    KNOWN_MEDIA_EXTENSIONS,
    TREE_SELECT_COLUMN_WIDTH,
    TREE_STATUS_COLUMN_WIDTH,
    TREE_TITLE_COLUMN_WIDTH,
)
from app.custom_widgets.cloudcast_q_tree_widget_item import CloudcastQTreeWidgetItem
from app.custom_widgets.error_dialog import ErrorDialog
from app.data_classes import Cloudcast, MixcloudUser
from app.services.api_service import MixcloudAPIService
from app.services.download_service import DownloadService
from app.services.file_service import FileService
from app.threads import DownloadThread, GetCloudcastsThread


class CloudcastQTreeWidget(QTreeWidget):
    """Tree widget for displaying cloudcasts with selection and download functionality.

    This widget shows a list of cloudcasts from a selected user, allows selection
    of multiple items, and provides download functionality with progress tracking.
    """

    def __init__(
        self,
        api_service: MixcloudAPIService | None = None,
        download_service: DownloadService | None = None,
        file_service: FileService | None = None,
    ) -> None:
        """Initialize the cloudcast tree widget with columns and background threads.

        Args:
            api_service: Service for API operations. If None, creates default.
            download_service: Service for downloads. If None, creates default.
            file_service: Service for file operations. If None, creates default.
        """
        super().__init__()

        # Store services
        self.api_service = api_service or MixcloudAPIService()
        self.download_service = download_service or DownloadService()
        self.file_service = file_service or FileService()

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

        # Initialize and connect download thread
        self.download_thread = DownloadThread(download_service=self.download_service)
        self.download_thread.error_signal.connect(self.show_error)
        self.download_thread.progress_signal.connect(self.update_item_download_progress)

    def _get_download_dir(self) -> str:
        """Show directory selection dialog and return selected path.

        Returns:
            Selected directory path, or empty string if cancelled
        """
        return self.file_service.select_download_directory(
            parent=self, title="Select download location"
        )

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
        """Start downloading all selected cloudcasts to user-chosen directory."""
        download_dir = self._get_download_dir()
        if not download_dir:  # User cancelled directory selection
            return

        items = self.get_selected_cloudcasts()
        if not items:  # No items selected
            return

        self.download_thread.download_dir = download_dir
        self.download_thread.urls = [item.cloudcast.url for item in items]
        self.download_thread.start()

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
        """Cancel the current download operation."""
        self.download_thread.stop()

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
        for ext in KNOWN_MEDIA_EXTENSIONS:
            if result.endswith(ext):
                result = result[: -len(ext)]
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
