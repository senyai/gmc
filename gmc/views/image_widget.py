from typing import Any, List, Tuple, Union
from PyQt5 import QtCore, QtGui, QtWidgets
from ..utils import separator, new_action
from .image_view import ImageView
from ..markup_objects import MarkupSelect
Qt = QtCore.Qt
tr = lambda text: QtCore.QCoreApplication.translate("@default", text)


class ImageWidget(QtWidgets.QWidget):
    # on_paste is emmited when user pastes objects, copied from gmc
    on_paste = QtCore.pyqtSignal(list)

    def __init__(self, default_actions: List[QtWidgets.QAction], view_cls=ImageView):
        super().__init__()
        self._default_actions = default_actions
        self._markup_group = QtWidgets.QActionGroup(self)
        self._toolbar = self._create_toolbar()
        self._view = view_cls()
        layout = QtWidgets.QHBoxLayout(self, margin=0, spacing=0)
        layout.addWidget(self._toolbar, 0, Qt.AlignTop)
        layout.addWidget(self._view)

    def add_user_action(self, name: str, shortcut: str,
                        icon: Union[str, QtGui.QIcon], **kwargs: Any
                       ) -> QtWidgets.QAction:
        action = new_action(self, icon, name, (shortcut,), **kwargs)
        self.add_action(action)
        return action

    def add_action(self, action: QtWidgets.QAction) -> None:
        # For really custom actions and splitters
        self._toolbar.addAction(action)
        self._view.addAction(action)

    def add_markup_action(self, name: str,
                          shortcut: Union[str, Tuple[str, ...]],
                          icon: str,
                          markup_object,
                          **kwargs: Any) -> QtWidgets.QAction:
        if isinstance(shortcut, str):
            shortcut = (shortcut,)  # support str as shortcut for convenience
        action = new_action(
            self, icon, name, shortcut,
            triggered=lambda: self._set_markup_object(markup_object),
            checkable=True, **kwargs)
        self._markup_group.addAction(action)
        self.add_action(action)
        return action

    def add_select_action(self) -> QtWidgets.QAction:
        """Adds default "Select and Transform Objects" action"""
        return self.add_markup_action(
            tr("Select and Transform Objects"), ("m", "esc"), "pointer", MarkupSelect)

    def add_default_actions(self) -> None:
        selection = (
            self._view.select_all_action,
            self._view.delete_action,
            self._view.undo_action,
            self._view.redo_action,
            self._view.copy_action,
            self._view.paste_action,
        )
        for actions in (self._view.get_zoom_actions(),
                        selection, self._default_actions):
            self._view.addAction(separator(self))
            self._view.addActions(actions)
            if actions is not selection:
                self._toolbar.addAction(separator(self))
                self._toolbar.addActions(actions)
        del self._default_actions

    def _create_toolbar(self) -> QtWidgets.QToolBar:
        toolbar = QtWidgets.QToolBar(self)
        toolbar.setOrientation(Qt.Vertical)
        return toolbar

    def _set_markup_object(self, cls):
        return self._view.set_markup_object(cls)

    def set_pixmap(self,
                   pixmap: QtGui.QPixmap) -> QtWidgets.QGraphicsPixmapItem:
        return self._view.set_pixmap(pixmap)

    def scene(self):
        # Known to raise RuntimeError, since the scene can disappear
        return self._view.scene()

    def view(self) -> ImageView:
        return self._view  # user might want to zoom or something

    def focusInEvent(self, event: QtGui.QFocusEvent) -> None:
        super().focusInEvent(event)
        self._view.setFocus()
