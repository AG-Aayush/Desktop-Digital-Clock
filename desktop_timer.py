"""
Retro Flip Clock Desktop Overlay - Fixed Size Version
A beautiful flip clock widget for Windows desktop.

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
from PyQt6.QtCore import QTimer, Qt, QPoint, QSettings
from PyQt6.QtGui import QFont, QColor, QAction, QIcon, QPainter, QPen, QCursor
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


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
    """Individual flip clock digit - fixed size"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_digit = "0"
        self.show_am_pm = False
        self.am_pm_text = ""
        
        # Perfect size for 16-inch laptop
        self.setFixedSize(70, 95)
        
    def set_digit(self, digit):
        """Update digit"""
        if digit != self.current_digit:
            self.current_digit = digit
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
        
        w = self.width()
        h = self.height()
        
        # Background tile
        painter.setBrush(QColor(45, 45, 45))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 8, 8)
        
        # Horizontal split line
        painter.setPen(QPen(QColor(25, 25, 25), 2))
        painter.drawLine(5, h // 2, w - 5, h // 2)
        
        # Draw digit
        font = QFont("Arial", 48, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, self.current_digit)
        
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
        
        self.init_ui()
        self.move(pos)
        self.apply_settings()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        
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
        
        date_str = now.strftime("%a %b %d").upper()
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