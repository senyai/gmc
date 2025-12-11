from __future__ import annotations
from typing import Literal
import unittest
from unittest.mock import patch

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
        view.copy_action.trigger()
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.undo_action.trigger()
        self.assertEqual(schema._get_markup(), ref_point_markup)
        view.redo_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.paste_action.trigger()
        self.assertEqual(schema._get_markup(), ref_point_markup)
        view.select_all_action.trigger()
        view.delete_action.trigger()
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

    @patch("PyQt5.QtCore.QElapsedTimer")
    def test_quadrangle(self, _timer):
        schema, view, viewport, make_pos, _reference = self._create_schema()
        schema._add_quadrangle_action.trigger()
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(10, 10))
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(200, 10))
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(190, 20))
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(10, 20))
        ref_quad_markup = {
            "objects": [
                {
                    "data": [
                        (10.0, 10.0),
                        (200.0, 10.0),
                        (190.0, 20.0),
                        (10, 20),
                    ],
                    "type": "quad",
                }
            ],
            "size": [640, 480],
        }
        self.assertEqual(dict(schema._get_markup()), ref_quad_markup)
        view.copy_action.trigger()
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.undo_action.trigger()
        self.assertEqual(dict(schema._get_markup()), ref_quad_markup)
        view.select_all_action.trigger()
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.paste_action.trigger()
        self.assertEqual(dict(schema._get_markup()), ref_quad_markup)
        view.select_all_action.trigger()
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)

    @patch("PyQt5.QtCore.QElapsedTimer")
    def test_rect(self, _timer):
        schema, view, viewport, make_pos, _reference = self._create_schema()
        schema._add_rect_action.trigger()
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(10, 10))
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(200, 21))
        ref_rect_markup = {
            "objects": [
                {
                    "data": [10.0, 10.0, 190.0, 11.0],
                    "type": "rect",
                }
            ],
            "size": [640, 480],
        }
        self.assertEqual(dict(schema._get_markup()), ref_rect_markup)
        view.copy_action.trigger()
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.undo_action.trigger()
        self.assertEqual(dict(schema._get_markup()), ref_rect_markup)
        view.redo_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.paste_action.trigger()
        self.assertEqual(dict(schema._get_markup()), ref_rect_markup)
        view.select_all_action.trigger()
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)

    def _test_two_points(
        self,
        name_type: (
            tuple[Literal["seg"], Literal["segment"]]
            | tuple[Literal["line"], Literal["line"]]
        ),
    ):
        schema, view, viewport, make_pos, _reference = self._create_schema()
        getattr(schema, f"_add_{name_type[1]}_action").trigger()
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(10, 20))
        QTest.mouseClick(viewport, Qt.LeftButton, pos=make_pos(11, 40))
        ref_segment_markup = {
            "objects": [
                {"data": [(10.0, 20.0), (11.0, 40.0)], "type": name_type[0]}
            ],
            "size": [640, 480],
        }
        self.assertEqual(dict(schema._get_markup()), ref_segment_markup)
        view.copy_action.trigger()
        view.delete_action.trigger()
        self.assertEqual(dict(schema._get_markup()), self.REF_EMPTY_MARKUP)
        view.undo_action.trigger()
        self.assertEqual(schema._get_markup(), ref_segment_markup)
        view.redo_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)
        view.paste_action.trigger()
        self.assertEqual(dict(schema._get_markup()), ref_segment_markup)
        view.select_all_action.trigger()
        view.delete_action.trigger()
        self.assertEqual(schema._get_markup(), self.REF_EMPTY_MARKUP)

    @patch("PyQt5.QtCore.QElapsedTimer")
    def test_segment(self, _timer):
        self._test_two_points(("seg", "segment"))

    @patch("PyQt5.QtCore.QElapsedTimer")
    def test_line(self, _timer):
        self._test_two_points(("line", "line"))
