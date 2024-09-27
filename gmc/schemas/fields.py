from PyQt5 import QtCore, QtGui, QtWidgets
from collections import defaultdict
from . import MarkupSchema
from ..markup_objects.polygon import EditableMarkupPolygon, MarkupObjectMeta
from ..markup_objects.tags import HasTags, edit_tags
from ..views.image_widget import ImageWidget
from ..utils.json import load as load_json, dump as dump_json
from ..utils.dicts import dicts_are_equal
from ..utils.svg import icon_from_data
from ..utils.image import load_pixmap
from ..utils import get_icon, separator
from ..file_widgets.one_source_one_destination import OneSourceOneDestination

Qt = QtCore.Qt


BASE_PEN = QtGui.QPen(Qt.white, 2)
BASE_PEN_DASHED = QtGui.QPen(Qt.darkGreen, 2, Qt.DashLine)
BASE_PEN_SELECTED = QtGui.QPen(Qt.yellow, 2)
BASE_PEN_SELECTED_DASHED = QtGui.QPen(Qt.blue, 2, Qt.DashLine)


def paint(self, painter, f=QtGui.QPainter.drawPolygon):
    if self._base:
        if self.isSelected():
            pen, dashed = BASE_PEN_SELECTED, BASE_PEN_SELECTED_DASHED
        else:
            pen, dashed = BASE_PEN, BASE_PEN_DASHED
    else:
        if self.isSelected():
            pen, dashed = self.PEN_SELECTED, self.PEN_SELECTED_DASHED
        else:
            pen, dashed = self.PEN, self.PEN_DASHED
    painter.setPen(pen)
    f(painter, self._polygon)
    painter.setPen(dashed)
    f(painter, self._polygon)
    painter.setPen(Qt.blue)


class CustomPath(HasTags, EditableMarkupPolygon):
    def __init__(self, schema, base: bool, polygon=None, **kwargs):
        assert isinstance(base, bool), type(base)
        if polygon is None:
            polygon = QtGui.QPolygonF()
        elif not isinstance(polygon, QtGui.QPolygonF):
            raise TypeError("Invalid polygon type")
        super().__init__(polygon, **kwargs)
        self._schema = schema
        self._base = base

    def paint(self, painter, option, widget):
        paint(self, painter, f=QtGui.QPainter.drawPolyline)
        self.draw_tags(painter)

    def shape(self):
        return EditableMarkupPolygon.shape(self, close=False)

    def tag_pos(self):
        return self._polygon[0]

    def after_creation(self):
        if self._base:
            self._schema._add_m_broken_line_action.trigger()
        else:
            self._schema._add_broken_line_action.trigger()

    def is_base(self):
        return self._base

    def toggle_base(self):
        self._base = not self._base
        self.update()


class CustomRegion(CustomPath):
    _brushes = {}

    def paint(self, painter, option, widget, brushes=_brushes):
        for tag in self._tags:
            color = brushes.get(tag)
            if color is not None:
                painter.setBrush(color)
                break
            elif tag.startswith("color(") and tag.endswith(")"):
                color = brushes[tag] = QtGui.QColor(tag[6:-1])
                if tag[6] != "#":
                    color.setAlpha(80)
                painter.setBrush(color)
                break
        paint(self, painter)
        self.draw_tags(painter)

    def shape(self):
        return EditableMarkupPolygon.shape(self)

    def after_creation(self):
        if self._base:
            self._schema._add_m_region_action.trigger()
        else:
            self._schema._add_region_action.trigger()


