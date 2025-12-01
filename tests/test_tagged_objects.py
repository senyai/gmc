from __future__ import annotations
import unittest

from __init__ import qapplication
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtTest import QTest

Qt = QtCore.Qt

from gmc.schemas.tagged_objects import CustomPoint, TaggedObjects


class FakeMarkupWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._next_action = QtWidgets.QAction()


class TaggedObjectsTest(unittest.TestCase):
    REF_EMPTY_MARKUP = {"objects": [], "size": [640, 480]}

    def _create_schema(self):
        parent = FakeMarkupWindow()
        schema = TaggedObjects(parent, [])
        schema._original_markup = {}
        schema._properties = {}
        schema._current_root_properties = None
        schema._size = self.REF_EMPTY_MARKUP["size"].copy()
        view = schema._image_widget.view()
        viewport = view.viewport()

        def make_pos(x: int, y: int):
            return view.mapFromScene(QtCore.QPoint(x, y))

        return schema, view, viewport, make_pos, parent

    def test_point(self):
        schema, view, viewport, make_pos, _reference = self._create_schema()
        schema._add_point_action.trigger()
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(10, 20))
        ref_point_markup = {
            "objects": [{"data": [10.0, 20.0], "type": "point"}],
            "size": [640, 480],
        }
        self.assertEqual(schema._get_markup(), ref_point_markup)
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.undo_action.trigger()
        self.assertEqual(schema._get_markup(), ref_point_markup)
        view.redo_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)

    def test_region(self):
        schema, view, viewport, make_pos, _reference = self._create_schema()
        schema._add_region_action.trigger()
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(10, 10))
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(200, 10))
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(10, 20))
        QTest.mouseDClick(viewport, Qt.LeftButton, pos=make_pos(10, 20))
        ref_region_markup = {
            "objects": [
                {
                    "data": [(10.0, 10.0), (200.0, 10.0), (10.0, 20.0)],
                    "type": "region",
                }
            ],
            "size": [640, 480],
        }
        self.assertEqual(dict(schema._get_markup()), ref_region_markup)
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.undo_action.trigger()
        self.assertEqual(schema._get_markup(), ref_region_markup)
        view.redo_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
