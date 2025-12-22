"""Theme styles for 2TTS application"""
import sys

# Modern Color Palette (Tokyo Night / Catppuccin inspired)
COLORS = {
    "dark": {
        "bg_main": "#1a1b26",          # Deep background
        "bg_secondary": "#24283b",      # Component background
        "bg_tertiary": "#2f3549",       # Hover/Active background
        "fg_primary": "#c0caf5",        # Primary text
        "fg_secondary": "#a9b1d6",      # Secondary text
        "fg_tertiary": "#565f89",       # Muted text
        "accent_primary": "#7aa2f7",    # Primary Blue
        "accent_secondary": "#bb9af7",  # Secondary Purple
        "accent_hover": "#89ddff",      # Hover Cyan
        "success": "#9ece6a",           # Green
        "warning": "#e0af68",           # Orange/Yellow
        "error": "#f7768e",             # Red
        "border": "#414868",            # Border color
        "input_bg": "#16161e",          # Input field background
        "selection": "#3d59a1"          # Selection background
    },
    "light": {
        "bg_main": "#f3f4f6",           # Outer background
        "bg_secondary": "#ffffff",      # Component background
        "bg_tertiary": "#f9fafb",       # Hover/Active background
        "fg_primary": "#111827",        # Primary text
        "fg_secondary": "#4b5563",      # Secondary text
        "fg_tertiary": "#9ca3af",       # Muted text
        "accent_primary": "#3b82f6",    # Primary Blue
        "accent_secondary": "#8b5cf6",  # Secondary Purple
        "accent_hover": "#2563eb",      # Hover Blue
        "success": "#10b981",           # Green
        "warning": "#f59e0b",           # Orange
        "error": "#ef4444",             # Red
        "border": "#e5e7eb",            # Border color
        "input_bg": "#ffffff",          # Input field background
        "selection": "#bfdbfe"          # Selection background
    }
}

