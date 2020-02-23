from PySide2.QtCore import qApp
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QAction, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self, widget):
        QMainWindow.__init__(self)
        self.setWindowTitle('Earthquakes information')
        self.setCentralWidget(widget)

        # menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('File')

        # exit QAction
        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)

        self.file_menu.addAction(exit_action)

        # status bar
        self.status = self.statusBar()
        self.status.showMessage('Data loaded and plotted')

        # Window dimensions
        geometry = qApp.desktop().availableGeometry(self)
        self.setFixedSize(geometry.width() * 0.8, geometry.height() * 0.7)
