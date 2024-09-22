from typing import Any, Callable, Sequence
from PyQt5 import QtCore, QtWidgets, QtGui
from ..utils import separator, new_action
from ..views.filesystem_widget import SingleFilesystemWidget, FilesystemTitle
from ..settings import settings

Qt = QtCore.Qt
MB = QtWidgets.QMessageBox
tr: Callable[[str], str] = lambda text: QtCore.QCoreApplication.translate(
    "@default", text
)


class OneSourceOneDestination:
    @classmethod
    def create_data_widget(
        cls, mdi_area: QtWidgets.QMdiArea, extra_args: dict[str, Any]
    ) -> QtWidgets.QSplitter:
        """
        :param cls: like `gmc.schemas.tagged_objects.TaggedObjects`
        :param mdi_area: `QMidArea` instance
        """

        def _on_open(src_files: Sequence[str], new_tab: bool) -> None:
            assert hasattr(src_files, "__iter__")
            dst_dir: QtCore.QDir = cls._destination_widget.get_root_qdir()
            src_dir: QtCore.QDir = cls._source_widget.get_root_qdir()
            if dst_dir is None:
                return MB.warning(
                    mdi_area,
                    tr("Warning"),
                    tr("Destination directory must be specified"),
                )
            for file_path in src_files:
                all_files = cls._source_widget.view().all_files_in(
                    QtCore.QFileInfo(file_path).absoluteDir(), src_dir
                )
                try:  # sometimes not all required data is there - so try
                    window = OneSourceOneDestinationMarkupWindow(
                        dst_dir, src_dir, file_path, all_files, cls
                    )
                    mdi_area.add(window, new_tab)
                    window.open_current()
                except Exception as e:  # like json.decoder.JSONDecodeError
                    MB.warning(
                        mdi_area,
                        tr("Error"),
                        "Error while opening {file_path}:"
                        "\n{e}".format(file_path=file_path, e=e),
                    )
                    print("Printing traceback for the developer")
                    print("=" * 40)
                    import traceback

                    traceback.print_exc()
                    print("=" * 40)
                    break
                new_tab = True

        def _on_open_src(new_tab: bool = False) -> None:
            _on_open(cls._source_widget.view().selected_files(), new_tab)

        def _on_open_dst(_, new: bool = False) -> None:
            src_dir = cls._source_widget.get_root_qdir()

            def selected_files():
                view = cls._destination_widget.view()
                trim = -len(getattr(cls, "MARKUP_EXT", ".json"))
                for path in view.selected_files_relative:
                    path = path[:trim]
                    yield src_dir.filePath(path)

            _on_open(selected_files(), new)

        def _on_view_dst_file():
            for path in cls._destination_widget.view().selected_files():
                f = QtCore.QFile(path)
                if not f.open(f.ReadOnly | f.Text):
                    continue
                text = f.readData(1024 * 1024 * 200).decode("utf-8")
                f.close()
                window = QtWidgets.QPlainTextEdit(
                    text, windowTitle=path, readOnly=1
                )
                mdi_area.add(window, True)

        cls._splitter = splitter = QtWidgets.QSplitter(orientation=Qt.Vertical)
        cls._source_widget = SingleFilesystemWidget(
            splitter,
            FilesystemTitle(
                action=tr("&Source Directory"),
                select=tr("Select Source Directory"),
                help=tr("Now select source directory"),
            ),
            [
                new_action(
                    splitter,
                    "folder",
                    tr("Open Image"),
                    triggered=_on_open_src,
                ),
                new_action(
                    splitter,
                    "folder",
                    tr("Open Image in New Tab"),
                    triggered=lambda: _on_open_src(True),
                ),
            ],
        )
        cls._destination_widget = SingleFilesystemWidget(
            splitter,
            FilesystemTitle(
                action=tr("&Destination Directory"),
                select=tr("Select Destination Directory"),
                help=tr("Then select destination directory"),
            ),
            [
                new_action(
                    splitter,
                    "folder",
                    tr("Open Image Corresponding to Markup"),
                    triggered=_on_open_dst,
                ),
                new_action(
                    splitter,
                    "eye_open",
                    tr("View File"),
                    triggered=_on_view_dst_file,
                ),
            ],
        )
        settings.load_state(splitter, cls.__name__ + "_splitter")

        src_path = extra_args.get("src_dir")
        if src_path is None:
            src_path = settings.value(cls.__name__ + "_src_dir", "", str)
        dst_path = extra_args.get("dst_dir")
        if dst_path is None:
            dst_path = settings.value(cls.__name__ + "_dst_dir", "", str)

        if src_path:
            cls._source_widget.view().set_path(src_path)
            cls._source_widget.view().setFocus()
        if dst_path:
            cls._destination_widget.view().set_path(dst_path)

        cls._source_widget.view().set_name_filters(cls.DATA_FILTERS)
        cls._destination_widget.view().set_name_filters(cls.MARKUP_FILTERS)

        return splitter

    @classmethod
    def save_settings(cls, settings: QtCore.QSettings) -> None:
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

    @classmethod
    def set_selected(cls, file_path: str, markup_path: str) -> None:
        cls._source_widget.view().model().set_selected(file_path)
        cls._destination_widget.view().model().set_selected(markup_path)


