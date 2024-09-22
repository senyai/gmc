import json
from typing import Any
from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import QFileInfo
from . import CantOpenMarkup


class ZeroDict(dict):
    def __setitem__(self, _key, _value):
        raise RuntimeError("ZeroDict modification makes no sense")

    def __deepcopy__(self, memo):
        # it makes sense that deepcopying returns empty dict
        return {}


def load(json_filename: str, widget: QWidget):
    try:
        with open(json_filename, "r", encoding="utf-8") as inp:
            return json.load(inp)
    except ValueError as e:
        msg = "Failed parsing `{}`\n{}".format(json_filename, e)
        QMessageBox.warning(widget, "Warning", msg)
        raise CantOpenMarkup(msg)
    except IOError as e:
        return ZeroDict()  # special class so `dicts_are_equal` returns False


def dump(json_filename: str, data: dict[str, Any]) -> None:
    the_qdir = QFileInfo(json_filename).absoluteDir()
    the_qdir.mkpath(the_qdir.absolutePath())

    # save first to raw_json, as `json.dump` will corrupt file in extreme cases
    raw_json = json.dumps(
        data, allow_nan=False, indent=2, sort_keys=True, ensure_ascii=False
    )

    with open(json_filename, "w", encoding="utf-8") as out:
        out.write(raw_json)
