"""Tree widget item for displaying individual cloudcasts."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

from app.data_classes import Cloudcast


class CloudcastQTreeWidgetItem(QTreeWidgetItem):
    """Tree widget item representing a single cloudcast with checkbox and progress display.

    This item displays cloudcast information in a tree widget with columns for
    selection checkbox, title, and download progress.
    """

    def __init__(self, cloudcast: Cloudcast) -> None:
        """Initialize the tree item with cloudcast data.

        Args:
            cloudcast: Cloudcast data to display in this item
        """
        super().__init__()

        self.cloudcast = cloudcast

        # Set up the tree item columns
        self.setCheckState(0, Qt.CheckState.Unchecked)  # Column 0: Checkbox (unchecked by default)
        self.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.setText(1, cloudcast.name)  # Column 1: Cloudcast title

        # Column 2: Download progress (initially empty)
        self.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def update_download_progress(self, progress: str) -> None:
        """Update the download progress display for this item.

        Args:
            progress: Progress information string to display
        """
        self.setText(2, progress)
