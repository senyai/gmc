from __future__ import annotations
from typing import TypedDict, Sequence, cast
import argparse
import signal
import sys


class GMCArguments(TypedDict):
    schema: str | None
    src_dir: str | None
    dst_dir: str | None
    external_schemas: list[str]


def _sigint(signum: int, _: None) -> None:
    from time import time

    now = time()
    if now - getattr(_sigint, "time", 0) < 3:
        sys.exit(signum)
    print(" Ctrl+C now to force exit ")
    setattr(_sigint, "time", now)


def application(args: GMCArguments):
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt

    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    except AttributeError:
        print("warning: old PyQt5. HighDpi support disabled")

    app = QApplication(sys.argv)

    try:
        xrange
        from PyQt5.QtWidgets import QMessageBox

        QMessageBox.critical(None, "GMC", "Python 3 is required")
        return
    except NameError:
        pass  # good, python 3

    try:
        from .main_window import MainWindow
        from . import __version__

        main_window = MainWindow(__version__, app, args)
        signal.signal(signal.SIGINT, _sigint)
    except Exception:
        import traceback

        traceback.print_exc(file=sys.stdout)
        print("press <Enter> to exit")
        input()
        return

    main_window.show()
    return app, main_window


def parse_args(external: Sequence[str]) -> GMCArguments:
    from .schemas import iter_schemas

    parser = argparse.ArgumentParser("GMC runner")

    all_schemas = ", ".join([info[0] for info in iter_schemas(external)])
    parser.add_argument(
        "--schema",
        help=f"schema, e.g. tagged_objects (default: previously used schema,\n"
        f"Available: {all_schemas})",
    )
    parser.add_argument("-s", "--src_dir", help="root of images dir")
    parser.add_argument("-d", "--dst_dir", help="root of markup dir")
    parser.add_argument(
        "--external-schemas",
        nargs="*",
        default=[],
        help="list of files/directories to treat like a schema",
    )
    args = parser.parse_args()
    args.external_schemas.extend(external)
    return cast(GMCArguments, vars(args))


def main(external: Sequence[str] = ()):
    app = application(parse_args(external))
    if app:
        exit(app[0].exec_())
