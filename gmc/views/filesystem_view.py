from __future__ import annotations
from typing import Any, Iterable, TYPE_CHECKING
from PyQt5 import QtCore, QtGui, QtWidgets
from ..utils import separator, new_action, tr

Qt = QtCore.Qt
QDir = QtCore.QDir


def _question_deletion(paths: list[str]) -> str:
    n = len(paths)
    if n < 6:
        return "\n".join(paths)
    extensions = set(path[path.rfind(".") + 1 :] for path in paths)
    if len(extensions) == 1:
        total = f"{n} .{next(iter(extensions))}"
    else:
        total = n
    return tr("Total {} files\n(including\n{}\n…)").format(
        total, "\n".join(paths[:3])
    )


class FilesystemView(QtWidgets.QTreeView):
    _valid_root: bool = False

    def __init__(self, actions: Iterable[QtWidgets.QAction] | None = None):
        super().__init__(
            headerHidden=True,
            selectionMode=self.ExtendedSelection,
            contextMenuPolicy=QtCore.Qt.ActionsContextMenu,
            dragEnabled=True,
        )
        self._actions = actions
        if actions:
            self.activated.connect(self._on_activated)
            self.addActions(actions)
        self.addAction(separator(self))
        self.addAction(
            new_action(
                self,
                "copy",
                tr("Copy Path"),
                ("Ctrl+Alt+C",),
                triggered=self._on_copy_path_action,
            )
        )
        self.addAction(
            new_action(
                self,
                "new",
                tr("Default OS Action"),
                ("Alt+Enter",),
                triggered=self._on_default_os_action,
            )
        )
        self.addAction(
            new_action(
                self,
                "delete",
                tr("Delete"),
                ("Del",),
                triggered=self._on_delete_action,
            )
        )

        model = MinimalFileSystemModel(self)
        self.setModel(model)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if (
            event.key() in (Qt.Key_Enter, Qt.Key_Return)
            and event.modifiers() & Qt.AltModifier
        ):
            self._on_default_os_action()
            event.ignore()
        else:
            super().keyPressEvent(event)

    def _on_default_os_action(self) -> None:
        index = self.currentIndex()
        if index.isValid():
            path = self.model().filePath(index)
            QtGui.QDesktopServices.openUrl(QtCore.QUrl("file:///" + path))

    def _on_delete_action(self) -> None:
        paths = list(
            info.absoluteFilePath() for info in self._selected_info_map
        )
        if paths:
            response = QtWidgets.QMessageBox.question(
                self,
                "GMC",
                "\n".join(
                    (
                        tr("Move selected files to trash?"),
                        _question_deletion(paths),
                    )
                ),
            )
            if response == QtWidgets.QMessageBox.Yes:
                for path in paths:
                    QtCore.QFile.moveToTrash(path)

    def _on_copy_path_action(self) -> None:
        infos = list(self._selected_info_map)
        if infos:
            paths = "\n".join(info.absoluteFilePath() for info in infos)
            QtWidgets.QApplication.clipboard().setText(paths)

    def selectionChanged(
        self,
        selected: QtCore.QItemSelection,
        deselected: QtCore.QItemSelection,
    ):
        self._update_actions()
        super().selectionChanged(selected, deselected)

    def _on_activated(self) -> None:
        default_action = self._actions[0]
        if default_action.isEnabled():
            default_action.triggered.emit(False)

    def _update_actions(self) -> None:
        if self._actions:
            all_file = all(info.isFile() for info in self._selected_info_map)
            for action in self._actions:
                action.setEnabled(all_file)

    def selected_files(self, *_args: Any) -> list[str]:
        """
        Called when user selects multiple files and performs "view" action,
        for example
        """
        return [
            info.filePath()
            for info in self._selected_info_map
            if info.isFile()
        ]

    @classmethod
    def _all_selected_files(
        cls, finfos: Iterable[QtCore.QFileInfo], masks: list[str]
    ):
        for info in finfos:
            if info.isFile():
                yield info.filePath()
            elif info.isDir():
                qdir = QDir(info.filePath())
                qdir.setFilter(QDir.Files | QDir.NoSymLinks | QDir.Readable)
                qdir.setNameFilters(masks)
                for fi in qdir.entryInfoList():
                    yield fi.filePath()
                qdir.setFilter(
                    QDir.Dirs
                    | QDir.NoDotAndDotDot
                    | QDir.NoSymLinks
                    | QDir.Readable
                )
                qdir.setNameFilters(())
                yield from cls._all_selected_files(qdir.entryInfoList(), masks)

    def all_selected_files(self):
        """
        Just like :func:`selected_files`, but selects files in selected folders
        """
        masks = self.model().nameFilters()
        return list(self._all_selected_files(self._selected_info_map, masks))

    @property
    def _selected_info_map(self) -> Iterable[QtCore.QFileInfo]:
        return map(self.model().fileInfo, self.selectedIndexes())

    @property
    def selected_files_relative(self) -> list[str]:
        root_dir = self.model().root_dir_qdir
        return [
            root_dir.relativeFilePath(info.filePath())
            for info in self._selected_info_map
            if info.isFile()
        ]

    def all_files_in(
        self, path: QtCore.QDir, src_path: QtCore.QDir
    ) -> list[str]:
        """
        :param path: `QDir` to list files in
        :param src_path: base `QDir` instance (== self.get_root_qdir())
        :returns: `list` of files in `path` directory relative to src_path
        """
        import re

        assert isinstance(path, QtCore.QDir)
        assert isinstance(src_path, QtCore.QDir)
        path.setNameFilters(self.model().nameFilters())
        infos = path.entryInfoList(QtCore.QDir.Files, QtCore.QDir.Name)
        # natural sort to match QFilesystemModel
        infos.sort(
            key=lambda info: [
                int(part) if part.isdigit() else part
                for part in re.split("([0-9]+)", info.fileName())
            ]
        )
        return [
            src_path.relativeFilePath(info.absoluteFilePath())
            for info in infos
        ]

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        menu = QtWidgets.QMenu(self)
        menu.addActions(self.actions())
        if hasattr(self, "default_action"):
            menu.setDefaultAction(self.default_action)
        menu.exec_(event.globalPos())

    def set_path(self, path: str) -> None:
        model = self.model()
        index = model.setRootPath(path)
        self.setRootIndex(index)

    def set_name_filters(self, name_filters: Iterable[str]):
        model = self.model()
        model.setNameFilters(name_filters)

    def user_select_path(
        self, title: str, callback=lambda view, path: view.set_path(path)
    ):
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            title,
            self.model().root_dir_string,
            QtWidgets.QFileDialog.ShowDirsOnly
            | QtWidgets.QFileDialog.DontResolveSymlinks,
        )
        if path:
            callback(self, path)

    if TYPE_CHECKING:

        def model(self) -> MinimalFileSystemModel: ...


