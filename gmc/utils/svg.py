from PyQt5 import QtGui


def icon_from_data(data: bytes):
    return QtGui.QIcon(QtGui.QPixmap.fromImage(QtGui.QImage.fromData(data)))
