import sys
from typing import Callable

from PySide2.QtCore import Slot, Qt, QTimer
from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
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

        self.search_account_name_button = QPushButton('Search')
        self.search_account_name_button.clicked.connect(self.search_account)

        self.search_layout.addWidget(self.account_name)
        self.search_layout.addWidget(self.search_account_name_button)

        self.layout.addLayout(self.search_layout)

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
        phrase = self.account_name.text()

        from pprint import pprint
        print()
        print()
        pprint(phrase)
        print()
        print()


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
