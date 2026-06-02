from __future__ import annotations
from typing import Any, ClassVar, TYPE_CHECKING
from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsView, QGraphicsSceneMouseEvent
from ..settings import settings

if TYPE_CHECKING:
    from ..views.image_view import ImageView


class MarkupObjectMeta:
    # default values
    PEN: ClassVar[QtGui.QPen]
    PEN_DASHED: ClassVar[QtGui.QPen]
    PEN_SELECTED: ClassVar[QtGui.QPen]
    PEN_SELECTED_DASHED: ClassVar[QtGui.QPen]

    ACTION_KEYS: ClassVar[dict[Qt.Key, tuple[int, ...]]] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        assert not hasattr(self, "_edit_mode")
        self._edit_mode = False
        super().__init__(*args, *kwargs)

    @classmethod
    def on_settings_updated(cls):
        cls.PEN = QtGui.QPen(settings.line_1, settings.line_w)
        cls.PEN_DASHED = QtGui.QPen(
            settings.line_2, settings.line_w, Qt.PenStyle.DashLine
        )
        cls.PEN_SELECTED = QtGui.QPen(settings.line_sel_1, settings.line_w)
        cls.PEN_SELECTED_DASHED = QtGui.QPen(
            settings.line_sel_2, settings.line_w, Qt.PenStyle.DashLine
        )

    def mouseDoubleClickEvent(self, _event: QGraphicsSceneMouseEvent) -> None:
        if self._edit_mode:
            self.stop_edit_nodes()
        else:
            self.start_edit_nodes()

    def attach(self, view: ImageView) -> None:
        raise NotImplementedError(
            f"class `{type(self).__name__}` must implement `attach` method"
        )

    def start_edit_nodes(self) -> None:
        self._edit_mode = True
        self.on_start_edit()
        self.scene().set_current_markup_object(self)

    def ensure_edition_canceled(self):
        if self.in_edit_mode():
            self.stop_edit_nodes()

    def stop_edit_nodes(self) -> None:
        assert (
            self._edit_mode
        ), "programming error (ensure object is edit_mode)"
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
            QtWidgets.QGraphicsItem.keyPressEvent(
                self, event
            )  # - not required ?

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
    def attach(cls, view: ImageView) -> None:
        view.setCursor(Qt.CursorShape.ArrowCursor)
        view.set_mouse_press(cls._mouse_press)

    @classmethod
    def _mouse_press(cls, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        assert event.button() == Qt.MouseButton.LeftButton
        view.setDragMode(view.RubberBandDrag)
        view.set_mouse_press(None)
        view.set_mouse_release(cls._mouse_release)
        return False

    @classmethod
    def _mouse_release(cls, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        assert event.button() == Qt.MouseButton.LeftButton

        # weird trick to make sure that rubber band vanished
        QGraphicsView.mouseReleaseEvent(view, event)

        view.setDragMode(view.NoDrag)
        view.set_mouse_release(None)
        view.set_mouse_press(cls._mouse_press)
        return True


MarkupObjectMeta.on_settings_updated()
settings.register(MarkupObjectMeta.on_settings_updated)
