#!/usr/bin/env python3
"""
gmc
===

Main module for gui start
"""
import argparse
import signal
import sys
__version__ = "1.5.2"


def _sigint(signum:int, _: int) -> None:
    from time import time
    now = time()
    if now - getattr(_sigint, 'time', 0) < 3:
        sys.exit(signum)
    print(" Ctrl+C now to force exit ")
    setattr(_sigint, 'time', now)


def application():
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
        from gmc.main_window import MainWindow
        main_window = MainWindow(__version__, app, vars(parse_args()))
        signal.signal(signal.SIGINT, _sigint)
    except Exception:
        import traceback
        traceback.print_exc(file=sys.stdout)
        print('press <Enter> to exit')
        input()
        return

    main_window.show()
    return app, main_window


def parse_args() -> argparse.Namespace:
    from gmc.schemas import iter_schemas
    parser = argparse.ArgumentParser("GMC runner")

    parser.add_argument('--schema',
        choices=[s for (s, _) in iter_schemas()],
        help="schema, e.g. tagged_objects (default: previously used schema)")
    parser.add_argument('-s', '--src_dir',
        help="root of images dir")
    parser.add_argument('-d', '--dst_dir',
        help="root of markup dir")

    return parser.parse_args()


def main() -> None:
    app = application()
    if app:
        sys.exit(app[0].exec_())


if __name__ == "__main__":
    main()
