"""
Retro Flip Clock Desktop Overlay - Production Ready
A beautiful flip clock widget for Windows desktop with animations.

Requirements: PyQt6
Install: pip install PyQt6

Usage: python desktop_timer.py
"""

import sys
import winreg
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout,
                              QSystemTrayIcon, QMenu, QSlider, QDialog, 
                              QFormLayout, QCheckBox, QPushButton, QComboBox)
from PyQt6.QtCore import QTimer, Qt, QPoint, QSettings, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QAction, QIcon, QPainter, QPen


class FlipDigit(QWidget):
    """Individual flip clock digit with animation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_digit = "0"
        self.next_digit = "0"
        self._flip_progress = 0.0
        self.show_am_pm = False
        self.am_pm_text = ""
        
        self.setFixedSize(80, 110)
        
    def set_digit(self, digit, animate=True):
        """Update digit with optional animation"""
        if digit != self.current_digit:
            self.next_digit = digit
            if animate:
                self.animate_flip()
            else:
                self.current_digit = digit
                self.update()
    
    def animate_flip(self):
        """Animate the flip transition"""
        self.animation = QPropertyAnimation(self, b"flip_progress")
        self.animation.setDuration(400)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.on_animation_finished)
        self.animation.start()
    
    def on_animation_finished(self):
        """Complete the flip animation"""
        self.current_digit = self.next_digit
        self._flip_progress = 0.0
        self.update()
    
    @pyqtProperty(float)
    def flip_progress(self):
        return self._flip_progress
    
    @flip_progress.setter
    def flip_progress(self, value):
        self._flip_progress = value
        self.update()
    
    def set_am_pm(self, text):
        """Set AM/PM indicator"""
        self.show_am_pm = True
        self.am_pm_text = text
        self.update()
    
    def paintEvent(self, event):
        """Custom paint for flip clock appearance"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background tile
        painter.setBrush(QColor(45, 45, 45))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 80, 110, 8, 8)
        
        # Horizontal split line
        painter.setPen(QPen(QColor(25, 25, 25), 2))
        painter.drawLine(5, 55, 75, 55)
        
        # Determine which digit to show based on animation
        display_digit = self.current_digit
        opacity = 1.0
        
        if self._flip_progress > 0:
            if self._flip_progress < 0.5:
                display_digit = self.current_digit
                opacity = 1.0 - (self._flip_progress * 2)
            else:
                display_digit = self.next_digit
                opacity = (self._flip_progress - 0.5) * 2
        
        # Draw digit
        painter.setOpacity(opacity)
        font = QFont("Arial", 56, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, display_digit)
        
        # Draw AM/PM indicator
        if self.show_am_pm:
            painter.setOpacity(1.0)
            small_font = QFont("Arial", 10, QFont.Weight.Bold)
            painter.setFont(small_font)
            painter.drawText(8, 20, self.am_pm_text)


