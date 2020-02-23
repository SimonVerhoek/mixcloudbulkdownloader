from PySide2.QtCore import QDateTime, Qt
from PySide2.QtGui import QPainter
from PySide2.QtWidgets import QHBoxLayout, QHeaderView, QSizePolicy, QTableView, QWidget
from PySide2.QtCharts import QtCharts

from .table_model import CustomTableModel


class Widget(QWidget):
    def __init__(self, data):
        QWidget.__init__(self)

        self.model = CustomTableModel(data)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)

        # QTableView Headers
        self.horizontal_header = self.table_view.horizontalHeader()
        self.horizontal_header.setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontal_header.setStretchLastSection(True)
        self.vertical_header = self.table_view.verticalHeader()
        self.vertical_header.setSectionResizeMode(QHeaderView.ResizeToContents)

        # Creating QChart
        self.chart = QtCharts.QChart()
        self.chart.setAnimationOptions(QtCharts.QChart.AllAnimations)
        self.add_series(name='Magnitude (Column 1)', columns=[0, 1])

        # Creating QChartView
        self.chart_view = QtCharts.QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        # QWidget Layout
        self.main_layout = QHBoxLayout()
        size = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        ## Left layout
        size.setHorizontalStretch(1)
        self.table_view.setSizePolicy(size)
        self.main_layout.addWidget(self.table_view)

        ## Right Layout
        size.setHorizontalStretch(4)
        self.chart_view.setSizePolicy(size)
        self.main_layout.addWidget(self.chart_view)

        # Set the layout to the QWidget
        self.setLayout(self.main_layout)

    def add_series(self, name, columns):
        self.series = QtCharts.QLineSeries()
        self.series.setName(name)

        # Fill with data
        for i in range(self.model.rowCount()):
            # get data
            t = self.model.index(i, 0).data()
            date_fmt = 'yyyy-MM-dd HH:mm:ss.zzz'

            x = QDateTime().fromString(t, date_fmt).toSecsSinceEpoch()
            y = float(self.model.index(i, 1).data())

            if x > 0 and y > 0:
                self.series.append(x, y)

        self.chart.addSeries(self.series)

        # set X-axis
        self.axis_x = QtCharts.QDateTimeAxis()
        self.axis_x.setTickCount(10)
        self.axis_x.setFormat('dd.MM (h:mm)')
        self.axis_x.setTitleText('Date')
        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.series.attachAxis(self.axis_x)

        # set Y-axis
        self.axis_y = QtCharts.QValueAxis()
        self.axis_y.setTickCount(10)
        self.axis_y.setLabelFormat('%.2f')
        self.axis_y.setTitleText('Magnitude')
        self.chart.addAxis(self.axis_y, Qt.AlignLeft)
        self.series.attachAxis(self.axis_y)

        # get color from QChart to use it on QTableView
        self.model.color = f'{self.series.pen().color().name()}'
