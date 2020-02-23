import sys

from PySide2.QtCore import Slot, Qt
from PySide2.QtWidgets import (
    QAction,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qtpy.QtCharts import QtCharts
from qtpy.QtGui import QPainter


class Widget(QWidget):
    def __init__(self):
        QWidget.__init__(self)
        self.items = 0

        # example data
        self._data = {
            "Water": 24.5,
            "Electricity": 55.1,
            "Rent": 850.0,
            "Supermarket": 230.4,
            "Internet": 29.99,
            "Bars": 21.85,
            "Public transportation": 60.0,
            "Coffee": 22.45,
            "Restaurants": 120,
        }

        # left
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Description', 'Price'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # chart
        self.chart_view = QtCharts.QChartView()
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        # right
        self.description = QLineEdit()
        self.price = QLineEdit()
        self.add = QPushButton('Add')
        self.clear = QPushButton('Clear')
        self.quit = QPushButton('Quit')
        self.plot = QPushButton('Plot')

        # disabling 'add' buttonn
        self.add.setEnabled(False)

        self.right = QVBoxLayout()
        self.right.setMargin(10)
        self.right.addWidget(QLabel('Description'))
        self.right.addWidget(self.description)
        self.right.addWidget(QLabel('Price'))
        self.right.addWidget(self.price)
        self.right.addWidget(self.add)
        self.right.addWidget(self.plot)
        self.right.addWidget(self.chart_view)
        self.right.addWidget(self.clear)
        self.right.addWidget(self.quit)

        # QWidget Layout
        self.layout = QHBoxLayout()

        self.layout.addWidget(self.table)
        self.layout.addLayout(self.right)

        # set layout to QWidget
        self.setLayout(self.layout)

        # signals and Slots
        self.add.clicked.connect(self.add_element)
        self.quit.clicked.connect(self.quit_application)
        self.plot.clicked.connect(self.plot_data)
        self.clear.clicked.connect(self.clear_table)
        self.description.textChanged[str].connect(self.check_disable)
        self.price.textChanged[str].connect(self.check_disable)

        self.fill_table()

    @Slot()
    def add_element(self):
        des = self.description.text()
        price = self.price.text()

        self.table.insertRow(self.items)
        description_item = QTableWidgetItem(des)
        price_item = QTableWidgetItem(f'{float(price):.2f}')
        price_item.setTextAlignment(Qt.AlignRight)

        self.table.setItem(self.items, 0, description_item)
        self.table.setItem(self.items, 1, price_item)

        self.description.setText('')
        self.price.setText('')

        self.items += 1

    @Slot()
    def check_disable(self, s):
        if not self.description.text() or not self.price.text():
            self.add.setEnabled(False)
        else:
            self.add.setEnabled(True)

    @Slot()
    def plot_data(self):
        # get table information
        series = QtCharts.QPieSeries()
        for i in range(self.table.rowCount()):
            text = self.table.item(i, 0).text()
            number = float(self.table.item(i, 1).text())
            series.append(text, number)

        chart = QtCharts.QChart()
        chart.addSeries(series)
        chart.legend().setAlignment(Qt.AlignLeft)
        self.chart_view.setChart(chart)

    @Slot()
    def quit_application(self):
        QApplication.quit()

    def fill_table(self, data=None):
        data = self._data if not data else data
        for desc, price in data.items():
            description_item = QTableWidgetItem(desc)
            price_item = QTableWidgetItem(f'{price:.2f}')
            price_item.setTextAlignment(Qt.AlignRight)
            self.table.insertRow(self.items)
            self.table.setItem(self.items, 0, description_item)
            self.table.setItem(self.items, 1, price_item)
            self.items += 1

    @Slot()
    def clear_table(self):
        self.table.setRowCount(0)
        self.items = 0


class MainWindow(QMainWindow):
    def __init__(self, widget):
        QMainWindow.__init__(self)
        self.setWindowTitle('Tutorial')

        # menu
        self.menu = self.menuBar()
        self.file_menu = self.menu.addMenu('File')

        # exit QAction
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.exit_app)

        self.file_menu.addAction(exit_action)
        self.setCentralWidget(widget)

    @Slot()
    def exit_app(self, checked):
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    widget = Widget()
    window = MainWindow(widget)
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec_())
