from __future__ import annotations
from typing import Any, Iterator, Sequence, TypedDict, Literal, TYPE_CHECKING
from PyQt5.QtCore import QFileInfo, QDir
from PyQt5.QtWidgets import QWidget
from .json import load
from .dicts import dicts_merge

if TYPE_CHECKING:
    from typing import NotRequired

    class BoolProp(TypedDict):
        type: Literal["bool"]
        name: str
        value: NotRequired[bool]
        display: NotRequired[str]

    class SeparatorProp(TypedDict):
        type: Literal["separator"]

    class FloatProp(TypedDict):
        type: Literal["float"]
        name: str
        value: NotRequired[float]
        minimum: NotRequired[float]
        maximum: NotRequired[float]
        display: NotRequired[str]

    class IntProp(TypedDict):
        type: Literal["int"]
        name: str
        value: NotRequired[int]
        minimum: NotRequired[int]
        maximum: NotRequired[int]
        display: NotRequired[str]

    class StrProp(TypedDict):
        type: Literal["str"]
        name: str
        value: NotRequired[str]
        display: NotRequired[str]

    class VisItem(TypedDict):
        name: str
        display: str

    class ItemProp(TypedDict):
        type: Literal["item"]
        name: str
        display: str
        items: list[VisItem]
        value: str

    class SetProp(TypedDict):
        type: Literal["set"]
        name: str
        display: str
        items: list[VisItem]
        value: list[str]

    GMCProps = (
        StrProp
        | IntProp
        | FloatProp
        | BoolProp
        | SeparatorProp
        | ItemProp
        | SetProp
    )

    class ObjectsProperty(TypedDict):
        properties: list[GMCProps]
        tags: NotRequired[list[str]]


class GMCProperties(TypedDict):
    objects: NotRequired[list[ObjectsProperty]]
    properties: NotRequired[list[GMCProps]]
    tags: NotRequired[list[str]]


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
) -> GMCProperties:
    ret: GMCProperties = {}
    for path in paths:
        the_dir = QFileInfo(path).dir()
        properties_paths = list(_paths(the_dir, filename, depth))
        for properties_path in reversed(properties_paths):
            data = load(properties_path, widget)
            dicts_merge(ret, data)
    return ret


def prop_schema_for_tags(
    properties: list[ObjectsProperty], tags: set[str]
) -> list[GMCProps]:
    schema: list[GMCProps] = []
    for prop in properties:
        if "tags" in prop and not any(tag in tags for tag in prop["tags"]):
            continue
        schema.extend(prop["properties"])
    return schema
