import sys
from typing import Callable

import requests
from PySide2.QtCore import Qt, QTimer, Slot
from PySide2.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from .api import search_user_API_url, user_cloudcasts_API_url
from .custom_widgets import CloudcastQListWidgetItem, UserQListWidgetItem
from .data_classes import Cloudcast, MixcloudUser


class Widget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()

        self.search_user_layout = QHBoxLayout()
        self.search_user_layout.setAlignment(Qt.AlignTop)

        self.search_user_label = QLabel('Search account/artist:')
        self.search_user_layout.addWidget(self.search_user_label)

        self.search_user_input = QLineEdit()
        self.search_user_layout.addWidget(self.search_user_input)

        self.search_user_result_layout = QVBoxLayout()
        self.search_user_results_list = QListWidget()
        self.search_user_result_layout.addWidget(self.search_user_results_list)

        self.user_cloudcasts_layout = QVBoxLayout()
        self.user_cloudcasts_results = QListWidget()
        self.user_cloudcasts_layout.addWidget(self.user_cloudcasts_results)

        self.layout.addLayout(self.search_user_layout)
        self.layout.addLayout(self.search_user_result_layout)
        self.layout.addLayout(self.user_cloudcasts_layout)

        self.setLayout(self.layout)

        self._connect_with_delay(
            input=self.search_user_input.textChanged[str],
            slot=self.search_account
        )

    def _connect_with_delay(self, input: Callable, slot: Slot, delay_ms: int = 750):
        """Connects a given input to a given Slot with a given delay."""
        self.timer = QTimer()
        self.timer.setInterval(delay_ms)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(slot)
        input.connect(self.timer.start)

    @Slot()
    def search_account(self):
        self.search_user_results_list.clear()
        phrase = self.search_user_input.text()
        url = search_user_API_url(phrase=phrase)
        req = requests.get(url=url)
        response = req.json()
        data = response['data']

        for result in data:
            user = MixcloudUser(**result)
            item = UserQListWidgetItem(user=user)

            self.search_user_results_list.addItem(item)

        self.search_user_results_list.itemClicked.connect(self.get_cloudcasts)

    @Slot()
    def get_cloudcasts(self):
        self.user_cloudcasts_results.clear()
        username = self.search_user_results_list.currentItem().user.username
        self._query_cloudcasts(username=username)

    def _query_cloudcasts(self, username: str, url: str = ''):
        if not url:
            url = user_cloudcasts_API_url(username=username)

        req = requests.get(url=url)
        response = req.json()
        data = response['data']

        for cloudcast in data:
            cloudcast = Cloudcast(
                name=cloudcast['name'],
                url=cloudcast['url'],
                user=self.search_user_results_list.currentItem().user,
            )
            item = CloudcastQListWidgetItem(cloudcast=cloudcast)

            item.setCheckState(Qt.Unchecked)
            self.user_cloudcasts_results.addItem(item)

        if response.get('paging') and response['paging'].get('next'):
            next_url = response['paging'].get('next')
            self._query_cloudcasts(username=username, url=next_url)


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        widget = Widget()

        self.setWindowTitle('MCDLR')
        self.setMinimumSize(600, 400)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('Exit', QApplication.quit)

        self.setCentralWidget(widget)


if __name__ == '__main__':
    application = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(application.exec_())
