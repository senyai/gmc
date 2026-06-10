from __future__ import annotations
from typing import Any, ClassVar
from PyQt5 import QtCore, QtGui, QtWidgets
from ..settings import settings

Qt = QtCore.Qt


class MoveableDiamond(QtWidgets.QAbstractGraphicsShapeItem):
    _polygon: ClassVar[QtGui.QPolygonF]
    _pen: ClassVar[QtGui.QPen]

    _brush: ClassVar[QtGui.QBrush]

    NO_PEN: ClassVar = QtGui.QPen(Qt.PenStyle.NoPen)
    no_doubleclick: ClassVar = True  # allow doubleclick to stop editing

    Flag = QtWidgets.QGraphicsItem.GraphicsItemFlag
    FLAGS = (
        Flag.ItemIgnoresTransformations
        | Flag.ItemIsMovable
        | Flag.ItemIsSelectable
        | Flag.ItemIsFocusable
        | Flag.ItemSendsGeometryChanges
    )
    del Flag

    @classmethod
    def on_settings_updated(cls):
        size = (settings.line_w or 1) * 4.0
        cls._polygon = QtGui.QPolygonF(
            [
                QtCore.QPointF(0, -size),
                QtCore.QPointF(size, 0),
                QtCore.QPointF(0, size),
                QtCore.QPointF(-size, 0),
            ]
        )
        cls._pen = QtGui.QPen(settings.diamond, size / 2.0)
        cls._pen.setCosmetic(True)
        cls._brush = QtGui.QBrush(QtGui.QColor(settings.line_sel_2))
        # we hope that there are no active diamonds, so we leave it here

    def __init__(
        self, parent: QtWidgets.QGraphicsItem, idx: int, pos: QtCore.QPointF
    ) -> None:
        self.idx = idx  # public because user must know daimond's index
        super().__init__(parent)
        self.setZValue(1000)
        self.setBrush(self._brush)
        self.setPen(self._pen)
        self.setPos(pos)
        self.setFlags(self.FLAGS)

    def itemChange(
        self, change: QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any
    ) -> Any:
        if change == self.ItemPositionHasChanged:
            self.parentItem().notify(self.idx, value)
        return value

    def paint(self, painter: QtGui.QPainter, option, widget) -> None:
        painter.setPen(self.pen())
        painter.drawConvexPolygon(self._polygon)
        if self.isSelected():
            painter.setBrush(self.brush())
            painter.setPen(self.NO_PEN)
            painter.drawConvexPolygon(self._polygon)

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(-10, -10, 20, 20)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.addEllipse(-10, -10, 20, 20)
        return path

    def delete(self) -> None:
        """
        Deletion of `MoveableDiamond` makes sense
        for `EditableMarkupPolygon` objects
        """
        parent = self.parentItem()
        try:
            notify_delete = parent.notify_delete
        except AttributeError:
            return
        notify_delete()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        self.parentItem().keyPressEvent(event)


MoveableDiamond.on_settings_updated()
settings.register(MoveableDiamond.on_settings_updated)
