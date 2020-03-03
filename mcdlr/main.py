import sys
from typing import Callable

import requests
from PySide2.QtCore import Qt, QTimer, Slot
from PySide2.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class Widget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.layout = QVBoxLayout()

        self.search_layout = QHBoxLayout()
        self.search_layout.setAlignment(Qt.AlignTop)
        self.account_name = QLineEdit()

        self._connect_with_delay(
            input=self.account_name.textChanged[str],
            slot=self.search_account,
            delay_ms=750,
        )

        self.search_layout.addWidget(self.account_name)

        self.search_result_layout = QVBoxLayout()
        self.search_results_list = QListWidget()
        self.search_result_layout.addWidget(self.search_results_list)

        self.layout.addLayout(self.search_layout)
        self.layout.addLayout(self.search_result_layout)

        self.setLayout(self.layout)

    def _connect_with_delay(self, input: Callable, slot: Slot, delay_ms: int):
        """Connects a given input to a given Slot with a given delay."""
        self.timer = self._set_timer(ms=delay_ms)
        self.timer.timeout.connect(slot)
        input.connect(self.timer.start)

    def _set_timer(self, ms: int = 750):
        """Sets a SingleShot timer."""
        timer = QTimer()
        timer.setInterval(ms)
        timer.setSingleShot(True)
        return timer

    @Slot()
    def search_account(self):
        self.search_results_list.clear()
        phrase = self.account_name.text()

        req = requests.get(f'https://api.mixcloud.com/search/?q={phrase}&type=user')
        response = req.json()
        data = response['data']

        for result in data:
            username = result['username']
            name = result['name']
            item = QListWidgetItem(f'{name} ({username})')
            # item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            # item.setCheckState(Qt.Unchecked)
            self.search_results_list.addItem(item)


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
