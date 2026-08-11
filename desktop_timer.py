"""
Retro Flip Clock Desktop Overlay - Fixed Size Version
A beautiful flip clock widget for Windows desktop.

Requirements: PyQt6, Windows
Install: py -m pip install -r requirements.txt

Usage: py desktop_timer.py  (or double-click run_timer.bat)
"""

import sys
import math
import winreg
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout,
                              QSystemTrayIcon, QMenu, QSlider, QDialog,
                              QFormLayout, QCheckBox, QPushButton, QComboBox)
from PyQt6.QtCore import (QTimer, Qt, QPoint, QPointF, QRect, QSettings,
                          QVariantAnimation, QEasingCurve)
from PyQt6.QtGui import (QFont, QColor, QAction, QIcon, QPainter, QPen, QCursor,
                         QPixmap, QFontMetrics, QFontDatabase, QPolygonF)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


# Bahnschrift is Microsoft's DIN derivative -- DIN is the transit-signage
# typeface, and split-flap boards are railway hardware, so it suits the form
# far better than Arial. Each fallback is checked before use because font
# availability varies across Windows versions.
FONT_PREFERENCES = ("Bahnschrift SemiBold", "Bahnschrift", "Segoe UI", "Arial")
LIGHT_FONT_PREFERENCES = ("Bahnschrift Light", "Bahnschrift", "Segoe UI", "Arial")
MONO_FONT_PREFERENCES = ("Cascadia Mono", "Consolas", "Courier New")
_family_cache = {}


def _first_available_family(preferences):
    """First installed family from the list. Requires a QApplication."""
    cached = _family_cache.get(preferences)
    if cached is None:
        available = set(QFontDatabase.families())
        cached = next((n for n in preferences if n in available), "Arial")
        _family_cache[preferences] = cached
    return cached


def clock_font_family():
    return _first_available_family(FONT_PREFERENCES)


def light_font_family():
    return _first_available_family(LIGHT_FONT_PREFERENCES)


def mono_font_family():
    return _first_available_family(MONO_FONT_PREFERENCES)


# The clock's interchangeable skins. All of them render the same time from the
# same overlay; only the display widget differs.
TEMPLATES = ("flip", "digital", "minimal", "terminal")


# Name of our value under the Run key, and the two registry locations that
# together decide whether Windows actually launches us at sign-in.
AUTOSTART_NAME = "FlipClockOverlay"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APPROVED_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
)


class SingleInstance:
    """Ensure only one instance of the application runs"""
    
    def __init__(self, app_id):
        self.app_id = app_id
        self.socket = QLocalSocket()
        self.socket.connectToServer(app_id)
        
        if self.socket.waitForConnected(500):
            self.is_running = True
            self.socket.disconnectFromServer()
        else:
            self.is_running = False
            self.server = QLocalServer()
            self.server.listen(app_id)
    
    def __del__(self):
        if not self.is_running and hasattr(self, 'server'):
            self.server.close()