BROKEN_LINE_ICON = icon_from_data(
    b"""\
<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(0 -1020.4)">
<path d="m4.8537 1024.7 22.27.7174-3.2287 7.3763-17.925 8.5381 19.116 6.83"
fill="none" stroke="#09640d" stroke-width="3"/></g></svg>"""
)
REGION_ICON = icon_from_data(
    b"""\
<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="rotate(90 526.19 526.23)"><path d="m27.124 1025.4-2.1586
22.654-10.904-1.5724-.47259-12.847-10.531-.023-.42544-8.341z" fill="#999"
stroke="#09640d" stroke-width="3"/></g></svg>"""
)
SWAP_ICON = icon_from_data(
    b"""\
<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="matrix(.34 0 0 .33296 4.5092 -321.53)" stroke-width="2.9721">
<path d="m4.8537 1024.7 22.27.7174-3.2287 7.3763-17.925 8.5381 19.116 6.83" fill="none" stroke="#09640d" stroke-width="8.9164"/>
</g>
<path d="m20.159 3.5609 7.5718.23886-1.0978 2.456-6.0945 2.8428 6.4994 2.2741" fill="none" stroke="#010701" stroke-width="2"/>
<path d="m16.58 4.4023-10.73.039062 3.1504 1.7266c-1.0278.36595-1.9375.94202-2.6602 1.7695-1.3281 1.5209-2.0008 3.8127-1.8164 6.9297l1-.058594c-.17434-2.9465.45762-4.9429 1.5684-6.2148.54214-.62084 1.2085-1.0804 1.9785-1.3945l-1.6016 2.8711 9.1113-5.668z" fill-opacity=".75294" fill-rule="evenodd"/>
<path d="m15.298 27.225 10.73-.03906-3.1504-1.7266c1.0278-.36596 1.9375-.94202 2.6602-1.7695 1.3281-1.5209 2.0008-3.8127 1.8164-6.9297l-1 .05859c.17434 2.9465-.45762 4.9429-1.5684 6.2148-.54214.62084-1.2085 1.0804-1.9785 1.3945l1.6016-2.8711z" fill-opacity=".75294" fill-rule="evenodd"/>
</svg>
"""
)


