from PyQt5 import QtGui, QtWidgets

from ..views.image_view import ImageView
from . import MarkupObjectMeta
from typing import Callable, Optional
from PyQt5.QtCore import Qt, QRectF, QPointF, QCoreApplication

tr: Callable[[str], str] = lambda text: QCoreApplication.translate(
    "@default", text
)


class MarkupPoint(QtWidgets.QGraphicsItem, MarkupObjectMeta):
    _rect = QRectF(-4, -4, 8, 8)
    PEN = QtGui.QPen(Qt.GlobalColor.white, 4)
    PEN_SELECTED = QtGui.QPen(Qt.GlobalColor.yellow, 4)
    CURSOR = QtGui.QCursor(QtGui.QPixmap("gmc:cursors/add_point.svg"), 6, 6)

    def __init__(self, pos: Optional[QPointF] = None):
        super(MarkupPoint, self).__init__()
        if pos is None:
            pos = QPointF()
        else:
            assert isinstance(pos, QPointF)
        self.setPos(pos)
        self.setFlags(
            self.ItemIsMovable
            | self.ItemIgnoresTransformations
            | self.ItemIsSelectable
            | self.ItemIsFocusable
            | self.ItemSendsGeometryChanges
        )

    def attach(self, view: ImageView) -> None:
        view.setCursor(self.CURSOR)
        assert isinstance(view, ImageView), view
        view.set_mouse_press(self.mouse_press)

    def paint(self, painter: QtGui.QPainter, _option, _widget) -> None:
        # Don't set brush, so it can be set outside
        if self.isSelected():
            pen, dashed = self.PEN_SELECTED, self.PEN_SELECTED_DASHED
        else:
            pen, dashed = self.PEN, self.PEN_DASHED
        radii_px = 2.0
        painter.setPen(pen)
        painter.drawEllipse(QPointF(), radii_px, radii_px)
        painter.setPen(dashed)
        painter.drawEllipse(QPointF(), radii_px, radii_px)

    def data(self):
        pos = self.pos()
        return [pos.x(), pos.y()]

    def boundingRect(self):
        return self._rect

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.addEllipse(self._rect)
        return path

    def on_start_edit(self):
        pass

    def on_stop_edit(self):
        pass

    def on_change_point(self, _):
        pass  # for overriding

    def mouse_press(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self._create_pos = view.mapToScene(event.pos())
        scene = view.scene()
        scene.undo_stack.push(UndoPointCreate(scene, self, self._create_pos))
        view.set_mouse_move(self.mouse_move)
        view.set_mouse_release(self.mouse_release)
        view.set_mouse_press(None)
        view.set_cancel(self._cancel)
        return True

    def mouse_move(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self.setPos(view.mapToScene(event.pos()))
        self.update()
        return True

    def mouse_release(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self.mouse_move(event, view)  # update position
        view.set_mouse_move(None)
        view.set_mouse_release(None)
        view.set_cancel(None)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.on_created()
        return True

    def _cancel(self, view: ImageView) -> None:
        view.unset_all_events()
        view.scene().removeItem(self)
        self.setPos(QPointF())
        view.set_mouse_press(self.mouse_press)  # start over

    def mousePressEvent(
        self, event: QtWidgets.QGraphicsSceneMouseEvent
    ) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._last_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(
        self, event: QtWidgets.QGraphicsSceneMouseEvent
    ) -> None:
        # if point moved
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.buttonDownScenePos(Qt.MouseButton.LeftButton)
            != event.scenePos()
        ):
            self.scene().undo_stack.push(
                UndoPointMove(self, self._last_pos, self.pos())
            )
        super().mouseReleaseEvent(event)


class UndoPointCreate(QtWidgets.QUndoCommand):
    def __init__(
        self, scene: QtWidgets.QGraphicsScene, point: MarkupPoint, pos: QPointF
    ) -> None:
        self._scene = scene
        self._point = point
        self._pos = pos
        super().__init__(tr("Point Creation"))

    def redo(self) -> None:
        self._point.setPos(self._pos)
        self._scene.addItem(self._point)

    def undo(self) -> None:
        self._scene.removeItem(self._point)


class UndoPointMove(QtWidgets.QUndoCommand):
    def __init__(
        self, markup_point: MarkupPoint, old_pos: QPointF, new_pos: QPointF
    ) -> None:
        self._markup_point = markup_point
        self._old_pos = old_pos
        self._new_pos = new_pos
        super().__init__(tr("Point Move"))

    def redo(self) -> None:
        self._markup_point.setPos(self._new_pos)

    def undo(self) -> None:
        self._markup_point.setPos(self._old_pos)
