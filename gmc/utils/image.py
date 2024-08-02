from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QMessageBox as MB
from os.path import getmtime
if TYPE_CHECKING:
    import numpy.typing as npt
    from PIL.Image import Image


CONVERT: dict[int, QImage.Format] = {
    4: QImage.Format.Format_ARGB32,
    3: QImage.Format.Format_RGB888,
    1: QImage.Format.Format_Indexed8,
}

one_image_cache: tuple[str | None, float | None, QPixmap | None] = (
    None, None, None)


def numpy_to_pixmap(arr_like: npt.ArrayLike | Image) -> QPixmap:
    import numpy as np
    arr = np.ascontiguousarray(arr_like)
    if arr.dtype != np.uint8:
        max_val = np.max(arr)
        arr = (arr / (max_val / 255)).astype(np.uint8)
    num_channels = 1 if arr.ndim <= 2 else arr.shape[2]
    qformat = CONVERT[num_channels]
    pointer, read_only_flag = arr.__array_interface__['data']
    image = QImage(pointer, arr.shape[1], arr.shape[0],
                   arr.strides[0], qformat)
    return QPixmap.fromImage(image)


def load_pixmap(path: str) -> QPixmap:
    global one_image_cache
    try:
        mtime = getmtime(path)
    except OSError:
        mtime = None
    try:
        # use cache for faster markup updating, when image takes time to load
        if one_image_cache[:2] == (path, mtime):
            return one_image_cache[2]
        pixmap = QPixmap(path)
        if pixmap.isNull():
            try:
                from PIL import Image
            except ImportError as e:
                raise ValueError(f"Failed to load `{path}`. And {e}")
            pil_image = Image.open(path)
            pixmap = numpy_to_pixmap(pil_image)
    except (ValueError, FileNotFoundError) as e:
        MB.warning(None, "Error", f"Error while opening {path}:\n\n{e}")
        return QPixmap()
    one_image_cache = (path, mtime, pixmap)
    return pixmap
