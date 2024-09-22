from typing import Any, Iterator, Sequence
from PyQt5.QtCore import QFileInfo, QDir
from PyQt5.QtWidgets import QWidget
from .json import load
from .dicts import dicts_merge


def _paths(the_dir: QDir, filename: str, depth: int) -> Iterator[str]:
    for _ in range(depth):
        yield the_dir.absoluteFilePath(filename)
        if not the_dir.cdUp():
            break


def read_properties(
    paths: Sequence[str],
    widget: QWidget,
    filename: str = ".gmc_properties.json",
    depth: int = 6,
) -> dict[str, Any]:
    ret: dict[str, Any] = {}
    for path in paths:
        the_dir = QFileInfo(path).dir()
        properties_paths = list(_paths(the_dir, filename, depth))
        for properties_path in reversed(properties_paths):
            data = load(properties_path, widget)
            dicts_merge(ret, data)
    return ret
