from typing import Any
from PyQt5 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt


class MoveableDiamond(QtWidgets.QAbstractGraphicsShapeItem):
    POLYGON = QtGui.QPolygonF([
        QtCore.QPointF(0, -4.0),
        QtCore.QPointF(4.0, 0),
        QtCore.QPointF(0, 4.0),
        QtCore.QPointF(-4.0, 0),
    ])
    NO_PEN = QtGui.QPen(Qt.PenStyle.NoPen)
    no_doubleclick = True  # allow doubleclick to stop editing

    def __init__(self, parent:QtWidgets.QGraphicsItem, idx: int, pos: QtCore.QPointF,
                 brush:QtGui.QBrush=QtGui.QBrush(QtGui.QColor(Qt.GlobalColor.red)),
                 pen:QtGui.QPen=QtGui.QPen(Qt.GlobalColor.magenta, 1)
        ) -> None:
        self.idx = idx  # public because user must know daimond's index
        super().__init__(parent)
        self.setZValue(1000)
        self.setBrush(brush)
        self.setPen(pen)
        self.setPos(pos)
        Flag = QtWidgets.QGraphicsItem.GraphicsItemFlag
        # ItemFlag = QtWidgets. parent.GraphicsItemFlag
        self.setFlags(Flag.ItemIgnoresTransformations | Flag.ItemIsMovable |
                      Flag.ItemIsSelectable | Flag.ItemIsFocusable |
                      Flag.ItemSendsGeometryChanges)

    def itemChange(self, change: QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == self.ItemPositionHasChanged:
            self.parentItem().notify(self.idx, value)
        return value

    def paint(self, painter: QtGui.QPainter, option, widget) -> None:
        painter.setPen(self.pen())
        painter.drawConvexPolygon(self.POLYGON)
        if self.isSelected():
            painter.setBrush(self.brush())
            painter.setPen(self.NO_PEN)
            painter.drawConvexPolygon(self.POLYGON)

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