class FieldsSchema(OneSourceOneDestination, MarkupSchema):
    tags_hidden = False

    def __init__(self, markup_window, default_actions):
        iw = self._image_widget = ImageWidget(default_actions)
        layout = QtWidgets.QVBoxLayout(markup_window, margin=0, spacing=0)
        layout.addWidget(iw)

        self._select_action = iw.add_select_action()
        self._add_broken_line_action = iw.add_markup_action(
            "Add Broken Line",
            "e",
            "broken_line",
            lambda: CustomPath(self, False),
        )
        self._add_region_action = iw.add_markup_action(
            "Add Region", "d", "region", lambda: CustomRegion(self, False)
        )

        iw.add_action(separator(iw))
        self._add_m_broken_line_action = iw.add_markup_action(
            "Add Broken Line",
            "w",
            BROKEN_LINE_ICON,
            lambda: CustomPath(self, True),
        )
        self._add_m_region_action = iw.add_markup_action(
            "Add Region", "s", REGION_ICON, lambda: CustomRegion(self, True)
        )

        iw.add_action(separator(iw))
        self._swap_action = iw.add_user_action(
            "Change Object Type",
            "b",
            SWAP_ICON,
            enabled=False,
            triggered=self._swap,
        )
        self._tag_txt_action = iw.add_user_action(
            "Tag &Text",
            "t,t",
            "tag_txt",
            enabled=False,
            triggered=self._trigger_tag_edit,
        )
        self._image_widget.scene().selectionChanged.connect(
            self._on_selection_changed
        )

        show_tags_icon = get_icon("tag_eye_close")
        show_tags_icon.addFile("gmc:tag_eye_open.svg", state=show_tags_icon.On)
        iw.add_user_action(
            "Toggle Tags &Visibility",
            "t,v",
            show_tags_icon,
            checkable=True,
            toggled=self._toggle_tag_visibility,
        )

        show_items_icon = get_icon("eye_close")
        show_items_icon.addFile("gmc:eye_open.svg", state=show_items_icon.On)
        iw.add_user_action(
            "Toggle Selected &Items Visibility",
            "h",
            show_items_icon,
            checkable=True,
            toggled=self._toggle_visibility,
        )

        iw.add_default_actions()
        self._select_action.trigger()
        self._next_action = markup_window._next_action
        self._unique_cache = {}

    def _on_select_default_action(self, action):
        getattr(self, str(action.data())).trigger()

    def _toggle_tag_visibility(self, state):
        self.tags_hidden = state
        self._image_widget.scene().update()

    def _toggle_visibility(self, state):
        scene = self._image_widget.scene()
        state = not state
        for item in scene.selectedItems() or scene.items():
            if isinstance(item, MarkupObjectMeta):
                item.setVisible(state)

    def _trigger_tag_edit(self):
        edit_tags(
            self._image_widget, self._get_selected_items(), self._user_tags
        )

    def _swap(self):
        for item in self._get_selected_items():
            if isinstance(item, HasTags):
                item.toggle_base()

    def _get_selected_items(self):
        try:
            all_items = self._image_widget.scene().selectedItems()
        except RuntimeError:
            return []  # ImageView has been destroyed
        # check for HasTags, since `MoveableDiamond` can be selected too
        return [item for item in all_items if isinstance(item, HasTags)]

    def _on_selection_changed(self):
        items = self._get_selected_items()
        enabled = bool(items)
        self._tag_txt_action.setEnabled(enabled)
        self._swap_action.setEnabled(enabled)

    def open_markup(self, src_data_path: str, dst_markup_path: str) -> None:
        src_dir = QtCore.QFileInfo(src_data_path).dir()
        try:
            with open(src_dir.absoluteFilePath("tags.txt"), "r") as f:
                self._user_tags = set(
                    filter(None, (line.strip() for line in f))
                )
        except IOError:
            self._user_tags: set[str] = set()

        pixmap = load_pixmap(src_data_path)
        self._size = (pixmap.width(), pixmap.height())
        self._image_widget.set_pixmap(pixmap)

        self._dst_markup_path = dst_markup_path
        dst_dir = QtCore.QFileInfo(dst_markup_path).dir()
        self._dst_main_path = dst_dir.absoluteFilePath("base.json")
        self._original_markup = (
            load_json(self._dst_main_path, self._image_widget),
            load_json(dst_markup_path, self._image_widget),
        )
        scene = self._image_widget.scene()
        item = None
        for obj in self._original_markup[0].get("objects", ()):
            the_type = obj["type"]
            if the_type == "path":
                cls, args = CustomPath, (
                    True,
                    QtGui.QPolygonF(
                        [QtCore.QPointF(x, y) for x, y in obj["data"]]
                    ),
                )
            elif the_type == "region":
                cls, args = CustomRegion, (
                    True,
                    QtGui.QPolygonF(
                        [QtCore.QPointF(x, y) for x, y in obj["data"]]
                    ),
                )
            else:
                print("invalid object type = `{}`".format(the_type))
            item = cls(self, *args, tags=obj.get("tags", ()))
            scene.addItem(item)
        for obj in self._original_markup[1].get("objects", ()):
            the_type = obj["type"]
            if the_type == "path":
                cls, args = CustomPath, (
                    False,
                    QtGui.QPolygonF(
                        [QtCore.QPointF(x, y) for x, y in obj["data"]]
                    ),
                )
            elif the_type == "region":
                cls, args = CustomRegion, (
                    False,
                    QtGui.QPolygonF(
                        [QtCore.QPointF(x, y) for x, y in obj["data"]]
                    ),
                )
            else:
                print("invalid object type = `{}`".format(the_type))
            item = cls(self, *args, tags=obj.get("tags", ()))
            scene.addItem(item)

        self._image_widget.setFocus()

        if item is not None:
            item.setSelected(True)

    def markup_has_changes(self):
        return not dicts_are_equal(self._get_markup(), self._original_markup)

    def save_markup(self, force=True):
        markup = self._get_markup()
        if dicts_are_equal(markup, self._original_markup) and not force:
            print("not changed `{}`".format(self._dst_markup_path))
            return
        markup_main, markup = markup
        print("saving to", self._dst_main_path)
        dump_json(self._dst_main_path, markup_main)
        print("saving to", self._dst_markup_path)
        dump_json(self._dst_markup_path, markup)
        self._original_markup = markup

    def _get_markup(self):
        markup_main = defaultdict(list, self._original_markup[0])
        markup_main["objects"] = []
        markup = defaultdict(list, self._original_markup[1])
        markup["objects"] = []
        markup_main["size"] = self._size
        for item in self._image_widget.scene().items():
            if isinstance(item, CustomRegion):
                the_type = "region"
                where = markup_main if item.is_base() else markup
            elif isinstance(item, CustomPath):
                the_type = "path"
                where = markup_main if item.is_base() else markup
            else:
                continue
            data = item.data()
            assert "type" not in data
            data["type"] = the_type
            where["objects"].append(data)
        return markup_main, markup
