from typing import List, NamedTuple, Sequence
from PyQt5 import QtCore, QtWidgets
from .filesystem_view import FilesystemView
from ..help_label import HelpLabel
from ..utils import get_icon
Qt = QtCore.Qt


FilesystemTitle = NamedTuple('FilesystemTitle', (
    ('action', str),  # &Source dir … (without …)
    ('select', str),  # Select Source Directory
    ('help', str)  # Now select source dir
))

class SingleFilesystemWidget(QtWidgets.QFrame):
    def __init__(self,
                 parent: QtWidgets.QWidget,
                 title: FilesystemTitle,
                 actions: List[QtWidgets.QAction]):
        assert isinstance(title, FilesystemTitle), title
        super().__init__(
            parent,
            frameShape=self.NoFrame,
            frameShadow=self.Plain,
        )

        view = self._view = FilesystemView(actions)
        button = QtWidgets.QPushButton(
            self,
            clicked=lambda: view.user_select_path(title.select),
            text=title.action + ' …',
            icon=get_icon('folder'))

        self._layout = QtWidgets.QVBoxLayout(self, spacing=0, margin=2)
        self._layout.addWidget(button)
        self._layout.addWidget(HelpLabel(title.help, align='center'))

        view.model().rootPathChanged.connect(self._root_changed)

    def _root_changed(self):
        self._view.model().rootPathChanged.disconnect(self._root_changed)
        self._layout.takeAt(1).widget().setParent(None)
        self._layout.addWidget(self._view)

    def view(self) -> FilesystemView:
        return self._view

    def get_root_qdir(self) -> QtCore.QDir:
        return self._view.model().root_dir_qdir

    def get_root_string(self) -> str:
        return self._view.model().root_dir_string


class MultipleFilesystemWidget(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget, title: FilesystemTitle,
                 captions: List[str],
                 actions_list: Sequence[List[QtWidgets.QAction]],
                 N: int) -> None:
        super().__init__(
            parent,
            frameShape=self.NoFrame,
            frameShadow=self.Plain,
        )
        assert len(actions_list) == len(captions) == N
        assert all(isinstance(action, QtWidgets.QAction)
                   for actions in actions_list for action in actions)

        def callback(_view, path):
            for view in views:
                view.set_path(path)

        self._views = views = [
            FilesystemView(actions) for actions in actions_list]
        self._captions = captions
        button = QtWidgets.QPushButton(
            self, flat=False,
            clicked=(
                lambda: views[0].user_select_path(title.select, callback=callback)),
            text=title.action + ' …',
            icon=get_icon('folder'))

        self._layout = QtWidgets.QVBoxLayout(self, spacing=0, margin=2)
        self._layout.addWidget(button)
        self._layout.addWidget(HelpLabel(title.help, align='center'))

        views[0].model().rootPathChanged.connect(self._root_changed)

    def _root_changed(self) -> None:
        self._views[0].model().rootPathChanged.disconnect(self._root_changed)
        self._layout.takeAt(1).widget().setParent(None)
        for view, caption in zip(self._views, self._captions):
            self._layout.addWidget(QtWidgets.QLabel(caption))
            self._layout.addWidget(view)

    def views(self) -> List[FilesystemView]:
        return self._views

    def get_root_qdir(self) -> QtCore.QDir:
        return self._views[0].model().root_dir_qdir

    def get_root_string(self) -> str:
        return self._views[0].model().root_dir_string
