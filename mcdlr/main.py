import sys
from os.path import expanduser
from typing import Any, Callable, Dict

from PySide2.QtCore import Qt, QTimer, Slot
from PySide2.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .api import (
    get_mixcloud_API_data,
    search_user_API_url,
)
from .custom_widgets import CloudcastQTree
from .data_classes import MixcloudUser
from .threading import DownloadThread


class Widget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()

        search_user_layout = QHBoxLayout()
        search_user_layout.setAlignment(Qt.AlignTop)

        self.search_user_label = QLabel('Search account/artist:')
        search_user_layout.addWidget(self.search_user_label)

        # self.search_user_input = QLineEdit()
        self.search_user_input = QComboBox()
        self.search_user_input.setEditable(True)
        self.user_suggestions: Dict[str, MixcloudUser] = {}
        self.selected_user: Any[MixcloudUser, None] = None
        self.get_cloudcasts_button = QPushButton('Get cloudcasts')
        search_user_layout.addWidget(self.search_user_input)
        search_user_layout.addWidget(self.get_cloudcasts_button)

        user_cloudcasts_layout = QVBoxLayout()
        self.user_cloudcasts_results = CloudcastQTree()
        user_cloudcasts_layout.addWidget(self.user_cloudcasts_results)

        cloudcast_action_buttons = QHBoxLayout()
        self.select_all_button = QPushButton('Select All')
        self.unselect_all_button = QPushButton('Unselect All')
        self.cancel_button = QPushButton('Cancel')
        self.download_button = QPushButton('Download')
        cloudcast_action_buttons.addWidget(self.select_all_button)
        cloudcast_action_buttons.addWidget(self.unselect_all_button)
        cloudcast_action_buttons.addWidget(self.cancel_button)
        cloudcast_action_buttons.addWidget(self.download_button)

        self.layout.addLayout(search_user_layout)
        self.layout.addLayout(user_cloudcasts_layout)
        self.layout.addLayout(cloudcast_action_buttons)

        self.setLayout(self.layout)

        # connections
        self._connect_with_delay(
            input=self.search_user_input.lineEdit().textEdited,
            slot=self.show_suggestions,
        )
        self.search_user_input.activated.connect(self.set_selected_user)
        self.get_cloudcasts_button.clicked.connect(
            lambda user: self.user_cloudcasts_results.get_cloudcasts(
                user=self.selected_user
            )
        )
        self.select_all_button.clicked.connect(self.user_cloudcasts_results.select_all)
        self.unselect_all_button.clicked.connect(
            self.user_cloudcasts_results.unselect_all
        )
        self.download_button.clicked.connect(self.download_selected_cloudcasts)

    @Slot()
    def set_selected_user(self) -> None:
        selected_option = self.search_user_input.currentText()
        username = selected_option.split('(')[1].split(')')[0]
        self.selected_user = self.user_suggestions[username]

    @Slot()
    def show_suggestions(self) -> None:
        phrase = self.search_user_input.currentText()

        if phrase:
            url = search_user_API_url(phrase=phrase)
            response = get_mixcloud_API_data(url=url)

            self.search_user_input.clear()
            self.user_suggestions.clear()

            for result in response['data']:
                user = MixcloudUser(**result)
                self.user_suggestions[user.username] = user
                self.search_user_input.addItem(f'{user.name} ({user.username})')

    @Slot()
    def download_selected_cloudcasts(self) -> None:
        download_dir = self._get_download_dir()
        urls = [item.cloudcast.url for item in self._get_checked_cloudcast_items()]

        DownloadThread(urls=urls, download_dir=download_dir).start()

    def _get_download_dir(self) -> QFileDialog:
        dialog = QFileDialog()
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setOption(QFileDialog.DontResolveSymlinks)
        download_dir = dialog.getExistingDirectory(
            self, 'Select download location', expanduser('~')
        )
        return download_dir

    def _get_checked_cloudcast_items(self):
        selected_cloudcasts = []
        root = self.user_cloudcasts_results.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.Checked:
                selected_cloudcasts.append(item)
        return selected_cloudcasts

    def _connect_with_delay(self, input: Callable, slot: Slot, delay_ms: int = 750):
        """Connects a given input to a given Slot with a given delay."""
        self.timer = QTimer()
        self.timer.setInterval(delay_ms)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(slot)
        input.connect(self.timer.start)


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
