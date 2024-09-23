from __future__ import annotations
from typing import Any, Callable, TYPE_CHECKING
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPointF

from ..graphics import chess
from ..utils import new_action, get_icon, tr, clipboard

Qt = QtCore.Qt


def no_action(event: QtGui.QMouseEvent, self: ImageView) -> bool:
    return False


def no_cancel(view: ImageView) -> None:
    pass


class MarkupScene(QtWidgets.QGraphicsScene):
    MOVEMENTS: dict[int, QPointF] = {
        Qt.Key.Key_Up: QPointF(0, -1),
        # Qt.Key.Key_8: QPointF(0, -1),
        Qt.Key.Key_Right: QPointF(1, 0),
        # Qt.Key.Key_6: QPointF(1, 0),
        Qt.Key.Key_Down: QPointF(0, 1),
        # Qt.Key.Key_2: QPointF(0, 1),
        Qt.Key.Key_Left: QPointF(-1, 0),
        # Qt.Key_4: QPointF(-1, 0),
    }
    _current_object: MarkupObjectMeta | None = None

    # False: don't try to show cursor
    # None: cursor not on window
    # QPointF: draw cursor

    _cross_pos: QPointF | bool | None = False
    _cross_pen = QtGui.QPen(
        QtGui.QColor(255, 32, 32, 224), 0.0, Qt.PenStyle.CustomDashLine
    )
    _cross_pen.setDashPattern([16, 8])

    def __init__(self, parent: QtCore.QObject) -> None:
        super().__init__(parent)
        self.undo_stack = QtWidgets.QUndoStack(self, undoLimit=8192)
        self.selectionChanged.connect(self._on_selection_changed)
        self.setItemIndexMethod(self.ItemIndexMethod.NoIndex)

    def mouseDoubleClickEvent(
        self, event: QtWidgets.QGraphicsSceneMouseEvent
    ) -> None:
        # This function exists to clear current object when nothing is clicked
        item = self.itemAt(event.scenePos(), QtGui.QTransform())
        if item is None or getattr(item, "no_doubleclick", False):
            self.set_current_markup_object(None)
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(
        self, event: QtWidgets.QGraphicsSceneMouseEvent
    ) -> None:
        if self._cross_pos is not False:
            self._cross_pos = event.scenePos()
            self.invalidate(QtCore.QRectF(), self.SceneLayer.ForegroundLayer)
        super().mouseMoveEvent(event)

    def drawForeground(
        self, painter: QtGui.QPainter, rect: QtCore.QRectF
    ) -> None:
        coords = self._cross_pos
        if type(coords) is not QPointF:
            return
        painter.setClipRect(rect)
        painter.setPen(self._cross_pen)
        painter.drawLine(
            QPointF(coords.x(), rect.top() - 24 + coords.y() % 24),
            QPointF(coords.x(), rect.bottom()),
        )
        painter.drawLine(
            QPointF(rect.left() + coords.x() % 24 - 24, coords.y()),
            QPointF(rect.right(), coords.y()),
        )

    def event(self, event: QtCore.QEvent) -> bool:
        if event.type() == event.Type.Leave and self._cross_pos is not False:
            self._cross_pos = None
            self.invalidate(QtCore.QRectF(), self.SceneLayer.ForegroundLayer)
        return super().event(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        selected = self.selectedItems()
        self.parent().delete_action.setEnabled(bool(selected))
        self.parent().copy_action.setEnabled(bool(selected))
        if selected:
            vec = self.MOVEMENTS.get(event.key())
            if vec:
                modif = event.modifiers()
                if modif & Qt.AltModifier or modif & Qt.ControlModifier:
                    vec = vec * 0.25
                elif modif & Qt.ShiftModifier:
                    vec = vec * 4.0
                moved: list[MarkupObjectMeta] = []
                for item in selected:
                    if isinstance(item, MarkupObjectMeta):
                        moved.append(item)
                    else:
                        item.setPos(item.pos() + vec)
                if moved:
                    self.undo_stack.push(UndoObjectsMovement(moved, vec))
                return
        super().keyPressEvent(event)

    def _on_selection_changed(self) -> None:
        items = self.selectedItems()
        if len(items) == 1:
            items[0].setFocus()
        self.parent().delete_action.setEnabled(bool(items))
        self.parent().copy_action.setEnabled(bool(items))

    def set_current_markup_object(
        self, markup_object: MarkupObjectMeta | None
    ) -> None:
        """
        :purpose: unknown

        probably bad design
        """
        if self._current_object is markup_object:
            return
        if self._current_object is not None:
            self._current_object.ensure_edition_canceled()
        self._current_object = markup_object

    def show_cross_cursor(self, pos: QPointF | None) -> None:
        self._cross_pos = pos
        self.invalidate(QtCore.QRectF(), self.SceneLayer.ForegroundLayer)

    def hide_cross_cursor(self) -> None:
        if self._cross_pos is not False:
            self._cross_pos = False
            self.invalidate(QtCore.QRectF(), self.SceneLayer.ForegroundLayer)


# should return `True` when the event is accepted
MouseCallback = Callable[[QtGui.QMouseEvent, "ImageView"], bool]
CancelCallback = Callable[["ImageView"], None]


class ImageView(QtWidgets.QGraphicsView):
    _scene_padding_px = 20

    def __init__(self):
        from ..settings import settings

        super().__init__(
            contextMenuPolicy=Qt.ActionsContextMenu,
            backgroundBrush=chess(16, settings.bg_1, settings.bg_2),
            cacheMode=self.CacheBackground,
            viewportUpdateMode=self.FullViewportUpdate,
            transformationAnchor=self.AnchorUnderMouse,
            resizeAnchor=self.AnchorViewCenter,
            focusPolicy=Qt.WheelFocus,
            font=settings.font_label,
        )  # type: ignore
        self._scene = MarkupScene(self)
        self.setScene(self._scene)
        self.addAction(
            QtWidgets.QAction(tr("Debug"), self, triggered=self._debug)
        )
        KS = QtGui.QKeySequence

        self.delete_action = new_action(
            self,
            "delete",
            tr("Delete Selection"),
            (Qt.Key_Delete,),
            triggered=self._delete,
            enabled=False,
        )
        self.select_all_action = new_action(
            self,
            "select_all",
            tr("Select All"),
            (KS.StandardKey.SelectAll,),
            triggered=self._select_all,
        )

        self.copy_action = new_action(
            self,
            "copy",
            tr("Copy"),
            (KS.StandardKey.Copy,),
            triggered=self._copy,
        )
        self.paste_action = new_action(
            self,
            "paste",
            tr("Paste"),
            (KS.StandardKey.Paste,),
            triggered=self._paste,
        )

        # undo
        self.undo_action = self._scene.undo_stack.createUndoAction(
            self, tr("Undo")
        )
        ctrl_z = KS(Qt.CTRL + Qt.Key_Z)
        undo_shortcuts = KS.keyBindings(KS.StandardKey.Undo)
        if ctrl_z not in undo_shortcuts:
            undo_shortcuts.append(ctrl_z)
        self.undo_action.setShortcuts(undo_shortcuts)
        self.undo_action.setIcon(get_icon("undo"))

        # redo
        self.redo_action = self._scene.undo_stack.createRedoAction(
            self, tr("Redo")
        )
        ctrl_y = KS(Qt.CTRL + Qt.Key_Y)
        redo_shortcuts = KS.keyBindings(KS.StandardKey.Redo)
        if ctrl_y not in redo_shortcuts:
            redo_shortcuts.append(ctrl_y)
        self.redo_action.setShortcuts(redo_shortcuts)
        self.redo_action.setIcon(get_icon("redo"))

        self.unset_all_events()

    def unset_all_events(self) -> None:
        self.set_mouse_press(None)
        self.set_mouse_move(None)
        self.set_mouse_release(None)
        self.set_mouse_move(None)
        self.set_mouse_doubleclick(None)
        self.set_cancel(None)

    def set_markup_object(self, cls: type[MarkupObjectMeta]) -> None:
        """
        :param cls: callable, that returns markup object.
        """
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.hide_cross_cursor()
        # cancel function MUST be clever enough to clean up after itself
        self._current_cancel(self)

        obj = cls()  # SHOULD keep itself alive
        obj.attach(self)

    def set_mouse_press(self, func: MouseCallback | None) -> None:
        self._current_mouse_press = func or no_action

    def set_mouse_release(self, func: MouseCallback | None) -> None:
        self._current_mouse_release = func or no_action

    def set_mouse_doubleclick(self, func: MouseCallback | None) -> None:
        self._current_mouse_doubleclick = func or no_action

    def set_mouse_move(self, func: MouseCallback | None) -> None:
        self._current_mouse_move = func or self._dummy_mouse_move

    def set_cancel(self, func: CancelCallback | None) -> None:
        self._current_cancel = func or no_cancel

    def _delete(self) -> None:
        deleted_items: list[MarkupObjectMeta] = []
        for item in self._scene.selectedItems():
            # we delete even `MoveableDiamond` because how otherwise delete it
            if hasattr(item, "delete"):
                # we check that item's scene exists, because `delete` method
                # can remove other selected items.
                if item.delete() and item.scene():
                    item.ensure_edition_canceled()
                    self._scene.removeItem(item)
                    if isinstance(item, MarkupObjectMeta):
                        deleted_items.append(item)
        if deleted_items:
            self._scene.undo_stack.push(
                UndoObjectsDelete(self._scene, deleted_items)
            )

    def _copy(self) -> None:
        data_list: list[dict[Any, Any]] = []
        for item in self._scene.selectedItems():
            if hasattr(item, "data"):
                try:
                    data: dict[Any, Any] = item.data()
                except TypeError:
                    continue  # data(self, int): not enough arguments
                data["_class"] = item.__class__.__name__
                data_list.append(data)
        clipboard.set_objects(data_list)

    def _paste(self) -> None:
        data_list = clipboard.get_objects() or []
        image_widget = self.parent()
        image_widget.on_paste.emit(data_list)

    def _select_all(self) -> None:
        flags = QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        for item in self._scene.items():
            if item.flags() & flags:
                item.setSelected(True)

    def _debug(self) -> None:
        print("debug", self._scene.items())

    def set_pixmap(
        self, pixmap: QtGui.QPixmap
    ) -> QtWidgets.QGraphicsPixmapItem:
        self.unset_all_events()
        self._scene.set_current_markup_object(None)
        self._scene.clear()
        item = QtWidgets.QGraphicsPixmapItem(pixmap)
        item.no_doubleclick = True
        self._scene.addItem(item)
        p = self._scene_padding_px
        self._scene.setSceneRect(
            -p, -p, pixmap.width() + p * 2, pixmap.height() + p * 2
        )
        self._auto_zoom(self._auto_zoom_act.isChecked())
        return item

    def get_zoom_actions(
        self,
    ) -> tuple[
        QtWidgets.QAction,
        QtWidgets.QAction,
        QtWidgets.QAction,
        QtWidgets.QAction,
    ]:
        zoom_in = new_action(
            self,
            "zoom_in",
            tr("Zoom In"),
            (Qt.Key.Key_Plus, Qt.Key.Key_Equal),
            triggered=lambda: self._scale_view(1.2),
        )
        zoom_out = new_action(
            self,
            "zoom_out",
            tr("Zoom Out"),
            (Qt.Key.Key_Minus, Qt.Key.Key_Underscore),
            triggered=lambda: self._scale_view(1 / 1.2),
        )
        zoom_1_1 = new_action(
            self,
            "zoom_1_1",
            tr("Zoom 1:1"),
            (Qt.Key.Key_0, Qt.Key.Key_Insert),
            triggered=lambda: self._set_scale(1.0),
        )
        self._auto_zoom_act = new_action(
            self,
            "zoom_auto",
            tr("Auto Zoom"),
            (Qt.Key.Key_ParenRight,),
            checkable=True,
            triggered=self._auto_zoom,
        )
        return (zoom_in, zoom_out, zoom_1_1, self._auto_zoom_act)

    def _auto_zoom(self, yes: bool) -> None:
        if yes:
            p = self._scene_padding_px
            rc = self._scene.sceneRect().adjusted(p, p, -p, -p)
            self.fitInView(rc, Qt.AspectRatioMode.KeepAspectRatio)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            # to not clear selection on menu
            event.accept()
        elif event.button() == Qt.MouseButton.MiddleButton:  # dragging
            LB = Qt.MouseButton.LeftButton
            lmbe = lambda: QtGui.QMouseEvent(
                event.type(), event.pos(), LB, LB, event.modifiers()
            )
            self._prev_drag_mode = self.dragMode()
            self.setDragMode(self.ScrollHandDrag)
            event = lmbe()
            event.setAccepted(True)
            self.setInteractive(False)
            super().mousePressEvent(event)
        elif not self._current_mouse_press(event, self):
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        # view receives event before scene
        if not self._current_mouse_doubleclick(event, self):
            super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            event.accept()
            self.setInteractive(True)
            self.setDragMode(self._prev_drag_mode)
            return
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
            return
        if not self._current_mouse_release(event, self):
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if not self._current_mouse_move(event, self):
            super().mouseMoveEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._scale_view(2.0 ** (event.angleDelta().y() / 240.0))
        else:
            super().wheelEvent(event)

    def _scale_view(self, factor: float) -> None:
        new_factor = (
            self.transform()
            .scale(factor, factor)
            .mapRect(QtCore.QRectF(0, 0, 1, 1))
            .width()
        )
        current_factor = self.transform().map(1.0, 1.0)[0]
        if (
            0.01 <= new_factor <= 256.0
            or current_factor < 0.01
            and new_factor > current_factor
            or new_factor > 256.0
            and new_factor < current_factor
        ):
            self.scale(factor, factor)

    def _set_scale(self, scale: float) -> None:
        old_matrix = self.transform()
        self.resetTransform()
        self.translate(old_matrix.dx(), old_matrix.dy())
        self.scale(scale, scale)

    @staticmethod
    def _dummy_mouse_move(
        event: QtGui.QMouseEvent, self: "ImageView", *args: Any
    ) -> None:
        # Mouse is just moving
        # pos = self.mapToScene(event.pos())
        size = self.viewport().size()
        width, height = size.width(), size.height()
        event_x, event_y = event.x(), event.y()
        # mouse wrap implementation from
        # https://overthere.co.uk/2012/11/29/qgraphicsview-with-mouse-wrapping/
        if event.buttons() == Qt.MiddleButton and (
            event_y < 0 or event_y > height or event_x < 0 or event_x > width
        ):
            # Mouse cursor has left the widget. Wrap the mouse.
            global_pos = self.mapToGlobal(event.pos())
            if event_y < 0 or event_y > height:
                # Cursor left on the y axis. Move cursor to the
                # opposite side.
                global_pos.setY(
                    global_pos.y() + (height if event_y < 0 else -height)
                )
            else:
                # Cursor left on the x axis. Move cursor to the
                # opposite side.
                global_pos.setX(
                    global_pos.x() + (width if event_x < 0 else -width)
                )

            # For the scroll hand dragging to work with mouse wrapping
            # we have to emulate a mouse release, move the cursor and
            # then emulate a mouse press. Not doing this causes the
            # scroll hand drag to stop after the cursor has moved.
            r_event = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonRelease,
                self.mapFromGlobal(QtGui.QCursor.pos()),
                Qt.MiddleButton,
                Qt.NoButton,
                Qt.NoModifier,
            )
            self.mouseReleaseEvent(r_event)
            QtGui.QCursor.setPos(global_pos)
            p_event = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonPress,
                self.mapFromGlobal(QtGui.QCursor.pos()),
                Qt.MiddleButton,
                Qt.MiddleButton,
                Qt.NoModifier,
            )
            QtCore.QTimer.singleShot(0, lambda: self.mousePressEvent(p_event))

    def show_cross_cursor(self):
        pos = self.mapFromGlobal(QtGui.QCursor.pos())
        if self.rect().contains(pos):
            pos = self.mapToScene(pos)
        else:
            pos = None
        self.scene().show_cross_cursor(pos)

    def hide_cross_cursor(self):
        self.scene().hide_cross_cursor()

    if TYPE_CHECKING:

        def scene(self) -> MarkupScene: ...


class UndoObjectsMovement(QtWidgets.QUndoCommand):
    def __init__(
        self, items: list[QtWidgets.QGraphicsItem], vec: QPointF
    ) -> None:
        self._items = items
        self._prev_poses = [item.pos() for item in items]
        self._vec = vec
        super().__init__(tr("Movement"))

    def redo(self) -> None:
        for item, pos in zip(self._items, self._prev_poses):
            item.setPos(pos + self._vec)

    def undo(self) -> None:
        for item, pos in zip(self._items, self._prev_poses):
            item.setPos(pos)


class UndoObjectsDelete(QtWidgets.QUndoCommand):
    def __init__(
        self,
        scene: QtWidgets.QGraphicsScene,
        items: list[QtWidgets.QGraphicsItem],
    ) -> None:
        self._scene = scene
        self._items = items
        super().__init__(tr("Deletion"))

    def redo(self) -> None:
        for item in self._items:
            if item.scene():
                self._scene.removeItem(item)

    def undo(self) -> None:
        for item in self._items:
            self._scene.addItem(item)


from ..markup_objects import MarkupObjectMeta  # here fixing circular reference
