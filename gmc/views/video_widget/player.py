import sys
from gmcffmpeg import VideoReader
from itertools import count
from time import clock, sleep
from minimg.view import connect


def main():
    vr = VideoReader(
        r"rtsp://10.0.70.45:554/user=admin&password=&channel=1&stream=0.sdp?"
    )
    minviewer = connect(__file__)
    minviewer.clear()
    frame_no, img = vr.next_frame(backend="minimg")
    img_idx = minviewer.add_image(img, contrast=False)
    while True:
        a = clock()
        frame_no, img = vr.next_frame(backend="minimg")
        b = clock()
        minviewer.set_image(img_idx, img.scale(0.25))
        c = clock()
        print("FPS: read", 1 / (b - a), " display", 1 / (c - b))


if __name__ == "__main__":
    main()
