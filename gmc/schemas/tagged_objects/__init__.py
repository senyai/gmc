from __future__ import annotations
from pathlib import Path
from PyQt5 import QtCore, QtGui, QtWidgets
from collections import defaultdict
from math import hypot
from typing import Any, ClassVar
from copy import deepcopy

from .. import MarkupSchema
from ...markup_objects.polygon import EditableMarkupPolygon, MarkupObjectMeta
from ...markup_objects.quadrangle import Quadrangle
from ...markup_objects.line import MarkupLine
from ...markup_objects.point import MarkupPoint
from ...markup_objects.rect import MarkupRect
from ...markup_objects.tags import HasTags, edit_tags, UndoTagModification
from ...views.image_widget import ImageWidget
from ...utils.json import load as load_json, dump as dump_json
from ...utils.dicts import dicts_are_equal
from ...utils.image import load_pixmap
from ...utils.read_properties import read_properties, prop_schema_for_tags
from ...utils import get_icon, separator, new_action, tr, clipboard
from ...file_widgets.one_source_one_destination import OneSourceOneDestination
from ...application import GMCArguments

Qt = QtCore.Qt
MB = QtWidgets.QMessageBox


# ToDo: find better technique
class with_brush:
    """
    Mixin to assign a brush to a markup_object based on tags
    """

    _colors = {
        "forest": QtGui.QColor(173, 209, 158, 128),
        "buildings": QtGui.QColor(224, 223, 223, 128),
        "grass": QtGui.QColor(182, 227, 182, 128),
        "road": QtGui.QColor(182, 227, 182, 128),
        "concrete": QtGui.QColor(255, 0, 255, 128),
    }

    def __new__(cls, markup_object: type[HasTags]):
        assert not hasattr(markup_object, "_current_color")
        assert issubclass(markup_object, HasTags), markup_object
        markup_object._current_color = Qt.NoBrush
        if "_on_tags_changed" not in markup_object.__dict__:
            markup_object._on_tags_changed = cls.on_tags_changed
        return markup_object

    @staticmethod
    def on_tags_changed(
        self: HasTags, brushes: dict[str, QtGui.QColor] = _colors
    ) -> None:
        for tag in self._tags:
            color = brushes.get(tag)
            if color is not None:
                self._current_color = color
                break
            elif tag.startswith("color(") and tag.endswith(")"):
                color = brushes[tag] = QtGui.QColor(tag[6:-1])
                if tag[6] != "#":
                    color.setAlpha(80)
                self._current_color = color
                break
        else:
            if self._current_color is not Qt.NoBrush:
                del self._current_color
        HasTags._on_tags_changed(self)


def from_json_polygon(
    cls: type[CustomQuadrangle | CustomSegment | CustomPath],
    schema: TaggedObjects,
    data: dict[str, Any],
):
    match data:
        case {"data": points, **extra}:
            polygon = QtGui.QPolygonF(
                [QtCore.QPointF(x, y) for x, y in points]
            )
            return cls(schema, polygon, **extra)
    raise ValueError(f"incorrect {cls.__name__} `{data}`")


def from_json_point(
    cls: type[CustomPoint], schema: TaggedObjects, data: dict[str, Any]
):
    match data:
        case {"data": xy, **extra}:
            point = QtCore.QPointF(*xy)
            return cls(schema, point, **extra)
    raise ValueError(f"incorrect point `{data}`")


def from_json_rect(
    cls: type[CustomRectangle], schema: TaggedObjects, data: dict[str, Any]
):
    match data:
        case {"data": points, **extra}:
            rect = QtCore.QRectF(*points)
            return cls(schema, rect, **extra)
    raise ValueError(f"incorrect rect `{data}`")


@with_brush
class CustomQuadrangle(HasTags, Quadrangle):
    from_json = classmethod(from_json_polygon)

    def __init__(
        self, schema: TaggedObjects, frame=QtGui.QPolygonF(), **kwargs: Any
    ):
        super().__init__(frame, **kwargs)
        self._schema = schema

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionGraphicsItem,
        widget: QtWidgets.QWidget | None,
    ) -> None:
        painter.setBrush(self._current_color)
        super().paint(painter, option, widget)

    def on_created(self) -> None:
        self.setSelected(True)
        self._schema.on_object_created(self)

    def tag_pos(self) -> QtCore.QPointF:
        return self._polygon.at(1)


