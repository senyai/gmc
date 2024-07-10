from PyQt5 import QtGui, QtCore

from ..views.image_view import ImageView
from ..settings import settings
from .polygon import MarkupPolygon, UndoPolygonCreate
Qt = QtCore.Qt


class MarkupLine(MarkupPolygon):
    # Use MarkupPolygon as base since QLineF does not represent two points.
    ACTION_KEYS = {
        Qt.Key.Key_7: (0,),
        Qt.Key.Key_4: (0,),
        Qt.Key.Key_1: (0,),

        Qt.Key.Key_5: (0, 1),
        Qt.Key.Key_2: (0, 1),
        Qt.Key.Key_8: (0, 1),

        Qt.Key.Key_9: (1,),
        Qt.Key.Key_6: (1,),
        Qt.Key.Key_3: (1,),
    }
    CURSOR = QtGui.QCursor(QtGui.QPixmap('gmc:cursors/add_segment.svg'), 6, 6)

    def attach(self, view: ImageView):
        view.setCursor(self.CURSOR)
        view.set_mouse_press(self.mouse_press)

    def shape(self) -> QtGui.QPainterPath:
        p = self._polygon
        if p[0] == p[1]:
            # Special case for zero size line. Don't know, it might be better
            # in MarkupPolygon, but hard to check.
            rc = QtCore.QRectF(0.0, 0.0, 8.0, 8.0)
            rc.moveTo(p[0] - QtCore.QPointF(4.0, 4.0))
            path = QtGui.QPainterPath()
            path.addEllipse(rc)
            return path
        return MarkupPolygon.shape(self)

    def mouse_press(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self._press_timer = QtCore.QElapsedTimer()
        self._press_timer.start()
        view.set_mouse_press(None)
        view.set_cancel(self.cancel)
        view.set_mouse_move(self.mouse_move)
        view.set_mouse_release(self.mouse_release)
        pos = view.mapToScene(event.pos())
        self._polygon = QtGui.QPolygonF([pos, pos])
        self.setFlag(self.ItemIsSelectable, False)
        self.setFlag(self.ItemIsMovable, False)
        view.scene().addItem(self)
        return True

    def mouse_move(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self._polygon[1] = view.mapToScene(event.pos())
        self.update()
        self.on_change_polygon(self._polygon)
        return True

    def mouse_release(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self.mouse_move(event, view)
        if self._polygon.boundingRect() and self._press_timer.hasExpired(settings.click_ms):
            del self._press_timer
            view.unset_all_events()
            self.setFlag(self.ItemIsSelectable, True)
            self.on_change_polygon(self._polygon)
            self.scene().undo_stack.push(UndoPolygonCreate(self.scene(), self))
            self.on_created()
        else:
            view.set_mouse_press(self.prevent_event)
        return True

    def cancel(self, view: ImageView):
        view.unset_all_events()
        view.scene().removeItem(self)
        view.set_mouse_press(self.mouse_press)  # start over
