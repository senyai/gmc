from PyQt5 import QtCore, QtGui, QtWidgets
from . import MarkupSchema
from ..markup_objects.polygon import MarkupObjectMeta
from ..markup_objects.tags import HasTags, edit_tags
from ..views.image_widget import ImageWidget
from ..utils.json import load as load_json, dump as dump_json
from ..utils.dicts import dicts_are_equal
from ..utils.image import load_pixmap
from ..utils import get_icon, separator
from ..utils.svg import icon_from_data
from ..file_widgets.one_source_one_destination import OneSourceOneDestination
from ..markup_objects.rect import MarkupRect

Qt = QtCore.Qt


class CustomRectangle(HasTags, MarkupRect):
    PEN = QtGui.QPen(Qt.GlobalColor.darkGreen, 0)
    PEN_DASHED = QtGui.QPen(Qt.GlobalColor.green, 0, Qt.PenStyle.DashLine)
    # from_json = classmethod(from_json_rect)

    def __init__(self, schema, point=QtCore.QRectF(), **kwargs):
        super().__init__(point, **kwargs)
        self._schema = schema
        self._scene_rect = QtCore.QRectF(0.0, 0.0, *self._schema._size)

    def paint(self, painter: QtGui.QPainter, option, widget):
        # painter.setBrush(self._current_color)
        super().paint(painter, option, widget)

    def on_created(self) -> None:
        self.setSelected(True)
        self._schema.on_object_created(self)

    def tag_pos(self):
        return self._rect.topRight()

    def limit(self):
        self._rect = self._rect.intersected(self._scene_rect).normalized()
        self.setVisible(not self._rect.isEmpty())
        self.update()


from ..views.image_view import ImageView


