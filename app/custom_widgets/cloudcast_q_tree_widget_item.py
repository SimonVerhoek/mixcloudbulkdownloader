from PySide2.QtCore import Qt
from PySide2.QtWidgets import QTreeWidgetItem

from ..data_classes import Cloudcast


class CloudcastQTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, cloudcast: Cloudcast):
        super().__init__()

        self.cloudcast = cloudcast
        self.setCheckState(0, Qt.Unchecked)
        self.setText(1, cloudcast.name)

    def update_download_progress(self, progress: str):
        self.setText(2, progress)