class CustomSegment(HasTags, MarkupLine):
    from_json = classmethod(from_json_polygon)

    def __init__(self, schema, frame=QtGui.QPolygonF(), **kwargs):
        super().__init__(frame, **kwargs)
        self._schema = schema

    def on_created(self):
        self.setSelected(True)
        self._schema.on_object_created(self)

    def tag_pos(self):
        return self._polygon[1]


class CustomLine(CustomSegment):
    CURSOR = QtGui.QCursor(QtGui.QPixmap("gmc:cursors/add_line.svg"), 6, 6)

    def paint(self, painter: QtGui.QPainter, option, widget) -> None:
        painter.setBrush(Qt.NoBrush)
        if self.isSelected():
            pen, dashed = self.PEN_SELECTED, self.PEN_SELECTED_DASHED
        else:
            pen, dashed = self.PEN, self.PEN_DASHED
        p0, p1 = self._polygon
        d = p0 - p1
        d /= hypot(d.x(), d.y())
        x_shift, y_shift = d.x() * 3e3, d.y() * 3e3
        painter.setPen(pen)
        painter.drawLine(p0, p1)
        painter.setPen(dashed)
        painter.drawLine(
            QtCore.QPointF(p0.x() + x_shift, p0.y() + y_shift),
            QtCore.QPointF(p1.x() - x_shift, p1.y() - y_shift),
        )
        super().paint(painter, option, widget)


@with_brush
class CustomPoint(HasTags, MarkupPoint):
    from_json = classmethod(from_json_point)

    def __init__(self, schema, point=QtCore.QPointF(), **kwargs):
        super().__init__(point, **kwargs)
        self._schema = schema

    def _on_tags_changed(self):
        with_brush.on_tags_changed(self)
        if self._current_color != Qt.NoBrush:
            self.PEN = QtGui.QPen(self._current_color, 4)
        else:
            self.PEN = MarkupPoint.PEN
        super()._on_tags_changed()

    def on_created(self) -> None:
        self.setSelected(True)
        self._schema.on_object_created(self)

    def tag_pos(self):
        return QtCore.QPointF()


@with_brush
class CustomRectangle(HasTags, MarkupRect):
    PEN = QtGui.QPen(Qt.GlobalColor.darkGreen, 0)
    PEN_DASHED = QtGui.QPen(Qt.GlobalColor.green, 0, Qt.PenStyle.DashLine)
    from_json = classmethod(from_json_rect)

    def __init__(self, schema, rect: QtCore.QRectF | None = None, **kwargs):
        super().__init__(rect, **kwargs)
        self._schema = schema

    def paint(self, painter: QtGui.QPainter, option, widget):
        painter.setBrush(self._current_color)
        super().paint(painter, option, widget)

    def on_created(self) -> None:
        self.setSelected(True)
        self._schema.on_object_created(self)

    def tag_pos(self):
        return self._rect.topRight()


class CustomPath(HasTags, EditableMarkupPolygon):
    from_json = classmethod(from_json_polygon)
    CURSOR = QtGui.QCursor(
        QtGui.QPixmap("gmc:cursors/add_broken_line.svg"), 6, 6
    )

    def __init__(
        self,
        schema: TaggedObjects,
        polygon: QtGui.QPolygonF | None = None,
        **kwargs: Any,
    ) -> None:
        if polygon is None:
            polygon = QtGui.QPolygonF()
        elif not isinstance(polygon, QtGui.QPolygonF):
            raise TypeError("Invalid polygon type")
        super().__init__(polygon, **kwargs)
        self._schema = schema

    def paint(self, painter: QtGui.QPainter, option, widget) -> None:
        EditableMarkupPolygon.paint(
            self, painter, option, widget, f=QtGui.QPainter.drawPolyline
        )
        self.draw_tags(painter)

    def shape(self) -> QtGui.QPainterPath:
        return EditableMarkupPolygon.shape(self, close=False)

    def tag_pos(self) -> QtCore.QPointF:
        return self._polygon[0]

    def after_creation(self):
        self._schema.on_object_created(self)


