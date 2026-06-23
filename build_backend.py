from subprocess import check_call
from setuptools.build_meta import *

_build_wheel = build_wheel


def build_wheel(
    wheel_directory, config_settings=None, metadata_directory=None
):
    for executable in ("lrelease-qt5", "lrelease"):
        try:
            check_call(
                [executable, "../i18n/gmc_ru.ts", "-qm", "gmc_ru.qm"],
                cwd="gmc/resources",
            )
        except FileNotFoundError:
            pass
        else:
            break
    else:
        raise FileNotFoundError("`lrelease-qt5` and `lrelease` are missing")
    return _build_wheel(wheel_directory, config_settings, metadata_directory)
