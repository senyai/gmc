from os import path as osp, name as osname
import sys
from cffi import FFI
from .error import check_ret, AVERROR_EOF
from fractions import Fraction


def dlname(name):
    # check standard directories for windows an linux
    if osname == "nt":
        name += ".dll"
        fn = osp.join(osp.dirname(__file__), name)
    else:
        name = name.rsplit("-", 1)[0]
        fn = osp.join(
            osp.expanduser("~"), ".local", "lib", "lib" + name + ".so"
        )
    if osp.isfile(fn):
        return fn

    from ctypes.util import find_library

    return find_library(name)


ffi = FFI()
NULL = ffi.NULL
for libname in (
    "avutil_t.h",
    "avutil.h",
    "avcodec_t.h",
    "avcodec.h",
    "avformat_t.h",
    "avformat.h",
    "swscale_t.h",
    "swscale.h",
):
    with open(osp.join(osp.dirname(__file__), libname)) as f:
        ffi.cdef(f.read())

AVUTIL = ffi.dlopen(dlname("avutil-55"))
ffi.dlopen(dlname("swresample-2"))  # trick to have in right folder
AVCODEC = ffi.dlopen(dlname("avcodec-57"))
AVFORMAT = ffi.dlopen(dlname("avformat-57"))
SWSCALE = ffi.dlopen(dlname("swscale-4"))

AVFORMAT.av_register_all()  # void
AVFORMAT.avformat_network_init()
AVCODEC.avcodec_register_all()

AV_CODEC_CAP_DELAY = 1 << 5


