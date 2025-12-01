import sys
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon, QPixmap

from gmc import utils


def stub_get_icon(name: str) -> QIcon:
    return QIcon(QPixmap(16, 16))


utils.get_icon = stub_get_icon

qapplication = QtWidgets.QApplication(sys.argv)