@with_brush
class CustomRegion(CustomPath):
    CURSOR = QtGui.QCursor(QtGui.QPixmap("gmc:cursors/add_region.svg"), 6, 6)

    def paint(self, painter: QtGui.QPainter, option, widget):
        painter.setBrush(self._current_color)
        EditableMarkupPolygon.paint(self, painter, option, widget)
        self.draw_tags(painter)

    def shape(self):
        return EditableMarkupPolygon.shape(self)


last_used_default_action = ""


class TaggedObjects(OneSourceOneDestination, MarkupSchema):
    _cls_to_type: ClassVar[dict[str, str]] = {
        "CustomQuadrangle": "quad",
        "CustomLine": "line",
        "CustomSegment": "seg",
        "CustomPoint": "point",
        "CustomRectangle": "rect",
        "CustomRegion": "region",
        "CustomPath": "path",
    }
    _current_root_properties: dict[str, Any] | None
    _current_properties: dict[str, Any] | None

    def __init__(self, markup_window, default_actions):
        iw = self._image_widget = ImageWidget(default_actions)
        layout = QtWidgets.QVBoxLayout(markup_window, margin=0, spacing=0)

        cat_toolbar = self._create_cat_toolbar()
        layout.addWidget(cat_toolbar)
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(iw)
        iw.on_paste.connect(self._on_paste)
        from ...views.properties_view import PropertiesView

        self._properties_view = PropertiesView()
        splitter.addWidget(self._properties_view)
        self._properties_view.property_changed.connect(self._property_changed)
        layout.addWidget(splitter)
        splitter.setSizes([1000, 300])

        self._select_action = iw.add_select_action()
        self._add_quadrangle_action = iw.add_markup_action(
            tr("Add Quadrangle"),
            "q",
            "quadrangle",
            lambda: CustomQuadrangle(self),
        )
        self._add_line_action = iw.add_markup_action(
            tr("Add Line"), "l", "line", lambda: CustomLine(self)
        )
        self._add_segment_action = iw.add_markup_action(
            tr("Add Segment"), "s", "segment", lambda: CustomSegment(self)
        )
        self._add_point_action = iw.add_markup_action(
            tr("Add Point"), ".", "point", lambda: CustomPoint(self)
        )
        self._add_rect_action = iw.add_markup_action(
            tr("Add Rectangle"), "r", "rect", lambda: CustomRectangle(self)
        )
        self._add_broken_line_action = iw.add_markup_action(
            tr("Add Broken Line"), "w", "broken_line", lambda: CustomPath(self)
        )
        self._add_region_action = iw.add_markup_action(
            tr("Add Region"), "g", "region", lambda: CustomRegion(self)
        )
        iw.add_action(separator(iw))
        self._tag_red_action = iw.add_user_action(
            tr("Tag &Red"),
            "t,r",
            "tag_red",
            enabled=False,
            checkable=True,
            triggered=lambda arg: self._trigger_tag("red", arg),
        )
        self._tag_green_action = iw.add_user_action(
            tr("Tag &Green"),
            "t,g",
            "tag_green",
            enabled=False,
            checkable=True,
            triggered=lambda arg: self._trigger_tag("green", arg),
        )
        self._tag_blue_action = iw.add_user_action(
            tr("Tag &Blue"),
            "t,b",
            "tag_blue",
            enabled=False,
            checkable=True,
            triggered=lambda arg: self._trigger_tag("blue", arg),
        )
        self._tag_yellow_action = iw.add_user_action(
            tr("Tag &Yellow"),
            "t,y",
            "tag_yellow",
            enabled=False,
            checkable=True,
            triggered=lambda arg: self._trigger_tag("yellow", arg),
        )
        self._tag_txt_action = iw.add_user_action(
            tr("Tag &Text"),
            "t,t",
            "tag_txt",
            enabled=False,
            triggered=self._trigger_tag_edit,
        )
        self._image_widget.scene().selectionChanged.connect(
            self._on_selection_changed
        )

        show_cat_act = new_action(
            markup_window,
            "cat",
            tr("Show Mad Cat Toolbar"),
            ("Ctrl+T",),
            checkable=True,
            checked=True,
            toggled=cat_toolbar.setVisible,
        )
        iw.add_action(show_cat_act)
        iw.add_default_actions()

        # so that user can go to the next file
        self._next_action = markup_window._next_action
        self._unique_cache: dict[str, tuple[QtCore.QDateTime, set[str]]] = {}

    @classmethod
    def create_data_widget(
        cls, mdi_area: QtWidgets.QMdiArea, extra_args: GMCArguments
    ):
        splitter = super().create_data_widget(mdi_area, extra_args)
        iterpolate_act = new_action(
            splitter,
            "cat",
            tr("&Interpolate"),
            (Qt.CTRL + Qt.Key_I,),
            triggered=cls._interpolate,
        )
        tags_act = new_action(
            splitter,
            "cat",
            tr("Interpolate &Tags"),
            (Qt.CTRL + Qt.ALT + Qt.Key_I,),
            triggered=lambda: cls._interpolate(True),
        )
        tags_act = new_action(
            splitter,
            "paste",
            tr("&Paste Objects"),
            (Qt.CTRL + Qt.Key_V,),
            triggered=lambda: cls._on_paste_into_files(),
        )
        cls._source_widget.view().addActions((iterpolate_act, tags_act))
        return splitter

    def _create_cat_toolbar(self) -> QtWidgets.QToolBar:
        toolbar = QtWidgets.QToolBar()
        # visibility action:
        self.tags_hidden = False
        show_tags_icon = get_icon("tag_eye_close")
        show_tags_icon.addFile("gmc:tag_eye_open.svg", state=show_tags_icon.On)
        toolbar.addAction(
            new_action(
                toolbar,
                show_tags_icon,
                tr("Toggle Tags &Visibility"),
                ("t,v",),
                checkable=True,
                toggled=self._toggle_tag_visibility,
                shortcutContext=Qt.WindowShortcut,
            )
        )
        show_items_icon = get_icon("eye_close")
        show_items_icon.addFile("gmc:eye_open.svg", state=show_items_icon.On)
        toolbar.addAction(
            new_action(
                toolbar,
                show_items_icon,
                tr("Toggle Selected &Items Visibility"),
                ("h",),
                checkable=True,
                toggled=self._toggle_visibility,
                shortcutContext=Qt.WindowShortcut,
            )
        )
        toolbar.addSeparator()
        # default actions:
        self._default_action_cb = cb = QtWidgets.QComboBox()
        default_action_label = QtWidgets.QLabel(
            tr("Default &Action:"), styleSheet="padding-left:1px"
        )
        toolbar.addWidget(default_action_label)
        toolbar.addWidget(cb)
        default_action_label.setBuddy(cb)
        for text, icon_name, data in (
            (tr("Select and Transform Objects"), "pointer", "_select_action"),
            (tr("Add Quadrangle"), "quadrangle", "_add_quadrangle_action"),
            (tr("Add Line"), "line", "_add_line_action"),
            (tr("Add Segment"), "segment", "_add_segment_action"),
            (tr("Add Point"), "point", "_add_point_action"),
            (tr("Add Rectangle"), "rect", "_add_rect_action"),
            (tr("Add Broken Line"), "broken_line", "_add_broken_line_action"),
            (tr("Add Region"), "region", "_add_region_action"),
        ):
            cb.addItem(get_icon(icon_name), text, data)
            if text == last_used_default_action:
                cb.setCurrentIndex(cb.count() - 1)
        cb.currentTextChanged.connect(self._default_action_cb_updated)
        toolbar.addSeparator()
        # default tags:
        hlp = "List of tags splitter by `,` character"
        default_tags_label = QtWidgets.QLabel(
            tr("Default &Tags:"), toolTip=hlp, styleSheet="padding-left:1px"
        )
        toolbar.addWidget(default_tags_label)
        self._default_tags_edit = QtWidgets.QLineEdit(
            maximumWidth=97, toolTip=hlp
        )
        default_tags_label.setBuddy(self._default_tags_edit)
        toolbar.addWidget(self._default_tags_edit)
        toolbar.addWidget(
            QtWidgets.QPushButton(
                tr("&Unique Tag"),
                icon=get_icon("prev"),
                clicked=self._on_unique_tag,
                shortcut="Ctrl+U",
                toolTip="Generate unique tag per directory",
            )
        )
        toolbar.addSeparator()
        # mad cat mode
        self._mad_cat_btn = QtWidgets.QPushButton(
            tr("Mad Cat Mode"),
            icon=get_icon("cat"),
            checkable=True,
            shortcut="Ctrl+M",
            toolTip="Save and switch to next frame after adding any object",
        )
        toolbar.addWidget(self._mad_cat_btn)
        return toolbar

    def _default_action_cb_updated(self, text: str):
        global last_used_default_action
        last_used_default_action = text

    @classmethod
    def _list_paths(cls) -> tuple[list[str], list[str]]:
        dst_dir = cls._destination_widget.get_root_qdir()
        relative_path = cls._source_widget.get_root_qdir().relativeFilePath
        source_view = cls._source_widget.view()
        image_paths = source_view.selected_files()
        return (
            image_paths,
            [
                dst_dir.filePath(relative_path(path) + ".json")
                for path in image_paths
            ],
        )

    @classmethod
    def _interpolate(cls, use_filter: bool = False):
        image_paths, markup_paths = cls._list_paths()
        try:
            from .markup_interpolation import interpolate_many

            interpolate_many(image_paths, markup_paths, use_filter)
        except Exception as e:
            MB.warning(cls._source_widget, tr("Can't interpolate:"), str(e))

    @classmethod
    def _on_paste_into_files(cls) -> None:
        image_paths, markup_paths = cls._list_paths()
        new_objects = clipboard.get_objects()

        def convert_to_markup(obj: dict[str, Any]):
            obj["type"] = cls._cls_to_type[obj.pop("_class")]
            return obj

        new_objects = [convert_to_markup(obj) for obj in new_objects]

        if not new_objects or not markup_paths:
            return
        question = tr("Paste {} objects into {} files?").format(
            len(new_objects), len(markup_paths)
        )
        if (
            MB.question(cls._source_widget, tr("Paste"), question)
            != MB.StandardButton.Yes
        ):
            return
        for image_path, markup_path in zip(image_paths, markup_paths):
            if Path(markup_path).exists():
                data = load_json(markup_path, cls._source_widget)
            else:
                size = load_pixmap(image_path).size()
                data = {"objects": [], "size": [size.width(), size.height()]}
            existing_objects: list[Any] = data["objects"]
            filtered_new_objects = [
                obj for obj in new_objects if obj not in existing_objects
            ]
            existing_objects.extend(filtered_new_objects)
            dump_json(markup_path, data)

    def _on_select_default_action(self, action):
        getattr(self, str(action.data())).trigger()

    def _trigger_default_action(self):
        cb = self._default_action_cb
        checked_data = cb.itemData(cb.currentIndex())
        default_action = getattr(self, str(checked_data))
        default_action.trigger()

    def on_object_created(self, obj: HasTags):
        default_tags = self._default_tags_edit.text()
        if default_tags:
            for tag in default_tags.split(","):
                obj.add_tag(tag.strip())
        if self._mad_cat_btn.isChecked() and self._next_action.isEnabled():
            self._next_action.trigger()
        else:
            self._trigger_default_action()

    def _on_unique_tag(self):
        from json import load

        qdir = QtCore.QFileInfo(self._dst_markup_path).dir()
        dir_filter = qdir.Files | qdir.NoDotAndDotDot
        all_sets: list[set[str]] = []
        cache = self._unique_cache
        for fi in qdir.entryInfoList(dir_filter, qdir.Name):
            if fi.suffix() != "json":
                continue
            last_modified = fi.lastModified()
            absolute_path = fi.absoluteFilePath()
            if absolute_path in cache:
                dt, tags = cache[absolute_path]
                if dt == last_modified:
                    all_sets.append(tags)
                    continue
            try:
                with open(absolute_path, "r") as f:
                    data = load(f)
            except Exception:
                print("invalid json", absolute_path, "(ignored)")
                continue
            tags: set[str] = set()
            for obj in data.get("objects", ()):
                tags |= set(obj.get("tags", ()))
            all_sets.append(tags)
            cache[absolute_path] = (last_modified, tags)

        all_tags: set[str] = set()
        for item in self._image_widget.scene().items():
            if isinstance(item, HasTags):
                all_tags |= item.get_tags()

        for tags in all_sets:
            all_tags |= tags

        for tag in self._alphabet_gen():
            if tag not in all_tags:
                break
        self._default_tags_edit.setText(tag)

    @staticmethod
    def _alphabet_gen():
        from string import digits, ascii_uppercase
        from itertools import product

        chars = ascii_uppercase + digits
        for n in range(1, 5):
            for comb in product(chars, repeat=n):
                yield "".join(comb)

    def _trigger_tag(self, tag: str, checked: int) -> None:
        items = self._get_selected_items()
        add, remove = [], []
        (add if checked else remove).append(tag)
        self._image_widget.scene().undo_stack.push(
            UndoTagModification(items, add, remove)
        )

    def _toggle_tag_visibility(self, state) -> None:
        self.tags_hidden = state
        self._image_widget.scene().update()

    def _toggle_visibility(self, state) -> None:
        scene = self._image_widget.scene()
        state = not state
        for item in scene.selectedItems() or scene.items():
            if isinstance(item, MarkupObjectMeta):
                item.setVisible(state)

    def _trigger_tag_edit(self) -> None:
        edit_tags(
            self._image_widget, self._get_selected_items(), self._user_tags
        )

    def _get_selected_items(self) -> list[HasTags]:
        try:
            all_items = self._image_widget.scene().selectedItems()
        except RuntimeError:
            return []  # ImageView has been destroyed
        # check for HasTags, since `MoveableDiamond` can be selected too
        return [item for item in all_items if isinstance(item, HasTags)]

    def _on_selection_changed(self) -> None:
        items = self._get_selected_items()
        enabled = bool(items)

        self._tag_red_action.setEnabled(enabled)
        self._tag_red_action.setChecked(
            all(item.has_tag("red") for item in items)
        )
        self._tag_green_action.setEnabled(enabled)
        self._tag_green_action.setChecked(
            all(item.has_tag("green") for item in items)
        )
        self._tag_blue_action.setEnabled(enabled)
        self._tag_blue_action.setChecked(
            all(item.has_tag("blue") for item in items)
        )
        self._tag_yellow_action.setEnabled(enabled)
        self._tag_yellow_action.setChecked(
            all(item.has_tag("yellow") for item in items)
        )

        self._tag_txt_action.setEnabled(enabled)
        try:
            self._update_properties(items)
        except RuntimeError:
            pass  # wrapped C/C++ object of type PropertiesView has been deleted

    def _update_properties(self, items: list[HasTags]) -> None:
        self._current_properties = None
        if not items and self._current_root_properties is not None:
            prop_schema = self._properties.get("properties", [])
            self._properties_view.set_schema(prop_schema)
            self._properties_view.set_properties(self._current_root_properties)
            self._current_properties = self._current_root_properties
        elif len(items) == 1 and (
            "objects" in self._properties or hasattr(items[0], "properties")
        ):
            if hasattr(items[0], "properties"):
                properties = items[0].properties
            else:
                properties = items[0].properties = {}
            tags = set[str].intersection(*[item.get_tags() for item in items])
            prop_schema = prop_schema_for_tags(
                self._properties.get("objects", {}), tags
            )
            self._properties_view.set_schema(prop_schema)
            self._properties_view.set_properties(properties)
            self._current_properties = properties
        else:
            self._properties_view.set_schema([])
            self._properties_view.setEnabled(False)
            return
        if (
            self._current_root_properties is not None
            or "objects" in self._properties
        ):
            self._properties_view.show()
        else:
            self._properties_view.hide()
        self._properties_view.setEnabled(True)

    def _property_changed(self, key_value: tuple[str, Any]):
        if self._current_properties is not None:
            key, value = key_value
            if value is None:
                self._current_properties.pop(key)
            else:
                self._current_properties[key] = value

    def open_markup(self, src_data_path: str, dst_markup_path: str) -> None:
        self._properties = read_properties(
            (src_data_path, dst_markup_path), self._image_widget
        )
        self._user_tags = set(self._properties.get("tags", ()))
        pixmap = load_pixmap(src_data_path)
        self._size = (pixmap.width(), pixmap.height())
        self._image_widget.set_pixmap(pixmap)

        self._dst_markup_path = dst_markup_path
        self._original_markup = {}  # for cases when 'load_json' raises
        self._original_markup = load_json(dst_markup_path, self._image_widget)
        if "properties" in self._original_markup:
            self._current_root_properties = deepcopy(
                self._original_markup["properties"]
            )
        else:
            self._current_root_properties = None
        scene = self._image_widget.scene()
        item = None
        mapping = {
            "quad": CustomQuadrangle,
            "line": CustomLine,
            "seg": CustomSegment,
            "point": CustomPoint,
            "rect": CustomRectangle,
            "path": CustomPath,
            "region": CustomRegion,
        }

        for obj in self._original_markup.get("objects", ()):
            match obj:
                case {"type": the_type, **rest}:
                    pass
                case _:
                    raise KeyError(f"invalid type for {obj!r}")
            if the_type not in mapping:
                print("ignoring unknown object type = `{}`".format(the_type))
                continue
            cls = mapping[the_type]
            item = cls.from_json(self, rest)
            scene.addItem(item)

        self._trigger_default_action()
        self._image_widget.setFocus()

        self._update_properties([])
        if item is not None:
            item.setSelected(True)
            self._on_selection_changed()

    def markup_has_changes(self) -> bool:
        return not dicts_are_equal(self._get_markup(), self._original_markup)

    def save_markup(self, force: bool = True) -> None:
        view = self._image_widget.view()

        # trick to make "Space" button to save tags
        if not self._mad_cat_btn.isChecked():
            r_event = QtGui.QMouseEvent(
                QtCore.QEvent.MouseButtonRelease,
                view.mapFromGlobal(QtGui.QCursor.pos()),
                Qt.LeftButton,
                Qt.NoButton,
                Qt.NoModifier,
            )
            view._current_mouse_release(r_event, view)
        markup = self._get_markup()
        if dicts_are_equal(markup, self._original_markup) and not force:
            print("not changed `{}`".format(self._dst_markup_path))
            return
        print("saving to", self._dst_markup_path)
        dump_json(self._dst_markup_path, markup)
        self._original_markup = markup

    def _get_markup(self) -> dict[str, Any]:
        markup = defaultdict(list, self._original_markup)
        markup["objects"] = []
        markup["size"] = self._size
        for item in self._image_widget.scene().items():
            the_type = self._cls_to_type.get(type(item).__name__)
            if the_type is None:
                continue
            data = item.data()
            assert "type" not in data
            data["type"] = the_type
            markup["objects"].append(data)
        properties = self._properties_view.get_properties()
        if properties:
            markup["properties"] = properties
        elif "properties" in markup:
            del markup["properties"]  # so we don't store old options
        return markup

    def _on_paste(self, objects) -> None:
        scene = self._image_widget.scene()
        for obj in objects:
            cls = globals().get(obj.get("_class"))
            if issubclass(cls, HasTags):
                item = cls.from_json(self, obj)
                scene.addItem(item)
