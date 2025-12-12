from __future__ import annotations
from PyQt5.QtWidgets import (
    QMainWindow,
    QMessageBox as MB,
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from gmc import __version__ as gmc_version
from gmc.utils import get_icon


def about_qt(main_window: QMainWindow) -> None:
    import platform

    MB.aboutQt(
        main_window,
        f"{main_window.windowTitle()} @ python "
        f"{platform.python_version()} : {platform.architecture()[0]}",
    )


class AboutDialog(QDialog):
    def __init__(self, parent: QMainWindow):
        super().__init__(parent, windowTitle=f"About GMC", minimumWidth=320)
        issues_url = "https://github.com/senyai/gmc/issues"
        doc_url = "https://github.com/senyai/gmc/blob/main/doc/source/tagged_objects.rst"

        layout = QVBoxLayout(self)

        logo = QLabel()
        logo.setPixmap(QPixmap("gmc:gmc.svg"))
        layout.addWidget(logo, alignment=Qt.AlignCenter)

        layout.addWidget(
            QLabel(f"<h1>GMC {gmc_version}</h1>", self),
            alignment=Qt.AlignCenter,
        )
        layout.addWidget(
            QLabel("General Markup Creator.", self),
            alignment=Qt.AlignCenter,
        )

        for link in (
            f'<a href="{doc_url}">Documentation on GitHub</a>',
            f'<a href="{issues_url}">Report issues on GitHub</a>',
        ):
            layout.addWidget(
                QLabel(
                    link,
                    self,
                    openExternalLinks=True,
                    textInteractionFlags=Qt.TextBrowserInteraction,
                ),
                alignment=Qt.AlignCenter,
            )
        for text in (
            "Author: <big>Arseniy Terekhin</big> and the team",
            "Copyright: 2015-2025",
        ):
            layout.addWidget(
                QLabel(text, self),
                alignment=Qt.AlignCenter,
            )

        btn_box = QDialogButtonBox(QDialogButtonBox.Close)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)


def about_gmc(main_window: QMainWindow) -> None:
    AboutDialog(main_window).exec()
