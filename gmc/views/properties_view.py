from __future__ import annotations
from typing import Any, TypeVar, TYPE_CHECKING
from PyQt5 import QtCore, QtWidgets, QtGui
from ..utils import get_icon, tr
from json import loads, dumps

if TYPE_CHECKING:
    from ..utils.read_properties import GMCProps, BoolProp

Qt = QtCore.Qt


def _check_state(
    value: bool | None,
    checked: Qt.CheckState = Qt.CheckState.Checked,
    unchecked: Qt.CheckState = Qt.CheckState.Unchecked,
    partially: Qt.CheckState = Qt.CheckState.PartiallyChecked,
) -> Qt.CheckState:
    return checked if value else (partially if value is None else unchecked)


class BaseItem:
    parent: BaseItem
    children: list[BaseItem]

    def row_count(self) -> int:
        return len(self.children)

    def index(self, model: PropertiesModel, column: int) -> QtCore.QModelIndex:
        if self is model.root:
            return QtCore.QModelIndex()
        return model.createIndex(self.row(), column, self)

    def row(self) -> int:
        try:
            return self.parent.children.index(self)
        except ValueError:
            print("PARENT'S CHILDREN!!", self, self.parent)
            for child in self.parent.children:
                print("   >", child)
            raise

    def delete(self) -> None:
        position = self.row()
        model = self.get_model()
        model.removeRows(position, 1, self.parent.index(model, 0))

    def insert(
        self, model: PropertiesModel, items: list[BaseItem], idx: int = -1
    ):
        total = len(items)
        first = len(self.children) if idx == -1 else idx
        last = first + total - 1

        index = self.index(model, 0)
        model.beginInsertRows(index, first, last)
        if idx == -1:
            self.children.extend(items)
        else:
            self.children[idx:idx] = items
        model.endInsertRows()

    def get_model(self) -> PropertiesModel:
        item = self
        while not hasattr(item, "model"):
            item = item.parent
        return item.model

    def __repr__(self) -> str:
        # to shorten the representation
        return f"<{self.__class__.__name__} at 0x{id(self):x}>"


class RootItem(BaseItem):
    def __init__(self, model: PropertiesModel):
        self.model = model
        self.children = []


class PropertyItemBase(BaseItem):
    """
    Base class for all properties
    """

    has_children = False
    flags = (
        Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
        | Qt.ItemFlag.ItemIsEditable
    )

    def __init__(self, parent: BaseItem, prop: dict[str, str | int]) -> None:
        self.parent = parent
        match prop:
            case {"name": name, **kwargs}:
                self.name = name
            case _:
                raise ValueError(f"'name' field is required `{prop}`")
        self._display_name = kwargs.pop("display", self.name)
        self._kwargs = kwargs
        parent.insert(parent.get_model(), items=[self])

    @property
    def display_role0(self) -> str:
        return self._display_name

    @property
    def display_role1(self) -> str:
        """common method"""
        return str(self._value)

    def set_editor_value(
        self,
        widget: (
            QtWidgets.QDoubleSpinBox
            | QtWidgets.QCheckBox
            | QtWidgets.QLineEdit
        ),
        index: QtCore.QModelIndex,
    ) -> None:
        """common method"""
        widget.setValue(index.data(Qt.ItemDataRole.EditRole))

    def edit_role(self) -> str | int | bool:
        """common method"""
        return self._value

    @property
    def value(self) -> str | int | bool | list[str]:
        """common method; value to return as property"""
        return self._value

    def set_edit(self, value: str | int | bool) -> None:
        """common method"""
        self._value = value

    def emit(self) -> tuple[str, Any]:
        return (self.name, self.value)


TWidget = TypeVar("TWidget", bound=QtWidgets.QWidget)


def _apply_kwargs(widget: TWidget, kwargs: dict[str, Any]) -> TWidget:
    for key, val in kwargs.items():
        attr = "set" + key.capitalize()
        getattr(widget, attr)(val)
    return widget


class IntegerItem(PropertyItemBase):
    def __init__(self, parent: BaseItem, kwargs: dict[str, Any]) -> None:
        self._value = kwargs.pop("value", 0)
        super().__init__(parent, kwargs)

    def create_widget(self, parent: QtWidgets.QWidget) -> QtWidgets.QSpinBox:
        return _apply_kwargs(QtWidgets.QSpinBox(parent), self._kwargs)


