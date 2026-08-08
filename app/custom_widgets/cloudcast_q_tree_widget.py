"""Tree widget for displaying and managing cloudcasts."""

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem

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
        self.setMinimumWidth(
            TREE_SELECT_COLUMN_WIDTH + TREE_TITLE_COLUMN_WIDTH + TREE_STATUS_COLUMN_WIDTH
        )

        # Set column resize modes for dynamic resizing
        header = self.header()

        self.setColumnWidth(0, TREE_SELECT_COLUMN_WIDTH)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select column - fixed size
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Title column - stretches
        header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )  # Status column - content-aware size

        # Initially hide the status column until downloads start
        self.setColumnHidden(2, True)

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

    def clear(self) -> None:
        """Clear all items from the tree and hide the status column."""
        super().clear()
        # Hide status column since there are no items with progress to display
        self.setColumnHidden(2, True)

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

        # Show status column since downloads will start
        self.setColumnHidden(2, False)

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

    @Slot(Cloudcast)
    def add_single_cloudcast(self, cloudcast: Cloudcast) -> None:
        """Clear the tree and show a single cloudcast selected directly from search.

        Args:
            cloudcast: Cloudcast to display as the sole tree item
        """
        if self.get_cloudcasts_thread.isRunning():
            self.get_cloudcasts_thread.stop()
        self.clear()
        self.add_result(cloudcast=cloudcast)

    @Slot()
    def cancel_cloudcasts_download(self) -> None:
        """Cancel all active downloads using DownloadManager system."""
        self.download_manager.cancel_all()

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
