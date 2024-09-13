from typing import Optional
from PyQt5 import QtGui, QtCore, QtWidgets
from .utils import get_icon, separator, new_action, tr

Qt = QtCore.Qt


class TabRenamer(QtCore.QObject):
    def eventFilter(
        self, tab_bar: QtWidgets.QTabBar, event: QtCore.QEvent
    ) -> bool:
        if event.type() == event.MouseButtonDblClick:
            tab_idx = tab_bar.tabAt(event.pos())
            if tab_idx >= 0:
                text, ok = QtWidgets.QInputDialog.getText(
                    tab_bar,
                    tr("Tab Name"),
                    "?",
                    QtWidgets.QLineEdit.Normal,
                    tab_bar.tabText(tab_idx),
                )
                if ok and text:
                    tab_bar.setTabText(tab_idx, text)
            return True
        return False


class MdiArea(QtWidgets.QMdiArea):
    def __init__(self, parent: QtCore.QObject) -> None:
        super().__init__(
            parent,
            objectName="mdi_area",
            viewMode=QtWidgets.QMdiArea.TabbedView,
        )

        # Setting elide mode
        tab_bar: QtWidgets.QTabBar = self.findChild(QtWidgets.QTabBar)
        tab_bar.setElideMode(Qt.ElideMiddle)
        tab_bar.setMovable(True)
        tab_bar.setTabsClosable(True)
        self._renamer = TabRenamer()
        tab_bar.installEventFilter(self._renamer)

        # Actions
        close_all_act = new_action(
            self,
            QtGui.QIcon(),
            tr("Close &All"),
            ("Ctrl+Alt+Shift+W",),
            triggered=self.closeAllSubWindows,
        )

        close_others_act = new_action(
            self,
            QtGui.QIcon(),
            tr("Close &Others"),
            ("Ctrl+Alt+W",),
            triggered=self.close_others,
        )

        self.fullscreen_act = new_action(
            self,
            "fullscreen",
            tr("&Fullscreen"),
            ("Ctrl+F11",),
            checkable=True,
            toggled=self.fullscreen,
        )

        tile_act = new_action(
            self, "tile", tr("&Tile"), triggered=self.tileSubWindows
        )

        tile_vert_act = new_action(
            self,
            "tile_v",
            tr("&Tile Vertical"),
            ("Ctrl+Alt+Left",),
            triggered=self.tile_vertical,
        )

        tile_horz_act = new_action(
            self,
            "tile_h",
            tr("&Tile Horizontal"),
            ("Ctrl+Alt+Up",),
            triggered=self.tile_horizontal,
        )

        tile_vert_rev_act = new_action(
            self,
            "tile_v",
            tr("&Tile Vertical Reverse"),
            ("Ctrl+Alt+Right",),
            triggered=self.tile_vertical_rev,
        )

        tile_horz_rev_act = new_action(
            self,
            "tile_h",
            tr("&Tile Horizontal Reverse"),
            ("Ctrl+Alt+Down",),
            triggered=self.tile_horizontal_rev,
        )

        cascade_act = new_action(
            self,
            "cascade",
            tr("&Cascade"),
            ("Ctrl+Alt+C",),
            triggered=self.cascadeSubWindows,
        )

        KS = QtGui.QKeySequence
        next_act = new_action(
            self,
            "next",
            tr("Ne&xt"),
            (KS.NextChild,),
            triggered=self.activateNextSubWindow,
        )

        previous_act = new_action(
            self,
            "prev",
            tr("Pre&vious"),
            (KS.PreviousChild,),
            triggered=self.activatePreviousSubWindow,
        )

        self.menu_actions = [
            close_all_act,
            close_others_act,
            self.fullscreen_act,
            separator(self),
            tile_act,
            tile_vert_act,
            tile_horz_act,
            tile_vert_rev_act,
            tile_horz_rev_act,
            cascade_act,
            separator(self),
            next_act,
            previous_act,
        ]
        self.addActions(self.menu_actions)  # so shortcuts work

    def close_others(self) -> None:
        w = self.currentSubWindow()
        for window in self.subWindowList():
            if window is not w:
                window.close()

    def fullscreen(self, state: bool) -> None:
        if state:  # go fullscreen
            self.splitter: QtWidgets.QSplitter = self.parent()
            self._splitter_state = self.splitter.saveState()
            self.setParent(self.splitter.parent())
            self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
            self.showFullScreen()
        else:
            self.setParent(self.splitter)
            self.splitter.restoreState(self._splitter_state)
            self.splitter = None
            self.showNormal()

    def add(
        self,
        window: QtWidgets.QWidget,
        new: bool = False,
        icon: Optional[str] = None,
    ) -> None:
        if (
            not new
            and QtWidgets.QApplication.keyboardModifiers() != Qt.AltModifier
            and self.activeSubWindow() is not None
        ):
            self.closeActiveSubWindow()
        window.setAttribute(Qt.WA_DeleteOnClose)
        sub_window = self.addSubWindow(window)
        sub_window.setAttribute(Qt.WA_DeleteOnClose)
        sub_window.systemMenu().addActions(self.menu_actions)
        sub_window.destroyed.connect(self.should_exit_fullscren)

        if icon:
            sub_window.setWindowIcon(get_icon(icon))
        window.showMaximized()

    def tile_vertical_rev(self) -> None:
        self.tile_vertical(True)

    def tile_horizontal_rev(self) -> None:
        self.tile_horizontal(True)

    def tile_horizontal(self, reverse: bool) -> None:
        windows = self.subWindowList()  # len(windows) != 0 always!
        height = self.viewport().height() // len(windows)
        x = 0
        if reverse:
            windows.reverse()
        for window in windows:
            window.showNormal()
            window.resize(self.width(), height)
            window.move(0, x)
            x += height

    def tile_vertical(self, reverse: bool) -> None:
        windows = self.subWindowList()  # len(windows) != 0 always!
        width = self.width() // len(windows)
        x = 0
        if reverse:
            windows.reverse()
        height = self.viewport().height()
        for window in windows:
            window.showNormal()
            window.resize(width, height)
            window.move(x, 0)
            x += width

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        # Alt+F4 in fullscreen
        self.fullscreen_act.setChecked(False)
        event.ignore()

    def should_exit_fullscren(self, _) -> None:
        if not self.subWindowList():
            self.fullscreen_act.setChecked(False)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        # Not as action as `Ambiguous shortcut overload: Esc`
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.fullscreen_act.setChecked(False)
        else:
            return QtWidgets.QMdiArea.keyPressEvent(self, event)