class FloatItem(PropertyItemBase):
    def __init__(self, parent: BaseItem, kwargs: dict[str, Any]) -> None:
        self._value = kwargs.pop("value", 0.0)
        kwargs.setdefault("decimals", 6)
        super().__init__(parent, kwargs)

    def create_widget(
        self, parent: QtWidgets.QWidget
    ) -> QtWidgets.QDoubleSpinBox:
        return _apply_kwargs(QtWidgets.QDoubleSpinBox(parent), self._kwargs)


class BoolItem(PropertyItemBase):
    """
    Item with a single checkbox
    """

    display_role1 = None
    flags = (
        Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
        | Qt.ItemFlag.ItemIsEditable
        | Qt.ItemFlag.ItemIsUserCheckable
    )

    def __init__(self, parent: SetItem | RootItem, kwargs: dict[str, object]):
        self._value = kwargs.get("value", None)
        super().__init__(parent, kwargs)

    def create_widget(self, parent: QtWidgets.QWidget):
        return None

    def set_editor_value(
        self, widget: QtWidgets.QCheckBox, index: QtCore.QModelIndex
    ) -> None:
        edit_data = index.data(Qt.ItemDataRole.EditRole)
        widget.setCheckState(_check_state(edit_data))

    def emit(self) -> tuple[str, Any]:
        if isinstance(self.parent, SetItem):
            return self.parent.emit()
        return super().emit()


class StringItem(PropertyItemBase):
    def __init__(self, parent: BaseItem, kwargs: dict[str, Any]) -> None:
        self._value = kwargs.pop("value", "")
        super().__init__(parent, kwargs)

    def create_widget(self, parent: QtWidgets.QWidget):
        return _apply_kwargs(QtWidgets.QLineEdit(parent), self._kwargs)

    def set_editor_value(
        self, widget: QtWidgets.QLineEdit, index: QtCore.QModelIndex
    ):
        widget.setText(index.data(Qt.ItemDataRole.EditRole))


class UserItem(PropertyItemBase):
    flags = Qt.ItemFlag.ItemIsEnabled

    def __init__(self, parent: BaseItem, kwargs: dict[str, Any]) -> None:
        self._value = kwargs["value"]
        super().__init__(parent, kwargs)

    def create_widget(self, parent: QtWidgets.QWidget):
        pass

    def set_editor_value(
        self, widget: QtWidgets.QLineEdit, index: QtCore.QModelIndex
    ):
        pass


class RadioItem(PropertyItemBase):
    display_role1 = None
    flags = (
        Qt.ItemFlag.ItemIsEnabled
        | Qt.ItemFlag.ItemIsSelectable
        | Qt.ItemFlag.ItemIsEditable
        | Qt.ItemFlag.ItemIsUserCheckable
    )

    def __init__(
        self, parent: SingleItem, kwargs: dict[str, str], checked: bool
    ):
        super().__init__(parent, kwargs)
        self._value = checked

    def create_widget(self, parent: QtWidgets.QWidget):
        return None

    def set_edit(self, value: bool) -> None:
        self._value = value
        if value:
            model = self.get_model()
            for item in self.parent.children:
                if item is self:
                    continue
                item._value = False
                index = item.index(model, 1)
                model.dataChanged.emit(index, index)
        else:
            # disallow selecting none of the items
            if not any(item._value for item in self.parent.children):
                self._value = True

    def set_editor_value(
        self, widget: QtWidgets.QCheckBox, index: QtCore.QModelIndex
    ):
        edit_data = index.data(Qt.ItemDataRole.EditRole)
        widget.setCheckState(_check_state(edit_data))

    def emit(self) -> tuple[str, Any]:
        return (self.parent.name, self.name)


class SingleItem(PropertyItemBase):
    """
    List of radios
    """

    display_role1 = None
    has_children = True
    flags = Qt.ItemFlag.ItemIsSelectable

    def __init__(self, parent: BaseItem, kwargs: dict[str, Any]) -> None:
        self.children: list[RadioItem] = []
        items = kwargs["items"]
        assert items
        self._value = kwargs.pop("value", None)  # None to indicate lazy user
        super().__init__(parent, kwargs)
        for item in items:
            name = item["name"]
            RadioItem(self, item, checked=name == self._value)

    def set_edit(self, value: str) -> None:
        for item in self.children:
            item.set_edit(item.name == value)

    @property
    def value(self) -> str | None:
        for item in self.children:
            if item._value:
                return item.name


