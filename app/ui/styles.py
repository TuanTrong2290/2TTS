"""Theme styles for 2TTS application"""
import sys

# Color Palette (Modern Midnight / Tokyo Night inspired)
COLORS = {
    "dark": {
        "bg_main": "#1a1b26",
        "bg_secondary": "#24283b",
        "bg_tertiary": "#414868",
        "fg_primary": "#c0caf5",
        "fg_secondary": "#a9b1d6",
        "fg_tertiary": "#565f89",
        "accent_primary": "#7aa2f7",    # Blue
        "accent_secondary": "#bb9af7",  # Purple
        "accent_hover": "#89ddff",      # Cyan/Light Blue
        "success": "#9ece6a",
        "warning": "#e0af68",
        "error": "#f7768e",
        "border": "#414868",
        "input_bg": "#1f2335",
        "selection": "#364da4"
    },
    "light": {
        "bg_main": "#f3f4f6",           # Outer padding background
        "bg_secondary": "#ffffff",       # Main panels (white)
        "bg_tertiary": "#fafafa",        # Secondary panels
        "fg_primary": "#1f2937",          # Dark text for readability
        "fg_secondary": "#4b5563",        # Secondary text
        "fg_tertiary": "#9ca3af",         # Muted text
        "accent_primary": "#3b82f6",      # Modern blue
        "accent_secondary": "#10b981",    # Green for success actions
        "accent_hover": "#2563eb",        # Darker blue on hover
        "success": "#22c55e",
        "warning": "#f59e0b",
        "error": "#ef4444",
        "border": "#e5e7eb",
        "input_bg": "#ffffff",
        "selection": "#dbeafe"
    }
}

