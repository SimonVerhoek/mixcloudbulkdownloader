import sys
from os.path import expanduser

from PySide2.QtCore import Qt, Slot
from PySide2.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .custom_widgets import CloudcastQTree, SearchUserComboBox
from .threading import DownloadThread


class Widget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()

        search_user_layout = QHBoxLayout()
        search_user_layout.setAlignment(Qt.AlignTop)

        self.search_user_label = QLabel('Search account/artist:')
        search_user_layout.addWidget(self.search_user_label)

        self.search_user_input = SearchUserComboBox()
        self.get_cloudcasts_button = QPushButton('Get cloudcasts')
        search_user_layout.addWidget(self.search_user_input)
        search_user_layout.addWidget(self.get_cloudcasts_button)

        user_cloudcasts_layout = QVBoxLayout()
        self.cloudcasts = CloudcastQTree()
        user_cloudcasts_layout.addWidget(self.cloudcasts)

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
        self.get_cloudcasts_button.clicked.connect(
            lambda user: self.cloudcasts.get_cloudcasts(
                user=self.search_user_input.selected_result
            )
        )
        self.select_all_button.clicked.connect(self.cloudcasts.select_all)
        self.unselect_all_button.clicked.connect(self.cloudcasts.unselect_all)
        self.download_button.clicked.connect(self.download_selected_cloudcasts)

    @Slot()
    def download_selected_cloudcasts(self) -> None:
        download_dir = self._get_download_dir()
        urls = [
            item.cloudcast.url for item in self.cloudcasts.get_selected_cloudcasts()
        ]

        DownloadThread(urls=urls, download_dir=download_dir).start()

    def _get_download_dir(self) -> QFileDialog:
        dialog = QFileDialog()
        dialog.setOption(QFileDialog.ShowDirsOnly)
        dialog.setOption(QFileDialog.DontResolveSymlinks)
        download_dir = dialog.getExistingDirectory(
            self, 'Select download location', expanduser('~')
        )
        return download_dir


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
