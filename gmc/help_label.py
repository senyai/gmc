from typing import Callable
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QLabel, QMessageBox
from PyQt5.QtCore import Qt, QCoreApplication

tr: Callable[[str], str] = lambda text: QCoreApplication.translate(
    "@default", text
)


class HelpLabel(QLabel):
    def __init__(self, text: str, align: str = "left"):
        super().__init__(
            f'<div align="{align}" style="font-size: 28pt;'
            " font-weight: 600;"
            " text-decoration: underline;"
            " color: #d60606;"
            ' margin-left: 4px">⇧</div>'
            f'<p align="{align}">{text}</p>',
            alignment=Qt.AlignmentFlag.AlignTop,
            wordWrap=True,
        )  # type: ignore

    def mousePressEvent(self, event: QMouseEvent) -> None:
        QMessageBox.warning(
            self,
            tr("Information"),
            tr("Click the target the arrow is pointing at"),
        )
        super().mousePressEvent(event)
