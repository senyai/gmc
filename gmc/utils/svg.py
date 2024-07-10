from PyQt5 import QtGui


def icon_from_data(data):
    return QtGui.QIcon(
      QtGui.QPixmap.fromImage(
        QtGui.QImage.fromData(data)))
