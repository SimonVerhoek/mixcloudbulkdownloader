from typing import List

from PySide2.QtCore import Qt, Slot
from PySide2.QtWidgets import QTreeWidget, QTreeWidgetItem

from ..api import get_mixcloud_API_data, user_cloudcasts_API_url
from ..data_classes import Cloudcast, MixcloudUser
from .cloudcast_q_tree_widget_item import CloudcastQTreeWidgetItem


class CloudcastQTreeWidget(QTreeWidget):
    def __init__(self):
        super().__init__()

        self.setColumnCount(3)
        self.setHeaderLabels(['select', 'title', 'download status'])
        self.header().resizeSection(0, 50)
        self.header().resizeSection(1, 400)
        self.setHeaderHidden(True)

        self.results: List[Cloudcast] = []

    def _get_tree_items(self) -> List[QTreeWidgetItem]:
        root = self.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount())]

    def get_selected_cloudcasts(self) -> List[QTreeWidgetItem]:
        selected_cloudcasts = []
        for item in self._get_tree_items():
            if item.checkState(0) == Qt.Checked:
                selected_cloudcasts.append(item)
        return selected_cloudcasts

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

    @Slot(MixcloudUser)
    def get_cloudcasts(self, user: MixcloudUser) -> None:
        self.clear()
        self._query_cloudcasts(user=user)
        for cloudcast in self.results:
            item = CloudcastQTreeWidgetItem(cloudcast=cloudcast)
            self.addTopLevelItem(item)

    @Slot()
    def select_all(self) -> None:
        for item in self._get_tree_items():
            item.setCheckState(0, Qt.Checked)

    @Slot()
    def unselect_all(self) -> None:
        for item in self._get_tree_items():
            item.setCheckState(0, Qt.Unchecked)
