"""Generate FlipClock.ico from the app's own visual language.

Run this only when the icon needs changing:

    py make_icon.py

Windows picks whichever embedded size best fits the context, so the small
sizes deliberately drop the numeral -- at 16px a digit is unreadable mush and
the tile silhouette alone reads better.
"""
import struct
import sys

from PyQt6.QtCore import Qt, QBuffer, QByteArray, QRectF, QPointF
from PyQt6.QtGui import (QGuiApplication, QImage, QPainter, QColor, QFont,
                         QFontMetrics, QPen)

SIZES = [16, 24, 32, 48, 64, 128, 256]

TILE = QColor(45, 45, 45)
SEAM = QColor(33, 150, 243)   # the app's accent blue
DIGIT = QColor(255, 255, 255)


def render(size):
    """Draw a single flip tile at the given pixel size."""
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    inset = max(1.0, size * 0.06)
    radius = max(2.0, size * 0.16)
    body = QRectF(inset, inset, size - 2 * inset, size - 2 * inset)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(TILE)
    painter.drawRoundedRect(body, radius, radius)

    # Below roughly 48px the numeral turns to mush, so show the tile alone.
    if size >= 48:
        font = QFont("Arial", 1, QFont.Weight.Bold)
        font.setPixelSize(int(size * 0.60))
        painter.setFont(font)
        painter.setPen(DIGIT)
        ink = QFontMetrics(font).tightBoundingRect("8")
        x = (size - ink.width()) / 2.0 - ink.x()
        y = (size - ink.height()) / 2.0 - ink.y()
        painter.drawText(int(round(x)), int(round(y)), "8")

    painter.setPen(QPen(SEAM, max(1.0, size * 0.055)))
    mid = size / 2.0
    painter.drawLine(QPointF(inset + radius * 0.25, mid),
                     QPointF(size - inset - radius * 0.25, mid))
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
