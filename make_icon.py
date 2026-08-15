"""Generate FlipClock.ico from the app's own visual language.

Run this only when the icon needs changing:

    py make_icon.py

Unlike a numeral rendered in a text font, this glyph is pure geometry (a
stadium-shaped ring split by a seam), so it holds up at every embedded size
down to 16px without needing to be dropped or simplified.
"""
import struct
import sys

from PyQt6.QtCore import Qt, QBuffer, QByteArray, QRectF, QPointF
from PyQt6.QtGui import QGuiApplication, QImage, QPainter, QColor, QPen, QPainterPath

SIZES = [16, 24, 32, 48, 64, 128, 256]

TILE = QColor(20, 20, 20)      # near-black tile, matching the app's flip-tile look
DIGIT = QColor(247, 165, 63)   # the orange from the app's digit segments


def render(size):
    """Draw a single flip tile with an orange '0'-ring digit, split by a seam."""
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background tile.
    tile_inset = max(1.0, size * 0.03)
    tile_radius = size * 0.14
    tile_body = QRectF(tile_inset, tile_inset,
                       size - 2 * tile_inset, size - 2 * tile_inset)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(TILE)
    painter.drawRoundedRect(tile_body, tile_radius, tile_radius)

    # The digit: a tall stadium-shaped ring (rounded-rect outline), narrower
    # than the tile so it reads as a "0" rather than a donut.
    digit_w = size * 0.46
    digit_h = size * 0.72
    cx, cy = size / 2.0, size / 2.0
    digit_box = QRectF(cx - digit_w / 2.0, cy - digit_h / 2.0, digit_w, digit_h)

    pen_w = max(2.0, size * 0.135)
    ring_radius = digit_w / 2.0  # fully rounded ends

    ring_path = QPainterPath()
    ring_path.addRoundedRect(digit_box, ring_radius, ring_radius)

    painter.setPen(QPen(DIGIT, pen_w))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(ring_path)

    # Seam: punch a thin gap through the ring's midline using the tile color,
    # same visual language as a physical flip-clock tile split.
    gap_h = max(1.0, size * 0.045)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(TILE)
    painter.drawRect(QRectF(0, cy - gap_h / 2.0, size, gap_h))

    painter.end()
    return image


def png_bytes(image):
    # The QByteArray must outlive the QBuffer that writes into it, so bind it
    # to a name rather than passing a temporary.
    store = QByteArray()
    buffer = QBuffer(store)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(store)


def write_ico(path, images):
    """Assemble a multi-resolution .ico with PNG-compressed entries."""
    payloads = [png_bytes(img) for img in images]

    header = struct.pack("<HHH", 0, 1, len(payloads))
    offset = len(header) + 16 * len(payloads)

    entries, blobs = b"", b""
    for image, data in zip(images, payloads):
        side = 0 if image.width() >= 256 else image.width()
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32,
                               len(data), offset)
        blobs += data
        offset += len(data)

    with open(path, "wb") as handle:
        handle.write(header + entries + blobs)


def main():
    # Must be bound to a name: if it is garbage collected the font database
    # goes with it and every QFont call crashes.
    app = QGuiApplication(sys.argv)  # noqa: F841
    images = [render(size) for size in SIZES]
    write_ico("FlipClock.ico", images)
    print(f"wrote FlipClock.ico with sizes: {', '.join(map(str, SIZES))}")


if __name__ == "__main__":
    main()