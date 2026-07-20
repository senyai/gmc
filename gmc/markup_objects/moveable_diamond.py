from __future__ import annotations
from typing import Any, ClassVar
from PyQt5 import QtCore, QtGui, QtWidgets
from ..settings import settings

Qt = QtCore.Qt


class MoveableDiamond(QtWidgets.QAbstractGraphicsShapeItem):
    _polygon: ClassVar[QtGui.QPolygonF]
    _bounding_rect: ClassVar[QtCore.QRectF]
    _shape = ClassVar[QtGui.QPainterPath]
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
        ls = settings.line_w or 1
        size = ls * 4.0
        cls._polygon = QtGui.QPolygonF(
            (
                QtCore.QPointF(0, -size),
                QtCore.QPointF(size, 0),
                QtCore.QPointF(0, size),
                QtCore.QPointF(-size, 0),
            )
        )
        cls._pen = QtGui.QPen(settings.diamond, ls * 1.5)  # 1.5 looks nice
        cls._pen.setCosmetic(True)
        cls._pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        cls._brush = QtGui.QBrush(QtGui.QColor(settings.line_sel_2))
        rc = cls._bounding_rect = cls._polygon.boundingRect().adjusted(
            -ls, -ls, ls, ls
        )

        cls._shape = QtGui.QPainterPath()
        cls._shape.moveTo(rc.x() + rc.width() * 0.5, rc.y())
        cls._shape.lineTo(rc.right(), 0.0)
        cls._shape.lineTo(rc.x() + rc.width() * 0.5, rc.bottom())
        cls._shape.lineTo(rc.x(), 0.0)
        cls._shape.closeSubpath()

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
        return self._bounding_rect

    def shape(self) -> QtGui.QPainterPath:
        return self._shape

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
