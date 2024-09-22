from __future__ import annotations
from typing import Any, ClassVar
from PyQt5.QtCore import QSettings, QByteArray
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QMainWindow


default_font_label = QFont("Arial")
default_font_label.setPointSizeF(10.0)
default_font_label.setFixedPitch(False)


class Settings:
    # `settings` as a public attribute, so custom properties are possible
    settings = QSettings("Visillect", "GMC")
    _defaults: ClassVar[dict[str, QColor | QFont | int]] = {
        "bg_1": QColor(0),
        "bg_2": QColor(0xF, 0xF, 0xF),
        "font_label": default_font_label,
        "click_ms": 250,
        # 'schema': str,
    }
    __slots__ = tuple(_defaults)

    def __init__(self) -> None:
        value = self.value
        # all values that are set here should also be set in `sync`
        for attr, default_value in self._defaults.items():
            setattr(self, attr, value(attr, default=default_value))

    def get_default(self, key: str):
        return self._defaults[key]

    @classmethod
    def value(
        cls, key: str, default: Any = None, type_: type[Any] = str
    ) -> Any:
        """for values that are rarely needed"""
        if key in cls._defaults:
            type_ = type(cls._defaults[key])
        return cls.settings.value(key, default, type_)

    def sync(self) -> None:
        for attr in self._defaults:
            self.set_value(attr, getattr(self, attr))
        self.settings.sync()

    def set_value(self, key: str, value: Any, type_: type[Any] = str) -> None:
        if value is not None:
            if key in self._defaults:
                type_ = type(self._defaults[key])
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
