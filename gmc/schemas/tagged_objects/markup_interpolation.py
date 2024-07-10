from __future__ import annotations
from json import load as json_load
from collections import OrderedDict
from typing import Any, Callable, Dict, Iterator, List, Literal, Optional, Tuple, TypedDict
from ...utils.json import dump as dump_json
from ...utils import tr
from PyQt5 import QtGui, QtWidgets

import cv2
import numpy as np
import copy


CONVERT = {  # channels, mintype
    QtGui.QImage.Format.Format_ARGB32: 4,
    QtGui.QImage.Format.Format_RGB32: 3,
    QtGui.QImage.Format.Format_RGB888: 3,
    QtGui.QImage.Format.Format_Indexed8: 1,
}

IMAGES_CACHE: Dict[str, Any] = OrderedDict()


class NumpyHolder:
    def __init__(self, interface):
        self.__array_interface__ = interface


class GMCItem_(TypedDict):
    type: Literal['quad', 'rect', 'point']
    data: List[Any]


class GMCItem(GMCItem_, total=False):
    tags: List[str]


class GMCMarkup(TypedDict):
    size: Tuple[int, int]
    objects: List[GMCItem]


def load_image(path: str) -> Any:
    try:
        qimg = IMAGES_CACHE.pop(path)
        IMAGES_CACHE[path] = qimg
        return qimg[0]
    except KeyError:
        if len(IMAGES_CACHE) >= 100:
            IMAGES_CACHE.popitem(last=False)
    qimg = QtGui.QImage(path)
    channels = CONVERT[qimg.format()]
    shape = qimg.height(), qimg.width(), channels
    nh = NumpyHolder({
        'shape': shape,
        'data': (qimg.constBits().__int__(), False),
        'typestr': 'u1',
        'strides': (qimg.bytesPerLine(), channels, 1),
    })
    nparray = np.array(nh, copy=False)
    IMAGES_CACHE[path] = (nparray, qimg)
    return nparray


def read_markup(file_paths: List[str]) -> Iterator[Any]:
    for path in file_paths:
        try:
            with open(path, "r", encoding="utf-8") as inp:
                yield json_load(inp)
        except IOError:
            yield {'objects': []}
        except Exception as e:
            print("read_markup", e, 'in', path)


def get_filter_input():
    edit = QtWidgets.QLineEdit()
    DBB = QtWidgets.QDialogButtonBox
    button_box = DBB(DBB.Cancel)
    btn_all = QtWidgets.QPushButton(tr("Objects with every tag"))
    btn_any = QtWidgets.QPushButton(tr("Objects with any tag"))
    button_box.addButton(btn_all, DBB.AcceptRole)
    button_box.addButton(btn_any, DBB.AcceptRole)
    dialog = QtWidgets.QDialog()
    layout = QtWidgets.QVBoxLayout(dialog)
    field_name = tr("Interpolate objects with tags (comma separated):")
    layout.addWidget(QtWidgets.QLabel(field_name))
    layout.addWidget(edit)
    layout.addWidget(button_box)

    btn_all.clicked.connect(lambda: dialog.accept() or dialog.setResult(2))
    btn_any.clicked.connect(lambda: dialog.accept() or dialog.setResult(1))
    button_box.rejected.connect(dialog.reject)
    result = dialog.exec_()
    return result, [tag.strip() for tag in edit.text().split(',')]


