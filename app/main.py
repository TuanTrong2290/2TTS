#!/usr/bin/env python3
"""2TTS - ElevenLabs Text-To-Speech Tool"""
import sys
import os

# Determine if running as PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    app_dir = sys._MEIPASS
else:
    # Running as script
    app_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, app_dir)

# Set AppUserModelID for Windows taskbar icon (must be before QApplication)
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("2TTS.2TTS.1.0")
except:
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("2TTS")
    app.setOrganizationName("2TTS")
    
    # Set application icon
    icon_path = os.path.join(app_dir, "resources", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
