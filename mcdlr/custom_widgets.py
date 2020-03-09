from typing import List

from PySide2.QtCore import Qt, Slot
from PySide2.QtWidgets import QListWidgetItem, QTreeWidget, QTreeWidgetItem

from .api import (
    get_mixcloud_API_data,
    user_cloudcasts_API_url,
)
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

        self.results: List[Cloudcast] = []

    @Slot(MixcloudUser)
    def get_cloudcasts(self, user: MixcloudUser) -> None:
        self.clear()
        self._query_cloudcasts(user=user)
        for cloudcast in self.results:
            item = CloudcastQTreeItem(cloudcast=cloudcast)
            self.addTopLevelItem(item)

    def _query_cloudcasts(self, user: MixcloudUser, url: str = ''):
        if not url:
            url = user_cloudcasts_API_url(username=user.username)

        self.results.clear()
        response = get_mixcloud_API_data(url=url)

        for cloudcast in response['data']:
            cloudcast = Cloudcast(
                name=cloudcast['name'], url=cloudcast['url'], user=user,
            )
            self.results.append(cloudcast)

        if response.get('paging') and response['paging'].get('next'):
            next_url = response['paging'].get('next')
            self._query_cloudcasts(user=user, url=next_url)

    @Slot()
    def select_all(self) -> None:
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setCheckState(0, Qt.Checked)

    @Slot()
    def unselect_all(self) -> None:
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            item.setCheckState(0, Qt.Unchecked)


class CloudcastQTreeItem(QTreeWidgetItem):
    def __init__(self, cloudcast: Cloudcast):
        super().__init__()

        self.cloudcast = cloudcast
        self.setCheckState(0, Qt.Unchecked)
        self.setText(1, cloudcast.name)