def get_stylesheet(theme_name: str) -> str:
    """Generate stylesheet for the given theme name ('dark' or 'light')"""
    c = COLORS.get(theme_name, COLORS["dark"])
    
    return f"""
    /* Global Reset & Font */
    QWidget {{
        background-color: {c['bg_main']};
        color: {c['fg_primary']};
        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
        font-size: 14px;
        selection-background-color: {c['selection']};
        selection-color: {c['fg_primary']};
        outline: none;
    }}

    /* Main Window & Dialogs */
    QMainWindow, QDialog {{
        background-color: {c['bg_main']};
    }}

    /* Menu Bar */
    QMenuBar {{
        background-color: {c['bg_secondary']};
        border-bottom: 1px solid {c['border']};
        padding: 4px;
    }}
    QMenuBar::item {{
        padding: 6px 12px;
        border-radius: 4px;
        color: {c['fg_secondary']};
    }}
    QMenuBar::item:selected {{
        background-color: {c['bg_tertiary']};
        color: {c['fg_primary']};
    }}
    QMenu {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border']};
        padding: 5px;
        border-radius: 6px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {c['accent_primary']};
        color: #1a1b26; /* Always dark text on accent */
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {c['border']};
        margin: 5px 15px;
    }}

    /* Toolbar */
    QToolBar {{
        background-color: {c['bg_secondary']};
        border-bottom: 1px solid {c['border']};
        spacing: 10px;
        padding: 10px;
    }}

    /* Buttons */
    QPushButton {{
        background-color: {c['bg_tertiary']};
        color: {c['fg_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {c['fg_tertiary']};
        border-color: {c['fg_secondary']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_secondary']};
        padding-top: 9px; /* Press effect */
        padding-bottom: 7px;
    }}
    QPushButton:disabled {{
        background-color: {c['bg_secondary']};
        color: {c['fg_tertiary']};
        border-color: {c['bg_main']};
    }}

    /* Primary Action Button */
    QPushButton#primaryButton {{
        background-color: {c['accent_primary']};
        color: #1a1b26;
        border: none;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {c['accent_hover']};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {c['accent_primary']};
    }}

    /* Danger Button */
    QPushButton#dangerButton {{
        background-color: {c['error']};
        color: #ffffff;
        border: none;
    }}
    QPushButton#dangerButton:hover {{
        background-color: #ff8f9e; /* Lighter red */
    }}

    /* Success Button */
    QPushButton#successButton {{
        background-color: {c['success']};
        color: #1a1b26;
        border: none;
    }}

    /* Inputs */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {c['input_bg']};
        color: {c['fg_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {c['accent_primary']};
        background-color: {c['bg_secondary']};
    }}

    /* Combo Box */
    QComboBox {{
        background-color: {c['input_bg']};
        color: {c['fg_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
        min-width: 6em;
    }}
    QComboBox:hover {{
        border-color: {c['fg_secondary']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
        subcontrol-origin: padding;
        subcontrol-position: top right;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid {c['fg_secondary']};
        margin-right: 10px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent_primary']};
        selection-color: #1a1b26;
        outline: none;
    }}

    /* Tables */
    QTableWidget, QTableView {{
        background-color: {c['input_bg']};
        gridline-color: {c['bg_tertiary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        alternate-background-color: {c['bg_main']};
    }}
    QTableWidget::item, QTableView::item {{
        padding: 6px;
        border: none;
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        background-color: {c['selection']};
        color: {c['fg_primary']};
    }}
    QHeaderView::section {{
        background-color: {c['bg_secondary']};
        color: {c['fg_secondary']};
        padding: 8px;
        border: none;
        border-bottom: 2px solid {c['border']};
        font-weight: bold;
        text-transform: uppercase;
        font-size: 12px;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: {c['bg_main']};
        width: 14px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['bg_tertiary']};
        min-height: 30px;
        border-radius: 7px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['fg_tertiary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background: {c['bg_main']};
        height: 14px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['bg_tertiary']};
        min-width: 30px;
        border-radius: 7px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['fg_tertiary']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Progress Bar */
    QProgressBar {{
        border: none;
        background-color: {c['bg_tertiary']};
        border-radius: 4px;
        text-align: center;
        color: {c['fg_primary']};
        font-weight: bold;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent_primary']};
        border-radius: 4px;
    }}

    /* Sliders */
    QSlider::groove:horizontal {{
        border: 1px solid {c['bg_tertiary']};
        height: 6px;
        background: {c['bg_tertiary']};
        margin: 2px 0;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {c['accent_primary']};
        border: 1px solid {c['accent_primary']};
        width: 16px;
        height: 16px;
        margin: -6px 0;
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {c['accent_hover']};
    }}

    /* Tab Widget */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        background: {c['bg_secondary']};
        border-radius: 6px;
    }}
    QTabBar::tab {{
        background: {c['bg_main']};
        color: {c['fg_secondary']};
        padding: 8px 16px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {c['bg_secondary']};
        color: {c['accent_primary']};
        font-weight: bold;
    }}
    QTabBar::tab:hover:!selected {{
        background: {c['bg_tertiary']};
    }}

    /* Group Box */
    QGroupBox {{
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 20px; /* leave space for title */
        padding-top: 20px;
        background-color: {c['bg_secondary']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        color: {c['accent_primary']};
        font-weight: bold;
        left: 10px;
    }}

    /* Labels & Status */
    QLabel {{
        color: {c['fg_primary']};
    }}
    QLabel#titleLabel {{
        font-size: 20px;
        font-weight: 700;
        color: {c['accent_primary']};
    }}
    QLabel#subtitleLabel {{
        font-size: 13px;
        color: {c['fg_secondary']};
    }}
    QLabel#statusLabel {{
        font-weight: bold;
        color: {c['accent_secondary']};
    }}
    QLabel#errorLabel {{
        color: {c['error']};
    }}
    QLabel#warningLabel {{
        color: {c['warning']};
    }}

    /* Status Bar */
    QStatusBar {{
        background-color: {c['bg_secondary']};
        color: {c['fg_secondary']};
        border-top: 1px solid {c['border']};
    }}

    /* Splitter */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:vertical {{
        height: 2px;
    }}

    /* Checkbox & Radio */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {c['fg_primary']};
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {c['fg_tertiary']};
        border-radius: 4px;
        background: {c['input_bg']};
    }}
    QRadioButton::indicator {{
        border-radius: 9px;
    }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {c['accent_primary']};
        border-color: {c['accent_primary']};
    }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: {c['accent_hover']};
    }}

    /* Custom Widgets */
    QFrame#dropZone {{
        background-color: {c['bg_secondary']};
        border: 2px dashed {c['fg_tertiary']};
        border-radius: 12px;
    }}
    QFrame#dropZone:hover {{
        background-color: {c['bg_tertiary']};
        border-color: {c['accent_primary']};
    }}

    /* Status Colors for Table Text */
    QLabel#statusPending {{ color: {c['fg_secondary']}; }}
    QLabel#statusProcessing {{ color: {c['warning']}; }}
    QLabel#statusDone {{ color: {c['success']}; }}
    QLabel#statusError {{ color: {c['error']}; }}
    
    /* Secondary Button Style */
    QPushButton#secondaryButton {{
        background-color: {c['bg_tertiary']};
        color: {c['fg_secondary']};
        border: 1px solid {c['border']};
    }}
    QPushButton#secondaryButton:hover {{
        background-color: {c['border']};
        color: {c['fg_primary']};
    }}
    
    /* STT Section - Consistent theme styling */
    QTableWidget#sttQueue {{
        background-color: {c['bg_secondary']};
        color: {c['fg_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        gridline-color: {c['border']};
    }}
    QTableWidget#sttQueue::item {{
        color: {c['fg_primary']};
        background-color: {c['bg_secondary']};
        padding: 10px 8px;
    }}
    QTableWidget#sttQueue::item:selected {{
        background-color: {c['selection']};
        color: {c['fg_primary']};
    }}
    QTableWidget#sttQueue::item:alternate {{
        background-color: {c['bg_tertiary']};
    }}
    QTableWidget#sttQueue QHeaderView::section {{
        background-color: {c['bg_tertiary']};
        color: {c['fg_secondary']};
        padding: 10px 8px;
        border: none;
        border-bottom: 1px solid {c['border']};
        font-weight: 600;
        font-size: 12px;
    }}
    
    /* STT Transcript - Clean readable styling */
    QTextBrowser#sttTranscript {{
        background-color: {c['bg_secondary']};
        color: {c['fg_primary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        padding: 16px;
        font-size: 14px;
        line-height: 1.6;
    }}
    
    /* STT Export Buttons - Smaller, secondary style */
    QPushButton#sttExportBtn {{
        background-color: {c['bg_tertiary']};
        color: {c['fg_secondary']};
        border: 1px solid {c['border']};
        padding: 6px 12px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton#sttExportBtn:hover {{
        background-color: {c['border']};
        color: {c['fg_primary']};
    }}
    
    /* STT Start Button - Primary action */
    QPushButton#sttStartBtn {{
        background-color: {c['accent_primary']};
        color: #ffffff;
        border: none;
        padding: 10px 20px;
        font-weight: 600;
    }}
    QPushButton#sttStartBtn:hover {{
        background-color: {c['accent_hover']};
    }}
    
    /* STT Stop Button */
    QPushButton#sttStopBtn {{
        background-color: {c['fg_tertiary']};
        color: #ffffff;
        border: none;
        padding: 10px 20px;
    }}
    QPushButton#sttStopBtn:hover {{
        background-color: {c['fg_secondary']};
    }}
    
    /* STT Clear Button - Danger style */
    QPushButton#sttClearBtn {{
        background-color: transparent;
        color: {c['error']};
        border: 1px solid {c['error']};
        padding: 6px 12px;
    }}
    QPushButton#sttClearBtn:hover {{
        background-color: {c['error']};
        color: #ffffff;
    }}
    
    /* STT Drop Zone - Same as TTS DropZone */
    QWidget#sttDropZone {{
        background-color: {c['bg_secondary']};
        border: 2px dashed {c['fg_tertiary']};
        border-radius: 12px;
        padding: 8px;
    }}
    QWidget#sttDropZone:hover {{
        background-color: {c['bg_tertiary']};
        border-color: {c['accent_primary']};
    }}
    
    /* STT Group Boxes - More spacing */
    QGroupBox#sttGroup {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        margin-top: 24px;
        padding: 20px;
        padding-top: 28px;
    }}
    QGroupBox#sttGroup::title {{
        color: {c['fg_primary']};
        font-weight: 600;
        font-size: 14px;
    }}
    
    /* Modern rounded scrollbars */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px 2px 4px 2px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        min-height: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['fg_tertiary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
        height: 0px;
    }}
    """

def is_system_dark_mode() -> bool:
    """Detect if system is using dark mode"""
    try:
        import sys
        if sys.platform == "win32":
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0  # 0 = dark, 1 = light
        elif sys.platform == "darwin":
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True
            )
            return "Dark" in result.stdout
        else:
            # Linux - check various desktop environments
            import os
            # Check GTK theme
            gtk_theme = os.environ.get("GTK_THEME", "").lower()
            if "dark" in gtk_theme:
                return True
            # Check GNOME
            try:
                import subprocess
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    capture_output=True, text=True
                )
                return "dark" in result.stdout.lower()
            except:
                pass
            return False
    except:
        return True  # Default to dark on error

def get_theme_stylesheet(theme: str = "system") -> str:
    """Get stylesheet for theme"""
    if theme == "system":
        is_dark = is_system_dark_mode()
        return get_stylesheet("dark" if is_dark else "light")
    return get_stylesheet(theme)
