from PyQt5 import QtGui, QtWidgets

from ..views.image_view import ImageView
from . import MarkupObjectMeta
from .moveable_diamond import MoveableDiamond
from math import hypot
from typing import Any, Optional, List, Callable
from PyQt5.QtCore import Qt, QPointF, QCoreApplication, QRectF
tr: Callable[[str], str] = lambda text: QCoreApplication.translate("@default", text)


class MarkupPolygon(QtWidgets.QGraphicsItem, MarkupObjectMeta):
    """
    Polygon is a *closed* shape figure. But one can make it Polyline
    by subclassing and calling paint with different `f` argument.
    """
    _polygon: QtGui.QPolygonF
    CURSOR = QtGui.QCursor(QtGui.QPixmap('gmc:cursors/add_line.svg'), 6, 6)

    def __init__(self, polygon: Optional[QtGui.QPolygonF]) -> None:
        super().__init__()
        if polygon is None:
            polygon = QtGui.QPolygonF()
        else:
            assert isinstance(polygon, QtGui.QPolygonF), polygon
        self._polygon = polygon
        self._last_scale = 1.0  # dirty trick to make shape respect zoom
        self.setFlags(self.ItemIsSelectable | self.ItemIsFocusable)

    def paint(self, painter: QtGui.QPainter, _option, _widget, f=QtGui.QPainter.drawPolygon) -> None:
        # Warning: do not setBrush here, since it is useful to set it outside
        p = self._polygon
        if self.isSelected():
            pen, dashed = self.PEN_SELECTED, self.PEN_SELECTED_DASHED
            # draw circle when there's nothing to draw, for user to see it
            if p.size() == 1 or p[0] == p[1]:
                painter.setPen(pen)
                painter.drawEllipse(p[0], 1.0, 1.0)
                painter.setPen(dashed)
                painter.drawEllipse(p[0], 1.0, 1.0)
        else:
            pen, dashed = self.PEN, self.PEN_DASHED
        painter.setPen(pen)
        f(painter, p)
        painter.setPen(dashed)
        f(painter, p)
        self._last_scale = painter.transform().m11()
        painter.setPen(Qt.GlobalColor.blue)

    def boundingRect(self) -> QRectF:
        rc = self._polygon.boundingRect()
        rc.adjust(-5, -5, 5, 5)  # to make `shape` width work
        return rc

    def shape(self, close: bool=True) -> QtGui.QPainterPath:
        path = QtGui.QPainterPath()
        path.setFillRule(Qt.FillRule.WindingFill)
        path.addPolygon(self._polygon)
        if close:
            path.closeSubpath()
        ps = QtGui.QPainterPathStroker()
        ps.setWidth(10.0 / self._last_scale)
        return ps.createStroke(path)

    def notify(self, idx: int, pos: QPointF) -> None:
        p = self._polygon
        p[idx] = pos
        self.on_change_polygon(p)

    def itemChange(self, change: QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == self.ItemSelectedChange:
            if value:
                self.on_select()
            else:
                self.on_deselect()
        return value

    def on_start_edit(self) -> None:
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)
        self._start_edit_polygon = self._polygon[:]
        for idx, pos in enumerate(self._polygon):
            MoveableDiamond(self, idx, pos)

    def on_stop_edit(self) -> None:
        self.setFlags(self.ItemIsSelectable | self.ItemIsFocusable)
        scene = self.scene()
        if scene:
            for diamond in self.childItems():
                scene.removeItem(diamond)
            if self._start_edit_polygon != self._polygon:
                scene.undo_stack.push(UndoPolygonUndoEdit(
                    self, self._start_edit_polygon
                ))
        # is not deleted in UndoPolygonUndoEdit
        if hasattr(self, '._start_edit_polygon'):
            del self._start_edit_polygon

    def on_change_polygon(self, _: QtGui.QPolygonF) -> None:
        pass  # for overriding

    def on_select(self) -> None:
        pass  # for overriding

    def on_deselect(self) -> None:
        pass  # for overriding

    def data(self):
        pos = self.pos()
        return [(p.x() + pos.x(), p.y() + pos.y()) for p in self._polygon]


class dist_squared:
    ":returns: distance from segment to a point"

    def __new__(cls, a: QPointF, b: QPointF, d: QPointF):
        "a and b segment line; d - the point"
        p = b - a
        l2 = cls.length(p)
        if not l2:
            return cls.length(a - d)
        u = max(0.0, min(1.0, cls.add(cls.mul((d - a), p)) / l2))
        return cls.length(a + u * p - d)

    @staticmethod
    def mul(a: QPointF, b: QPointF) -> QPointF:
        return QPointF(a.x() * b.x(), a.y() * b.y())

    @staticmethod
    def add(a: QPointF) -> float:
        return a.x() + a.y()

    @staticmethod
    def length(a: QPointF) -> float:
        return a.x() * a.x() + a.y() * a.y()


