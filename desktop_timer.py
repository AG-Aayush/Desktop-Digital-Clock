"""
Desktop Timer Overlay - Production-Ready Windows Application
A lightweight, persistent digital clock/timer overlay for Windows desktop.

Requirements: PyQt6
Install: pip install PyQt6

Usage: python desktop_timer.py
"""

import sys
import winreg
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, 
                              QSystemTrayIcon, QMenu, QColorDialog, QSlider,
                              QDialog, QFormLayout, QCheckBox, QPushButton,
                              QHBoxLayout, QSpinBox, QComboBox)
from PyQt6.QtCore import QTimer, Qt, QPoint, QSettings
from PyQt6.QtGui import QFont, QColor, QAction, QIcon, QPalette, QCursor, QFontDatabase


class SettingsDialog(QDialog):
    """Settings dialog for timer customization"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timer Settings")
        self.setModal(True)
        self.resize(450, 500)
        
        layout = QFormLayout()
        
        # Time format
        self.time_format = QComboBox()
        self.time_format.addItem("Time + Day (10:26 PM • Mon)", "12h_short")
        self.time_format.addItem("Time + Full Day (10:26:45 PM • Monday)", "12h_full")
        self.time_format.addItem("Time + Date (10:26 PM • Jan 14)", "12h_date")
        self.time_format.addItem("Complete (10:26 PM • Mon, Jan 14)", "12h_complete")
        self.time_format.addItem("24-hour + Day (22:26 • Monday)", "24h_day")
        self.time_format.addItem("Simple 12-hour (10:26:45 PM)", "12h_simple")
        self.time_format.addItem("Simple 24-hour (22:26:45)", "24h_simple")
        
        # Set current format
        current_format = parent.time_format
        index = self.time_format.findData(current_format)
        if index >= 0:
            self.time_format.setCurrentIndex(index)
        
        layout.addRow("Time Format:", self.time_format)
        
        # Font family
        self.font_family = QComboBox()
        self.font_family.addItem("Segoe UI (Default)", "Segoe UI")
        self.font_family.addItem("Arial", "Arial")
        self.font_family.addItem("Consolas (Monospace)", "Consolas")
        self.font_family.addItem("Impact (Bold)", "Impact")
        self.font_family.addItem("Courier New", "Courier New")
        
        # Add custom fonts from folder
        custom_fonts = parent.load_custom_fonts()
        for font_name in custom_fonts:
            self.font_family.addItem(f"{font_name} (Custom)", font_name)
        
        # Set current font
        current_font = parent.font_family
        index = self.font_family.findData(current_font)
        if index >= 0:
            self.font_family.setCurrentIndex(index)
        
        layout.addRow("Font Style:", self.font_family)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(12, 200)
        self.font_size.setValue(parent.font_size)
        self.font_size.setSuffix(" pt")
        layout.addRow("Font Size:", self.font_size)
        
        # Opacity
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(10, 100)
        self.opacity.setValue(int(parent.opacity * 100))
        self.opacity.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity.setTickInterval(10)
        opacity_label = QLabel(f"{int(parent.opacity * 100)}%")
        self.opacity.valueChanged.connect(lambda v: opacity_label.setText(f"{v}%"))
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity)
        opacity_layout.addWidget(opacity_label)
        layout.addRow("Opacity:", opacity_layout)
        
        # Color picker
        self.color_btn = QPushButton("Choose Color")
        self.selected_color = parent.font_color
        self.color_btn.setStyleSheet(f"background-color: {parent.font_color.name()}; color: white; font-weight: bold;")
        self.color_btn.clicked.connect(self.pick_color)
        layout.addRow("Font Color:", self.color_btn)
        
        # Stay on desktop only (below other windows)
        self.desktop_only = QCheckBox()
        self.desktop_only.setChecked(parent.desktop_only)
        layout.addRow("Show on Wallpaper Only:", self.desktop_only)
        
        # Auto-start
        self.auto_start = QCheckBox()
        self.auto_start.setChecked(parent.is_autostart_enabled())
        layout.addRow("Start with Windows:", self.auto_start)
        
        # Preview label
        preview_label = QLabel("Preview will update after clicking Apply")
        preview_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addRow("", preview_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px 15px;")
        apply_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 5px 15px;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_layout)
        self.setLayout(layout)
    
    def pick_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Select Font Color")
        if color.isValid():
            self.selected_color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; color: white; font-weight: bold;")


class TimerOverlay(QWidget):
    """Main timer overlay window"""
    
    def __init__(self):
        super().__init__()
        
        # Settings persistence
        self.settings = QSettings("DesktopTimerOverlay", "TimerApp")
        
        # Default values
        self.time_format = self.settings.value("time_format", "12h_short", type=str)
        self.font_family = self.settings.value("font_family", "Segoe UI", type=str)
        self.font_size = self.settings.value("font_size", 48, type=int)
        self.opacity = self.settings.value("opacity", 0.9, type=float)
        self.font_color = QColor(self.settings.value("font_color", "#FFFFFF"))
        self.desktop_only = self.settings.value("desktop_only", True, type=bool)
        
        # Load custom fonts
        self.custom_fonts = self.load_custom_fonts()
        
        # Restore position
        pos = self.settings.value("position", QPoint(100, 100))
        
        self.init_ui()
        self.move(pos)
        self.apply_settings()
        
        # Timer for clock updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # Update every second
        
        # Initial time display
        self.update_time()
        
        # System tray
        self.setup_tray()
        
        # Mouse drag state
        self.drag_position = None
        self.is_dragging = False
    
    def load_custom_fonts(self):
        """Load custom fonts from the application directory"""
        custom_fonts = []
        app_dir = Path(__file__).parent
        
        # Look for font files in the main directory and subdirectories
        for font_path in app_dir.rglob("*.ttf"):
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                custom_fonts.extend(font_families)
        
        for font_path in app_dir.rglob("*.otf"):
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                custom_fonts.extend(font_families)
        
        return list(set(custom_fonts))  # Remove duplicates
    
    def init_ui(self):
        """Initialize the UI"""
        # Frameless window with transparent background
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Time label
        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)
        
        self.setLayout(layout)
        self.adjustSize()
    
    def apply_settings(self):
        """Apply current settings to the UI"""
        # Font
        font = QFont(self.font_family, self.font_size, QFont.Weight.Bold)
        self.time_label.setFont(font)
        
        # Color
        palette = self.time_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, self.font_color)
        self.time_label.setPalette(palette)
        
        # Opacity
        self.setWindowOpacity(self.opacity)
        
        # Window flags based on desktop_only setting
        if self.desktop_only:
            # Stay below normal windows, above desktop
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowStaysOnBottomHint
            )
        else:
            # Stay on top of everything
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowStaysOnTopHint
            )
        
        self.show()  # Re-show to apply window flags
        self.adjustSize()
    
    def update_time(self):
        """Update the displayed time based on selected format"""
        now = datetime.now()
        
        if self.time_format == "12h_short":
            # 10:26 PM • Mon
            time_str = now.strftime("%I:%M %p • %a")
        elif self.time_format == "12h_full":
            # 10:26:45 PM • Monday
            time_str = now.strftime("%I:%M:%S %p • %A")
        elif self.time_format == "12h_date":
            # 10:26 PM • Jan 14
            time_str = now.strftime("%I:%M %p • %b %d")
        elif self.time_format == "12h_complete":
            # 10:26 PM • Mon, Jan 14
            time_str = now.strftime("%I:%M %p • %a, %b %d")
        elif self.time_format == "24h_day":
            # 22:26 • Monday
            time_str = now.strftime("%H:%M • %A")
        elif self.time_format == "12h_simple":
            # 10:26:45 PM
            time_str = now.strftime("%I:%M:%S %p")
        else:  # 24h_simple
            # 22:26:45
            time_str = now.strftime("%H:%M:%S")
        
        self.time_label.setText(time_str)
    
    def setup_tray(self):
        """Setup system tray icon and menu"""
        # Create tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create icon
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
        
        # Create menu
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
        
        # Double-click to toggle
        self.tray_icon.activated.connect(self.tray_activated)
    
    def tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visibility()
    
    def toggle_visibility(self):
        """Toggle timer visibility"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Apply new settings
            self.time_format = dialog.time_format.currentData()
            self.font_family = dialog.font_family.currentData()
            self.font_size = dialog.font_size.value()
            self.opacity = dialog.opacity.value() / 100.0
            self.font_color = dialog.selected_color
            self.desktop_only = dialog.desktop_only.isChecked()
            
            # Save settings
            self.save_settings()
            self.apply_settings()
            
            # Update time immediately with new format
            self.update_time()
            
            # Handle auto-start
            if dialog.auto_start.isChecked():
                self.enable_autostart()
            else:
                self.disable_autostart()
    
    def save_settings(self):
        """Save settings to persistent storage"""
        self.settings.setValue("time_format", self.time_format)
        self.settings.setValue("font_family", self.font_family)
        self.settings.setValue("font_size", self.font_size)
        self.settings.setValue("opacity", self.opacity)
        self.settings.setValue("font_color", self.font_color.name())
        self.settings.setValue("desktop_only", self.desktop_only)
        self.settings.setValue("position", self.pos())
    
    def quit_app(self):
        """Quit the application"""
        self.save_settings()
        QApplication.quit()
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.drag_position = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.save_settings()  # Save position after drag
            event.accept()
    
    def enterEvent(self, event):
        """Change cursor when hovering"""
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def leaveEvent(self, event):
        """Reset cursor when leaving"""
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def closeEvent(self, event):
        """Handle close event"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Desktop Timer",
            "Timer is still running in system tray. Right-click tray icon to exit.",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    
    @staticmethod
    def get_autostart_key():
        """Get the registry key for auto-start"""
        return winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_ALL_ACCESS
        )
    
    def enable_autostart(self):
        """Enable auto-start with Windows"""
        try:
            key = self.get_autostart_key()
            exe_path = str(Path(sys.executable).resolve())
            script_path = str(Path(__file__).resolve())
            
            # Use pythonw.exe to avoid console window
            if "python.exe" in exe_path.lower():
                exe_path = exe_path.lower().replace("python.exe", "pythonw.exe")
            
            value = f'"{exe_path}" "{script_path}"'
            winreg.SetValueEx(key, "DesktopTimerOverlay", 0, winreg.REG_SZ, value)
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to enable auto-start: {e}")
    
    def disable_autostart(self):
        """Disable auto-start with Windows"""
        try:
            key = self.get_autostart_key()
            winreg.DeleteValue(key, "DesktopTimerOverlay")
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Failed to disable auto-start: {e}")
    
    def is_autostart_enabled(self):
        """Check if auto-start is enabled"""
        try:
            key = self.get_autostart_key()
            winreg.QueryValueEx(key, "DesktopTimerOverlay")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    overlay = TimerOverlay()
    overlay.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()