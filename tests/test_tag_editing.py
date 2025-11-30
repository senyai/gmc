from __future__ import annotations
import unittest

from __init__ import qapplication
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtTest import QTest

Qt = QtCore.Qt

from gmc.markup_objects.tags import TagsDialog
from gmc.views.image_widget import ImageWidget
from gmc.schemas.tagged_objects import CustomPoint


class TestTagEditing(unittest.TestCase):
    def _create_dialog(self, tags: list[str]):
        image_view = ImageWidget(default_actions=[])
        point = CustomPoint(schema=None, tags=tags)
        dialog = TagsDialog(parent=image_view, items=[point])
        dialog.setFocus()
        return dialog, point, image_view

    def test_add_tag_on_accept(self):
        dialog, point, _reference = self._create_dialog(["aaa", "bbb"])
        QTest.keyClicks(dialog._tag_line_edit, "ccc")
        dialog._on_accept()
        self.assertEqual(point.get_tags(), {"aaa", "bbb", "ccc"})

    def test_delete_tag(self):
        dialog, point, _reference = self._create_dialog(["aaa", "bbb"])
        dialog._tag_list_widget.setCurrentRow(0)
        QTest.keyClick(dialog._tag_list_widget, Qt.Key_Space)
        dialog._on_accept()
        self.assertEqual(point.get_tags(), {"bbb"})

    def test_rename_tag(self):
        dialog, point, _reference = self._create_dialog(["aaa", "bbb"])
        dialog._tag_list_widget.item(0).setText("renamed")
        dialog._on_accept()
        self.assertEqual(point.get_tags(), {"renamed", "bbb"})

    def test_all_actions(self):
        # keep aaa
        # rename bbb
        # delete ccc
        # add xxx
        dialog, point, _reference = self._create_dialog(["aaa", "bbb", "ccc"])
        dialog._tag_list_widget.item(1).setText("renamed")
        dialog._tag_list_widget.takeItem(2)
        QTest.keyClicks(dialog._tag_line_edit, "xxx")
        dialog._on_accept()
        self.assertEqual(point.get_tags(), {"aaa", "renamed", "xxx"})