class iter_interpolatable_objects:
    def __new__(cls, markup_list: List[Any], use_filter: bool) -> Iterator[Tuple[GMCItem, GMCItem, int, int]]:
        objects = cls._iter_all_objects(markup_list)
        if use_filter:
            result, tags = get_filter_input()
            if result == 0:  # user canceled
                return
            if result == 1:
                f = any
            elif result == 2:
                f = all
            else:
                raise Exception("Unexpected filter")
            objects = cls.filter_by_tags(objects, tags, f)
        for idx, obj in objects:
            shift, next_obj = cls._find_next_object(obj, markup_list[idx + 1:])
            if next_obj is not None:
                yield obj, next_obj, idx, shift

    @staticmethod
    def _iter_all_objects(markup_list: List[GMCMarkup]) -> Iterator[Tuple[int, GMCItem]]:
        for idx, markup in enumerate(markup_list):
            for obj in markup.get('objects', ()):
                assert isinstance(obj, dict), obj
                if obj['type'] in ('rect', 'quad', 'point'):
                    yield idx, obj

    @staticmethod
    def _key(obj: GMCItem) -> Tuple[str, Tuple[str, ...]]:
        return obj['type'], tuple(obj.get('tags',()))

    @classmethod
    def _find_next_object(
            cls,
            obj: GMCItem,
            markup_list: List[GMCItem]
        ) -> Tuple[int, Optional[GMCItem]]:
        """
        Find first `obj` in `markup_list` using `cls.key`
        """
        key = cls._key
        key_to_find = key(obj)
        for idx, markup in enumerate(markup_list):
            assert isinstance(obj, dict), obj
            for obj in markup.get('objects', ()):
                if key(obj) == key_to_find:
                    return idx, obj
        return 0, None

    @staticmethod
    def filter_by_tags(
            objects: Iterator[Tuple[int, GMCItem]],
            tags: List[str],
            f: Callable[[Iterator[bool]], bool]
        ) -> Iterator[Tuple[int, GMCItem]]:
        for idx, obj in objects:
            obj_tags = obj.get('tags')
            if not obj_tags:  # because f(empty list) is always true
                continue
            if f(tag in tags for tag in obj_tags):
                yield idx, obj


def interpolate_many(
        image_paths: List[str],
        markup_paths: List[str],
        use_filter: bool) -> None:
    MB = QtWidgets.QMessageBox
    if not use_filter and MB.warning(
            QtWidgets.QApplication.activeWindow(), tr("GMC Interpolation"),
            tr("Are you sure want to interpolate all objects in {} files?")
            .format(len(image_paths)), MB.Ok | MB.Cancel) != MB.Ok:
        return

    markup_list: List[Any] = list(read_markup(markup_paths))
    save: Dict[str, Dict[str, Any]] = {}
    objects = iter_interpolatable_objects(markup_list, use_filter)
    for obj, next_obj, idx, shift in objects:
        if shift == 0:
            continue
        frames = interpolate_core([obj], [next_obj], image_paths[idx:idx+shift+2])
        out_s = slice(idx+1, idx+1+len(frames)-2)
        for obj_src, markup_dst, markup_path in zip(
                frames[1:-1], markup_list[out_s], markup_paths[out_s]):
            assert isinstance(obj_src, list) and len(obj_src) == 1, obj_src
            obj_src = obj_src[0]
            if 'tags' in obj:
                obj_src['tags'] = obj['tags']
            markup_dst.setdefault('objects', []).append(obj_src)
            save[markup_path] = markup_dst
        # print((obj, next_obj, idx, shift), frames)
    IMAGES_CACHE.clear()
    for path, markup in save.items():
        dump_json(path, markup)


def prepare_obj(obj: GMCItem) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    if obj['type'] == 'point':
        size = (20, 20)  # TODO: size as parameter
        center = tuple(obj['data'])
    elif obj['type'] == 'rect':
        size = (int(obj['data'][2]), int(obj['data'][3]))
        center = (obj['data'][0] + (obj['data'][2] / 2),
                  obj['data'][1] + (obj['data'][3]/ 2))
    else:
        raise NotImplementedError(f"Unsupported object type `{obj['type']}`")
    return center, size


def move_obj(pt: Tuple[float, float], obj: GMCItem) -> GMCItem:
    obj_moved = copy.deepcopy(obj)

    if obj['type'] == 'point':
        obj_moved['data'][0] = pt[0]
        obj_moved['data'][1] = pt[1]
    elif obj['type'] == 'rect':
        obj_moved['data'][0] = pt[0] - (obj['data'][2] / 2)
        obj_moved['data'][1] = pt[1] - (obj['data'][3] / 2)
        # 2 and 3 as in obj
    else:
        raise NotImplementedError(f"Unsupported object type `{obj['type']}`")

    return obj_moved


def predict_cv(objects: List[Any], frame1_path: str, frame2_path: str) -> List[GMCItem]:
    frame1 = load_image(frame1_path)
    frame2 = load_image(frame2_path)
    prediction: List[GMCItem] = []
    for obj in objects:
        center, size = prepare_obj(obj)
        center = np.atleast_2d(np.array(center)).astype(np.float32)
        pt_moved, _, _ = cv2.calcOpticalFlowPyrLK(
            frame1, frame2, center, None, winSize = size, maxLevel=4)
        obj_moved = move_obj(pt_moved[0], obj)
        prediction.append(obj_moved)
    return prediction


