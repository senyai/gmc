"""
Standalone script for generating json schema file

Run `python -m gmc.utils.properties_schema` to generate 'schema.json'
"""

from __future__ import annotations

from typing import Literal, Annotated, Any
from pydantic import BaseModel, Field


class StrictModel(BaseModel):
    class Config:
        extra = "forbid"
        frozen = True


NameFiled = Field(..., description="Key stored in json")
DisplayFiled = Field(None, description="Label in the tree view")


def ValueFiled(default: Any):
    return Field(default, description="Default value")


class BoolProp(StrictModel):
    """
    Arbitrary bool displayed as a checkbox (`QtWidgets.QCheckBox`)
    """

    type: Literal["bool"] = Field(..., description=__doc__)
    name: str = NameFiled
    value: bool | None = ValueFiled(None)
    display: str | None = DisplayFiled


class SeparatorProp(StrictModel):
    """
    Visual divider
    """

    type: Literal["separator"] = Field(..., description=__doc__)


class FloatProp(StrictModel):
    """
    Arbitrary float displayed as a spin box (`QDoubleSpinBox`)
    https://doc.qt.io/qt-6/qdoublespinbox.html
    """

    type: Literal["float"] = Field(..., description=__doc__)
    name: str = NameFiled
    value: float | None = ValueFiled(None)
    minimum: float | None = None
    maximum: float | None = None
    decimals: int = Field(
        2, description="precision of the spin box, in decimals"
    )
    singleStep: float | None = Field(None, description="step value")
    display: str | None = DisplayFiled


class IntProp(StrictModel):
    """
    Arbitrary integer displayed as a spin box (`QtWidgets.QSpinBox`)
    https://doc.qt.io/qt-6/qspinbox.html
    """

    type: Literal["int"] = Field(..., description=__doc__)
    name: str = NameFiled
    value: int = ValueFiled(0)
    minimum: int | None = None
    maximum: int | None = None
    display: str | None = DisplayFiled


class StrProp(StrictModel):
    """
    Arbitrary string displayed as a (`QtWidgets.QLineEdit`)
    https://doc.qt.io/qt-6/qlineedit.html
    """

    type: Literal["str"] = Field(..., description=__doc__)
    name: str = NameFiled
    value: str | None = ValueFiled(None)
    display: str | None = DisplayFiled


class VisItem(StrictModel):
    name: str | bool = Field(..., description="Value stored in json")
    display: str | None = DisplayFiled


class ItemProp(StrictModel):
    """
    An item that is selected using a list of radio buttons
    """

    type: Literal["item"] = Field(..., description=__doc__)
    name: str = NameFiled
    display: str | None = DisplayFiled
    items: list[VisItem] = Field(..., min_length=1)
    value: str | None = ValueFiled(None)


class SetProp(StrictModel):
    """
    An item that is selected using a list of radio buttons
    """

    type: Literal["set"] = Field(..., description=__doc__)
    name: str = NameFiled
    display: str | None = DisplayFiled
    items: list[VisItem] = Field(..., min_length=1)
    value: list[str] = ValueFiled([])


GMCProps = Annotated[
    StrProp
    | IntProp
    | FloatProp
    | BoolProp
    | SeparatorProp
    | ItemProp
    | SetProp,
    Field(..., discriminator="type"),
]


class ObjectsProperty(StrictModel):
    properties: list[GMCProps] = Field(
        ..., description="List of properties schema"
    )
    tags: list[str] | None = Field(
        None, description="Only apply 'properties' to these tags"
    )


class GMCProperties(StrictModel):
    objects: list[ObjectsProperty] | None = Field(
        None, description="Schemas for objects"
    )
    properties: list[GMCProps] | None = Field(
        None, description="Schema for the whole image"
    )
    tags: list[str] | None = Field(None, description="List of default tags")


def main():
    import json

    schema = GMCProperties.model_json_schema()
    with open("schema.json", "w") as out:
        json.dump(schema, out, ensure_ascii=False, separators=(",", ":"))
    print("schema.json generated")


if __name__ == "__main__":
    main()
