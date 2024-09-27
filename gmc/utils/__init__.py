from __future__ import annotations
from typing import Any
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtCore import QObject, Qt, QCoreApplication


class CantOpenMarkup(Exception):
    "When a schema can't open markup, ignore it"
    pass


def separator(parent: QObject) -> QAction:
    separator_act = QAction(parent)
    separator_act.setSeparator(True)
    return separator_act


def _create_icon(name: str) -> QIcon:
    icon = QIcon("gmc:%s.svg" % name)
    get_icon.__dict__[name] = icon
    return icon


def get_icon(name: str) -> QIcon:
    return get_icon.__dict__.get(name) or _create_icon(name)


def new_action(
    parent: QObject,
    icon: str | QIcon,
    text: str,
    shortcuts: tuple[str | QKeySequence.StandardKey | Qt.Key | int, ...] = (),
    shortcutContext: Qt.ShortcutContext = Qt.ShortcutContext.WidgetShortcut,
    **kwargs: Any,
) -> QAction:
    sequences = [QKeySequence(s) for s in shortcuts]
    shrtctext = "; ".join(
        s.toString(format=QKeySequence.SequenceFormat.NativeText)
        for s in sequences
    )
    if not isinstance(icon, QIcon):
        icon = get_icon(icon)
    action = QAction(
        icon,
        f"{text}\t{shrtctext}",
        parent,
        toolTip=f"{text.replace('&', '')} ({shrtctext})",
        shortcutContext=shortcutContext,
        **kwargs,  # type: ignore[call-overload]
    )
    action.setShortcuts(sequences)
    return action


def tr(text: str) -> str:
    return QCoreApplication.translate("@default", text)
