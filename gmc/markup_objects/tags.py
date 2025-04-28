from typing import Any, Callable, Sequence
from PyQt5 import QtCore, QtGui, QtWidgets
from collections import defaultdict
from gmc.views.image_widget import ImageWidget
from . import MarkupObjectMeta
from PyQt5.QtCore import Qt, QPointF, QCoreApplication

tr: Callable[[str], str] = lambda text: QCoreApplication.translate(
    "@default", text
)


class TagText:
    def __init__(self, text: str, width: float, height: float):
        self._text = text
        self.width = width
        self.height = height

    def __call__(
        self,
        painter: QtGui.QPainter,
        pen: QtGui.QPen = QtGui.QPen(Qt.GlobalColor.black),
        _align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft
        | Qt.AlignmentFlag.AlignVCenter,
    ):
        rc = QtCore.QRectF(0.0, 0.0, self.width, self.height)
        # painter.setPen(QtGui.QPen(Qt.magenta))
        # painter.drawRect(rc)
        painter.setPen(pen)
        painter.drawText(rc, _align, self._text)


class TagSplit:
    def __init__(self, height: float):
        self.width = height * 0.3
        self._line = QtCore.QLineF(self.width, 0.0, 0.0, height)

    def __call__(
        self,
        painter: QtGui.QPainter,
        pen=QtGui.QPen(QtGui.QColor(0, 0, 0, 128)),
    ):
        painter.setPen(pen)
        painter.drawLine(self._line)


class TagColor:
    def __init__(self, _text: str, _width: float, height: float):
        sz = height * 0.7
        self.width = sz
        self._rc = QtCore.QRectF(0.0, 3.0, sz, sz)

    def __call__(self, painter: QtGui.QPainter):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawEllipse(self._rc)
        return self


class TagRed(TagColor):
    pen = QtGui.QPen(QtGui.QColor(Qt.GlobalColor.red).darker(), 1.2)
    brush = QtGui.QBrush(Qt.GlobalColor.red)


class TagGreen(TagColor):
    pen = QtGui.QPen(QtGui.QColor(Qt.GlobalColor.darkGreen).darker(), 1.2)
    brush = QtGui.QBrush(Qt.GlobalColor.darkGreen)


class TagBlue(TagColor):
    pen = QtGui.QPen(QtGui.QColor(Qt.GlobalColor.darkBlue).darker(), 1.2)
    brush = QtGui.QBrush(Qt.GlobalColor.darkBlue)


class TagYellow(TagColor):
    pen = QtGui.QPen(QtGui.QColor(Qt.GlobalColor.yellow).darker(), 1.2)
    brush = QtGui.QBrush(Qt.GlobalColor.yellow)


COLOR_TAG_DICT_GET = {
    "red": TagRed,
    "green": TagGreen,
    "blue": TagBlue,
    "yellow": TagYellow,
}.get


class HasTags:
    grad = QtGui.QRadialGradient(QPointF(0.0, 8.0), 4.0)
    grad.setColorAt(0, QtGui.QColor(245, 162, 82))
    grad.setColorAt(1, QtGui.QColor(251, 191, 128))
    grad.setSpread(grad.RepeatSpread)
    tag_brush = QtGui.QBrush(grad)
    grad.setColorAt(0, QtGui.QColor(108, 112, 247))
    grad.setColorAt(1, QtGui.QColor(149, 147, 252))
    tag_brush_sel = QtGui.QBrush(grad)
    del grad
    properties: dict[str, float | int | str | bool]  # optional properties

    def __init__(self, *args: Any, tags: Sequence[str] = (), **kwargs: Any):
        self._tags: set[str] = set(tags)
        self._draws: list[Callable[[QtGui.QPainter], None]] = []
        self._tag_polygon = QtGui.QPolygonF()
        self._last_fm = None
        if "properties" in kwargs:
            self.properties = kwargs.pop("properties")
        super().__init__(*args, **kwargs)
        self._on_tags_changed()

    def get_tags(self):
        return self._tags

    def add_tag(self, tag: str):
        self._tags.add(tag)
        self._on_tags_changed()

    def remove_tag(self, tag: str):
        try:
            self._tags.remove(tag)
        except KeyError:  # created for user keys (ToDo: better explanation)
            pass
        else:
            self._on_tags_changed()

    def has_tag(self, tag: str):
        return tag in self._tags

    def _on_tags_changed(self):
        self._last_fm = None
        self.update()
        pass  # for overriding

    def data(self) -> dict[str, Any]:
        tags = sorted(self._tags)
        ret = {"data": super().data()}
        if tags:
            ret["tags"] = tags
        if hasattr(self, "properties") and self.properties:
            ret["properties"] = self.properties
        return ret

    def paint(self, painter: QtGui.QPainter, option, widget, **kwargs) -> None:
        super().paint(painter, option, widget, **kwargs)
        self.draw_tags(painter)

    def _construct_draws(
        self, painter: QtGui.QPainter, color_tag_dict_get=COLOR_TAG_DICT_GET
    ):
        fm: QtGui.QFontMetrics = painter.fontMetrics()
        if self._last_fm == fm:
            return

        self.height = fm.height()
        total_width: float = self.height * 0.5
        prev_is_text = False
        self._draws.clear()
        append = self._draws.append
        for tag in sorted(self._tags):
            cls = color_tag_dict_get(tag, TagText)
            width = fm.width(tag)
            draw = cls(tag, width, self.height)
            cur_is_text = cls is TagText
            if prev_is_text and cur_is_text:
                split = TagSplit(self.height)
                append(split)
                total_width += split.width
            prev_is_text = cur_is_text
            append(draw)
            total_width += draw.width
        hh: float = self.height * 0.5
        self._tag_polygon = QtGui.QPolygonF(
            [
                QPointF(),
                QPointF(hh, -hh),
                QPointF(total_width, -hh),
                QPointF(total_width, hh),
                QPointF(hh, hh),
            ]
        )
        self._tag_width = total_width
        self._last_fm = fm

    def draw_tags(
        self,
        painter: QtGui.QPainter,
        brush: QtGui.QBrush = QtGui.QBrush(QtGui.QColor(178, 154, 50, 122)),
    ):
        if not self._tags or self._schema.tags_hidden:
            return
        self._construct_draws(painter)
        factor = 1.0 / painter.transform().m11()
        painter.translate(self.tag_pos())
        painter.scale(factor, factor)
        painter.setPen(Qt.NoPen)

        # draw shadow
        painter.setBrush(brush)
        painter.drawPolygon(self._tag_polygon.translated(QPointF(1.5, 1.5)))

        painter.setBrush(
            self.tag_brush_sel if self.isSelected() else self.tag_brush
        )
        painter.drawPolygon(self._tag_polygon)

        painter.translate(self.height * 0.5, -self.height * 0.5)
        painter.setRenderHint(painter.Antialiasing)
        for draw in self._draws:
            draw(painter)
            painter.translate(draw.width, 0.0)


