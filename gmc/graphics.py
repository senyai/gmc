from PyQt5.QtGui import QPixmap, QPainter, QBrush
from PyQt5.QtCore import Qt


def chess(size: int=4, color1:int=Qt.red, color2:int=Qt.white) -> QBrush:
    pixmap = QPixmap(size, size)
    painter = QPainter(pixmap)
    painter.fillRect(0, 0, size, size, color1)
    painter.fillRect(0, 0, size // 2, size // 2, color2)
    painter.fillRect(size // 2, size // 2, size, size, color2)
    painter.end()
    return QBrush(pixmap)
