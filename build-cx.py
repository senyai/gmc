#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# usage example: setup.py bdist_msi
# usage example: setup.py build

import sys
import os
from cx_Freeze import setup, Executable

os.environ['TCL_LIBRARY'] = os.path.join(sys.exec_prefix, 'tcl', 'tcl8.6')
os.environ['TK_LIBRARY'] = os.path.join(sys.exec_prefix, 'tcl', 'tk8.6')

# "import" __version__
for line in open("gmc/__init__.py"):
    if line.startswith("__version__"):
        exec(line)
        break
else:
    raise ValueError('no version')

shortcut_table = [
    ("DesktopShortcut",        # Shortcut
     "DesktopFolder",          # Directory_
     "GMC",                    # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]run_gmc.exe", # Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
    ),
    ("StartupShortcut",        # Shortcut
     "StartupFolder",          # Directory_
     "GMC",                    # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]run_gmc.exe", # Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
    )
]

options = {
    'build_exe': {
        'packages': [
            'PyQt5.sip',
            'numpy',
            'PIL',
            'cv2',
        ],
        "excludes": [
            "tkinter",
            "nbconvert",
            "nbformat",
            "scipy",
            "pygments",
            "jinja2",
            "jupyter_client",
            "matplotlib",
            "notebook",
            "setuptools",
            "xml",
            "xmlrpc",
            "zmq",
            "tornado",
            "traitlets",
            "curses",
            "asyncio",
            "backcall",
            "certifi",
            "chardet",
            "lib2to3",
            "unittest",
            # "urllib",
            "pytz",
            "distutils",
            # "ctypes",
            "html",
            "http",
        ],
        'includes': [
            'atexit',

            'gmc.markup_objects',
            'gmc.markup_objects.graph',
            'gmc.markup_objects.line',
            'gmc.markup_objects.moveable_diamond',
            'gmc.markup_objects.point',
            'gmc.markup_objects.polygon',
            'gmc.markup_objects.quadrangle',
            'gmc.markup_objects.rect',
            'gmc.markup_objects.tags',

            'gmc.file_widgets',
            'gmc.file_widgets.multiple_sources_one_destination',
            'gmc.file_widgets.one_source_one_destination',

            'gmc.utils',
            'gmc.utils.dicts',
            'gmc.utils.image',
            'gmc.utils.json',
            'gmc.utils.read_properties',

            'gmc.views',
            'gmc.views.filesystem_view',
            'gmc.views.filesystem_widget',
            'gmc.views.image_view',
            'gmc.views.image_widget',
            'gmc.views.properties_view',

            'gmc.schemas',
            'gmc.schemas.tagged_objects',
            # 'gmc.schemas.map_markup',
            # 'gmc.schemas.number_plates_video',
            # 'gmc.schemas.feature_matching',
            'gmc.schemas.fields',
            # 'gmc.schemas.ballfish',

        ],
        'include_files': [
            ('gmc/schemas/tagged_objects/__init__.py',
             'lib/gmc/schemas/tagged_objects/__init__.py'
            ),
            ('gmc/schemas/tagged_objects/markup_interpolation.py',
             'lib/gmc/schemas/tagged_objects/markup_interpolation.py'
            ),
            # ('api_for_python.dll',
            #  'lib/gmc/schemas/number_plates/api_for_python.dll'
            # ),
            # ('../../data/logos',
            #  'lib/gmc/schemas/number_plates/data/logos'
            # ),
            # ('../../data/alphabets.json',
            #  'lib/gmc/schemas/number_plates/data/alphabets.json'
            # ),
            # ('../../data/symbol_recognizers.json',
            #  'lib/gmc/schemas/number_plates/data/symbol_recognizers.json'
            # ),
            # ('../../data/templates',
            #  'lib/gmc/schemas/number_plates/data/templates'
            # ),
        ],
    },
    'bdist_msi': {
        'data': {
            'Shortcut': shortcut_table
        }
    }
}

here = os.path.dirname(__file__)
executables = [
    Executable(
        'run_gmc.py',
        base=None,
        icon=os.path.join(here, 'gmc/resources/gmc.ico'),
    )
]

setup(name='GMC',
      version=__version__,
      description='General Markup Creator',
      options=options,
      executables=executables
      )