class TagEdit(QtWidgets.QLineEdit):
    commit = QtCore.pyqtSignal()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            modif = event.modifiers()
            if modif & Qt.AltModifier or modif & Qt.ControlModifier:
                self.commit.emit()
        super().keyPressEvent(event)


def edit_tags(
    parent: ImageWidget,
    items: list[MarkupObjectMeta],
    extra_tags: Sequence[str] = (),
) -> None:
    """
    :param parent: QDialog's parent QWidget
    :param tags: dict. tag name: number of objects with that tag
    :param items: number of objects selected. guaranteed to be > 0
    """
    if not items:
        return
    tags: defaultdict[str, int] = defaultdict(
        int, {tag: 0 for tag in extra_tags}
    )
    for item in items:
        for tag in item.get_tags():
            tags[tag] += 1

    dialog = QtWidgets.QDialog(parent, windowTitle=tr("Edit Tags"))

    def item_changed(item: QtWidgets.QListWidgetItem) -> None:
        if (
            item.checkState() == Qt.Checked
            and int(QtGui.QGuiApplication.keyboardModifiers()) == Qt.ALT
        ):
            for i in range(tag_list_widget.count()):
                it = tag_list_widget.item(i)
                if it.checkState() == Qt.Checked and it != item:
                    it.setCheckState(Qt.Unchecked)

    tag_list_widget = QtWidgets.QListWidget(
        itemChanged=item_changed, toolTip="Alt+click to check single item"
    )
    tags_label = QtWidgets.QLabel(tr("&Tags:"))
    tags_label.setBuddy(tag_list_widget)

    count = len(items)
    for tag in sorted(tags):
        item = QtWidgets.QListWidgetItem(tag, tag_list_widget)
        item.setFlags(item.flags() | Qt.ItemIsTristate | Qt.ItemIsEditable)
        if tags[tag] == count:
            state = Qt.Checked
        elif tags[tag]:
            state = Qt.PartiallyChecked
        else:
            state = Qt.Unchecked
        item.setCheckState(state)

    tag_line_edit = TagEdit()
    add_tag_label = QtWidgets.QLabel(tr("&Add Tag:"))
    add_tag_label.setBuddy(tag_line_edit)

    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(tags_label)
    layout.addWidget(tag_list_widget)

    add_layout = QtWidgets.QHBoxLayout(margin=0)
    add_layout.addWidget(tag_line_edit)

    def append_tag() -> None:
        tag = tag_line_edit.text().strip()
        if not tag:
            return
        tag_line_edit.setText("")
        existing_item = tag_list_widget.findItems(tag, Qt.MatchExactly)
        if existing_item:
            existing_item[0].setCheckState(Qt.Checked)
        else:
            item = QtWidgets.QListWidgetItem(tag, tag_list_widget)
            item.setFlags(item.flags() | Qt.ItemIsTristate)
            item.setCheckState(Qt.Checked)

    tag_line_edit.commit.connect(append_tag)
    add_layout.addWidget(
        QtWidgets.QPushButton(
            tr("A&ppend"), clicked=append_tag, toolTip="Ctrl+Enter, Ald+Enter"
        )
    )
    layout.addWidget(add_tag_label)
    layout.addLayout(add_layout)

    box = QtWidgets.QDialogButtonBox
    button_box = box(box.Ok | box.Cancel, Qt.Horizontal, dialog)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)
    tag_line_edit.setFocus()

    if dialog.exec_() == dialog.Accepted:
        add, remove = [], []
        append_tag()
        for idx in range(tag_list_widget.count()):
            item = tag_list_widget.item(idx)
            state = item.checkState()
            # ToDo: make code cooler by not readding tags
            if state == Qt.Checked:
                add.append(item.text())
            elif state == Qt.Unchecked:
                remove.append(item.text())
        if remove or add:
            parent.scene().undo_stack.push(
                UndoTagModification(items, add, remove)
            )


class UndoTagModification(QtWidgets.QUndoCommand):
    def __init__(
        self, items: list[HasTags], add: list[str], remove: list[str]
    ):
        self._items = items
        self._add = add
        self._remove = remove
        super().__init__(tr("Tag Modification"))

    def redo(self) -> None:
        for item in self._items:
            for tag in self._remove:
                item.remove_tag(tag)
            for tag in self._add:
                item.add_tag(tag)
            item.update()

    def undo(self) -> None:
        for item in self._items:
            for tag in self._remove:
                item.add_tag(tag)
            for tag in self._add:
                item.remove_tag(tag)
            item.update()
