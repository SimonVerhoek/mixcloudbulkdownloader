from PySide2.QtCore import Qt
from PySide2.QtWidgets import QListWidgetItem, QTreeWidget, QTreeWidgetItem

from .data_classes import Cloudcast, MixcloudUser


class UserQListWidgetItem(QListWidgetItem):
    def __init__(self, user: MixcloudUser):
        super().__init__(f'{user.name} ({user.username})')

        self.user = user


class CloudcastQTree(QTreeWidget):
    def __init__(self):
        super().__init__()

        self.setColumnCount(3)
        self.setHeaderLabels(['select', 'title', 'download status'])
        self.header().resizeSection(0, 50)
        self.header().resizeSection(1, 400)
        self.setHeaderHidden(True)


class CloudcastQTreeItem(QTreeWidgetItem):
    def __init__(self, cloudcast: Cloudcast):
        super().__init__()

        self.cloudcast = cloudcast
        self.setCheckState(0, Qt.Unchecked)
        self.setText(1, cloudcast.name)
