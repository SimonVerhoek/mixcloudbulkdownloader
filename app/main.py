import sys

from PySide2.QtCore import Qt
from PySide2.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.custom_widgets import CloudcastQTreeWidget, SearchUserQComboBox
# from app.logging import logging


# logger = logging.getLogger(__name__)


class CentralWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()

        # search user layout
        search_user_layout = QHBoxLayout()
        search_user_layout.setAlignment(Qt.AlignTop)

        self.search_user_label = QLabel('Search account:')
        self.search_user_input = SearchUserQComboBox()
        self.get_cloudcasts_button = QPushButton('Get cloudcasts')

        search_user_layout.addWidget(self.search_user_label)
        search_user_layout.addWidget(self.search_user_input)
        search_user_layout.addWidget(self.get_cloudcasts_button)

        search_user_layout.setStretch(0, 1)
        search_user_layout.setStretch(1, 3)
        search_user_layout.setStretch(2, 1)

        # user cloudcasts layout
        user_cloudcasts_layout = QVBoxLayout()
        self.cloudcasts = CloudcastQTreeWidget()
        user_cloudcasts_layout.addWidget(self.cloudcasts)

        # cloudcast action buttons layout
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
        self.download_button.clicked.connect(
            self.cloudcasts.download_selected_cloudcasts
        )


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        widget = CentralWidget()

        self.setWindowTitle('Mixcloud Bulk Downloader')
        self.setMinimumSize(700, 400)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu('File')
        file_menu.addAction('Exit', QApplication.quit)

        self.setCentralWidget(widget)


if __name__ == '__main__':
    application = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(application.exec_())
