from __future__ import annotations
from typing import Callable
from PyQt5 import QtCore, QtWidgets
from ..utils import separator, get_icon
from ..views.filesystem_widget import (
    MultipleFilesystemWidget,
    SingleFilesystemWidget,
    FilesystemTitle,
)
from itertools import zip_longest
from ..application import GMCArguments

Qt = QtCore.Qt
tr: Callable[[str], str] = lambda text: QtCore.QCoreApplication.translate(
    "@default", text
)


class MultipleSourcesOneDestination:
    NSOURCES = 2
    SOURCE_TITLES = ["First Image", "Second Image"]

    @classmethod
    def create_data_widget(cls, mdi_area, settings, extra_args: GMCArguments):
        def _on_open_src(view_idx, new_tab):
            view = cls._source_widget.views()[view_idx]
            dst_dir = cls._destination_widget.get_root_qdir()
            if dst_dir is None:
                return QtWidgets.QMessageBox.warning(
                    mdi_area,
                    "Warning",
                    "Destination directory must be specified",
                )

            src_dir = cls._source_widget.get_root_qdir()

            for file_path in view.selected_files():
                all_files = view.all_files_in(
                    QtCore.QFileInfo(file_path).absoluteDir(), src_dir
                )
                cur = mdi_area.currentSubWindow()
                cur = cur and cur.widget()
                if isinstance(cur, MultipleSourcesOneDestinationMarkupWindow):
                    window = cur
                else:
                    window = MultipleSourcesOneDestinationMarkupWindow(cls)
                    mdi_area.add(window, new_tab)
                window.open_current(
                    view_idx, dst_dir, src_dir, file_path, all_files
                )
                new_tab = True

        def _on_open_dst(self, new=False):
            def selected_files(root_path):
                for path in self._destination_view.selected_files_relative:
                    path = path[: -len(".json")]
                    yield root_path.filePath(path)

            self._on_open(selected_files, new)

        def _on_view_dst_file():
            for path in cls._destination_widget.view().selected_files():
                f = QtCore.QFile(path)
                if not f.open(f.ReadOnly | f.Text):
                    continue
                text = f.readData(1024 * 1024 * 200)
                f.close()
                window = QtWidgets.QPlainTextEdit(
                    text, windowTitle=path, readOnly=1
                )
                mdi_area.add(window, True)

        cls._splitter = splitter = QtWidgets.QSplitter(orientation=Qt.Vertical)
        cls._source_widget = MultipleFilesystemWidget(
            splitter,
            FilesystemTitle(
                action=tr("&Source Directory"),
                select=tr("Select Source Directory"),
                help=tr("Now select source directory"),
            ),
            cls.SOURCE_TITLES,
            [
                [
                    QtWidgets.QAction(
                        tr("Open Image"),
                        splitter,
                        triggered=lambda _, idx=idx: _on_open_src(idx, False),
                    ),
                    QtWidgets.QAction(
                        tr("Open Image in New Tab"),
                        splitter,
                        triggered=lambda _, idx=idx: _on_open_src(idx, True),
                    ),
                ]
                for idx in range(cls.NSOURCES)
            ],
            cls.NSOURCES,
        )
        cls._destination_widget = SingleFilesystemWidget(
            splitter,
            FilesystemTitle(
                action=tr("&Destination Directory"),
                select=tr("Select Destination Directory"),
                help=tr("Then select destination directory"),
            ),
            [
                QtWidgets.QAction(
                    tr("Open Image Corresponding to Markup"),
                    splitter,
                    triggered=_on_open_dst,
                ),
                QtWidgets.QAction(
                    tr("View File"), splitter, triggered=_on_view_dst_file
                ),
            ],
        )
        splitter.restoreState(
            settings.value(cls.__name__ + "_splitter", QtCore.QByteArray())
        )

        src_path = extra_args.get("src_dir")
        if src_path is None:
            src_path = settings.value(cls.__name__ + "_src_dir", str())
        dst_path = extra_args.get("dst_dir")
        if dst_path is None:
            dst_path = settings.value(cls.__name__ + "_dst_dir", str())

        if src_path:
            for view in cls._source_widget.views():
                view.set_path(src_path)
            cls._source_widget.views()[0].setFocus()
        if dst_path:
            cls._destination_widget.view().set_path(dst_path)

        for view in cls._source_widget.views():
            view.set_name_filters(cls.DATA_FILTERS)
        cls._destination_widget.view().set_name_filters(cls.MARKUP_FILTERS)

        return splitter

    @classmethod
    def save_settings(cls, settings):
        settings.setValue(
            cls.__name__ + "_src_dir", cls._source_widget.get_root_string()
        )
        settings.setValue(
            cls.__name__ + "_dst_dir",
            cls._destination_widget.get_root_string(),
        )
        settings.setValue(
            cls.__name__ + "_splitter", cls._splitter.saveState()
        )

    # @classmethod
    # def set_selected(cls, file_path, markup_path):
    #     cls._source_widget.view().model().set_selected(file_path)
    #     cls._destination_widget.view().model().set_selected(markup_path)


