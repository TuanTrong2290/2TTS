"""Icon management for 2TTS application

Provides consistent icon access using Qt standard icons with emoji fallbacks.
This allows easy migration to custom icons in the future while maintaining
consistent visual styling across the application.
"""
from PyQt6.QtWidgets import QStyle, QApplication
from PyQt6.QtGui import QIcon


# Mapping of icon names to Qt standard icons and emoji fallbacks
ICON_MAP = {
    # File operations
    "new": (QStyle.StandardPixmap.SP_FileIcon, "📄"),
    "open": (QStyle.StandardPixmap.SP_DialogOpenButton, "📂"),
    "save": (QStyle.StandardPixmap.SP_DialogSaveButton, "💾"),
    "folder": (QStyle.StandardPixmap.SP_DirIcon, "📁"),
    
    # Media/playback
    "play": (QStyle.StandardPixmap.SP_MediaPlay, "▶"),
    "pause": (QStyle.StandardPixmap.SP_MediaPause, "⏸"),
    "stop": (QStyle.StandardPixmap.SP_MediaStop, "⏹"),
    "audio": (QStyle.StandardPixmap.SP_MediaVolume, "🔊"),
    
    # Actions
    "refresh": (QStyle.StandardPixmap.SP_BrowserReload, "↻"),
    "delete": (QStyle.StandardPixmap.SP_TrashIcon, "🗑"),
    "add": (QStyle.StandardPixmap.SP_FileDialogNewFolder, "➕"),
    "remove": (QStyle.StandardPixmap.SP_DialogDiscardButton, "➖"),
    "settings": (QStyle.StandardPixmap.SP_ComputerIcon, "⚙"),
    "help": (QStyle.StandardPixmap.SP_DialogHelpButton, "❓"),
    "info": (QStyle.StandardPixmap.SP_MessageBoxInformation, "ℹ"),
    "warning": (QStyle.StandardPixmap.SP_MessageBoxWarning, "⚠"),
    "error": (QStyle.StandardPixmap.SP_MessageBoxCritical, "❌"),
    "success": (QStyle.StandardPixmap.SP_DialogApplyButton, "✓"),
    
    # Navigation
    "up": (QStyle.StandardPixmap.SP_ArrowUp, "↑"),
    "down": (QStyle.StandardPixmap.SP_ArrowDown, "↓"),
    "left": (QStyle.StandardPixmap.SP_ArrowLeft, "←"),
    "right": (QStyle.StandardPixmap.SP_ArrowRight, "→"),
    "back": (QStyle.StandardPixmap.SP_ArrowBack, "←"),
    "forward": (QStyle.StandardPixmap.SP_ArrowForward, "→"),
    
    # App-specific
    "voice": (None, "🗣"),
    "key": (None, "🔑"),
    "proxy": (None, "🌐"),
    "export": (None, "📤"),
    "import": (None, "📥"),
    "join": (None, "🎵"),
    "srt": (None, "📝"),
    "split": (None, "✂"),
    "merge": (None, "🔗"),
    "retry": (None, "🔄"),
    "cloud": (None, "☁"),
    "mic": (None, "🎤"),
    "library": (None, "📚"),
    "preview": (None, "👁"),
    "clone": (None, "🎤"),
    "document": (None, "📄"),
    "tip": (None, "💡"),
}


def get_icon(name: str, use_qt_icons: bool = False) -> QIcon:
    """
    Get a QIcon for the given name.
    
    Args:
        name: Icon identifier from ICON_MAP
        use_qt_icons: If True, prefer Qt standard icons; if False, return empty icon
        
    Returns:
        QIcon instance (may be empty if no Qt icon available and use_qt_icons=False)
    """
    if name not in ICON_MAP:
        return QIcon()
    
    qt_pixmap, _ = ICON_MAP[name]
    
    if use_qt_icons and qt_pixmap is not None:
        app = QApplication.instance()
        if app:
            style = app.style()
            if style:
                return style.standardIcon(qt_pixmap)
    
    return QIcon()


def get_emoji(name: str) -> str:
    """
    Get the emoji string for the given icon name.
    
    Args:
        name: Icon identifier from ICON_MAP
        
    Returns:
        Emoji string or empty string if not found
    """
    if name not in ICON_MAP:
        return ""
    
    _, emoji = ICON_MAP[name]
    return emoji


def get_icon_text(name: str, text: str = "", use_qt_icons: bool = False) -> str:
    """
    Get formatted text with icon prefix.
    
    Args:
        name: Icon identifier from ICON_MAP
        text: Text to append after icon
        use_qt_icons: Whether to skip emoji (for use with QIcon)
        
    Returns:
        Formatted string with emoji prefix and text
    """
    if use_qt_icons:
        return text
    
    emoji = get_emoji(name)
    if emoji and text:
        return f"{emoji} {text}"
    return emoji or text


# Convenience function for button text
def btn_text(icon_name: str, label: str) -> str:
    """Create button text with emoji icon prefix"""
    return get_icon_text(icon_name, label)
