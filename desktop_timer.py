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
from PyQt6.QtCore import (QTimer, Qt, QPoint, QRect, QSettings, QVariantAnimation,
                          QEasingCurve)
from PyQt6.QtGui import (QFont, QColor, QAction, QIcon, QPainter, QPen, QCursor,
                         QPixmap, QFontMetrics)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


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
        painter.setBrush(QColor(45, 45, 45))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 8, 8)
        font = QFont("Arial", 48, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))

        # Centre on the glyph's actual ink, not the font's line box. The line
        # box reserves room for descenders that digits never use, so plain
        # AlignCenter sits the number noticeably low of the seam.
        ink = QFontMetrics(font).tightBoundingRect(digit)
        baseline_x = (w - ink.width()) / 2.0 - ink.x()
        baseline_y = (h - ink.height()) / 2.0 - ink.y()
        painter.drawText(int(round(baseline_x)), int(round(baseline_y)), digit)
        painter.end()

        self._face_cache[key] = pixmap
        return pixmap
    
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

            # The halves that have already settled: the new digit is waiting
            # up top, the old one still shows below until the card covers it.
            painter.drawPixmap(top, new_face, top)
            painter.drawPixmap(bottom, old_face, bottom)

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
            painter.drawPixmap(dest, leaf, source)
            # Darken it as it turns edge-on, so the fold has some depth.
            painter.fillRect(dest, QColor(0, 0, 0, int(90 * (1.0 - factor))))
            painter.restore()

        # Seam last, so it sits above the moving card. Kept a touch lighter
        # than the tile so it reads as a hinge rather than a black slash.
        painter.setPen(QPen(QColor(70, 70, 70), 2))
        painter.drawLine(5, mid, w - 5, mid)

        # Draw AM/PM indicator - always visible
        if self.show_am_pm:
            small_font = QFont("Arial", 11, QFont.Weight.Bold)
            painter.setFont(small_font)
            painter.setPen(QColor(220, 220, 220))
            painter.drawText(8, 18, self.am_pm_text)


class ColonSeparator(QLabel):
    """Colon separator - minimal width"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText(":")
        self.setFixedWidth(15)
        self.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 50px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
                background: transparent;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


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
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # Close button
        self.close_btn = CloseButtonWidget(self)
        self.close_btn.clicked.connect(self.quit_app)
        self.close_btn.hide()
        
        # Digits layout
        self.digits_widget = QWidget()
        self.digits_layout = QHBoxLayout(self.digits_widget)
        self.digits_layout.setSpacing(4)
        self.digits_layout.setContentsMargins(0, 0, 0, 0)
        
        self.hour1 = FlipDigit()
        self.hour2 = FlipDigit()
        self.colon1 = ColonSeparator()
        self.min1 = FlipDigit()
        self.min2 = FlipDigit()
        self.colon2 = ColonSeparator()
        self.sec1 = FlipDigit()
        self.sec2 = FlipDigit()
        
        self.digits_layout.addWidget(self.hour1)
        self.digits_layout.addWidget(self.hour2)
        self.digits_layout.addWidget(self.colon1)
        self.digits_layout.addWidget(self.min1)
        self.digits_layout.addWidget(self.min2)
        
        if self.show_seconds:
            self.digits_layout.addWidget(self.colon2)
            self.digits_layout.addWidget(self.sec1)
            self.digits_layout.addWidget(self.sec2)
        
        # Date label - VERY BOLD
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: 900;
                font-family: 'Arial Black', Arial;
                letter-spacing: 4px;
                padding: 8px;
                background: rgba(0, 0, 0, 35);
                border-radius: 4px;
            }
        """)
        
        main_layout.addWidget(self.digits_widget)
        main_layout.addWidget(self.date_label)
        
        self.setLayout(main_layout)
        self.adjustSize()
        self.setFixedSize(self.sizeHint())
        
        self.position_close_button()
    
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
        
        self.hour1.set_digit(digits[0])
        self.hour2.set_digit(digits[1])
        self.min1.set_digit(digits[2])
        self.min2.set_digit(digits[3])
        
        if self.show_seconds:
            self.sec1.set_digit(digits[4])
            self.sec2.set_digit(digits[5])
        
        if am_pm:
            self.hour1.set_am_pm(am_pm)
        else:
            # Without this the marker painted in 12-hour mode stays stuck on
            # the first digit after switching to 24-hour.
            self.hour1.clear_am_pm()

        date_str = now.strftime("%a %b %d").upper()
        if self.date_label.text() != date_str:
            self.date_label.setText(date_str)
    
    def rebuild_clock(self):
        """Rebuild the clock layout"""
        while self.digits_layout.count():
            item = self.digits_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        self.digits_layout.addWidget(self.hour1)
        self.digits_layout.addWidget(self.hour2)
        self.digits_layout.addWidget(self.colon1)
        self.digits_layout.addWidget(self.min1)
        self.digits_layout.addWidget(self.min2)
        
        if self.show_seconds:
            self.digits_layout.addWidget(self.colon2)
            self.digits_layout.addWidget(self.sec1)
            self.digits_layout.addWidget(self.sec2)
        
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
            old_seconds = self.show_seconds
            
            self.time_format = dialog.time_format.currentData()
            self.show_seconds = dialog.show_seconds.isChecked()
            self.opacity = dialog.opacity.value() / 100.0
            self.desktop_only = dialog.desktop_only.isChecked()
            
            self.save_settings()
            
            if old_seconds != self.show_seconds:
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