class FlipDigit(QWidget):
    """Individual flip clock digit - fixed size, split-flap animation"""

    FLIP_MS = 260

    # Face colours, overridable by subclasses that reskin the tile while
    # keeping the falling-card animation.
    TILE = QColor(45, 45, 45)
    INK = QColor(255, 255, 255)
    MARKER = QColor(220, 220, 220)
    SEAM = QColor(70, 70, 70)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_digit = "0"
        self.previous_digit = "0"
        self.show_am_pm = False
        self.am_pm_text = ""

        # None while idle; runs 0.0 -> 1.0 as the card falls.
        self._progress = None
        self._face_cache = {}

        self._animation = QVariantAnimation(self)
        self._animation.setDuration(self.FLIP_MS)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.valueChanged.connect(self._on_progress)
        self._animation.finished.connect(self._on_finished)

        # Perfect size for 16-inch laptop
        self.setFixedSize(70, 95)

    def _on_progress(self, value):
        self._progress = float(value)
        self.update()

    def _on_finished(self):
        self._progress = None
        self.previous_digit = self.current_digit
        self.update()

    def set_digit(self, digit):
        """Update digit, flipping the old card down to reveal it"""
        if digit == self.current_digit:
            return

        self.previous_digit = self.current_digit
        self.current_digit = digit
        self._animation.stop()
        self._animation.start()

    def _face(self, digit):
        """A fully rendered tile for one digit, cached per digit and size"""
        w, h = self.width(), self.height()
        key = (digit, w, h)
        cached = self._face_cache.get(key)
        if cached is not None:
            return cached

        # Render at device resolution so the tiles stay crisp when Windows
        # is scaling the display.
        ratio = self.devicePixelRatioF()
        pixmap = QPixmap(int(w * ratio), int(h * ratio))
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self.TILE)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 8, 8)
        self._paint_glyph(painter, digit, w, h)
        painter.end()

        self._face_cache[key] = pixmap
        return pixmap

    def _paint_glyph(self, painter, digit, w, h):
        """Draw one digit onto the tile. Subclasses swap in other faces."""
        font = QFont(clock_font_family(), 48, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(self.INK)

        # Centre on the glyph's actual ink, not the font's line box. The line
        # box reserves room for descenders that digits never use, so plain
        # AlignCenter sits the number noticeably low of the seam.
        ink = QFontMetrics(font).tightBoundingRect(digit)
        baseline_x = (w - ink.width()) / 2.0 - ink.x()
        baseline_y = (h - ink.height()) / 2.0 - ink.y()
        painter.drawText(int(round(baseline_x)), int(round(baseline_y)), digit)
    
    def set_am_pm(self, text):
        """Show the AM/PM indicator, repainting only when it actually changes"""
        if not self.show_am_pm or self.am_pm_text != text:
            self.show_am_pm = True
            self.am_pm_text = text
            self.update()

    def clear_am_pm(self):
        """Hide the AM/PM indicator, for 24-hour mode"""
        if self.show_am_pm:
            self.show_am_pm = False
            self.am_pm_text = ""
            self.update()
    
    def paintEvent(self, event):
        """Compose the tile, folding a card down over the seam mid-flip"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        mid = h // 2

        if self._progress is None:
            painter.drawPixmap(0, 0, self._face(self.current_digit))
        else:
            new_face = self._face(self.current_digit)
            old_face = self._face(self.previous_digit)
            top = QRect(0, 0, w, mid)
            bottom = QRect(0, mid, w, h - mid)

            # Source rectangles into a pixmap are addressed in device pixels,
            # not the logical units we lay out in. On a scaled display (this
            # was authored at 125%) passing logical rects crops the wrong
            # region of the face, so every half shows a zoomed digit fragment.
            ratio = new_face.devicePixelRatio()

            def dev(rect):
                return QRect(round(rect.x() * ratio), round(rect.y() * ratio),
                             round(rect.width() * ratio),
                             round(rect.height() * ratio))

            # The halves that have already settled: the new digit is waiting
            # up top, the old one still shows below until the card covers it.
            painter.drawPixmap(top, new_face, dev(top))
            painter.drawPixmap(bottom, old_face, dev(bottom))

            if self._progress < 0.5:
                # First half of the flip: the old top folds down to the seam.
                factor = math.cos(self._progress * math.pi)
                leaf, source, dest = old_face, top, QRect(0, -mid, w, mid)
            else:
                # Second half: the new bottom swings up from the seam.
                factor = math.cos((1.0 - self._progress) * math.pi)
                leaf, source, dest = new_face, bottom, QRect(0, 0, w, h - mid)

            factor = abs(factor)

            # Squashing the card vertically about the seam reads as rotation.
            painter.save()
            painter.translate(0, mid)
            painter.scale(1.0, factor)
            painter.drawPixmap(dest, leaf, dev(source))
            # Darken it as it turns edge-on, so the fold has some depth.
            painter.fillRect(dest, QColor(0, 0, 0, int(90 * (1.0 - factor))))
            painter.restore()

        # Seam last, so it sits above the moving card. Kept a touch lighter
        # than the tile so it reads as a hinge rather than a black slash.
        painter.setPen(QPen(self.SEAM, 2))
        painter.drawLine(5, mid, w - 5, mid)

        # Draw AM/PM indicator - always visible
        if self.show_am_pm:
            small_font = QFont(clock_font_family(), 11, QFont.Weight.Bold)
            painter.setFont(small_font)
            painter.setPen(self.MARKER)
            painter.drawText(8, 18, self.am_pm_text)


class SegmentFlipDigit(FlipDigit):
    """Seven-segment LED face on the same falling-card animation.

    Every digit is the one figure-eight skeleton with different segments lit,
    the unlit ones left as faint ghosts -- so a change reads as the shape
    itself transforming, and the split-flap fold carries it over.
    """

    TILE = QColor(22, 22, 25)
    MARKER = QColor(255, 178, 66, 210)
    SEAM = QColor(58, 54, 46)
    LIT = QColor(255, 178, 66)
    GHOST = QColor(255, 178, 66, 26)

    # Which segments light up per digit: A top, B top-right, C bottom-right,
    # D bottom, E bottom-left, F top-left, G middle.
    SEGMENTS = {
        "0": "ABCDEF", "1": "BC", "2": "ABGED", "3": "ABGCD", "4": "FGBC",
        "5": "AFGCD", "6": "AFGEDC", "7": "ABC", "8": "ABCDEFG", "9": "ABFGCD",
    }

    _skeleton_cache = {}

    @classmethod
    def _skeleton(cls, w, h):
        """The seven segment polygons for a tile of this size, cached."""
        cached = cls._skeleton_cache.get((w, h))
        if cached is not None:
            return cached

        x0, x1 = w * 0.27, w * 0.73
        y0, y1 = h * 0.17, h * 0.83
        ym = (y0 + y1) / 2
        ht = min(w, h) * 0.048   # half the segment thickness
        gap = ht * 0.55          # daylight between segments at the joints

        def hseg(xa, xb, y):
            xa, xb = xa + gap, xb - gap
            return QPolygonF([
                QPointF(xa, y), QPointF(xa + ht, y - ht),
                QPointF(xb - ht, y - ht), QPointF(xb, y),
                QPointF(xb - ht, y + ht), QPointF(xa + ht, y + ht),
            ])

        def vseg(x, ya, yb):
            ya, yb = ya + gap, yb - gap
            return QPolygonF([
                QPointF(x, ya), QPointF(x + ht, ya + ht),
                QPointF(x + ht, yb - ht), QPointF(x, yb),
                QPointF(x - ht, yb - ht), QPointF(x - ht, ya + ht),
            ])

        skeleton = {
            "A": hseg(x0, x1, y0), "G": hseg(x0, x1, ym), "D": hseg(x0, x1, y1),
            "F": vseg(x0, y0, ym), "B": vseg(x1, y0, ym),
            "E": vseg(x0, ym, y1), "C": vseg(x1, ym, y1),
        }
        cls._skeleton_cache[(w, h)] = skeleton
        return skeleton

    def _paint_glyph(self, painter, digit, w, h):
        lit = self.SEGMENTS.get(digit, "")
        painter.setPen(Qt.PenStyle.NoPen)
        for name, polygon in self._skeleton(w, h).items():
            painter.setBrush(self.LIT if name in lit else self.GHOST)
            painter.drawPolygon(polygon)


class ColonSeparator(QLabel):
    """Colon separator - minimal width"""

    def __init__(self, color="white", parent=None):
        super().__init__(parent)
        self.setText(":")
        self.setFixedWidth(15)
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: '{clock_font_family()}';
                font-size: 50px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
                background: transparent;
            }}
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class FlipTimeDisplay(QWidget):
    """Template: the original split-flap row of digit tiles."""

    digit_class = FlipDigit
    colon_color = "white"

    # Where the AM/PM marker lives. The flip face has quiet corners, so the
    # marker sits on the first tile; the seven-segment face fills its tile
    # right to the margins, so drawing it there overlaps the digit -- those
    # tiles hang the marker beside the row instead.
    external_marker_color = None

    def __init__(self, show_seconds, is_12h, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        self.digit_widgets = []
        for i in range(6 if show_seconds else 4):
            if i in (2, 4):
                layout.addWidget(ColonSeparator(self.colon_color))
            digit = self.digit_class()
            self.digit_widgets.append(digit)
            layout.addWidget(digit)

        self.marker_label = None
        if self.external_marker_color and is_12h:
            label = QLabel()
            label.setStyleSheet(f"""
                QLabel {{
                    color: {self.external_marker_color};
                    font-family: '{clock_font_family()}';
                    font-size: 13px;
                    font-weight: bold;
                    padding: 10px 0px 0px 6px;
                    background: transparent;
                }}
            """)
            layout.addWidget(label, 0, Qt.AlignmentFlag.AlignTop)
            self.marker_label = label

    def set_time(self, digits, am_pm):
        for widget, digit in zip(self.digit_widgets, digits):
            widget.set_digit(digit)

        if self.marker_label is not None:
            if self.marker_label.text() != am_pm:
                self.marker_label.setText(am_pm)
            return

        first = self.digit_widgets[0]
        if am_pm:
            first.set_am_pm(am_pm)
        else:
            first.clear_am_pm()


class DigitalTimeDisplay(FlipTimeDisplay):
    """Template: seven-segment LED tiles that flip like split-flap cards."""

    digit_class = SegmentFlipDigit
    colon_color = "#ffb242"
    external_marker_color = "#ffb242"


class MinimalTimeDisplay(QWidget):
    """Template: just the time, in large light type.

    No tiles and no seam -- only a whisper of a backdrop so the digits stay
    readable over a light wallpaper.
    """

    PAD_X = 30
    PAD_Y = 24

    def __init__(self, show_seconds, is_12h, parent=None):
        super().__init__(parent)
        self.text = ""
        self.am_pm = ""

        self.font = QFont(light_font_family(), 58, QFont.Weight.Light)
        self.small_font = QFont(light_font_family(), 13, QFont.Weight.Medium)

        metrics = QFontMetrics(self.font)
        ink = metrics.tightBoundingRect("0123456789")
        self.cell_w = metrics.horizontalAdvance("8")
        self.colon_w = int(self.cell_w * 0.55)
        self.ink_h = ink.height()
        self.ink_y = ink.y()

        digit_count = 6 if show_seconds else 4
        colon_count = 2 if show_seconds else 1
        width = (digit_count * self.cell_w + colon_count * self.colon_w
                 + 2 * self.PAD_X)
        if is_12h:
            width += 14 + QFontMetrics(self.small_font).horizontalAdvance("PM")

        self.setFixedSize(width, self.ink_h + 2 * self.PAD_Y)

    def set_time(self, digits, am_pm):
        pairs = [digits[i:i + 2] for i in range(0, len(digits), 2)]
        text = ":".join(pairs)
        if text != self.text or am_pm != self.am_pm:
            self.text = text
            self.am_pm = am_pm
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(QColor(12, 12, 14, 120))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 14, 14)

        painter.setFont(self.font)
        painter.setPen(QColor(242, 238, 228))
        metrics = QFontMetrics(self.font)
        baseline = self.PAD_Y - self.ink_y

        x = self.PAD_X
        for ch in self.text:
            cell = self.colon_w if ch == ":" else self.cell_w
            glyph_w = metrics.horizontalAdvance(ch)
            painter.drawText(int(x + (cell - glyph_w) / 2), baseline, ch)
            x += cell

        if self.am_pm:
            painter.setFont(self.small_font)
            painter.setPen(QColor(178, 174, 166))
            small_ink = QFontMetrics(self.small_font).tightBoundingRect(self.am_pm)
            painter.drawText(int(x + 14), self.PAD_Y - small_ink.y(), self.am_pm)


class TerminalTimeDisplay(QWidget):
    """Template: a quiet terminal panel with a prompt and a blinking cursor."""

    PAD_X = 24
    PAD_Y = 18
    PROMPT = "$ "

    INK = QColor(134, 222, 148)      # soft phosphor green
    DIM = QColor(92, 128, 100)
    PANEL = QColor(10, 14, 12, 235)
    EDGE = QColor(46, 66, 52)

    def __init__(self, show_seconds, is_12h, parent=None):
        super().__init__(parent)
        self.text = ""
        self.am_pm = ""
        self._cursor_on = True

        self.font = QFont(mono_font_family(), 26, QFont.Weight.Medium)
        metrics = QFontMetrics(self.font)
        self.char_w = metrics.horizontalAdvance("0")
        self.line_h = metrics.ascent() + metrics.descent()

        chars = len(self.PROMPT) + (8 if show_seconds else 5)
        if is_12h:
            chars += 3  # " PM"
        chars += 2      # gap + cursor block

        self.setFixedSize(int(chars * self.char_w + 2 * self.PAD_X),
                          self.line_h + 2 * self.PAD_Y)

        self._blink = QTimer(self)
        self._blink.timeout.connect(self._toggle_cursor)
        self._blink.start(600)

    def _toggle_cursor(self):
        self._cursor_on = not self._cursor_on
        self.update()

    def set_time(self, digits, am_pm):
        pairs = [digits[i:i + 2] for i in range(0, len(digits), 2)]
        text = ":".join(pairs)
        if text != self.text or am_pm != self.am_pm:
            self.text = text
            self.am_pm = am_pm
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(self.PANEL)
        painter.setPen(QPen(self.EDGE, 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

        painter.setFont(self.font)
        metrics = QFontMetrics(self.font)
        baseline = self.PAD_Y + metrics.ascent()

        x = self.PAD_X
        painter.setPen(self.DIM)
        painter.drawText(x, baseline, self.PROMPT)
        x += metrics.horizontalAdvance(self.PROMPT)

        painter.setPen(self.INK)
        painter.drawText(x, baseline, self.text)
        x += metrics.horizontalAdvance(self.text)

        if self.am_pm:
            painter.setPen(self.DIM)
            painter.drawText(x, baseline, " " + self.am_pm)
            x += metrics.horizontalAdvance(" " + self.am_pm)

        if self._cursor_on:
            painter.fillRect(int(x + self.char_w * 0.4), self.PAD_Y,
                             int(self.char_w * 0.85), self.line_h, self.INK)


class CloseButtonWidget(QPushButton):
    """Hovering close button"""
    
    def __init__(self, parent=None):
        super().__init__("✕", parent)
        self.setFixedSize(28, 28)
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 53, 69, 180);
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(200, 35, 51, 220);
            }
        """)
        self.hide()


