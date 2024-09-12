from __future__ import annotations
from typing import Any, ClassVar, Dict, Tuple
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsView, QGraphicsSceneMouseEvent


class MarkupObjectMeta:
    # default values
    PEN = QtGui.QPen(Qt.GlobalColor.white, 0)
    PEN_DASHED = QtGui.QPen(Qt.GlobalColor.red, 0, Qt.PenStyle.DashLine)
    PEN_SELECTED = QtGui.QPen(Qt.GlobalColor.yellow, 0)
    PEN_SELECTED_DASHED = QtGui.QPen(Qt.GlobalColor.blue, 0, Qt.PenStyle.DashLine)
    ACTION_KEYS: ClassVar[Dict[Qt.Key, Tuple[int, ...]]] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        assert not hasattr(self, '_edit_mode')
        self._edit_mode = False
        super().__init__(*args, *kwargs)

    def mouseDoubleClickEvent(self, _event: QGraphicsSceneMouseEvent) -> None:
        if self._edit_mode:
            self.stop_edit_nodes()
        else:
            self.start_edit_nodes()

    def attach(self, view: 'ImageView') -> None:
        raise NotImplementedError("class `{}` must implement `attach` method"
                                  .format(self.__class__.__name__))

    def start_edit_nodes(self) -> None:
        self._edit_mode = True
        self.on_start_edit()
        self.scene().set_current_markup_object(self)

    def stop_edit_nodes(self) -> None:
        assert self._edit_mode, 'programming error (ensure object is edit_mode)'
        self._edit_mode = False
        self.on_stop_edit()
        self.scene().set_current_markup_object(None)

    def on_start_edit(self) -> None:
        pass

    def on_stop_edit(self) -> None:
        pass

    def in_edit_mode(self) -> bool:
        return self._edit_mode

    def delete(self) -> bool:
        """
        Called when `Delete Selection` is triggered. Returns whether the object
        can be removed from the scene.
        """
        return True

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        act = self.ACTION_KEYS.get(event.key())
        if act is not None:
            if not self.in_edit_mode():
                self.start_edit_nodes()
            for idx, diamond in enumerate(self.childItems()):
                diamond.setSelected(idx in act)
        else:
            QtWidgets.QGraphicsItem.keyPressEvent(self, event)  # - not required ?

    def prevent_event(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        """
        Special method that should be used by `MarkupObjectMeta` users
        to ignore an event
        """
        return True

    def on_created(self) -> None:
        """
        For overriding. Should be called by instruments after user has
        created on object using input device.
        """
        pass


class MarkupSelect:
    @classmethod
    def attach(cls, view: 'ImageView') -> None:
        view.setCursor(Qt.CursorShape.ArrowCursor)
        view.set_mouse_press(cls._mouse_press)

    @classmethod
    def _mouse_press(cls, event: QtGui.QMouseEvent, view: 'ImageView') -> bool:
        assert event.button() == Qt.MouseButton.LeftButton
        view.setDragMode(view.RubberBandDrag)
        view.set_mouse_press(None)
        view.set_mouse_release(cls._mouse_release)
        return False

    @classmethod
    def _mouse_release(cls, event: QtGui.QMouseEvent, view: 'ImageView') -> bool:
        assert event.button() == Qt.MouseButton.LeftButton

        # weird trick to make sure that rubber band vanished
        QGraphicsView.mouseReleaseEvent(view, event)

        view.setDragMode(view.NoDrag)
        view.set_mouse_release(None)
        view.set_mouse_press(cls._mouse_press)
        return True


from ..views.image_view import ImageView