class MoveHorizontally:
    def __init__(self, schema: "QuarrySchema"):
        self._schema = schema
        self._rect_items = schema.get_rect_items()
        self._originals = [ri._rect.normalized() for ri in self._rect_items]
        self._start_pos_x: float | None = None

    def attach(self, view: ImageView) -> None:
        view.setCursor(Qt.CursorShape.ArrowCursor)
        view.set_mouse_move(self.mouse_move)
        view.set_mouse_press(self.mouse_press)
        view.set_cancel(self._cancel)
        QtGui.QCursor.pos()

    def _cancel(self, view: ImageView):
        view.unset_all_events()

    def mouse_move(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        pos_x = event.pos().x()
        if self._start_pos_x is None:
            self._start_pos_x = pos_x
            return True
        diff = pos_x - self._start_pos_x
        for origin, item in zip(self._originals, self._rect_items):
            rc = QtCore.QRectF(origin)
            left_attached = rc.left() == 0.0
            right_attached = rc.right() == self._schema._size[0]
            if left_attached and not right_attached:
                rc.setWidth(rc.width() + diff)
            elif not left_attached and right_attached:
                rc.setWidth(rc.width() - diff)
                rc.moveRight(self._schema._size[0])
            elif not left_attached and not right_attached:
                rc.moveRight(rc.right() + diff)
            item._rect = rc
        for item in self._rect_items:
            item.limit()
        return True

    def mouse_press(self, event: QtGui.QMouseEvent, view: ImageView) -> bool:
        view.unset_all_events()
        self._schema.done_moving()
        return True


CABIN_ICON = icon_from_data(
    b"""<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(0 -1020)" fill="none" stroke="#000" stroke-linejoin="round" stroke-width="2">
<path d="m15.3 1046h-11.7l0.065-13.8 7.63-10.7 17.8 0.194-0.0829 24.4h-2.86"/>
<path d="m18.3 1021-0.152 9.64-13.7-0.056"/>
<circle cx="20.6" cy="1045" r="5.55" style="paint-order:stroke fill markers"/>
</g>
</svg>"""
)

EMPTY_ROAD_ICON = icon_from_data(
    b"""<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(0 -1020)" fill="none" stroke="#000" stroke-linecap="round" stroke-linejoin="round" stroke-width="2">
<path d="m1.42 1048c3.8-5.32 6.44-7.85 7.39-11.8 0.774-3.18 2.82-10.8 6.21-14.5"/>
<path d="m3.59 1049c3.8-5.32 6.44-7.85 7.39-11.8 0.774-3.18 2.82-10.8 6.21-14.5"/>
<path d="m12.7 1049c3.8-5.32 6.44-7.85 7.39-11.8 0.774-3.18 2.82-10.8 6.21-14.5"/>
<path d="m14.9 1051c3.8-5.32 6.44-7.85 7.39-11.8 0.774-3.18 2.82-10.8 6.21-14.5"/>
</g>
</svg>"""
)

FULL_BODY_ICON = icon_from_data(
    b"""<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(0 -1020)" stroke="#000">
<path d="m4.65 1037 5.29-5.87 14 0.018 4.2 5.62" fill="#d59300" stroke-width="2"/>
<path d="m15.3 1046h-11.7l0.0596-9.21 25.5-0.148-0.0829 9.36h-2.86" fill="none" stroke-linejoin="round" stroke-width="2"/>
<circle cx="20.6" cy="1045" r="5.55" fill="none" stroke-linejoin="round" stroke-width="2" style="paint-order:stroke fill markers"/>
</g>
</svg>"""
)

EMPTY_BODY_ICON = icon_from_data(
    b"""<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="translate(0 -1020)" fill="none" stroke="#000" stroke-linejoin="round" stroke-width="2">
<path d="m15.3 1046h-11.7l0.0596-9.21 25.5-0.148-0.0829 9.36h-2.86"/>
<circle cx="20.6" cy="1045" r="5.55" style="paint-order:stroke fill markers"/>
</g>
</svg>"""
)

RECT_F_ICON = icon_from_data(
    b"""<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="rotate(90 526 526)">
<path d="m3.57 1027h24.9v19.1h-24.8z" fill="none" stroke="#000" stroke-width="2"/>
</g>
<path d="m21.2 8.19h-8.21l-2.2 15.6h2.13l0.975-6.87h5.05l0.227-1.7h-5.05l0.748-5.33h5.85z"/>
</svg>"""
)

RECT_B_ICON = icon_from_data(
    b"""<svg version="1.1" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
<g transform="rotate(90 526 526)">
<path d="m3.57 1027h24.9v19.1h-24.8z" fill="none" stroke="#000" stroke-width="2"/>
</g>
<path d="m18.2 15.6c1.86-0.385 3.49-1.68 3.49-3.88 0-2.4-2.06-3.49-4.9-3.49h-4.31l-2.2 15.6h4.31c5.12 0 6.75-2.24 6.75-4.99 0-2.2-1.54-2.97-3.15-3.26zm-1.34-5.67c1.41 0 2.65 0.34 2.65 1.86 0 2.15-1.65 3.06-3.54 3.06h-2.29l0.68-4.92zm-2.18 12.2h-2.02l0.793-5.62h2.58c1.7 0 3.08 0.521 3.08 2.31 0 1.88-0.929 3.31-4.44 3.31z"/>
</svg>"""
)


class QuarrySchema(OneSourceOneDestination, MarkupSchema):
    tags_hidden = False
    _forward_enabled = False
    _last_pixmap = None

    def __init__(self, markup_window, default_actions):
        iw = self._image_widget = ImageWidget(default_actions)
        layout = QtWidgets.QVBoxLayout(markup_window, margin=0, spacing=0)
        layout.addWidget(iw)

        self._select_action = iw.add_select_action()

        for name, shortcut, tag, icon in (
            ("Add Background", "g", "background", EMPTY_ROAD_ICON),
            ("Add Cab", "c", "cab", CABIN_ICON),
            ("Add Front Edge", "1", "front_edge", RECT_F_ICON),
            ("Add Empty Body", "e", "body_empty", EMPTY_BODY_ICON),
            ("Add Full Body", "f", "body_full", FULL_BODY_ICON),
            ("Add Back Edge", "2", "back_edge", RECT_B_ICON),
        ):
            iw.add_markup_action(
                name,
                shortcut,
                icon,
                lambda tag=tag: CustomRectangle(self, tags=(tag,)),
            )
        self._move_horizontally_act = iw.add_markup_action(
            "Move horizontally",
            "k",
            "cat",
            lambda: MoveHorizontally(self),
        )
        self._start_act = iw.add_user_action(
            "Move horizontally at the start",
            ";",
            "cat",
            checkable=True,
        )

        iw.add_action(separator(iw))
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
        self._next_action = markup_window._next_action

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

    # @staticmethod
    # def pixmap_to_numpy(pixmap: QtGui.QPixmap) -> npt.NDArray[np.uint8]:
    #     img = pixmap.toImage().convertToFormat(QtGui.QImage.Format.Format_BGR888)

    #     class numpy_holder:
    #         __array_interface__ = {
    #             'data': (int(img.constBits()), False),
    #             'strides': (img.bytesPerLine(), 3, 1),
    #             'typestr': 'u1',
    #             'shape': (img.height(), img.width(), 3)}
    #     return np.array(numpy_holder(), copy=True)

    def open_markup(self, src_data_path: str, dst_markup_path: str) -> None:
        file_info = QtCore.QFileInfo(src_data_path)
        src_dir = file_info.dir()
        try:
            with open(src_dir.absoluteFilePath("tags.txt"), "r") as f:
                self._user_tags = set(
                    filter(None, (line.strip() for line in f))
                )
        except IOError:
            self._user_tags: set[str] = {
                "background", "cab", "front_edge",
                "body_empty", "body_full", "back_edge"}

        pixmap = load_pixmap(src_data_path)
        self._size = (pixmap.width(), pixmap.height())
        self._image_widget.set_pixmap(pixmap)

        self._dst_markup_path = dst_markup_path
        previous_markup = getattr(self, "_original_markup", None)
        self._original_markup = {}  # for cases when 'load_json' raises
        markup = self._original_markup = load_json(
            dst_markup_path, self._image_widget
        )
        if (
            "objects" not in markup
            and previous_markup
            and "objects" in previous_markup
        ):
            if type(markup) is not dict:
                markup = {"size": self._size}
            markup["objects"] = previous_markup["objects"].copy()
        scene = self._image_widget.scene()
        item = None
        for obj in markup.get("objects", ()):
            the_type = obj["type"]
            if the_type == "rect":
                cls, args = CustomRectangle, (QtCore.QRectF(*obj["data"]),)
            else:
                print("invalid object type = `{}`".format(the_type))
            item = cls(self, *args, tags=obj.get("tags", ()))
            scene.addItem(item)

        self._image_widget.setFocus()
        self._select_action.trigger()

        if item is not None:
            item.setSelected(True)
        if self._start_act.isChecked():
            self._move_horizontally_act.trigger()

    def on_object_created(self, rect_item: CustomRectangle):
        rect_item.limit()
        self._select_action.trigger()

    def markup_has_changes(self) -> bool:
        return not dicts_are_equal(self._get_markup(), self._original_markup)

    def get_rect_items(self) -> list[CustomRectangle]:
        return [
            item
            for item in self._image_widget.scene().items()
            if isinstance(item, CustomRectangle)
        ]

    def _get_markup(self):
        markup = {**self._original_markup, "size": self._size, "objects": []}
        for item in self.get_rect_items():
            if not item.isVisible():
                continue  # hidden by `limit`
            data = item.data()
            assert "type" not in data
            data["type"] = "rect"
            markup["objects"].append(data)
        return markup

    def save_markup(self, force=True):
        markup = self._get_markup()
        if dicts_are_equal(markup, self._original_markup) and not force:
            print("not changed `{}`".format(self._dst_markup_path))
            return
        print("saving to", self._dst_markup_path)
        dump_json(self._dst_markup_path, markup)
        self._original_markup = markup

    def done_moving(self):
        print("done_moving")
