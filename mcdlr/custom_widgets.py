from typing import Callable, Dict, List, Optional

from PySide2.QtCore import Qt, QTimer, Slot
from PySide2.QtWidgets import QComboBox, QListWidgetItem, QTreeWidget, QTreeWidgetItem

from .api import get_mixcloud_API_data, search_user_API_url, user_cloudcasts_API_url
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
            item = CloudcastQTreeItem(cloudcast=cloudcast)
            self.addTopLevelItem(item)

    @Slot()
    def select_all(self) -> None:
        for item in self._get_tree_items():
            item.setCheckState(0, Qt.Checked)

    @Slot()
    def unselect_all(self) -> None:
        for item in self._get_tree_items():
            item.setCheckState(0, Qt.Unchecked)


class CloudcastQTreeItem(QTreeWidgetItem):
    def __init__(self, cloudcast: Cloudcast):
        super().__init__()

        self.cloudcast = cloudcast
        self.setCheckState(0, Qt.Unchecked)
        self.setText(1, cloudcast.name)


class SearchUserComboBox(QComboBox):
    def __init__(self):
        super().__init__()

        self.setEditable(True)
        self.results: Dict[str, MixcloudUser] = {}
        self.selected_result: Optional[MixcloudUser] = None

        self._connect_with_delay(
            input=self.lineEdit().textEdited, slot=self.show_suggestions,
        )
        self.activated.connect(self.set_selected_user)

    def _connect_with_delay(self, input: Callable, slot: Slot, delay_ms: int = 750):
        """Connects a given input to a given Slot with a given delay."""
        self.timer = QTimer()
        self.timer.setInterval(delay_ms)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(slot)
        input.connect(self.timer.start)

    @Slot()
    def show_suggestions(self) -> None:
        phrase = self.currentText()

        if phrase:
            url = search_user_API_url(phrase=phrase)
            response = get_mixcloud_API_data(url=url)

            self.clear()
            self.results.clear()

            for result in response['data']:
                user = MixcloudUser(**result)
                self.results[user.username] = user
                self.addItem(f'{user.name} ({user.username})')

    @Slot()
    def set_selected_user(self) -> None:
        selected_option = self.currentText()
        username = selected_option.split('(')[1].split(')')[0]
        self.selected_result = self.results[username]
