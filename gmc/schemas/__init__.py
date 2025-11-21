from __future__ import annotations
import os
import sys
import abc
import importlib
from typing import Iterable, Sequence
from PyQt5 import QtWidgets, QtCore
from ..application import GMCArguments


class MarkupSchema(metaclass=abc.ABCMeta):
    DATA_FILTERS = (
        "*.bmp",
        "*.jp2",
        "*.jpeg",
        "*.jpg",
        "*.png",
        "*.tga",
        "*.tif",
        "*.tiff",
        "*.wbmp",
        "*.webp",
    )  # Qt supported formats
    MARKUP_FILTERS = ("*.json",)  # reasonable default

    @abc.abstractmethod
    def __init__(self, markup_window, default_actions):
        raise NotImplementedError()

    @abc.abstractmethod
    def open_markup(self, src_data_path, dst_markup_path) -> None:
        raise NotImplementedError()

    def markup_has_changes(self) -> bool:
        return False

    @abc.abstractmethod
    def save_markup(self, force: bool = False) -> None:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def save_settings(cls, settings: QtCore.QSettings) -> None:
        raise NotImplementedError(cls)

    @classmethod
    @abc.abstractmethod
    def create_data_widget(
        cls, mdi_area: QtWidgets.QMdiArea, extra_args: GMCArguments
    ) -> QtWidgets.QWidget:
        raise NotImplementedError(cls)


def load_schema_cls(mod_name: str, path: str | None) -> type[MarkupSchema]:
    if path is not None:
        sys.path.insert(0, path)
    mod = importlib.import_module(mod_name)
    for obj in vars(mod).values():
        if (
            isinstance(obj, type)
            and issubclass(obj, MarkupSchema)
            and obj is not MarkupSchema
        ):
            return obj
    raise Exception(f"There are no schemas in `{mod_name}` module")


def iter_schemas(
    external_schemas: Sequence[str],
) -> Iterable[tuple[str, str, str | None]]:
    """
    :param external_schemas: paths to .py file importable directory,
                             or fully qualified module name
    :returns: sequence of (module_name, q_action_caption, path_add_to_sys_path)
    """
    for path in external_schemas:
        fi = QtCore.QFileInfo(path)
        if fi.exists():
            full_name = name = fi.baseName()
            sys_path = fi.absolutePath()
        else:
            full_name = path  # path like "my.module.markup"
            name = path.split(".")[-1]
            sys_path = None
        yield full_name, name.replace("_", " ").title(), sys_path

    QDir = QtCore.QDir
    qdir = QDir(__file__)
    qdir.cdUp()
    dir_filter = qdir.Dirs | qdir.Files | qdir.NoDotAndDotDot
    for fi in qdir.entryInfoList(dir_filter, qdir.Name):
        if fi.baseName()[:2] == "__":
            continue
        if fi.suffix() in ("py", "pyc") or fi.isDir():
            name = fi.baseName()
            if name:  # case for `.mypy_cache` folder
                yield "gmc.schemas." + name, name.replace(
                    "_", " "
                ).title(), None