class MultipleSourcesOneDestinationMarkupWindow(QtWidgets.QWidget):
    def __init__(self, schema):
        super().__init__()
        actions = self._get_default_actions(schema.NSOURCES)
        self._schema = schema(self, *tuple(actions))

        # self._dst_dir = dst_dir
        # self._src_dir = src_dir
        # self._all_files = all_files
        # rel_path = src_dir.relativeFilePath(file_path)
        # self._idx = all_files.index(rel_path)
        self._src_dir = [None] * schema.NSOURCES
        self._all_files = [None] * schema.NSOURCES
        self._idx = [None] * schema.NSOURCES

    def _create_go_actions(self, n, actions_name, actions, icon, where):
        for idx, (caption, shortcuts) in zip_longest(
            range(n), actions, fillvalue=(actions_name, None)
        ):
            action = QtWidgets.QAction(
                icon,
                caption,
                self,
                enabled=False,
                triggered=lambda _, idx=idx: self._go(idx, where),
            )
            shortcuts and action.setShortcuts(shortcuts)
            yield action

    def _get_default_actions(self, n):
        """:returns: actions, every markup window should have."""
        prev_shortcuts = (
            (
                tr("Previous File") + "\tPage Up; P; Backspace",
                [Qt.Key_P, Qt.Key_PageUp, Qt.Key_Backspace],
            ),
            (
                tr("Previous File")
                + "\tShift+Page Up; tShift+P; tShift+Backspace",
                [
                    Qt.SHIFT + Qt.Key_P,
                    Qt.SHIFT + Qt.Key_PageUp,
                    Qt.SHIFT + Qt.Key_Backspace,
                ],
            ),
        )
        next_shortcuts = (
            (
                tr("Next File") + "\tPage Down; N; Space",
                [Qt.Key_N, Qt.Key_PageDown, Qt.Key_Space],
            ),
            (
                tr("Next File") + "\tShift+Page Down; Shift+N; Shift+Space",
                [
                    Qt.SHIFT + Qt.Key_N,
                    Qt.SHIFT + Qt.Key_PageDown,
                    Qt.SHIFT + Qt.Key_Space,
                ],
            ),
        )
        self._prev_actions = list(
            self._create_go_actions(
                n, tr("Previous File"), prev_shortcuts, get_icon("prev"), -1
            )
        )
        self._next_actions = list(
            self._create_go_actions(
                n, tr("Next File"), next_shortcuts, get_icon("next"), 1
            )
        )
        save_action = QtWidgets.QAction(
            get_icon("save"),
            "Save\tCtrl+S",
            self,
            triggered=lambda: self._schema.save_markup(),
            shortcut=Qt.CTRL + Qt.Key_S,
        )

        for prev_action, next_action in zip(
            self._prev_actions, self._next_actions
        ):
            yield prev_action, next_action, separator(self), save_action

    def open_current(self, view_idx, dst_dir, src_dir, file_path, all_files):
        """The function is "public" only because it fixes focus issue."""
        self._dst_dir = dst_dir
        self._all_files[view_idx] = all_files
        self._src_dir[view_idx] = src_dir

        rel_path = src_dir.relativeFilePath(file_path)
        self._idx[view_idx] = all_files.index(rel_path)
        assert self._idx[view_idx] >= 0
        self._open_current(view_idx)

    def _open_current(self, view_idx: int) -> None:
        self._update_actions(view_idx)

        current_path = self._all_files[view_idx][self._idx[view_idx]]
        title = current_path
        self.setWindowTitle(title)

        dst_markup_path = self._dst_dir.filePath(
            current_path + getattr(self._schema, "MARKUP_EXT", ".json")
        )
        src_data_path = self._src_dir[view_idx].filePath(current_path)
        self._schema.open_markup(src_data_path, dst_markup_path, view_idx)

        # self._schema.set_selected(src_data_path, dst_markup_path)

    def _go(self, view_idx: int, where: int) -> None:
        assert isinstance(view_idx, int)
        assert isinstance(where, int)
        self._schema.save_markup(force=False)
        self._idx[view_idx] += where
        self._open_current(view_idx)

    def _update_actions(self, view_idx: int) -> None:
        n = len(self._all_files[view_idx])
        cur_idx = self._idx[view_idx]
        prev_enabled = n > 1 and cur_idx != 0
        self._prev_actions[view_idx].setEnabled(prev_enabled)
        next_enabled = n > 1 and cur_idx < n - 1
        self._next_actions[view_idx].setEnabled(next_enabled)