class SetItem(PropertyItemBase):
    display_role1 = None
    has_children = True
    flags = Qt.ItemFlag.ItemIsSelectable

    def __init__(self, parent: BaseItem, kwargs: dict[str, Any]) -> None:
        self.children: list[BoolItem] = []
        items = kwargs["items"]
        assert items
        self._value = set(kwargs.pop("value", set()))
        super().__init__(parent, kwargs)
        for item in items:
            item["value"] = item["name"] in self._value
            BoolItem(self, item)

    def set_edit(self, value: list[str]) -> None:
        for item in self.children:
            item.set_edit(item.name in value)

    @property
    def value(self) -> list[str]:
        return [item.name for item in self.children if item._value]


class SeparatorItem(BaseItem):
    has_children = False
    flags = Qt.ItemFlag.ItemNeverHasChildren
    display_role0 = display_role1 = None

    def __init__(self, parent: BaseItem) -> None:
        self.parent = parent


class PropertiesModel(QtCore.QAbstractItemModel):
    headers = (tr("Property"), tr("Value"))
    property_changed = QtCore.pyqtSignal(tuple, name="property_changed")

    def __init__(self):
        super().__init__()
        self.root = RootItem(self)

    def rowCount(self, parent: QtCore.QModelIndex) -> int:
        return self._get_item(parent).row_count()

    def index(
        self, row: int, column: int, parent: QtCore.QModelIndex
    ) -> QtCore.QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()
        try:
            return self._get_item(parent).children[row].index(self, column)
        except Exception as e:
            print("AAAAA", self._get_item(parent).children)
            raise e

    def parent(self, index: QtCore.QModelIndex) -> QtCore.QModelIndex:
        if not index.isValid():
            return QtCore.QModelIndex()
        parent_item = index.internalPointer().parent
        return parent_item.index(self, 0)

    def data(self, index: QtCore.QModelIndex, role: int):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            item = index.internalPointer()
            if index.column() == 0:
                return item.display_role0
            else:
                return item.display_role1
        if role == Qt.EditRole:
            item = index.internalPointer()
            return item.edit_role()
        if role == Qt.CheckStateRole:
            item = index.internalPointer()
            if isinstance(item, (BoolItem, RadioItem)) and index.column() == 1:
                return _check_state(item.edit_role())
            return
        if role == Qt.UserRole:
            return index.internalPointer()

    def setData(
        self, index: QtCore.QModelIndex, value: Any, role: Qt.ItemDataRole
    ) -> bool:
        if role == Qt.EditRole:
            item = index.internalPointer()
            item.set_edit(value)
        elif role == Qt.CheckStateRole:
            item = index.internalPointer()
            value = value == Qt.CheckState.Checked
            item.set_edit(value)
        else:
            assert False, f"Invalid role=`{role}`"
        self.dataChanged.emit(index, index)
        self.property_changed.emit(item.emit())
        return True

    def flags(self, index: QtCore.QModelIndex):
        return index.internalPointer().flags

    def hasChildren(self, parent: QtCore.QModelIndex) -> bool:
        if not parent.isValid():
            return True
        item = parent.internalPointer()
        return bool(item.has_children and len(item.children))

    def columnCount(self, parent: QtCore.QModelIndex) -> int:
        return len(self.headers)

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]

    def removeRows(
        self,
        row: int,
        count: int,
        parent: QtCore.QModelIndex = QtCore.QModelIndex(),
    ) -> bool:
        parent_item = self._get_item(parent)
        self.beginRemoveRows(parent, row, row + count - 1)
        for item in parent_item.children[row : row + count]:
            self.property_changed.emit((item.emit()[0], None))
        del parent_item.children[row : row + count]
        self.endRemoveRows()
        self.dataChanged.emit(parent, parent)
        return True

    def _get_item(self, index: QtCore.QModelIndex):
        if index.isValid():
            return index.internalPointer()
        return self.root

    def _create_item(self, prop: GMCProps) -> int | None:
        """
        inserts item into the tree

        returns item row, that indicates that items spans
        """
        root = self.root
        match prop:
            case {"type": "separator", **extra}:
                if extra:
                    raise TypeError(f"excess attributes `{prop}`")
                SeparatorItem(self.root)
            case {"type": "bool", **extra}:
                BoolItem(root, extra)
            case {"type": "float", **extra}:
                FloatItem(root, extra)
            case {"type": "int", **extra}:
                IntegerItem(root, extra)
            case {"type": "item", **extra}:
                return SingleItem(root, extra).row()
            case {"type": "set", **extra}:
                return SetItem(root, extra).row()
            case {"type": "str", **extra}:
                StringItem(root, extra)
            case {"type": "user", **extra}:
                UserItem(root, extra)
            case _:
                raise ValueError(f"unsupported type `{prop}`")

    def set_schema(self, schema: list[GMCProps]):
        self.beginResetModel()
        del self.root.children[:]
        self.endResetModel()

        for prop in schema:
            span_row = self._create_item(prop)
            if span_row is not None:
                yield span_row

    def set_properties(self, properties: dict[str, Any]):
        current_items = {
            prop.name: prop
            for prop in self.root.children
            if not type(prop) is SeparatorItem
        }
        extra: list[str] = []
        for name, value in properties.items():
            if name in current_items:
                item = current_items[name]
                item.set_edit(value)
            else:
                extra.append(name)
        for name in extra:
            value = properties[name]
            type_name = (
                type(value).__name__
                if type(value) in (int, str, float, bool)
                else "user"
            )
            self._create_item(
                {
                    "type": type_name,
                    "name": name,
                    "value": value,
                }
            )

    def get_properties(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        for child in self.root.children:
            if isinstance(child, SeparatorItem):
                continue
            properties[child.name] = child.value
        return properties


class ValueDelegate(QtWidgets.QItemDelegate):
    size = QtWidgets.QSpinBox().minimumSizeHint()

    def createEditor(
        self, parent: QtWidgets.QWidget, option, index: QtCore.QModelIndex
    ) -> QtWidgets.QWidget:
        item = index.internalPointer()
        assert isinstance(item, PropertyItemBase), item
        return item.create_widget(parent)

    def setEditorData(
        self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex
    ):
        item = index.internalPointer()
        item.set_editor_value(editor, index)

    def setModelData(
        self,
        editor: QtWidgets.QWidget,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        if isinstance(editor, QtWidgets.QComboBox):
            value = editor.currentData()
            model.setData(index, value, Qt.ItemDataRole.EditRole)
        else:
            super().setModelData(editor, model, index)

    def sizeHint(self, option, index: QtCore.QModelIndex) -> QtCore.QSize:
        item = index.internalPointer()
        if isinstance(item, PropertyItemBase):
            return self.size
        return super().sizeHint(option, index)

    def paint(
        self, painter: QtGui.QPainter, option, index: QtCore.QModelIndex
    ):
        self._is_radio = isinstance(index.internalPointer(), RadioItem)
        return super().paint(painter, option, index)

    def drawCheck(
        self, painter: QtGui.QPainter, option, rect: QtCore.QRect, state
    ):
        if not rect.isValid():
            return
        widget = option.widget
        style = widget.style()

        opt = QtWidgets.QStyleOptionViewItem(option)
        opt.rect = rect
        opt.state = opt.state & ~style.State_HasFocus

        if state == Qt.Unchecked:
            opt.state |= style.State_Off
        elif state == Qt.PartiallyChecked:
            opt.state |= style.State_NoChange
        elif state == Qt.Checked:
            opt.state |= style.State_On
        style.drawPrimitive(
            (
                style.PE_IndicatorRadioButton
                if self._is_radio
                else style.PE_IndicatorViewItemCheck
            ),
            opt,
            painter,
            widget,
        )


class PropertiesView(QtWidgets.QTreeView):
    def __init__(self) -> None:
        super().__init__(
            objectName="properties_tree_view",
            selectionMode=QtWidgets.QAbstractItemView.ExtendedSelection,
            selectionBehavior=QtWidgets.QAbstractItemView.SelectRows,
            frameShape=self.WinPanel,
            contextMenuPolicy=Qt.ActionsContextMenu,
            allColumnsShowFocus=True,
            rootIsDecorated=False,  #  Hides the expand/collapse arrows
            itemsExpandable=False,  # Disables expanding/collapsing entirely
            styleSheet="QTreeView::item{color: palette(text);}",
            editTriggers=(
                self.DoubleClicked | self.SelectedClicked | self.EditKeyPressed
            ),
        )
        self.setColumnWidth(0, 150)
        self.setItemDelegateForColumn(1, ValueDelegate(self))

        self._del_act = QtWidgets.QAction(
            get_icon("delete"),
            tr("Delete"),
            self,
            triggered=self._on_delete,
            enabled=False,
            shortcutContext=Qt.WidgetShortcut,
            shortcut=Qt.Key_Delete,
        )
        add_act = QtWidgets.QAction(
            get_icon("new"),
            tr("Add Property"),
            self,
            triggered=self._on_add,
            shortcutContext=Qt.WidgetShortcut,
            shortcut=Qt.Key_Plus,
        )
        self._copy_act = QtWidgets.QAction(
            get_icon("copy"),
            tr("Copy"),
            self,
            triggered=self._on_copy,
            shortcutContext=Qt.WidgetShortcut,
            shortcut=QtGui.QKeySequence.StandardKey.Copy,
        )
        paste_act = QtWidgets.QAction(
            get_icon("paste"),
            tr("Paste"),
            self,
            triggered=self._on_paste,
            shortcutContext=Qt.WidgetShortcut,
            shortcut=QtGui.QKeySequence.StandardKey.Paste,
        )
        for act in self._del_act, add_act, self._copy_act, paste_act:
            self.addAction(act)
        self._model = PropertiesModel()
        self.setModel(self._model)

    @property
    def property_changed(self):
        return self._model.property_changed

    def _on_add(self):
        name, ok = QtWidgets.QInputDialog.getText(
            self, tr("Add Property"), tr("Name")
        )
        if name and ok:
            item, ok = QtWidgets.QInputDialog.getItem(
                self,
                tr("Add Property"),
                tr("Type"),
                ("Bool", "Float", "Int", "String"),
            )
            if ok:
                the_type = {
                    "Bool": "bool",
                    "Float": "float",
                    "Int": "int",
                    "String": "str",
                }[item]
                self._model._create_item(
                    {
                        "type": the_type,
                        "name": name,
                    }
                )

    def _on_copy(self):
        items = {}
        for index in self.selectedIndexes():
            item = index.internalPointer()
            if index.column() == 0:
                key, value = item.emit()
                items[key] = value
        mime_data = QtCore.QMimeData()
        mime_data.setData("application/gmc-json-prop", dumps(items).encode())
        QtWidgets.QApplication.clipboard().setMimeData(mime_data)

    def _on_paste(self):
        data = (
            QtWidgets.QApplication.clipboard()
            .mimeData()
            .data("application/gmc-json-prop")
        )
        if not data:
            return
        properties = loads(data.data())
        self._model.set_properties(properties)

    def _on_delete(self) -> None:
        """
        There's `Delete` option in context menu
        """
        items = [
            index.internalPointer()
            for index in self.selectedIndexes()
            if index.column() == 0
        ]
        for item in items:
            item.delete()

    def selectionChanged(
        self,
        selected: QtCore.QItemSelection,
        deselected: QtCore.QItemSelection,
    ) -> None:
        super().selectionChanged(selected, deselected)
        has_selection = bool(self.selectedIndexes())
        self._del_act.setEnabled(has_selection)
        self._copy_act.setEnabled(has_selection)

    def edit(
        self,
        index: QtCore.QModelIndex,
        trigger: QtWidgets.QTreeView.EditTrigger,
        event: QtCore.QEvent,
    ) -> bool:
        # Trick to allow editing second column by trying to edit the first one.
        # hmm, there is `buddy` method
        if index.column() == 0:
            item = index.internalPointer()
            if isinstance(item, PropertyItemBase):
                index = self._model.createIndex(index.row(), 1, item)
                if type(item) is BoolItem and trigger == self.DoubleClicked:
                    state = _check_state(not index.data(Qt.EditRole))
                    self._model.setData(index, state, Qt.CheckStateRole)
                    self._model.dataChanged.emit(index, index)
                    return False
        return QtWidgets.QTreeView.edit(self, index, trigger, event)

    def set_schema(self, schema: list[GMCProps]):
        """
        initial schema load, with data from .gmc_properties.json
        """
        span_rows = list(self._model.set_schema(schema))
        for span_row in span_rows:
            self.setFirstColumnSpanned(span_row, QtCore.QModelIndex(), True)
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.expandAll()

    def set_properties(self, properties: dict[str, Any]):
        """
        schema["properties"]
        """
        self._model.set_properties(properties)
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.expandAll()

    def get_properties(self) -> dict[str, Any]:
        return self._model.get_properties()
