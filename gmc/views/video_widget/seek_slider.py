from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QSlider, QStyle, QStyleOptionSlider

Qt = QtCore.Qt
from .frame_tooltip import FrameTooltip


class SeekSlider(QSlider):
    _handle_width_val = None

    def __init__(self, limit_widget, *args, **kwargs):
        super().__init__(
            *args,
            singleStep=1,
            maximum=0,
            tickPosition=QSlider.TicksAbove,
            mouseTracking=True,
            orientation=Qt.Horizontal,
            **kwargs,
        )
        self._limit_widget = limit_widget
        self._frame_tooltip = FrameTooltip(self)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        tip_pos = event.globalPos()
        min_x = self._limit_widget.mapToGlobal(QtCore.QPoint()).x()
        tip_pos.setY(self.mapToGlobal(QtCore.QPoint()).y())
        self._frame_tooltip.set_tip(
            str(self._position_to_value(event.x())),
            tip_pos,
            min_x=min_x,
            max_x=min_x + self._limit_widget.width(),
        )

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._frame_tooltip.hide()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._frame_tooltip.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setValue(self._position_to_value(event.x()))
            event.accept()
            return
        super().mousePressEvent(event)

    def _position_to_value(self, x):
        return QStyle.sliderValueFromPosition(
            0,
            self.maximum(),
            x - self._handle_width() / 2,
            self.width() - self._handle_width(),
        )

    def _handle_width(self):
        if self._handle_width_val is None:
            option = QStyleOptionSlider()
            self.initStyleOption(option)
            self._handle_width_val = self.style().pixelMetric(
                QStyle.PM_SliderLength, option
            )
        return self._handle_width_val
