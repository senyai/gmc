# encoding: utf-8
from typing import Any, Dict, Optional, Type
from PyQt5 import QtCore, QtWidgets, QtGui
from .mdi_area import MdiArea
from .schemas import MarkupSchema, load_schema_cls, iter_schemas
from .utils import get_icon, new_action
from .help_label import HelpLabel
from .settings import settings
from .application import GMCArguments
MB = QtWidgets.QMessageBox
Qt = QtCore.Qt
tr = lambda text: QtCore.QCoreApplication.translate("@default", text)


class MainWindow(QtWidgets.QMainWindow):
    _schema_cls: Optional[Type[MarkupSchema]] = None
    _extra_args: GMCArguments

    def __init__(self,
                 version: str,
                 app: QtWidgets.QApplication,
                 extra_args: GMCArguments):
        # enable `get_icon`
        QtCore.QDir.addSearchPath(
            'gmc', QtCore.QFileInfo(f'{__file__}/../resources').absoluteFilePath())

        super().__init__(windowIcon=get_icon("gmc"))  # type: ignore
        self._extra_args = extra_args
        lang = settings.settings.value(
            "lang", QtCore.QLocale.system().name().partition('_')[0])
        if lang == "ru":
            translator = QtCore.QTranslator(self)
            translator.load('gmc:gmc_{}.qm'.format(lang))
            if (translator.isEmpty()):
                print("failed to load translator ({})".format(lang))
            app.installTranslator(translator)
        else:  # in case "C.utf8" locale or something else
            lang = "en"
        self.setWindowTitle(
            tr("GMC {} - General Markup Creator".format(version)))

        self._setup_ui()
        self._load_settings(lang)
        self.startTimer(200)  # this runs py code, to Ctrl+C is caught

    def timerEvent(self, _):
        pass

    def _setup_ui(self):
        self.resize(1000, 770)
        self.setStyleSheet("""QMainWindow::separator, QSplitter::handle {
                background:rgba(0,0,0,50);
                width:4px;
                height:4px;
            } """)
        # main_splitter splits left_frame and mdi_area
        self._main_splitter = QtWidgets.QSplitter(
            self, objectName="main_splitter", orientation=Qt.Horizontal)

        self._setup_left_panel()

        self._mdi_area = MdiArea(self._main_splitter)
        self._mdi_area.subWindowActivated.connect(self._sub_window_changed)

        self.setCentralWidget(self._main_splitter)

    def _sub_window_changed(self, window):
        if window is not None:
            try:
                on_activate = window.widget().on_activate
            except AttributeError:
                return
            on_activate()

    def _setup_left_panel(self):
        left_frame = QtWidgets.QFrame(
            self._main_splitter, objectName="left_frame",
            frameShape=QtWidgets.QFrame.WinPanel, frameShadow=QtWidgets.QFrame.Raised)
        menu_button = self._menu_button()
        self._schema_label = QtWidgets.QLabel(
            sizePolicy=QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred))

        top_widget = QtWidgets.QWidget(
            sizePolicy=QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        top_layout = QtWidgets.QHBoxLayout(top_widget, margin=0)
        top_layout.addWidget(menu_button)
        top_layout.addWidget(self._schema_label)

        self._left_layout = QtWidgets.QVBoxLayout(
            left_frame, objectName="_left_layout")
        self._left_layout.setContentsMargins(5, 0, 5, 5)
        self._left_layout.addWidget(top_widget)

    def _set_left_widget(self, widget: QtWidgets.QWidget):
        if self._left_layout.count() == 2:
            self._left_layout.takeAt(1).widget().setParent(None)
        self._left_layout.addWidget(widget)

    def _menu_button(self):
        size_policy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        menu_button = QtWidgets.QPushButton(
            maximumSize=QtCore.QSize(38, 24),
            icon=get_icon('menu'),
            flat=True,
            sizePolicy=size_policy,
            styleSheet="QPushButton{padding-left:-10px}",
            shortcut="Alt+M",
        )
        main_menu = QtWidgets.QMenu(menu_button)
        menu_button.setMenu(main_menu)

        schema_menu = main_menu.addMenu(get_icon('windows_list'), tr("&Schema"))
        self._schema_act_grp = QtWidgets.QActionGroup(
            schema_menu, triggered=self._schema_triggered)
        for schema_name, caption, path in iter_schemas(
                self._extra_args["external_schemas"]):
            action = QtWidgets.QAction( tr(caption), self, checkable=True)
            self._schema_act_grp.addAction(action)
            action.setData((schema_name, path))
            schema_menu.addAction(action)
        language_menu = main_menu.addMenu(get_icon('cat'), tr("&Language / Язык"))
        self._language_act_grp = QtWidgets.QActionGroup(language_menu)
        for language, caption in (('en', "English"), ('ru', "Русский")):
            action = QtWidgets.QAction(caption, self, checkable=True)
            self._language_act_grp.addAction(action)
            action.setData(language)
            language_menu.addAction(action)
        main_menu.addAction(new_action(
            self, 'help', tr("&Help"), shortcuts=(Qt.Key_F1,),
            triggered=self._on_help,
            shortcutContext=Qt.WindowShortcut
        ))
        settings_act = new_action(
            self, 'gears', tr("Se&ttings"), shortcuts=(Qt.CTRL + Qt.Key_Comma,),
            triggered=self._on_settings,
            shortcutContext=Qt.WindowShortcut
        )
        main_menu.addAction(settings_act)
        self.addAction(settings_act)
        main_menu.addSeparator()
        main_menu.addAction(QtWidgets.QAction(
            self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarMenuButton),
            tr("&About Qt"), self,
            triggered=self._on_about_qt, menuRole=QtWidgets.QAction.AboutQtRole))
        main_menu.addAction(QtWidgets.QAction(
            get_icon('quit'), tr("E&xit"), self,
            triggered=QtWidgets.qApp.quit,
            shortcut=Qt.CTRL + Qt.Key_Q,
            menuRole=QtWidgets.QAction.QuitRole))
        return menu_button

    def _on_help(self):
        path = QtCore.QFileInfo(
            f'{__file__}/../../doc/build/html/index.html').absoluteFilePath()
        if QtCore.QFileInfo.exists(path):
            import webbrowser
            webbrowser.open(u"file://" + path)
        else:
            msg = tr("Help not bundled. {} does not exist.").format(path)
            MB.warning(self, self.windowTitle(), msg, MB.Ok)

    def _on_settings(self):
        from .settings.dialog import create_setting_dialog
        create_setting_dialog(self)

    def _on_about_qt(self):
        import platform
        extra = " @ python {} : {}".format(
            platform.python_version(), platform.architecture()[0])
        MB.aboutQt(self, self.windowTitle() + extra)

    def _schema_triggered(self, action: QtWidgets.QAction):
        if self._schema_cls is not None:
            self._schema_cls.save_settings(settings.settings)
        try:
            self._schema_cls = load_schema_cls(*action.data())
        except Exception as e:
            msg = "Schema `{}` loading error:<br>{}".format(action.data(), e)
            MB.warning(self, self.windowTitle(), msg)
            import traceback
            traceback.print_exc()
            return
        self._schema_label.setText(action.text())
        self._schema_label.setToolTip(action.text())
        data_widget = self._schema_cls.create_data_widget(
            self._mdi_area, self._extra_args)
        assert data_widget, self._schema_cls
        focus_widget = data_widget.focusWidget()
        self._set_left_widget(data_widget)
        focus_widget and focus_widget.setFocus()

    def _load_settings(self, lang: str) -> None:
        settings.load_state_and_geometry(self, "main_window")
        settings.load_state(self._main_splitter, "main_splitter")

        for action in self._language_act_grp.actions():
            if action.data() == lang:
                action.setChecked(True)

        cur_schema = self._extra_args["schema"]
        if cur_schema is None:
            cur_schema = settings.value("schema")

        actions = self._schema_act_grp.actions()
        for action in actions:
            if action.data()[0] == cur_schema:
                action.trigger()
                break
        else:
            self._set_left_widget(
                HelpLabel(tr("Start by selecting a schema")))

    def closeEvent(self, event: QtGui.QCloseEvent):
        """User closes GMC. By default, the event is accepted."""
        self._mdi_area.closeAllSubWindows()
        if self._mdi_area.subWindowList():
            event.ignore()
        else:
            self._save_settings()

    def _save_settings(self):
        """Called from closeEvent."""

        settings.save_state_and_geometry(self, "main_window")
        settings.save_state(self._main_splitter, 'main_splitter')

        settings.set_value(
            'lang', self._language_act_grp.checkedAction().data())
        checked_schema_act = self._schema_act_grp.checkedAction()
        if checked_schema_act is not None:
            schema_name = checked_schema_act.data()[0]
            settings.set_value('schema', schema_name)
        settings.sync()
        if self._schema_cls is not None:
            self._schema_cls.save_settings(settings.settings)
