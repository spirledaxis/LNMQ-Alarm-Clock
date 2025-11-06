import framebuf  # type: ignore


def make_icon(data, x=8, y=8):
    return framebuf.FrameBuffer(
        bytearray(data), x, y, framebuf.MONO_VLSB)
