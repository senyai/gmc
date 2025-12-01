from math import copysign
from PyQt5 import QtGui, QtCore, QtWidgets
from ..markup_objects.moveable_diamond import MoveableDiamond
from ..views.image_view import ImageView
from .polygon import MarkupPolygon, UndoPolygonCreate
from ..settings import settings

Qt = QtCore.Qt


class Quadrangle(MarkupPolygon):
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
    CURSOR = QtGui.QCursor(
        QtGui.QPixmap("gmc:cursors/add_quadrangle.svg"), 6, 6
    )

    def shape(self) -> QtGui.QPainterPath:
        return super().shape(close=True)

    def attach(self, view: ImageView) -> None:
        view.setCursor(self.CURSOR)
        view.set_mouse_press(self.mouse_press)

    def mouse_press(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self._press_timer = QtCore.QElapsedTimer()
        self._press_timer.start()

        p = view.mapToScene(event.pos())
        self._polygon = QtGui.QPolygonF([p, p, p, p])

        Flag = QtWidgets.QGraphicsItem.GraphicsItemFlag
        self.setFlag(Flag.ItemIsSelectable, False)
        self.setFlag(Flag.ItemIsMovable, False)
        view.set_mouse_press(None)
        view.set_mouse_move(self.mouse_move)
        view.set_mouse_release(self.mouse_release)
        view.set_cancel(self._cancel)
        view.scene().addItem(self)
        return True

    def mouse_release_sequential(
        self, event: QtGui.QMouseEvent, view: ImageView
    ) -> bool:
        self.mouse_move_sequential(event, view)
        if self._polygon.count() == 4:
            self._finish(view)
        else:
            self._polygon.append(self._polygon[-1])
        return True

    def mouse_press_sequential(
        self, event: QtGui.QMouseEvent, view: ImageView
    ) -> bool:
        return True

    def mouse_move_sequential(
        self, event: QtGui.QMouseEvent, view: ImageView
    ) -> bool:
        self._polygon[-1] = view.mapToScene(event.pos())
        self.update()
        return True

    def mouse_move(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        p0 = self._polygon.at(0)
        p2 = view.mapToScene(event.pos())
        if QtGui.QGuiApplication.keyboardModifiers() != Qt.ShiftModifier:
            p1 = QtCore.QPointF(p2.x(), p0.y())
            p3 = QtCore.QPointF(p0.x(), p2.y())
        else:
            w, h = p2.x() - p0.x(), p2.y() - p0.y()
            size = max(abs(w), abs(h))
            w, h = copysign(size, w), copysign(size, h)
            p1 = QtCore.QPointF(p0.x() + w, p0.y())
            p2 = QtCore.QPointF(p0.x() + w, p0.y() + h)
            p3 = QtCore.QPointF(p0.x(), p0.y() + h)
        polygon = QtGui.QPolygonF((p0, p1, p2, p3))
        self._polygon = polygon
        self.update()
        self.on_change_polygon(polygon)
        return True

    def mouse_release(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        if self._polygon.boundingRect() and self._press_timer.hasExpired(
            settings.click_ms
        ):
            self._finish(view)
        else:
            self._polygon = QtGui.QPolygonF(
                [self._polygon[0], self._polygon[0]]
            )
            view.set_mouse_press(self.mouse_press_sequential)
            view.set_mouse_move(self.mouse_move_sequential)
            view.set_mouse_release(self.mouse_release_sequential)
        return True

    def notify_delete(self) -> None:
        if all(
            item.isSelected()
            for item in self.childItems()
            if isinstance(item, MoveableDiamond)
        ):
            self.ensure_edition_canceled()
            self.scene().add_undo_delete([self])

    def _finish(self, view: ImageView):
        view.unset_all_events()
        self.setFlag(self.ItemIsSelectable, True)
        self.scene().undo_stack.push(UndoPolygonCreate(self.scene(), self))
        self.on_change_polygon(self._polygon)
        self.on_created()

    def _cancel(self, view: ImageView) -> None:
        view.unset_all_events()
        view.scene().removeItem(self)
        view.set_mouse_press(self.mouse_press)  # start over
