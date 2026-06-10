from __future__ import annotations
from typing import Any, Callable
from PyQt5.QtCore import QSettings, QByteArray, Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QMainWindow

default_font_label = QFont("Arial")
default_font_label.setPointSizeF(10.0)
default_font_label.setFixedPitch(False)


class Settings:
    """
    Class for storing not only default settings from annotations,
    but also allow settings external settings
    """

    # `settings` as a public attribute, so custom properties are possible,
    # but still, `value` and `set_value` should be used (right?)
    settings = QSettings("Visillect", "GMC")
    bg_1: QColor = QColor(0)
    bg_2: QColor = QColor(0xF, 0xF, 0xF)
    line_1: QColor = QColor(Qt.GlobalColor.white)
    line_2: QColor = QColor(Qt.GlobalColor.red)
    line_sel_1: QColor = QColor(Qt.GlobalColor.yellow)
    line_sel_2: QColor = QColor(Qt.GlobalColor.blue)
    diamond: QColor = QColor(Qt.GlobalColor.magenta)
    font_label: QFont = default_font_label
    click_ms: int = 250
    line_w: int = 0
    zoom: int = 0  # default zoom%, 0 is auto

    def __init__(self) -> None:
        self._callbacks: set[Callable[[], None]] = set()
        # all values that are set here should also be set in `sync`
        assert len(self.__annotations__) == 11, f"Programmer error"
        value = self.value
        for attr in self.__annotations__:
            setattr(self, attr, value(attr, default=getattr(self, attr)))

    def register(self, callback: Callable[[], None]):
        """
        Register callbacks that will be called when settings are changed
        """
        self._callbacks.add(callback)
        return callback

    def unregister(self, callback: Callable[[], None]):
        self._callbacks.remove(callback)

    def update(self):
        """
        Notify all callbacks. Called from Setting dialog
        """
        for callback in self._callbacks:
            callback()

    @classmethod
    def get_default(cls, key: str) -> QColor | QFont | int:
        """
        Useful in settings dialog for "Default" button
        """
        return getattr(cls, key)

    @classmethod
    def value(
        cls, key: str, default: Any = None, type_: type[Any] = str
    ) -> Any:
        """
        Method for values that are rarely needed. Maybe it shouldn't be called.
        """
        if key in cls.__annotations__:
            type_ = type(cls.get_default(key))
        return cls.settings.value(key, default, type_)

    def sync(self) -> None:
        for attr in self.__annotations__:
            self.set_value(attr, getattr(self, attr))
        self.settings.sync()

    def set_value(self, key: str, value: Any, type_: type[Any] = str) -> None:
        if value is not None:
            if key in self.__annotations__:
                type_ = type(self.get_default(key))
            if not isinstance(value, type_):
                raise TypeError(key, value)
            self.settings.setValue(key, value)

    def load_state_and_geometry(self, widget: QMainWindow, name: str) -> None:
        value = self.settings.value
        widget.restoreGeometry(value(name + "_geometry", QByteArray()))
        widget.restoreState(value(name + "_state", QByteArray()))

    def load_state(self, widget: QMainWindow, name: str) -> None:
        widget.restoreState(self.settings.value(name + "_state", QByteArray()))

    def save_state_and_geometry(self, widget: QMainWindow, name: str) -> None:
        set_value = self.settings.setValue
        set_value(name + "_geometry", widget.saveGeometry())
        set_value(name + "_state", widget.saveState())

    def save_state(self, widget: QMainWindow, name: str) -> None:
        self.settings.setValue(name + "_state", widget.saveState())


settings = Settings()