class OneSourceOneDestinationMarkupWindow(QtWidgets.QWidget):
    def __init__(
        self,
        dst_dir: QtCore.QDir,
        src_dir: QtCore.QDir,
        file_path: str,
        all_files: list[str],
        schema,
    ):
        """
        :param dst_dir: `QDir` root destination path
        :param src_dir: `QDir` root source path
        :param file_path: absolute image file path
        :param all_files: `list` of relative paths
        :param schema: schema class
        """
        QtWidgets.QWidget.__init__(self)
        actions = self._get_default_actions()
        self._schema = schema(self, actions)

        self._dst_dir = dst_dir
        self._src_dir = src_dir
        self._all_files = all_files
        rel_path = src_dir.relativeFilePath(file_path)
        self._idx = all_files.index(rel_path)

    def _get_default_actions(self):
        """:returns: actions, every markup window should have"""

        def mod(*keys: int) -> tuple[int, ...]:
            return (
                keys
                + tuple(key + Qt.SHIFT for key in keys)
                + tuple(key + Qt.ALT for key in keys)
            )

        self._prev_action = new_action(
            self,
            "prev",
            tr("Previous File"),
            mod(Qt.Key_P, Qt.Key_PageUp, Qt.Key_Backspace),
            triggered=lambda: self._go(-1),
        )
        self._next_action = new_action(
            self,
            "next",
            tr("Next File"),
            mod(Qt.Key_N, Qt.Key_PageDown, Qt.Key_Space),
            triggered=lambda: self._go(1),
        )
        _save_action = new_action(
            self,
            "save",
            tr("Save"),
            (Qt.CTRL + Qt.Key_S,),
            triggered=lambda: self._schema.save_markup(),
        )

        return (
            self._next_action,
            self._prev_action,
            separator(self),
            _save_action,
        )

    def open_current(self) -> None:
        """This function is "public" only because it fixes focus issue"""
        self._update_actions()
        current_path = self._all_files[self._idx]
        n = len(self._all_files)
        title = "({}/{}) {}".format(self._idx + 1, n, current_path)
        self.setWindowTitle(title)
        markup_ext = getattr(self._schema, "MARKUP_EXT", ".json")
        self._dst_markup_path = self._dst_dir.filePath(
            current_path + markup_ext
        )
        src_data_path = self._src_dir.filePath(current_path)
        self._schema.open_markup(src_data_path, self._dst_markup_path)
        self._schema.set_selected(src_data_path, self._dst_markup_path)

    def _go(self, where: int) -> None:
        if not QtGui.QGuiApplication.keyboardModifiers():
            self._schema.save_markup(force=False)
        self._idx = (self._idx + where) % len(self._all_files)
        self.open_current()

    def _update_actions(self) -> None:
        enabled = bool(self._all_files)
        self._prev_action.setEnabled(enabled)
        self._next_action.setEnabled(enabled)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if not self._schema.markup_has_changes():
            return
        answer = MB.question(
            self,
            tr("Close Tab"),
            tr('Save changes in tab\n"{title}"\nbefore closing?').format(
                title=self.windowTitle()
            ),
            MB.Save | MB.Discard | MB.Cancel,
            MB.Save,
        )
        if answer == MB.Save:
            self._schema.save_markup(force=True)
        elif answer == MB.Discard:
            pass
        else:
            event.ignore()
