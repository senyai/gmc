from PyQt5 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt


class FrameTooltip(QtWidgets.QWidget):
    TIP_HEIGHT = 6

    def __init__(self, slider_widget):
        super().__init__( slider_widget, visible=False)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.ToolTip | Qt.Window |
            Qt.WindowStaysOnTopHint | Qt.X11BypassWindowManagerHint
        )
        self.setMouseTracking(True)
        self._slider_widget = slider_widget
        font = QtGui.QFont("Monospace", 10)
        font.setStyleHint(font.TypeWriter)
        self.setFont(font)

    def set_tip(self, text, tip_position, min_x, max_x):
        self._text = text
        self._update_position(tip_position, min_x, max_x)
        self.setVisible(True)
        self.update()

    def _update_position(self, tip_position, min_x, max_x):
        metrics = QtGui.QFontMetricsF(self.font())
        self._textbox = textbox = metrics.boundingRect(self._text)
        textbox.adjust(-2.0, -2.0, 2.0, 2.0)
        textbox.moveTo(0.0, 0.0)

        size = QtCore.QSize(textbox.width() + 1,
                            textbox.height() + self.TIP_HEIGHT)
        tooltip_position = QtCore.QPoint(
            min(max_x - size.width(),
                max(min_x, tip_position.x() - size.width() // 2)),
            tip_position.y() - size.height() + self.TIP_HEIGHT
        )
        self.move(tooltip_position)
        self.resize(size)
        self._build_paths(tip_position.x() - tooltip_position.x())
        self.setMask(self._mask)

    def _build_paths(self, tip_x):
        self._path = QtGui.QPainterPath()
        self._path.addRect(self._textbox)

        polygon = QtGui.QPolygonF()
        polygon << QtCore.QPoint(
            max(0, tip_x - 3), self._textbox.height())
        polygon << QtCore.QPoint(
            tip_x, self._textbox.height() + self.TIP_HEIGHT)
        polygon << QtCore.QPoint(
            min(tip_x + 3, self._textbox.width()), self._textbox.height())
        self._path.addPolygon(polygon)

        self._path = self._path.simplified()

        self._mask = QtGui.QBitmap(self.size())
        painter = QtGui.QPainter(self._mask)
        painter.fillRect(self._mask.rect(), Qt.white)
        painter.setPen(Qt.black)
        painter.setBrush(Qt.black)
        painter.drawPath(self._path)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.fillRect(0, 0, 300, 300, Qt.magenta)
        p.setRenderHints(p.HighQualityAntialiasing | p.TextAntialiasing)

        p.setPen(Qt.black)
        p.setBrush(self.palette().base())
        p.drawPath(self._path)

        p.setFont(self.font())
        p.setPen(QtGui.QPen(self.palette().text(), 1))
        p.drawText(self._textbox, Qt.AlignCenter, self._text)