class VideoReader:
    def __init__(self, path):
        path_enc = path.encode(sys.getfilesystemencoding())
        self._format_context = self._get_format_context(path_enc)
        self._av_stream = next(self._get_video_stream(self._format_context[0]))
        self._av_codec = self._get_decoder(self._av_stream)
        self._converter = self._get_converter(self._av_codec)
        self._frame = ffi.gc(AVUTIL.av_frame_alloc(), self._av_frame_free)
        self._current_frame = 0

        AVINDEX_KEYFRAME = AVFORMAT.AVINDEX_KEYFRAME
        self._key_index_table = [
            i
            for i in range(self._av_stream.nb_index_entries)
            if self._av_stream.index_entries[i].flags & AVINDEX_KEYFRAME
        ]
        # assert self._key_index_table

    def __len__(self):
        """
        :returns: number of frames
        """
        return self._av_stream.nb_index_entries

    @property
    def current_frame(self):
        """
        :returns: frame number that will be read on next `next_frame` call
        """
        return self._current_frame

    @property
    def fps(self):
        """
        :returns: average fps
        """
        r = self._av_stream.r_frame_rate
        return Fraction(r.num, r.den)

    def next_frame(self, backend=None):
        """
        :param backend: None, `qt4`, or `minimg`
        :returns: (frame number, image) or (None, None)
        """
        packet = ffi.gc(ffi.new("AVPacket *"), AVCODEC.av_packet_unref)
        got_frame = ffi.new("int*")

        while True:
            read_ret = AVFORMAT.av_read_frame(self._format_context[0], packet)
            if read_ret == AVERROR_EOF:
                break
            check_ret(read_ret)
            if packet.stream_index == self._av_stream.index:
                send_ret = AVCODEC.avcodec_send_packet(self._av_codec, packet)
                check_ret(send_ret)
                receive_ret = AVCODEC.avcodec_receive_frame(
                    self._av_codec, self._frame
                )
                EAGAIN = -11
                if receive_ret == EAGAIN:
                    continue
                check_ret(receive_ret)
                self._current_frame += 1
                if backend is None:
                    img = None
                else:
                    img = getattr(self, backend)()
                return (self._current_frame - 1, img)
            AVCODEC.av_packet_unref(packet)
        return (None, None)

    def minimg(self):
        from minimg import MinImg, TYP_UINT8

        img = MinImg.empty(
            self._av_codec.width, self._av_codec.height, 3, TYP_UINT8
        )
        SWSCALE.sws_scale(
            self._converter,
            self._frame.data,
            self._frame.linesize,
            0,
            self._frame.height,
            ffi.new("uint8_t **", img._mi.pScan0),
            ffi.new("int *", img._mi.stride),
        )
        return img

    def qt5(self):
        from PyQt5.QtGui import QImage

        img = QImage(
            self._av_codec.width, self._av_codec.height, QImage.Format_RGB888
        )
        pScan0 = ffi.cast("uint8_t *", int(img.bits()))
        SWSCALE.sws_scale(
            self._converter,
            self._frame.data,
            self._frame.linesize,
            0,
            self._frame.height,
            ffi.new("uint8_t **", pScan0),
            ffi.new("int *", img.bytesPerLine()),
        )
        return img

    def _find_key_index(self, pos):
        prev_key_frame = 0
        for i, key_frame in enumerate(self._key_index_table):
            if key_frame > pos:
                return prev_key_frame
            prev_key_frame = key_frame
        return prev_key_frame

    def seek(self, seek_frame):
        if seek_frame == self._current_frame:
            return
        key_frame = self._find_key_index(seek_frame)
        check_ret(
            AVFORMAT.av_seek_frame(
                self._format_context[0],
                self._av_stream.index,
                key_frame,
                0,  # seeks to key-frame in any direction
            )
        )
        self._current_frame = key_frame
        AVCODEC.avcodec_flush_buffers(self._av_codec)
        while self._current_frame < seek_frame:
            self.next_frame(backend=None)
        assert self._current_frame == seek_frame

    @staticmethod
    def _get_format_context(path):
        format_context = ffi.gc(
            ffi.new("AVFormatContext **"), AVFORMAT.avformat_close_input
        )

        opts = ffi.new("AVDictionary **")
        AVUTIL.av_dict_set(opts, b"analyzeduration", b"0", 0)
        AVUTIL.av_dict_set(opts, b"rtsp_transport", b"tcp", 0)
        AVUTIL.av_dict_set(opts, b"reorder_queue_size", b"1", 0)
        AVUTIL.av_dict_set(opts, b"stimeout", b"5000", 0)

        check_ret(
            AVFORMAT.avformat_open_input(format_context, path, NULL, opts)
        )
        if format_context[0] == NULL:
            raise Exception("Invalid context")
        return format_context

    @staticmethod
    def _get_decoder(av_stream):
        av_codec = AVCODEC.avcodec_find_decoder(av_stream.codec.codec_id)
        if av_codec == NULL:
            Exception("Unsupported codec")
        check_ret(AVCODEC.avcodec_open2(av_stream.codec, av_codec, NULL))
        return ffi.gc(av_stream.codec, AVCODEC.avcodec_close)

    @staticmethod
    def _get_video_stream(format_context):
        check_ret(AVFORMAT.avformat_find_stream_info(format_context, NULL))
        for i in range(format_context.nb_streams):
            av_stream = format_context.streams[i]
            if av_stream.codec.codec_type == AVUTIL.AVMEDIA_TYPE_VIDEO:
                yield av_stream

    @staticmethod
    def _get_converter(av_codec):
        pix_fmt = {
            AVUTIL.AV_PIX_FMT_YUVJ420P: AVUTIL.AV_PIX_FMT_YUV420P,
            AVUTIL.AV_PIX_FMT_YUVJ422P: AVUTIL.AV_PIX_FMT_YUV422P,
            AVUTIL.AV_PIX_FMT_YUVJ444P: AVUTIL.AV_PIX_FMT_YUV444P,
            AVUTIL.AV_PIX_FMT_YUVJ440P: AVUTIL.AV_PIX_FMT_YUV440P,
        }.get(av_codec.pix_fmt, av_codec.pix_fmt)
        converter = SWSCALE.sws_getContext(
            av_codec.width,
            av_codec.height,
            pix_fmt,
            av_codec.width,
            av_codec.height,
            AVUTIL.AV_PIX_FMT_RGB24,
            SWSCALE.SWS_BICUBIC,
            NULL,
            NULL,
            NULL,
        )
        if converter == NULL:
            raise Exception("Converter initialization failed")
        return ffi.gc(converter, SWSCALE.sws_freeContext)

    def _av_frame_free(self, frame):
        AVUTIL.av_frame_free(ffi.new("AVFrame**", frame))
