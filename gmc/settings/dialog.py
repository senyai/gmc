from typing import Any
from PyQt5 import QtCore, QtGui, QtWidgets
from gmc.settings import settings
from ..utils import tr

Qt = QtCore.Qt
CD = QtWidgets.QColorDialog
QColor = QtGui.QColor


class ColorWidget(QtWidgets.QAbstractButton):
    def __init__(self, color: QtGui.QColor, with_alpha: bool = True) -> None:
        super().__init__(autoFillBackground=True, clicked=self._on_click)  # type: ignore
        self._options = (
            CD.ColorDialogOption.ShowAlphaChannel
            if with_alpha
            else CD.ColorDialogOptions()
        )
        self.setValue(color)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(24, 16)

    def value(self) -> QtGui.QColor:
        palette = self.palette()
        return palette.color(palette.Background)

    def setValue(self, color: QtGui.QColor) -> None:
        palette = self.palette()
        palette.setColor(palette.Background, color)
        self.setPalette(palette)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        sz = self.size()
        rc = QtCore.QRectF(1, 1, sz.width() - 2, sz.height() - 2)
        painter.setBrush(self.value())
        painter.drawRoundedRect(rc, 2.5, 2.5)

    def _on_click(self) -> None:
        color = CD.getColor(self.value(), self, options=self._options)
        if color.isValid():
            self.setValue(color)


class FontWidget(QtWidgets.QPushButton):
    def __init__(self, text: str, font: QtGui.QFont) -> None:
        super().__init__(
            text,
            font=font,
            styleSheet="QLabel{background-color:white;color:black}",
            clicked=self._on_click,
        )  # type: ignore

    def value(self) -> QtGui.QFont:
        return self.font()

    def setValue(self, font: QtGui.QFont):
        self.setFont(font)

    def _on_click(self) -> None:
        font, ok = QtWidgets.QFontDialog.getFont(self.font(), self)
        if ok:
            self.setFont(font)


def add_default(
    form: QtWidgets.QFormLayout,
    label: str,
    widget: QtWidgets.QSpinBox | FontWidget | ColorWidget,
    attr: str,
) -> None:
    """ """

    def default_callback(_: Any):
        widget.setValue(settings.get_default(attr))

    layout = QtWidgets.QHBoxLayout(margin=0)  # type: ignore
    layout.addWidget(widget)
    layout.addWidget(
        QtWidgets.QPushButton(
            tr("Default"), flat=True, clicked=default_callback
        )
    )  # type: ignore
    label_widget = QtWidgets.QLabel(label)
    label_widget.setBuddy(widget)
    form.addRow(label_widget, layout)


def create_setting_dialog(parent: QtWidgets.QWidget) -> None:
    dialog = QtWidgets.QDialog(parent, windowTitle=f"GMC " + tr("Settings"))  # type: ignore
    form = QtWidgets.QFormLayout()

    bg_1 = ColorWidget(settings.bg_1, with_alpha=False)
    bg_2 = ColorWidget(settings.bg_2, with_alpha=False)
    line_1 = ColorWidget(settings.line_1)
    line_2 = ColorWidget(settings.line_2)
    line_sel_1 = ColorWidget(settings.line_sel_1)
    line_sel_2 = ColorWidget(settings.line_sel_2)
    diamond = ColorWidget(settings.diamond)
    click_ms = QtWidgets.QSpinBox(
        minimum=0,
        maximum=1000,
        value=settings.click_ms,
        suffix="ms",
    )
    zoom = QtWidgets.QSpinBox(
        minimum=0,  # 0 is auto
        maximum=1000,
        value=settings.zoom,
        suffix="%",
    )
    line_w = QtWidgets.QSpinBox(
        minimum=0, maximum=100, value=settings.line_w, suffix="px"
    )
    label_font = tr("Label &font")
    font_label = FontWidget(label_font.replace("&", ""), settings.font_label)

    add_default(form, tr("Checker") + " &1", bg_1, "bg_1")
    add_default(form, tr("Checker") + " &2", bg_2, "bg_2")

    add_default(form, tr("Line") + " &3", line_1, "line_1")
    add_default(form, tr("Line") + " &4", line_2, "line_2")

    add_default(form, tr("Line Selected") + " &5", line_sel_1, "line_sel_1")
    add_default(form, tr("Line Selected") + " &6", line_sel_2, "line_sel_2")
    add_default(form, tr("Diamond Color") + " &7", diamond, "diamond")

    add_default(form, tr("Line Width"), line_w, "line_w")

    add_default(form, tr("Default Zoom"), zoom, "zoom")
    add_default(form, label_font, font_label, "font_label")
    form.addWidget(
        QtWidgets.QLabel(
            tr(
                "Time between press and release with possible mouse movements that will be registered as single mouse click"
            ),
            wordWrap=True,
        )
    )
    add_default(form, tr("Click Reaction &time"), click_ms, "click_ms")

    Box = QtWidgets.QDialogButtonBox
    button_box = Box(Box.Ok | Box.Cancel, Qt.Orientation.Horizontal, dialog)
    button_box.accepted.connect(dialog.accept)  # type: ignore
    button_box.rejected.connect(dialog.reject)  # type: ignore

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addLayout(form)
    layout.addWidget(button_box)

    if dialog.exec_() == dialog.Accepted:
        settings.bg_1 = bg_1.value()
        settings.bg_2 = bg_2.value()
        settings.line_1 = line_1.value()
        settings.line_2 = line_2.value()
        settings.line_sel_1 = line_sel_1.value()
        settings.line_sel_2 = line_sel_2.value()
        settings.diamond = diamond.value()
        settings.line_w = line_w.value()
        settings.font_label = font_label.value()
        settings.click_ms = click_ms.value()
        settings.zoom = zoom.value()
        settings.sync()
        settings.update()