def get_stylesheet(theme_name: str) -> str:
    """Generate stylesheet for the given theme name ('dark' or 'light')"""
    c = COLORS.get(theme_name, COLORS["dark"])
    
    return f"""
    /* Global Reset */
    * {{
        outline: none;
    }}

    QWidget {{
        background-color: {c['bg_main']};
        color: {c['fg_primary']};
        font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
        font-size: 14px;
        selection-background-color: {c['selection']};
        selection-color: {c['fg_primary']};
    }}

    /* Main Container Structure */
    QMainWindow, QDialog {{
        background-color: {c['bg_main']};
    }}

    /* Menu Bar */
    QMenuBar {{
        background-color: {c['bg_secondary']};
        border-bottom: 1px solid {c['border']};
        padding: 2px 6px;
    }}
    QMenuBar::item {{
        padding: 6px 12px;
        border-radius: 4px;
        color: {c['fg_secondary']};
        background: transparent;
    }}
    QMenuBar::item:selected {{
        background-color: {c['bg_tertiary']};
        color: {c['fg_primary']};
    }}
    
    QMenu {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 24px 6px 12px;
        border-radius: 4px;
        color: {c['fg_secondary']};
    }}
    QMenu::item:selected {{
        background-color: {c['accent_primary']};
        color: #1a1b26; /* Dark text on accent */
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {c['border']};
        margin: 4px 8px;
    }}

    /* ToolBar */
    QToolBar {{
        background-color: {c['bg_secondary']};
        border-bottom: 1px solid {c['border']};
        padding: 6px;
        spacing: 8px;
    }}
    QToolButton {{
        padding: 6px;
        border-radius: 4px;
        background: transparent;
    }}
    QToolButton:hover {{
        background-color: {c['bg_tertiary']};
    }}

    /* Buttons */
    QPushButton {{
        background-color: {c['bg_secondary']};
        color: {c['fg_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {c['bg_tertiary']};
        border-color: {c['fg_secondary']};
        color: {c['fg_primary']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_main']};
        padding-top: 9px;
        padding-bottom: 7px;
    }}
    QPushButton:disabled {{
        background-color: {c['bg_main']};
        color: {c['fg_tertiary']};
        border-color: {c['border']};
    }}

    /* Primary Action Button */
    QPushButton#primaryButton {{
        background-color: {c['accent_primary']};
        color: #1a1b26;
        border: 1px solid {c['accent_primary']};
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {c['accent_hover']};
        border-color: {c['accent_hover']};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {c['accent_primary']};
    }}

    /* Danger Button */
    QPushButton#dangerButton {{
        background-color: transparent;
        color: {c['error']};
        border: 1px solid {c['error']};
    }}
    QPushButton#dangerButton:hover {{
        background-color: {c['error']};
        color: #ffffff;
    }}
    
    /* Small Tool Buttons */
    QPushButton#iconButton {{
        padding: 6px;
        min-width: 32px;
    }}

    /* Input Fields */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {c['input_bg']};
        color: {c['fg_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
    }}
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
        border: 1px solid {c['accent_primary']};
        background-color: {c['input_bg']};
    }}
    QLineEdit:disabled, QSpinBox:disabled {{
        background-color: {c['bg_main']};
        color: {c['fg_tertiary']};
    }}

    /* Combo Box */
    QComboBox {{
        background-color: {c['input_bg']};
        color: {c['fg_primary']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px 12px;
    }}
    QComboBox:hover {{
        border-color: {c['fg_secondary']};
    }}
    QComboBox:focus {{
        border: 1px solid {c['accent_primary']};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 30px;
        border-left-width: 0px;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border: none;
        /* Draw arrow using CSS borders */
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
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

    /* Table Widget */
    QTableWidget, QTableView {{
        background-color: {c['input_bg']};
        gridline-color: {c['border']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        alternate-background-color: {c['bg_secondary']};
    }}
    QTableWidget::item, QTableView::item {{
        padding: 8px;
        border-bottom: 1px solid {c['bg_main']};
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        background-color: {c['selection']};
        color: #ffffff;
    }}
    QHeaderView::section {{
        background-color: {c['bg_secondary']};
        color: {c['fg_secondary']};
        padding: 8px;
        border: none;
        border-bottom: 2px solid {c['border']};
        border-right: 1px solid {c['border']};
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
    }}
    QCornerButton::section {{
        background-color: {c['bg_secondary']};
        border: none;
        border-bottom: 2px solid {c['border']};
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: {c['bg_main']};
        width: 12px;
        margin: 0px;
        border-radius: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['bg_tertiary']};
        min-height: 20px;
        border-radius: 6px;
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
        height: 12px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['bg_tertiary']};
        min-width: 20px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['fg_tertiary']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* Sliders */
    QSlider::groove:horizontal {{
        border: 1px solid {c['bg_tertiary']};
        height: 4px;
        background: {c['bg_tertiary']};
        margin: 2px 0;
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {c['accent_primary']};
        border: 1px solid {c['accent_primary']};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {c['accent_hover']};
        border-color: {c['accent_hover']};
    }}

    /* Tab Widget */
    QTabWidget::pane {{
        border: 1px solid {c['border']};
        background: {c['bg_secondary']};
        border-bottom-left-radius: 6px;
        border-bottom-right-radius: 6px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: {c['bg_main']};
        color: {c['fg_secondary']};
        padding: 8px 20px;
        border: 1px solid transparent;
        border-bottom: 1px solid {c['border']};
        margin-right: 4px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 500;
    }}
    QTabBar::tab:hover {{
        background: {c['bg_tertiary']};
        color: {c['fg_primary']};
    }}
    QTabBar::tab:selected {{
        background: {c['bg_secondary']};
        color: {c['accent_primary']};
        border: 1px solid {c['border']};
        border-bottom-color: {c['bg_secondary']};
        font-weight: 600;
    }}

    /* Group Box */
    QGroupBox {{
        background-color: {c['bg_secondary']};
        border: 1px solid {c['border']};
        border-radius: 8px;
        margin-top: 1.5em;
        padding-top: 1.5em;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        color: {c['accent_primary']};
        font-weight: 600;
        left: 10px;
        background-color: transparent;
    }}

    /* Labels */
    QLabel {{
        color: {c['fg_primary']};
    }}
    QLabel#titleLabel {{
        font-size: 18px;
        font-weight: 700;
        color: {c['accent_primary']};
    }}
    QLabel#subtitleLabel {{
        font-size: 13px;
        color: {c['fg_secondary']};
    }}
    
    /* Progress Bar */
    QProgressBar {{
        border: none;
        background-color: {c['bg_main']};
        border-radius: 4px;
        text-align: center;
        color: {c['fg_primary']};
        font-size: 11px;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent_primary']};
        border-radius: 4px;
    }}

    /* Splitter */
    QSplitter::handle {{
        background-color: {c['bg_main']};
    }}
    QSplitter::handle:horizontal {{
        width: 4px;
    }}

    /* CheckBox */
    QCheckBox {{
        spacing: 8px;
        color: {c['fg_primary']};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border: 1px solid {c['fg_tertiary']};
        border-radius: 4px;
        background: {c['input_bg']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c['accent_primary']};
        border-color: {c['accent_primary']};
    }}

    /* Custom Widget: DropZone */
    QFrame#dropZone {{
        background-color: {c['bg_secondary']};
        border: 2px dashed {c['border']};
        border-radius: 12px;
    }}
    QFrame#dropZone:hover {{
        border-color: {c['accent_primary']};
        background-color: {c['bg_tertiary']};
    }}
    
    /* Status Bar */
    QStatusBar {{
        background-color: {c['bg_secondary']};
        color: {c['fg_secondary']};
        border-top: 1px solid {c['border']};
    }}
    QStatusBar QLabel {{
        padding: 0 10px;
    }}
    """

def is_system_dark_mode() -> bool:
    """Detect if system is using dark mode"""
    # ... (Same implementation as before)
    try:
        import sys
        if sys.platform == "win32":
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        return True
    except:
        return True

def get_theme_stylesheet(theme: str = "system") -> str:
    """Get stylesheet for theme"""
    if theme == "system":
        is_dark = is_system_dark_mode()
        return get_stylesheet("dark" if is_dark else "light")
    return get_stylesheet(theme)