class EditableMarkupPolygon(MarkupPolygon):
    def mouseDoubleClickEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        if self.in_edit_mode() and self._polygon:
            the_point = event.scenePos()
            min_dist = 1e900
            prev_point = self._polygon[-1]
            for idx, point in enumerate(self._polygon):
                dist = dist_squared(point, prev_point, the_point)
                prev_point = point
                if dist < min_dist:
                    min_idx = idx
                    min_dist = dist
            self._polygon.insert(min_idx, the_point)
            self.on_stop_edit()
            self.start_edit_nodes()
            self.update()
        else:
            MarkupObjectMeta.mouseDoubleClickEvent(self, event)

    def notify_delete(self) -> None:
        indices: List[int] = []
        for item in self.childItems():
            if isinstance(item, MoveableDiamond) and item.isSelected():
                indices.append(item.idx)
        scene = self.scene()
        if len(self._polygon) == len(indices):
            self.stop_edit_nodes()
            if scene is not None:
                scene.removeItem(self)
        else:
            scene.undo_stack.push(UndoPolygonDelPoints(self, indices))
            self.on_stop_edit()
            self.on_start_edit()

    def attach(self, view: ImageView) -> None:
        view.setCursor(self.CURSOR)
        view.set_mouse_press(self.mouse_press)

    def mouse_press(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        pos: QPointF = view.mapToScene(event.pos())
        scene = view.scene()
        if self._polygon.isEmpty():
            scene.addItem(self)
            self._polygon.append(pos)
        else:
            if len(self._polygon) == 2:
                scene.undo_stack.push(
                    UndoPolygonCreate(scene, self))
            else:
                new_points = QPointF(self._polygon[-1])
                del self._polygon[-1]
                scene.undo_stack.push(
                    UndoPolygonAddPoint(self, len(self._polygon), new_points))
            distance = view.transform().map(self._polygon[-2] - pos)
            if hypot(distance.x(), distance.y()) < 2.5:  # clicked on the same point
                self.mouse_doubleclick(event, view)
                return True
        self._polygon.append(pos)

        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, False)
        view.set_mouse_move(self.mouse_move)
        view.set_mouse_doubleclick(self.mouse_doubleclick)
        view.set_cancel(self.cancel)
        return True

    def mouse_doubleclick(self, _event: QtGui.QMouseEvent, view: ImageView) -> bool:
        view.unset_all_events()
        del self._polygon[-1]
        # important: there's no strong enough reason to remove one point paths
        self.setFlag(self.ItemIsSelectable, True)
        self.on_change_polygon(self._polygon)
        self.after_creation()
        return True

    def mouse_move(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        self._polygon[-1] = view.mapToScene(event.pos())
        self.update()
        self.on_change_polygon(self._polygon)
        return True

    def cancel(self, view: ImageView) -> None:
        view.unset_all_events()
        view.scene().removeItem(self)
        view.set_mouse_press(self.mouse_press)  # start over

    def after_creation(self):
        pass


class UndoPolygonCreate(QtWidgets.QUndoCommand):
    def __init__(self,
                 scene: QtWidgets.QGraphicsScene,
                 markup_polygon: MarkupPolygon) -> None:
        self._scene = scene
        self._markup_polygon = markup_polygon
        self._polygon = markup_polygon._polygon[:]
        super().__init__(tr("Polygon Creation"))

    def redo(self) -> None:
        mp = self._markup_polygon
        mp._polygon = self._polygon[:]
        if mp.scene() is None:
            self._scene.addItem(mp)

    def undo(self) -> None:
        mp = self._markup_polygon
        mp.stop_edit_nodes()
        self._scene.removeItem(mp)


class UndoPolygonAddPoint(QtWidgets.QUndoCommand):
    def __init__(self,
                 markup_polygon: MarkupPolygon,
                 idx: int,
                 pos: QPointF) -> None:
        self._markup_polygon = markup_polygon
        self._idx = idx
        self._pos = pos
        super().__init__(tr("Polygon Point Addition"))

    def redo(self) -> None:
        mp = self._markup_polygon
        mp._polygon.insert(self._idx, self._pos)
        mp.update()

    def undo(self) -> None:
        mp = self._markup_polygon
        mp.stop_edit_nodes()
        del mp._polygon[self._idx]
        mp.update()


class UndoPolygonDelPoints(QtWidgets.QUndoCommand):
    def __init__(self,
                 markup_polygon: MarkupPolygon,
                 indices: List[int]) -> None:
        indices.sort(reverse=True)
        polygon = markup_polygon._polygon
        self._points = [QPointF(polygon[idx]) for idx in indices]
        self._markup_polygon = markup_polygon
        self._indices = indices
        super().__init__(tr("Polygon Points Deletion"))

    def redo(self) -> None:
        mp = self._markup_polygon
        for index in self._indices:
            mp._polygon.remove(index)
        mp.update()

    def undo(self) -> None:
        mp = self._markup_polygon
        mp.stop_edit_nodes()
        for idx, point in zip(self._indices[::-1], self._points[::-1]):
            mp._polygon.insert(idx, point)
        mp.update()


class UndoPolygonUndoEdit(QtWidgets.QUndoCommand):
    def __init__(self,
                 markup_polygon: MarkupPolygon,
                 prev_polygon: QtGui.QPolygonF) -> None:
        self._markup_polygon = markup_polygon
        self._prev_polygon = prev_polygon
        self._polygon = markup_polygon._polygon[:]
        super().__init__(tr("Polygon Edition"))

    def redo(self) -> None:
        mp = self._markup_polygon
        if mp.in_edit_mode():
            mp.stop_edit_nodes()
        mp._polygon = self._polygon[:]
        mp.update()

    def undo(self) -> None:
        mp = self._markup_polygon
        if mp.in_edit_mode():
            mp.stop_edit_nodes()
        mp._polygon = self._prev_polygon[:]
        mp.update()
