from typing import Any, Optional, Tuple
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, QElapsedTimer

from ..views.image_view import ImageView
from . import MarkupObjectMeta
from .moveable_diamond import MoveableDiamond
from ..settings import settings
from ..utils import tr


class MarkupRect(QtWidgets.QGraphicsItem, MarkupObjectMeta):
    ACTION_KEYS = {
        Qt.Key.Key_7: (0,),
        Qt.Key.Key_8: (0, 1),
        Qt.Key.Key_9: (1,),
        Qt.Key.Key_4: (0, 3),
        Qt.Key.Key_5: (0, 1, 2, 3),
        Qt.Key.Key_6: (1, 2),
        Qt.Key.Key_1: (3,),
        Qt.Key.Key_2: (2, 3),
        Qt.Key.Key_3: (2,),
    }
    CURSOR = QtGui.QCursor(QtGui.QPixmap("gmc:cursors/add_rect.svg"), 6, 6)

    def __init__(self, rect: Optional[QRectF] = None):
        super().__init__()
        if rect is None:
            rect = QRectF()
        else:
            assert isinstance(rect, QRectF), (rect, type(rect))
        self._rect = rect
        self.setFlags(self.ItemIsSelectable | self.ItemIsFocusable)

    def paint(self, painter: QtGui.QPainter, _option, _widget) -> None:
        # Don't set brush, so it can be set outside
        if self.isSelected():
            pen, dashed = self.PEN_SELECTED, self.PEN_SELECTED_DASHED
        else:
            pen, dashed = self.PEN, self.PEN_DASHED
        painter.setPen(pen)
        painter.drawRect(self._rect)
        painter.setPen(dashed)
        painter.drawRect(self._rect)

    def shape(self) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        path.addRect(self._rect)
        ps = QtGui.QPainterPathStroker()
        scale = self.scene().views()[0].transform().m11()
        ps.setWidth(8 / scale)
        return ps.createStroke(path)

    def boundingRect(self) -> QRectF:
        return self._rect.normalized().adjusted(-4.0, -4.0, 4.0, 4.0)

    def notify(self, idx: int, pos: QPointF) -> None:
        if idx == 0:
            tl = pos
            br = self._rect.bottomRight()
        elif idx == 1:
            tl = QPointF(self._rect.x(), pos.y())
            br = QPointF(pos.x(), self._rect.bottom())
        elif idx == 2:
            tl = self._rect.topLeft()
            br = pos
        elif idx == 3:
            tl = QPointF(pos.x(), self._rect.top())
            br = QPointF(self._rect.right(), pos.y())
        else:
            assert False
        self._rect = QRectF(tl, br)
        for point, diamond in zip(self._four_points(), self.childItems()):
            # only notify unselected diamonds, because selected had moved
            if not diamond.isSelected():
                diamond.setPos(point)
        self.on_change_rect(self._rect)

    def notify_delete(self) -> None:
        if all(
            item.isSelected()
            for item in self.childItems()
            if isinstance(item, MoveableDiamond)
        ):
            self.ensure_edition_canceled()
            self.scene().removeItem(self)

    def itemChange(
        self, change: QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any
    ) -> Any:
        if change == self.ItemSelectedChange:
            if value:
                self.on_select()
            else:
                self.on_deselect()
        return value

    def _four_points(self) -> Tuple[QPointF, QPointF, QPointF, QPointF]:
        p = self._rect.topLeft()
        return (
            p + QPointF(0.0, 0.0),
            p + QPointF(self._rect.width(), 0.0),
            p + QPointF(self._rect.width(), self._rect.height()),
            p + QPointF(0.0, self._rect.height()),
        )

    def on_start_edit(self) -> None:
        self.setFlag(self.ItemIsMovable, False)
        self.setFlag(self.ItemIsSelectable, False)
        self._prev_rect = QRectF(self._rect)
        for idx, pos in enumerate(self._four_points()):
            MoveableDiamond(self, idx, pos)

    def on_stop_edit(self) -> None:
        self.setFlags(self.ItemIsSelectable | self.ItemIsFocusable)
        scene = self.scene()
        if scene:
            for diamond in self.childItems():
                scene.removeItem(diamond)
            if self._prev_rect != self._rect:
                scene.undo_stack.push(
                    UndoRectModification(
                        self, self._prev_rect, QRectF(self._rect)
                    )
                )
            self.prepareGeometryChange()

    def on_change_rect(self, _: QRectF) -> None:
        pass  # for overriding

    def on_select(self) -> None:
        pass  # for overriding

    def on_deselect(self) -> None:
        pass  # for overriding

    def on_created(self) -> None:
        pass  # for overriding

    def attach(self, view: ImageView) -> None:
        view.setCursor(self.CURSOR)
        view.show_cross_cursor()
        view.set_mouse_press(self.mouse_press)

    def mouse_press(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self._press_timer = QElapsedTimer()
        self._press_timer.start()
        self._rect = QRectF(view.mapToScene(event.pos()), QSizeF(0, 0))
        self.setFlag(self.ItemIsSelectable, False)
        self.setFlag(self.ItemIsMovable, False)
        view.set_mouse_press(None)
        view.set_cancel(self._cancel)
        view.set_mouse_move(self.mouse_move)
        view.set_mouse_release(self.mouse_release)
        view.scene().addItem(self)
        view.hide_cross_cursor()
        return True  # if not 'return True', back objects will be selected

    def mouse_move(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self._rect.setBottomRight(view.mapToScene(event.pos()))
        self.update()
        self.on_change_rect(self._rect)
        return True

    def mouse_release(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self.mouse_move(event, view)
        rc = self._rect
        if rc.normalized() and self._press_timer.hasExpired(settings.click_ms):
            view.unset_all_events()
            del self._press_timer
            self.setFlag(self.ItemIsSelectable, True)
            self.prepareGeometryChange()
            view.scene().undo_stack.push(
                UndoRectCreate(self.scene(), self, QRectF(rc))
            )
            self.on_change_rect(rc)
            self.on_created()
        else:
            view.set_mouse_press(self.prevent_event)
        return True

    def _cancel(self, view: ImageView):
        view.unset_all_events()
        view.scene().removeItem(self)
        view.set_mouse_press(self.mouse_press)  # start over

    def data(self):
        rc = self._rect
        pos = self.pos()
        return [rc.x() + pos.x(), rc.y() + pos.y(), rc.width(), rc.height()]


class UndoRectCreate(QtWidgets.QUndoCommand):
    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        markup_rect: MarkupRect,
        rect: QRectF,
    ) -> None:
        self._scene = scene
        self._markup_rect = markup_rect
        self._rect = rect
        super().__init__(tr("Rectangle Creation"))

    def redo(self) -> None:
        mr = self._markup_rect
        mr._rect = QRectF(self._rect)
        if mr.scene() is None:
            self._scene.addItem(mr)

    def undo(self) -> None:
        mr = self._markup_rect
        mr.ensure_edition_canceled()
        self._scene.removeItem(mr)


class UndoRectModification(QtWidgets.QUndoCommand):
    def __init__(
        self, markup_rect: MarkupRect, old_rect: QRectF, new_rect: QRectF
    ) -> None:
        self._markup_rect = markup_rect
        self._old_rect = old_rect
        self._new_rect = new_rect
        super().__init__(tr("Rectangle Modification"))

    def redo(self) -> None:
        mr = self._markup_rect
        mr.ensure_edition_canceled()
        mr._rect = QRectF(self._new_rect)
        mr.update()

    def undo(self) -> None:
        mr = self._markup_rect
        mr.ensure_edition_canceled()
        mr._rect = QRectF(self._old_rect)
        mr.update()