class SettingsDialog(QDialog):
    """Settings dialog for clock customization"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Flip Clock Settings")
        self.setModal(True)
        self.resize(400, 280)
        
        layout = QFormLayout()

        self.template = QComboBox()
        self.template.addItem("Flip — split-flap tiles", "flip")
        self.template.addItem("Digital — seven-segment LED", "digital")
        self.template.addItem("Minimal — just the time", "minimal")
        self.template.addItem("Terminal — prompt and cursor", "terminal")

        template_index = self.template.findData(parent.template)
        if template_index >= 0:
            self.template.setCurrentIndex(template_index)

        layout.addRow("Clock Style:", self.template)

        self.time_format = QComboBox()
        self.time_format.addItem("12-hour (with AM/PM)", "12hour")
        self.time_format.addItem("24-hour (military time)", "24hour")
        
        current_format = parent.time_format
        index = self.time_format.findData(current_format)
        if index >= 0:
            self.time_format.setCurrentIndex(index)
        
        layout.addRow("Time Format:", self.time_format)
        
        self.show_seconds = QCheckBox()
        self.show_seconds.setChecked(parent.show_seconds)
        layout.addRow("Show Seconds:", self.show_seconds)
        
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(30, 100)
        self.opacity.setValue(int(parent.opacity * 100))
        self.opacity.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity.setTickInterval(10)
        opacity_label = QLabel(f"{int(parent.opacity * 100)}%")
        self.opacity.valueChanged.connect(lambda v: opacity_label.setText(f"{v}%"))
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity)
        opacity_layout.addWidget(opacity_label)
        layout.addRow("Opacity:", opacity_layout)
        
        self.desktop_only = QCheckBox()
        self.desktop_only.setChecked(parent.desktop_only)
        layout.addRow("Stay on Wallpaper:", self.desktop_only)
        
        self.auto_start = QCheckBox()
        self.auto_start.setChecked(parent.is_autostart_enabled())
        layout.addRow("Start with Windows:", self.auto_start)
        
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px 20px; border-radius: 4px;")
        apply_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 8px 20px; border-radius: 4px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
        self.setLayout(layout)


class FlipClockOverlay(QWidget):
    """Main flip clock overlay - fixed size"""
    
    def __init__(self):
        super().__init__()
        
        self.settings = QSettings("FlipClockOverlay", "ClockApp")
        self.time_format = self.settings.value("time_format", "12hour", type=str)
        self.show_seconds = self.settings.value("show_seconds", True, type=bool)
        self.opacity = self.settings.value("opacity", 0.95, type=float)
        self.desktop_only = self.settings.value("desktop_only", True, type=bool)
        self.template = self.settings.value("template", "flip", type=str)
        if self.template not in TEMPLATES:
            self.template = "flip"
        
        pos = self.settings.value("position", QPoint(100, 100))
        if not isinstance(pos, QPoint):
            pos = QPoint(100, 100)

        self.init_ui()
        self.move(self.clamp_to_screen(pos))
        self.apply_settings()

        # Tick faster than once a second and redraw only on change. A plain
        # 1000ms timer drifts, which makes the clock visibly skip a second
        # every so often; the setters below all no-op when nothing changed,
        # so the extra ticks cost effectively nothing.
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(200)

        self.update_time()
        self.setup_tray()
        
        self.drag_position = None
        self.is_dragging = False
    
    def init_ui(self):
        """Initialize the UI with fixed size"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(8)

        # Close button
        self.close_btn = CloseButtonWidget(self)
        self.close_btn.clicked.connect(self.quit_app)
        self.close_btn.hide()

        # The interchangeable time display -- one of the three templates.
        self.display = self._create_display()

        # Date label - VERY BOLD
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-family: '{clock_font_family()}';
                font-size: 16px;
                font-weight: 900;
                letter-spacing: 4px;
                padding: 8px;
                background: rgba(0, 0, 0, 35);
                border-radius: 4px;
            }}
        """)
        
        self.main_layout.addWidget(self.display, 0,
                                   Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addWidget(self.date_label)

        self.setLayout(self.main_layout)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())

        self.position_close_button()

    def _create_display(self):
        """Build the time display widget for the current template."""
        is_12h = self.time_format == "12hour"
        if self.template == "digital":
            return DigitalTimeDisplay(self.show_seconds, is_12h)
        if self.template == "minimal":
            return MinimalTimeDisplay(self.show_seconds, is_12h)
        if self.template == "terminal":
            return TerminalTimeDisplay(self.show_seconds, is_12h)
        return FlipTimeDisplay(self.show_seconds, is_12h)

    def position_close_button(self):
        """Position close button in top-right corner"""
        self.close_btn.move(self.width() - 35, 8)
        self.close_btn.raise_()

    def clamp_to_screen(self, pos):
        """Keep the clock reachable.

        A saved position can point at a monitor that is no longer attached --
        undock the laptop and the clock reappears somewhere you cannot see or
        drag it back from. If the restored position touches no current screen,
        fall back to the primary one.
        """
        frame = self.frameGeometry()
        frame.moveTopLeft(pos)

        for screen in QApplication.screens():
            if screen.availableGeometry().intersects(frame):
                return pos

        primary = QApplication.primaryScreen().availableGeometry()
        return QPoint(primary.x() + 100, primary.y() + 100)
    
    def enterEvent(self, event):
        """Show close button on hover"""
        self.close_btn.show()
        self.close_btn.raise_()
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def leaveEvent(self, event):
        """Hide close button when not hovering"""
        self.close_btn.hide()
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def apply_settings(self):
        """Apply current settings"""
        self.setWindowOpacity(self.opacity)
        
        if self.desktop_only:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowStaysOnBottomHint
            )
        else:
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowStaysOnTopHint
            )
        
        self.show()
    
    def update_time(self):
        """Update the displayed time"""
        now = datetime.now()
        
        if self.time_format == "12hour":
            time_str = now.strftime("%I:%M:%S")
            am_pm = now.strftime("%p")
        else:
            time_str = now.strftime("%H:%M:%S")
            am_pm = ""
        
        digits = time_str.replace(":", "")
        if not self.show_seconds:
            digits = digits[:4]

        self.display.set_time(digits, am_pm)

        date_str = now.strftime("%a %b %d").upper()
        if self.date_label.text() != date_str:
            self.date_label.setText(date_str)
    
    def rebuild_clock(self):
        """Swap in a fresh display after a template or layout change"""
        self.main_layout.removeWidget(self.display)
        self.display.hide()
        self.display.deleteLater()

        self.display = self._create_display()
        self.main_layout.insertWidget(0, self.display, 0,
                                      Qt.AlignmentFlag.AlignHCenter)

        # The fresh widget stays hidden until the event loop next runs, and a
        # hidden widget contributes nothing to the layout -- so measuring now
        # would fix the window at the size of the date strip alone, clipping
        # the clock. Show it and settle the layout before taking the hint.
        self.display.show()
        self.main_layout.activate()

        self.adjustSize()
        self.setFixedSize(self.sizeHint())
        self.position_close_button()
        self.update_time()
    
    def setup_tray(self):
        """Setup system tray"""
        self.tray_icon = QSystemTrayIcon(self)
        
        icon = QIcon.fromTheme("clock")
        if icon.isNull():
            from PyQt6.QtGui import QPixmap
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#2196F3"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 2, 28, 28)
            painter.end()
            icon = QIcon(pixmap)
        
        self.tray_icon.setIcon(icon)
        
        tray_menu = QMenu()
        
        toggle_action = QAction("Show/Hide", self)
        toggle_action.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(toggle_action)
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        tray_menu.addAction(settings_action)
        
        tray_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_activated)
    
    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visibility()
    
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            # The display's geometry depends on all three of these, so any
            # change means building it afresh.
            old_layout = (self.show_seconds, self.time_format, self.template)

            self.time_format = dialog.time_format.currentData()
            self.show_seconds = dialog.show_seconds.isChecked()
            self.opacity = dialog.opacity.value() / 100.0
            self.desktop_only = dialog.desktop_only.isChecked()
            self.template = dialog.template.currentData()

            self.save_settings()

            if old_layout != (self.show_seconds, self.time_format,
                              self.template):
                self.rebuild_clock()
            
            self.apply_settings()
            self.update_time()
            
            if dialog.auto_start.isChecked():
                self.enable_autostart()
            else:
                self.disable_autostart()
    
    def save_settings(self):
        self.settings.setValue("time_format", self.time_format)
        self.settings.setValue("show_seconds", self.show_seconds)
        self.settings.setValue("opacity", self.opacity)
        self.settings.setValue("desktop_only", self.desktop_only)
        self.settings.setValue("template", self.template)
        self.settings.setValue("position", self.pos())
    
    def quit_app(self):
        self.save_settings()
        QApplication.quit()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Don't start drag if clicking close button
            if self.close_btn.isVisible() and self.close_btn.geometry().contains(event.pos()):
                return
            
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.drag_position = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.save_settings()
            event.accept()
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
    
    @staticmethod
    def get_autostart_key():
        return winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY,
            0,
            winreg.KEY_ALL_ACCESS
        )

    @staticmethod
    def is_autostart_approved():
        """Report whether Windows will honour our Run entry.

        Task Manager's Startup tab does not delete the Run value when you
        disable an entry -- it records a flag in a separate key, where the
        low bit of the first byte means "disabled". An entry can therefore
        look perfectly configured and still never launch.
        """
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_KEY) as key:
                data, _ = winreg.QueryValueEx(key, AUTOSTART_NAME)
                return not (data[0] & 1)
        except FileNotFoundError:
            # No flag recorded means it has never been disabled.
            return True
        except Exception:
            return True

    @staticmethod
    def approve_autostart():
        """Clear the disabled flag so the Run entry is actually honoured."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_APPROVED_KEY,
                                0, winreg.KEY_ALL_ACCESS) as key:
                try:
                    data = bytearray(winreg.QueryValueEx(key, AUTOSTART_NAME)[0])
                except FileNotFoundError:
                    data = bytearray(12)
                data[0] = 2  # 2 = enabled, 3 = disabled
                winreg.SetValueEx(key, AUTOSTART_NAME, 0,
                                  winreg.REG_BINARY, bytes(data))
        except FileNotFoundError:
            # The key only exists once something has been toggled; if it is
            # absent there is nothing suppressing us.
            pass
        except Exception as e:
            print(f"Failed to clear the startup-disabled flag: {e}")

    def enable_autostart(self):
        try:
            exe = Path(sys.executable).resolve()

            if getattr(sys, "frozen", False):
                # Packaged build: the executable is the whole application.
                # Appending __file__ here would point at PyInstaller's temp
                # extraction folder, which is deleted the moment we exit.
                value = f'"{exe}"'
            else:
                # pythonw.exe has no console, so nothing flashes up at sign-in.
                if exe.name.lower() == "python.exe":
                    windowless = exe.with_name("pythonw.exe")
                    if windowless.exists():
                        exe = windowless
                value = f'"{exe}" "{Path(__file__).resolve()}"'

            key = self.get_autostart_key()
            winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, value)
            winreg.CloseKey(key)

            # Writing the Run value is not enough on its own if the entry was
            # previously switched off in the Startup tab.
            self.approve_autostart()
        except Exception as e:
            print(f"Failed to enable auto-start: {e}")

    def disable_autostart(self):
        try:
            key = self.get_autostart_key()
            winreg.DeleteValue(key, AUTOSTART_NAME)
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Failed to disable auto-start: {e}")

    def is_autostart_enabled(self):
        """True only if the entry exists *and* Windows has not disabled it."""
        try:
            key = self.get_autostart_key()
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            winreg.CloseKey(key)
        except FileNotFoundError:
            return False
        except Exception:
            return False

        return self.is_autostart_approved()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Prevent multiple instances
    instance_check = SingleInstance("FlipClockOverlay_SingleInstance")
    if instance_check.is_running:
        print("Another instance is already running. Exiting.")
        sys.exit(0)
    
    clock = FlipClockOverlay()
    clock.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()