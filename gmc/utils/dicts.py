from collections.abc import Mapping, Sequence
from typing import Any
from .json import ZeroDict


def dicts_are_equal(
    a: Any,
    b: Any,
    eps: float = 1e-7,
    _basic_types: tuple[type[Any], ...] = (int, str, type(None)),
) -> bool:
    if isinstance(a, _basic_types) or isinstance(b, _basic_types):
        return a == b
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < eps
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        return (
            len(a) == len(b)
            and all(key in b for key in a)
            and all(dicts_are_equal(a[key], b[key]) for key in a)
        )
    if isinstance(a, Sequence) and isinstance(b, Sequence):
        return len(a) == len(b) and all(
            dicts_are_equal(v1, v2) for v1, v2 in zip(a, b)
        )
    if isinstance(a, ZeroDict) or isinstance(b, ZeroDict):
        return False
    if type(a) is not type(b):
        # this happens when comparing list of "objects" that have different
        # type i.e "quad" vs "rect"
        # print("WARNING: comparing `{}` and `{}`, which shouldn't happen"
        #       .format(type(a), type(b)))
        # print("a = ", a, "b = ", b)
        return False
    raise Exception("Invalid dict objects ({} vs {})".format(type(a), type(b)))


# assert dicts_are_equal([1, 2, 3], (1, 2, 3))


def dicts_merge(d: dict[str, Any], u: dict[str, Any]):
    for k, v in u.items():
        if isinstance(v, dict) and k in d:
            d[k] = dicts_merge(d[k], v)
        else:
            d[k] = u[k]
    return d


# assert dicts_merge({"a": 1}, {"a": 2, "c": 3}) == {"a": 2, "c": 3}