class ColonSeparator(QLabel):
    """Colon separator between digit pairs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText(":")
        self.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 48px;
                font-weight: bold;
                padding: 0px 8px;
                background: transparent;
            }
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class SettingsDialog(QDialog):
    """Settings dialog for clock customization"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Flip Clock Settings")
        self.setModal(True)
        self.resize(400, 350)
        
        layout = QFormLayout()
        
        # Time format
        self.time_format = QComboBox()
        self.time_format.addItem("12-hour (with AM/PM)", "12hour")
        self.time_format.addItem("24-hour (military time)", "24hour")
        
        current_format = parent.time_format
        index = self.time_format.findData(current_format)
        if index >= 0:
            self.time_format.setCurrentIndex(index)
        
        layout.addRow("Time Format:", self.time_format)
        
        # Show seconds
        self.show_seconds = QCheckBox()
        self.show_seconds.setChecked(parent.show_seconds)
        layout.addRow("Show Seconds:", self.show_seconds)
        
        # Opacity
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(30, 100)
        self.opacity.setValue(int(parent.opacity * 100))
        self.opacity.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity.setTickInterval(10)
        opacity_label = QLabel(f"{int(parent.opacity * 100)}%")
        self.opacity.valueChanged.connect(lambda v: opacity_label.setText(f"{v}%"))
        from PyQt6.QtWidgets import QHBoxLayout as HBox
        opacity_layout = HBox()
        opacity_layout.addWidget(self.opacity)
        opacity_layout.addWidget(opacity_label)
        layout.addRow("Opacity:", opacity_layout)
        
        # Desktop only
        self.desktop_only = QCheckBox()
        self.desktop_only.setChecked(parent.desktop_only)
        layout.addRow("Stay on Wallpaper:", self.desktop_only)
        
        # Auto-start
        self.auto_start = QCheckBox()
        self.auto_start.setChecked(parent.is_autostart_enabled())
        layout.addRow("Start with Windows:", self.auto_start)
        
        # Buttons
        from PyQt6.QtWidgets import QHBoxLayout as HBox
        btn_layout = HBox()
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
    """Main flip clock overlay widget"""
    
    def __init__(self):
        super().__init__()
        
        # Settings
        self.settings = QSettings("FlipClockOverlay", "ClockApp")
        self.time_format = self.settings.value("time_format", "12hour", type=str)
        self.show_seconds = self.settings.value("show_seconds", True, type=bool)
        self.opacity = self.settings.value("opacity", 0.95, type=float)
        self.desktop_only = self.settings.value("desktop_only", True, type=bool)
        
        # Restore position
        pos = self.settings.value("position", QPoint(100, 100))
        
        # Initialize UI
        self.init_ui()
        self.move(pos)
        self.apply_settings()
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        
        # Initial time
        self.last_time = ""
        self.update_time()
        
        # System tray
        self.setup_tray()
        
        # Drag state
        self.drag_position = None
        self.is_dragging = False
    
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)
        
        # Digits layout
        digits_layout = QHBoxLayout()
        digits_layout.setSpacing(4)
        
        # Create digit widgets
        self.hour1 = FlipDigit()
        self.hour2 = FlipDigit()
        self.min1 = FlipDigit()
        self.min2 = FlipDigit()
        self.sec1 = FlipDigit()
        self.sec2 = FlipDigit()
        
        # Build layout
        digits_layout.addWidget(self.hour1)
        digits_layout.addWidget(self.hour2)
        digits_layout.addWidget(ColonSeparator())
        digits_layout.addWidget(self.min1)
        digits_layout.addWidget(self.min2)
        
        if self.show_seconds:
            digits_layout.addWidget(ColonSeparator())
            digits_layout.addWidget(self.sec1)
            digits_layout.addWidget(self.sec2)
        
        # Date label
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 180);
                font-size: 16px;
                font-weight: normal;
                font-family: 'Segoe UI', Arial;
                letter-spacing: 3px;
                padding: 5px;
                background: transparent;
            }
        """)
        
        main_layout.addLayout(digits_layout)
        main_layout.addWidget(self.date_label)
        
        self.setLayout(main_layout)
        self.adjustSize()
    
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
        """Update the displayed time with animations"""
        now = datetime.now()
        
        # Format time based on settings
        if self.time_format == "12hour":
            time_str = now.strftime("%I:%M:%S")
            am_pm = now.strftime("%p")
        else:
            time_str = now.strftime("%H:%M:%S")
            am_pm = ""
        
        # Parse digits
        digits = time_str.replace(":", "")
        
        # Check if this is the first update
        animate = self.last_time != ""
        
        # Update digits with animation
        self.hour1.set_digit(digits[0], animate)
        self.hour2.set_digit(digits[1], animate)
        self.min1.set_digit(digits[2], animate)
        self.min2.set_digit(digits[3], animate)
        
        if self.show_seconds:
            self.sec1.set_digit(digits[4], animate)
            self.sec2.set_digit(digits[5], animate)
        
        # Update AM/PM indicator
        if am_pm:
            self.hour1.set_am_pm(am_pm)
        
        # Update date
        date_str = now.strftime("%a %b %d").upper()
        self.date_label.setText(date_str)
        
        self.last_time = time_str
    
    def setup_tray(self):
        """Setup system tray"""
        self.tray_icon = QSystemTrayIcon(self)
        
        icon = QIcon.fromTheme("clock")
        if icon.isNull():
            from PyQt6.QtGui import QPixmap, QPainter
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
            old_format = self.time_format
            old_seconds = self.show_seconds
            
            self.time_format = dialog.time_format.currentData()
            self.show_seconds = dialog.show_seconds.isChecked()
            self.opacity = dialog.opacity.value() / 100.0
            self.desktop_only = dialog.desktop_only.isChecked()
            
            self.save_settings()
            
            # Rebuild UI if seconds toggle changed
            if old_seconds != self.show_seconds:
                # Clear and rebuild
                while self.layout().count():
                    item = self.layout().takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                self.init_ui()
                self.last_time = ""
            
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
    
    def enterEvent(self, event):
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def leaveEvent(self, event):
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
    
    @staticmethod
    def get_autostart_key():
        return winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS
        )
    
    def enable_autostart(self):
        try:
            key = self.get_autostart_key()
            exe_path = str(Path(sys.executable).resolve())
            script_path = str(Path(__file__).resolve())
            
            if "python.exe" in exe_path.lower():
                exe_path = exe_path.lower().replace("python.exe", "pythonw.exe")
            
            value = f'"{exe_path}" "{script_path}"'
            winreg.SetValueEx(key, "FlipClockOverlay", 0, winreg.REG_SZ, value)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to enable auto-start: {e}")
    
    def disable_autostart(self):
        try:
            key = self.get_autostart_key()
            winreg.DeleteValue(key, "FlipClockOverlay")
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Failed to disable auto-start: {e}")
    
    def is_autostart_enabled(self):
        try:
            key = self.get_autostart_key()
            winreg.QueryValueEx(key, "FlipClockOverlay")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    clock = FlipClockOverlay()
    clock.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()