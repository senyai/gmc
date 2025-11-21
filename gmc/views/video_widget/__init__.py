from PyQt5 import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt
from ...utils import separator, get_icon
from ..image_view import ImageView
from .gmcffmpeg import VideoReader
from .seek_slider import SeekSlider


def _nicenum(x):
    from math import floor, log10

    expv10 = 10 ** floor(log10(x))
    return floor(x / expv10 * 2.0 + 0.5) * 0.5 * expv10


class VideoWidget(QtWidgets.QWidget):
    pixmap_changed = QtCore.pyqtSignal(QtGui.QPixmap, name="pixmap_changed")
    before_frame_load = QtCore.pyqtSignal(
        int, QtWidgets.QGraphicsScene, name="before_frame_load"
    )
    after_frame_load = QtCore.pyqtSignal(
        int, QtWidgets.QGraphicsScene, name="after_frame_load"
    )
    _frame_number = None

    def __init__(self, default_actions):
        super().__init__()
        self._default_actions = default_actions
        self._markup_group = QtWidgets.QActionGroup(self)
        self._toolbar = self._create_toolbar()
        self._view = ImageView()
        self._frame_label = QtWidgets.QLabel(
            alignment=Qt.AlignRight | Qt.AlignVCenter, margin=4
        )
        self._seek_slider = SeekSlider(
            limit_widget=self._view, valueChanged=self._seek
        )

        seek_toolbar = QtWidgets.QToolBar(self)
        seek_toolbar.setStyleSheet("QToolBar{border: 0px;}")
        seek_toolbar.setOrientation(Qt.Horizontal)

        self._play_action = QtWidgets.QAction(
            get_icon("play"),
            "Play",
            self,
            checkable=True,
            toggled=self._play_toggled,
        )
        seek_toolbar.addAction(self._play_action)
        seek_toolbar.addAction(
            QtWidgets.QAction(
                get_icon("prev_event"), "Previous Event", self, enabled=False
            )
        )
        seek_toolbar.addAction(
            QtWidgets.QAction(
                get_icon("next_event"), "Next Event", self, enabled=False
            )
        )
        slider_height = self._seek_slider.minimumSizeHint().height()
        seek_toolbar.setIconSize(QtCore.QSize(slider_height, slider_height))

        layout = QtWidgets.QHBoxLayout(self, margin=0, spacing=0)
        layout.addWidget(self._toolbar, 0, Qt.AlignTop)
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addWidget(self._view)
        slider_layout = QtWidgets.QHBoxLayout()
        slider_layout.addWidget(seek_toolbar)
        slider_layout.addSpacing(10)
        slider_layout.addWidget(self._seek_slider)
        slider_layout.addWidget(self._frame_label)
        right_layout.addLayout(slider_layout)
        right_layout.addSpacing(16)
        layout.addLayout(right_layout)

    def _play_toggled(self, play):
        if play:
            self._seek_slider.setRepeatAction(
                QtWidgets.QSlider.SliderSingleStepAdd,
                20,
                1.0 / self._fps * 500,
            )
        else:
            self._seek_slider.setRepeatAction(
                QtWidgets.QSlider.SliderNoAction, 0, 0
            )

    def add_markup_action(self, name, shortcut, icon, markup_object, **kwargs):
        action = QtWidgets.QAction(
            get_icon(icon),
            f"{name} ({shortcut})",
            self,
            triggered=lambda: self._set_markup_object(markup_object),
            shortcut=shortcut,
            checkable=True,
            **kwargs,
        )
        self._toolbar.addAction(action)
        self._markup_group.addAction(action)
        self._view.addAction(action)
        return action

    def add_default_actions(self):
        next_frame_action = QtWidgets.QAction(
            get_icon("next_frame"),
            "Next Frame (F)",
            self,
            triggered=self.next_frame,
            shortcut="F",
        )
        next_second_action_ = QtWidgets.QAction(
            get_icon("next_second"),
            "Next Second (Shift+F)",
            self,
            triggered=lambda: self._go(self._fps),
            shortcut="Shift+F",
        )

        previous_frame_action = QtWidgets.QAction(
            get_icon("prev_frame"),
            "Previous Frame (B)",
            self,
            triggered=lambda: self._go(-1),
            shortcut="B",
        )
        previous_second_action = QtWidgets.QAction(
            get_icon("prev_second"),
            "Previous Second (Shift+B)",
            self,
            triggered=lambda: self._go(-self._fps),
            shortcut="Shift+B",
        )

        nav = (
            next_frame_action,
            next_second_action_,
            previous_frame_action,
            previous_second_action,
        )

        for actions in (
            self._view.get_zoom_actions(),
            nav,
            (self._view.delete_action,),
            self._default_actions,
        ):
            self._view.addAction(separator(self))
            self._toolbar.addAction(separator(self))
            self._view.addActions(actions)
            self._toolbar.addActions(actions)
        del self._default_actions

    def next_frame(self):
        """for external user call"""
        self._go(1)

    def _create_toolbar(self):
        toolbar = QtWidgets.QToolBar(self)
        toolbar.setOrientation(Qt.Vertical)
        return toolbar

    def _set_markup_object(self, cls):
        return self._view.set_markup_object(cls)

    def open_file(self, movie_filename):
        self._video_reader = VideoReader(movie_filename)
        frames_count = len(self._video_reader)
        self._seek_slider.setMaximum(frames_count - 1)

        metrics = QtGui.QFontMetricsF(self.font())
        min_width = (
            metrics.width("9" * len(str(frames_count)))
            + self._frame_label.margin() * 2
        )
        self._frame_label.setMinimumWidth(min_width)
        self._seek_slider.setTickInterval(int(_nicenum(frames_count / 25)))
        self._seek_slider.valueChanged.emit(0)

    @property
    def _fps(self):
        return int(round(self._video_reader.fps))

    def _seek(self, frame_number):
        if self._frame_number is not None:
            self.before_frame_load.emit(self._frame_number, self.scene())
        self._frame_label.setText(str(frame_number))
        self._video_reader.seek(frame_number)

        res_frame, img = self._video_reader.next_frame(backend="qt5")
        assert frame_number == res_frame
        pixmap = QtGui.QPixmap.fromImage(img)
        self.pixmap_changed.emit(pixmap)
        self._view.set_pixmap(pixmap)
        self._frame_number = frame_number
        self.after_frame_load.emit(frame_number, self.scene())

    def _go(self, where):
        self._seek_slider.setValue(
            self._video_reader.current_frame + where - 1
        )

    def scene(self):
        return self._view.scene()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self._view.setFocus()
