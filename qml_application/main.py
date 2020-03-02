#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, urllib.request, json
import PySide2.QtQml
from PySide2.QtQuick import QQuickView
from PySide2.QtCore import QStringListModel, Qt, QUrl
from PySide2.QtGui import QGuiApplication


if __name__ == "__main__":
    # get data
    url = 'http://country.io/names.json'
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode('utf-8'))

    # format and sort data
    data_list = list(data.values())
    data_list.sort()

    # set up application window
    app = QGuiApplication(sys.argv)
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)

    # expose the list to the Qml code
    my_model = QStringListModel()
    my_model.setStringList(data_list)
    view.rootContext().setContextProperty('myModel', my_model)

    # load the QML file
    qml_file = os.path.join(os.path.dirname(__file__), 'view.qml')
    view.setSource(QUrl.fromLocalFile(os.path.abspath(qml_file)))

    # show the window
    if view.status() == QQuickView.Error:
        sys.exit(-1)
    view.show()

    # execute and cleanup
    app.exec_()
    del view