def merge_two_obj(obj1: GMCItem, obj2: GMCItem, k: float) -> GMCItem:
    assert obj1['type'] == obj2['type']
    assert obj1.get('tags') == obj2.get('tags')

    merged: GMCItem = {
        'type': obj1['type'],
        'data': [],
    }
    if 'tags' in obj1:
        merged['tags'] = obj1['tags']
    for d1, d2 in zip(obj1['data'], obj2['data']):
        merged['data'].append( k * d1 + (1 - k) * d2)

    return merged


def normalize_rects(objects: List[GMCItem]) -> List[GMCItem]:
    for obj in objects:
        if obj['type'] == 'rect':
            d = obj['data']
            if d[2] < 0:
                d[0] += d[2]
                d[2] = abs(d[2])
            if d[3] < 0:
                d[1] += d[3]
                d[3] = abs(d[3])
    return objects


def interpolate_core(
        first_objects: List[GMCItem],
        last_objects: List[GMCItem],
        file_paths: List[str]) -> List[List[GMCItem]]:
    assert file_paths, file_paths

    # normalize rects
    first_objects = normalize_rects(first_objects)
    last_objects = normalize_rects(last_objects)

    # forward loop
    forw: List[List[GMCItem]] = []
    forw.append(first_objects)
    for file1, file2 in zip(file_paths[:-1], file_paths[1:]):
        new_obj = predict_cv(forw[-1], file1, file2)
        forw.append(new_obj)

    # back loop
    back: List[List[GMCItem]] = []
    back.append(last_objects)
    for file1, file2 in reversed(list(zip(file_paths[:-1], file_paths[1:]))):
        new_obj = predict_cv(back[-1], file2, file1)
        back.append(new_obj)
    back = back[::-1]

    # merge
    ret: List[List[GMCItem]] = []
    ret.append(first_objects)
    n_frames = len(forw) - 1
    for frame_idx, (frame1_obj, frame2_obj) in enumerate(
            list(zip(forw, back))[1:-1]):
        k = float(n_frames - frame_idx - 1) / n_frames
        merged_frame: List[GMCItem]  = []
        for obj1, obj2 in zip(frame1_obj, frame2_obj):
            m_obj = merge_two_obj(obj1, obj2, k)
            merged_frame.append(m_obj)
        ret.append(merged_frame)
    ret.append(last_objects)

    return ret


def intersect_objects(a: List[GMCItem], b: List[GMCItem]) -> Tuple[List[GMCItem], List[GMCItem]]:
    # unused function
    a_objects = {
        ((obj['type'],), tuple(obj['tags'])): idx for idx, obj in enumerate(a)}
    assert len(a_objects) == len(a)
    b_objects = {
        ((obj['type'],), tuple(obj['tags'])): idx for idx, obj in enumerate(b)}
    assert len(b_objects) == len(b)
    out_tags = sorted(set(a_objects) & set(b_objects))
    return (
        [a[a_objects[tag]] for tag in out_tags],
        [b[b_objects[tag]] for tag in out_tags]
    )


def main_interpolate(first_frame_markup_path: str, last_frame_markup_path: str, file_paths: List[str]) -> None:
    # unused function
    with open(first_frame_markup_path) as f:
        first_frame_markup = json_load(f)
    with open(last_frame_markup_path) as f:
        last_frame_markup = json_load(f)

    first_intersected, last_intersected = intersect_objects(
        first_frame_markup.get('objects', ()),
        last_frame_markup.get('objects', ()))

    interpolated_objects = interpolate_core(
        first_intersected, last_intersected, file_paths)

    for idx, frame in enumerate(interpolated_objects):
        print(" {} ".format(idx).center(40, '-'))
        for obj in frame:
            print(obj)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    predict_parser = subparsers.add_parser("predict")
    predict_parser.add_argument("frame_1_path")
    predict_parser.add_argument("frame_2_path")
    predict_parser.add_argument("markup_path")
    predict_parser.set_defaults(func=predict)

    predict_parser = subparsers.add_parser("interpolate")
    predict_parser.add_argument("first_frame_markup_path")
    predict_parser.add_argument("last_frame_markup_path")
    predict_parser.add_argument("file_paths", nargs='+')
    predict_parser.set_defaults(func=main_interpolate)

    args = vars(parser.parse_args())
    func = args.pop('func')
    func(**args)

if __name__ == '__main__':
    main()
