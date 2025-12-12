from __future__ import annotations
from gmc.views.filesystem_view import FilesystemView
from unittest import TestCase
from PyQt5.QtCore import QFileInfo
from unittest.mock import patch, MagicMock


def _path(name: str) -> str:
    return QFileInfo(name).absoluteFilePath()


class FilesystemViewTest(TestCase):
    @patch("PyQt5.QtWidgets.QTreeView.selectedIndexes")
    @patch("gmc.views.filesystem_view.MinimalFileSystemModel.fileInfo")
    @patch("PyQt5.QtWidgets.QMessageBox.question")
    def _test_question(
        self,
        names: list[str],
        ref_text: str,
        question: MagicMock,
        fileInfo: MagicMock,
        indices: MagicMock,
    ):
        view = FilesystemView()
        indices.return_value = names
        fileInfo.side_effect = QFileInfo
        view.actions()[-1].trigger()
        question.assert_called_once_with(view, "GMC", ref_text)

    def test_question_delete_one_file(self):
        ref_text = f'Move selected files to trash?\n{_path("aaa")}'
        self._test_question(["aaa"], ref_text)

    def test_question_delete_10_files_of_the_same_extension(self):
        ref_text = (
            f"Move selected files to trash?\nTotal 10 .js files\n"
            f"(including\n{'\n'.join([_path('aaa.js')] * 3)}\n…)"
        )
        self._test_question(["aaa.js"] * 10, ref_text)

    def test_question_delete_9_files_of_different_extensions(self):
        exp_files = ["aaa.js"] * 2 + ["aaa.py"] * 7
        ref_text = (
            f"Move selected files to trash?\nTotal 9 files\n"
            f"(including\n{'\n'.join(map(_path, exp_files[:3]))}\n…)"
        )
        self._test_question(exp_files, ref_text)