class MinimalFileSystemModel(QtWidgets.QFileSystemModel):
    _sel_path: QtCore.QDir | None = None
    _root_dir: QtCore.QDir | None = None
    HIGHLIGHT_BRUSH = QtGui.QBrush(QtGui.QColor(68, 170, 0, 90))

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._reset_selection()

    def set_selected(self, path: str) -> None:
        self._reset_selection()
        fi = QtCore.QFileInfo(path)
        self._sel_path = fi.absoluteFilePath()
        self._sel_name = fi.fileName()
        self._update_selection()

    def _reset_selection(self) -> None:
        self._update_selection()
        self._sel_path = self._sel_name = None

    def _update_selection(self) -> None:
        if self._sel_path is not None:
            index = self.index(self._sel_path)
            self.dataChanged.emit(index, index)

    def columnCount(self, _parent) -> int:
        return 1

    def setRootPath(self, path: str) -> QtCore.QModelIndex:
        """Overrode this method as default `RootPath` is '.'"""
        self._root_dir = QtCore.QDir(path)
        return super().setRootPath(path)

    def data(self, index: QtCore.QModelIndex, role: int) -> Any:
        if (
            role == Qt.BackgroundRole
            and index.isValid()
            and index.data(Qt.DisplayRole) == self._sel_name
            and self.filePath(index) == self._sel_path
        ):
            return self.HIGHLIGHT_BRUSH
        return QtWidgets.QFileSystemModel.data(self, index, role)

    @property
    def root_dir_qdir(self) -> QtCore.QDir | None:
        # to check that directory is open, allow '_root_dir' to be None
        return self._root_dir  # or QtCore.QDir()

    @property
    def root_dir_string(self) -> str:
        """Used for saving as setting"""
        if self._root_dir is None:
            return ""
        return self._root_dir.absolutePath()
