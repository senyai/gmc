"""
Convenient ways to get/set gmc objects from clipboard. Not sure where to hold
the "scheme". Nobody will likely to complain about the ability to paste
from one scheme to another.
"""

from typing import Optional, List, Any
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMimeData
from json import dumps, loads


def set_objects(data_list: List[Any]) -> None:
    json_data = dumps(
        data_list, allow_nan=False, ensure_ascii=False, separators=",:"
    )
    mime_data = QMimeData()
    mime_data.setData("application/gmc-json", json_data.encode("utf-8"))
    QApplication.clipboard().setMimeData(mime_data)


def get_objects() -> Optional[List[Any]]:
    mime_data = QApplication.clipboard().mimeData()
    json_bytes = mime_data.data("application/gmc-json")
    if not json_bytes:
        return
    data_list = loads(json_bytes.data())
    return data_list
