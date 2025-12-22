"""Main window for 2TTS application"""
import os
import sys
import threading
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QStatusBar, QMenuBar, QMenu, QMessageBox,
    QFileDialog, QLabel, QPushButton, QComboBox, QGroupBox,
    QTextEdit, QCheckBox, QSpinBox, QApplication, QSystemTrayIcon,
    QDialog, QTabWidget, QProgressDialog, QToolBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QUrl
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from core.models import (
    Project, TextLine, LineStatus, Voice, VoiceSettings,
    APIKey, Proxy, ProjectSettings
)
from core.config import get_config
from services.file_import import FileImporter, TextSplitter
from services.elevenlabs import ElevenLabsAPI, APIKeyManager
from services.processing import ProcessingEngine, ProcessingStats
from services.audio import SRTGenerator, MP3Concatenator
from services.language import LanguageDetector
from ui.widgets import (
    DropZone, LineTableWidget, VoiceSettingsWidget, 
    ProgressWidget, CreditWidget, FilterWidget, ThreadStatusWidget,
    TableEmptyState
)
from ui.dialogs import (
    APIKeyDialog, ProxyDialog, VoiceLibraryDialog, SettingsDialog
)
from ui.new_dialogs import (
    PresetManagerDialog, VoiceAssignmentDialog, AudioProcessingDialog, AnalyticsDialog
)
from ui.styles import get_theme_stylesheet
from ui.transcribe_tab import TranscribeTab
from services.logger import get_logger
from services.command_manager import (
    CommandManager, AddLinesCommand, DeleteLinesCommand,
    EditLineTextCommand, ChangeVoiceCommand, MergeLinesCommand, SplitLineCommand
)
from services.preset_manager import get_preset_manager
from services.voice_matcher import get_voice_matcher
from services.audio_processor import AudioProcessor, AudioProcessingSettings
from services.analytics import get_analytics

from services.updater import get_update_checker, UpdateInfo

from services.localization import tr, set_language, get_localization


class LineUpdateEvent(QEvent):
    """Custom event for line updates"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, line: TextLine):
        super().__init__(self.EVENT_TYPE)
        self.line = line


class MainWindow(QMainWindow):
    """Main application window"""

    update_check_result = pyqtSignal(bool, object, str, bool)  # available, UpdateInfo|None, message, show_result
    update_download_result = pyqtSignal(bool, object, object, str)  # success, UpdateInfo, Path|None, message
    update_download_progress = pyqtSignal(int, int, int)  # downloaded, total, percent
    
    def __init__(self):
        super().__init__()
        
        # Config
        self._config = get_config()
        
        # Set language from config
        set_language(self._config.app_language)
        
        self.setWindowTitle(tr("app_title"))
        self.setMinimumSize(1280, 850)
        
        # Current project
        self._project = Project()
        self._project.settings.output_folder = self._config.default_output_folder
        
        # Services
        self._api = ElevenLabsAPI()
        self._importer = FileImporter()
        self._splitter = TextSplitter()
        self._lang_detector = LanguageDetector()
        self._srt_generator = SRTGenerator()
        self._mp3_concat = MP3Concatenator()
        self._engine: Optional[ProcessingEngine] = None
        
        # Voices cache
        self._voices: Dict[str, Voice] = {}
        
        # New services
        self._logger = get_logger()
        self._command_manager = CommandManager()
        self._command_manager.set_change_callback(self._on_command_change)
        self._preset_manager = get_preset_manager()
        self._voice_matcher = get_voice_matcher()
        self._audio_processor = AudioProcessor()
        self._audio_settings = AudioProcessingSettings()
        self._analytics = get_analytics()

        # Updater
        self._update_checker = get_update_checker()
        self._update_check_in_progress = False
        self._update_download_in_progress = False
        self._update_user_initiated = False
        self._update_install_scheduled = False
        self._pending_update_info: Optional[UpdateInfo] = None
        self._pending_update_installer: Optional[Path] = None
        self._update_progress_dialog: Optional[QProgressDialog] = None

        self.update_check_result.connect(self._on_update_check_result)
        self.update_download_result.connect(self._on_update_download_result)
        self.update_download_progress.connect(self._on_update_download_progress)

        ready_update = self._update_checker.get_ready_update()
        if ready_update and self._update_checker.is_newer_version(ready_update[0].version):
            self._pending_update_info, self._pending_update_installer = ready_update
        
        # Start analytics session
        self._analytics.start_session()
        
        # UI setup
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._apply_theme()
        
        # Timer for progress updates
        self._progress_timer = QTimer()
        self._progress_timer.timeout.connect(self._update_progress_display)
        
        # Auto-save timer (every 5 minutes)
        self._autosave_timer = QTimer()
        self._autosave_timer.timeout.connect(self._on_autosave)
        self._autosave_timer.start(300000)  # 5 minutes
        
        # Audio player for preview
        self._audio_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._audio_player.setAudioOutput(self._audio_output)
        
        # System tray
        self._setup_system_tray()
        
        # Load voices if keys available
        self._refresh_voices()
        self._refresh_credits(fetch_from_api=True)
        
        self._logger.info("Application started")

        # Background update check (non-blocking)
        QTimer.singleShot(5000, lambda: self._check_for_updates(force=False, show_result=False))
    
    def _setup_ui(self):
        """Setup main UI layout"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget for TTS and Transcribe
        self._tab_widget = QTabWidget()
        self._tab_widget.setDocumentMode(True)
        
        # TTS Tab
        tts_tab = QWidget()
        tts_layout = QHBoxLayout(tts_tab)
        tts_layout.setContentsMargins(12, 12, 12, 12)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)
        
        # Left panel - main content
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        # Drop zone (starts in full mode, switches to compact when lines exist)
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        left_layout.addWidget(self._drop_zone)
        
        # Filter widget
        self._filter_widget = FilterWidget()
        self._filter_widget.filter_changed.connect(self._on_filter_changed)
        left_layout.addWidget(self._filter_widget)
        
        # Empty state (shown when no lines)
        self._empty_state = TableEmptyState()
        self._empty_state.import_clicked.connect(self._on_import_files)
        left_layout.addWidget(self._empty_state)
        
        # Table
        self._table = LineTableWidget()
        self._table.lines_reordered.connect(self._on_lines_reordered)
        self._table.text_edited.connect(self._on_text_edited)
        self._table.play_requested.connect(self._on_play_audio)
        self._table.retry_requested.connect(self._on_retry_lines)
        self._table.delete_requested.connect(self._on_delete_lines)
        self._table.split_requested.connect(self._on_split_line)
        self._table.merge_requested.connect(self._on_merge_lines)
        left_layout.addWidget(self._table)
        
        # Initial state: show empty state, hide table
        self._update_empty_state()
        
        # Progress Bar
        self._progress = ProgressWidget()
        left_layout.addWidget(self._progress)
        
        # Control Buttons Area (Bottom of Left Panel)
        controls_frame = QFrame()
        controls_frame.setObjectName("controlsFrame")
        controls_frame.setStyleSheet("""
            QFrame#controlsFrame {
                background-color: transparent;
                border-top: 1px solid #414868;
                padding-top: 10px;
            }
        """)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Transport Controls
        transport_layout = QHBoxLayout()
        transport_layout.setSpacing(10)
        
        self._start_btn = QPushButton("▶ " + tr("start"))
        self._start_btn.setObjectName("primaryButton")
        self._start_btn.setMinimumHeight(40)
        self._start_btn.setMinimumWidth(100)
        self._start_btn.clicked.connect(self._on_start)
        
        self._pause_btn = QPushButton("⏸ " + tr("pause"))
        self._pause_btn.setMinimumHeight(40)
        self._pause_btn.clicked.connect(self._on_pause)
        self._pause_btn.setEnabled(False)
        
        self._stop_btn = QPushButton("⏹ " + tr("stop"))
        self._stop_btn.setObjectName("dangerButton")
        self._stop_btn.setMinimumHeight(40)
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)
        
        transport_layout.addWidget(self._start_btn)
        transport_layout.addWidget(self._pause_btn)
        transport_layout.addWidget(self._stop_btn)
        
        controls_layout.addLayout(transport_layout)
        controls_layout.addStretch()
        
        # Export Menu Button (consolidated export actions)
        self._export_btn = QPushButton("📤 " + tr("export") + " ▾")
        self._export_btn.setMinimumHeight(40)
        self._export_btn.setToolTip("Export options: Join MP3, Generate SRT, Open folder")
        
        export_menu = QMenu(self._export_btn)
        export_menu.addAction("🎵 " + tr("join_mp3"), self._on_join_mp3)
        export_menu.addAction("📝 " + tr("generate_srt"), self._on_generate_srt)
        export_menu.addSeparator()
        export_menu.addAction("📂 " + tr("open_folder"), self._on_open_folder)
        self._export_btn.setMenu(export_menu)
        
        controls_layout.addWidget(self._export_btn)
        left_layout.addWidget(controls_frame)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Tools and Settings using QToolBox
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self._toolbox = QToolBox()
        self._toolbox.setMinimumWidth(340)
        
        # 1. Voice Settings Group
        voice_page = QWidget()
        voice_page_layout = QVBoxLayout(voice_page)
        voice_page_layout.setContentsMargins(10, 10, 10, 10)
        voice_page_layout.setSpacing(12)
        
        # Voice Selection Row
        voice_select_layout = QHBoxLayout()
        voice_select_layout.addWidget(QLabel(tr("default_voice") + ":"))
        self._voice_combo = QComboBox()
        self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        voice_select_layout.addWidget(self._voice_combo)
        
        self._voice_lib_btn = QPushButton("📚")
        self._voice_lib_btn.setFixedWidth(36)
        self._voice_lib_btn.setToolTip("Open Voice Library")
        self._voice_lib_btn.clicked.connect(self._on_voice_library)
        voice_select_layout.addWidget(self._voice_lib_btn)
        
        self._voice_preview_btn = QPushButton("🔊")
        self._voice_preview_btn.setFixedWidth(36)
        self._voice_preview_btn.setToolTip("Preview Selected Voice")
        self._voice_preview_btn.clicked.connect(self._on_voice_preview)
        voice_select_layout.addWidget(self._voice_preview_btn)
        
        voice_page_layout.addLayout(voice_select_layout)
        
        # Voice Settings Widget
        self._voice_settings = VoiceSettingsWidget(title="Params")
        self._voice_settings.settings_changed.connect(self._on_voice_settings_changed)
        voice_page_layout.addWidget(self._voice_settings)
        
        # Apply Buttons
        apply_layout = QHBoxLayout()
        self._apply_voice_btn = QPushButton(tr("apply_to_selected"))
        self._apply_voice_btn.setToolTip("Apply current voice to selected lines")
        self._apply_voice_btn.clicked.connect(self._on_apply_voice_to_selected)
        apply_layout.addWidget(self._apply_voice_btn)
        
        self._apply_voice_all_btn = QPushButton(tr("apply_to_all"))
        self._apply_voice_all_btn.setToolTip("Apply current voice to all lines in project")
        self._apply_voice_all_btn.clicked.connect(self._on_apply_voice_to_all)
        apply_layout.addWidget(self._apply_voice_all_btn)
        
        voice_page_layout.addLayout(apply_layout)
        voice_page_layout.addStretch()
        
        self._toolbox.addItem(voice_page, QIcon(), "🗣 " + tr("voice_settings"))
        
        # 2. Processing Options Group
        proc_page = QWidget()
        proc_layout = QVBoxLayout(proc_page)
        proc_layout.setContentsMargins(10, 10, 10, 10)
        
        # Threading
        threads_group = QGroupBox(tr("threads"))
        threads_layout = QHBoxLayout(threads_group)
        threads_layout.addWidget(QLabel(tr("threads") + ":"))
        self._threads_spin = QSpinBox()
        self._threads_spin.setRange(1, 50)
        self._threads_spin.setValue(self._project.settings.thread_count)
        self._threads_spin.setToolTip("Number of concurrent requests")
        threads_layout.addWidget(self._threads_spin)
        proc_layout.addWidget(threads_group)
        
        # Loop Mode
        loop_group = QGroupBox(tr("loop_mode"))
        loop_layout = QVBoxLayout(loop_group)
        
        self._loop_check = QCheckBox("Enable " + tr("loop_mode"))
        self._loop_check.setChecked(self._project.settings.loop_enabled)
        loop_layout.addWidget(self._loop_check)
        
        loop_params_layout = QHBoxLayout()
        loop_params_layout.addWidget(QLabel(tr("loop_count_label") + ":"))
        self._loop_count_spin = QSpinBox()
        self._loop_count_spin.setRange(0, 1000)
        self._loop_count_spin.setValue(self._project.settings.loop_count)
        loop_params_layout.addWidget(self._loop_count_spin)
        loop_layout.addLayout(loop_params_layout)
        
        proc_layout.addWidget(loop_group)
        proc_layout.addStretch()
        
        self._toolbox.addItem(proc_page, QIcon(), "⚙ " + tr("processing"))
        
        # 3. Status & Logs
        status_page = QWidget()
        status_layout = QVBoxLayout(status_page)
        status_layout.setContentsMargins(10, 10, 10, 10)
        
        # Thread Status
        self._thread_status = ThreadStatusWidget(max_threads=10)
        status_layout.addWidget(self._thread_status)
        
        # Logs
        log_label_layout = QHBoxLayout()
        log_label_layout.addWidget(QLabel("Activity Log:"))
        log_label_layout.addStretch()
        
        export_log_btn = QPushButton("💾 " + tr("export_log"))
        export_log_btn.clicked.connect(self._on_export_log)
        export_log_btn.setFixedHeight(24)
        log_label_layout.addWidget(export_log_btn)
        
        status_layout.addLayout(log_label_layout)
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setFontFamily("Consolas")
        status_layout.addWidget(self._log_text)
        
        self._toolbox.addItem(status_page, QIcon(), "📊 " + tr("log"))
        
        right_layout.addWidget(self._toolbox)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (ratio)
        splitter.setSizes([900, 380])
        splitter.setCollapsible(0, False) # Left panel not collapsible
        splitter.setCollapsible(1, True)  # Right panel collapsible
        
        tts_layout.addWidget(splitter)
        
        # Add TTS tab
        self._tab_widget.addTab(tts_tab, "🔊 " + tr("app_title").split(" - ")[0])
        
        # Add Transcribe tab
        self._transcribe_tab = TranscribeTab()
        self._tab_widget.addTab(self._transcribe_tab, "🎤 " + tr("transcribe_tab"))
        
        main_layout.addWidget(self._tab_widget)
    
    def _setup_menu(self):
        """Setup menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&" + tr("file"))
        
        new_action = QAction("&" + tr("new_project"), self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&" + tr("open_project") + "...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction("&" + tr("save_project"), self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction(tr("save_project_as"), self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._on_save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("&" + tr("import_files") + "...", self)
        import_action.setShortcut(QKeySequence("Ctrl+I"))
        import_action.triggered.connect(self._on_import_files)
        file_menu.addAction(import_action)
        
        import_folder_action = QAction(tr("import") + " Folder...", self)
        import_folder_action.triggered.connect(self._on_import_folder)
        file_menu.addAction(import_folder_action)
        
        file_menu.addSeparator()
        
        export_txt_action = QAction("&" + tr("export") + " Text...", self)
        export_txt_action.triggered.connect(self._on_export_text)
        file_menu.addAction(export_txt_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(tr("exit"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&" + tr("edit"))
        
        self._undo_action = QAction("&" + tr("undo"), self)
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_action.triggered.connect(self._on_undo)
        self._undo_action.setEnabled(False)
        edit_menu.addAction(self._undo_action)
        
        self._redo_action = QAction("&" + tr("redo"), self)
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_action.triggered.connect(self._on_redo)
        self._redo_action.setEnabled(False)
        edit_menu.addAction(self._redo_action)
        
        edit_menu.addSeparator()
        
        clear_action = QAction("&" + tr("clear_all"), self)
        clear_action.triggered.connect(self._on_clear_all)
        edit_menu.addAction(clear_action)
        
        remove_done_action = QAction("&" + tr("completed"), self)
        remove_done_action.triggered.connect(self._on_remove_completed)
        edit_menu.addAction(remove_done_action)
        
        retry_failed_action = QAction(tr("retry_failed"), self)
        retry_failed_action.triggered.connect(self._on_retry_failed)
        edit_menu.addAction(retry_failed_action)
        
        edit_menu.addSeparator()
        
        bulk_voice_action = QAction("&" + tr("voice_assignment") + "...", self)
        bulk_voice_action.triggered.connect(self._on_bulk_voice_assignment)
        edit_menu.addAction(bulk_voice_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&" + tr("tools"))
        
        api_keys_action = QAction("&" + tr("api_keys") + "...", self)
        api_keys_action.triggered.connect(self._on_manage_api_keys)
        tools_menu.addAction(api_keys_action)
        
        proxies_action = QAction("&" + tr("proxies") + "...", self)
        proxies_action.triggered.connect(self._on_manage_proxies)
        tools_menu.addAction(proxies_action)
        
        tools_menu.addSeparator()
        
        presets_action = QAction(tr("presets") + "...", self)
        presets_action.triggered.connect(self._on_presets)
        tools_menu.addAction(presets_action)
        
        audio_proc_action = QAction("&" + tr("audio_processing") + "...", self)
        audio_proc_action.triggered.connect(self._on_audio_processing)
        tools_menu.addAction(audio_proc_action)
        
        tools_menu.addSeparator()
        
        analytics_action = QAction("&" + tr("analytics") + "...", self)
        analytics_action.triggered.connect(self._on_analytics)
        tools_menu.addAction(analytics_action)
        
        tools_menu.addSeparator()
        
        # Transcription actions
        transcribe_action = QAction("🎤 " + tr("transcribe_audio") + "...", self)
        transcribe_action.triggered.connect(self._on_transcribe_files)
        tools_menu.addAction(transcribe_action)
        
        tools_menu.addSeparator()
        
        settings_action = QAction("&" + tr("settings") + "...", self)
        settings_action.triggered.connect(self._on_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("&" + tr("help"))
        
        check_update_action = QAction(tr("check_updates") + "...", self)
        check_update_action.triggered.connect(lambda: self._check_for_updates(force=True, show_result=True))
        help_menu.addAction(check_update_action)
        
        view_logs_action = QAction(tr("log") + "...", self)
        view_logs_action.triggered.connect(self._on_view_logs)
        help_menu.addAction(view_logs_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("&" + tr("about"), self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self):
        """Setup toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        toolbar.addAction("🔑 " + tr("api_keys"), self._on_manage_api_keys)
        toolbar.addAction("🌐 " + tr("proxies"), self._on_manage_proxies)
        toolbar.addSeparator()
        toolbar.addAction("⚙ " + tr("settings"), self._on_settings)
    
    def _setup_statusbar(self):
        """Setup status bar"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        self._credit_widget = CreditWidget()
        self._credit_widget.refresh_btn.clicked.connect(lambda: self._refresh_credits(fetch_from_api=True))
        statusbar.addPermanentWidget(self._credit_widget)
        
        # Model indicator in status bar
        self._model_status_label = QLabel("")
        self._model_status_label.setStyleSheet("color: #7aa2f7; font-weight: bold;")
        statusbar.addPermanentWidget(self._model_status_label)
        
        # Transcription status indicator
        self._transcribe_status_label = QLabel("")
        self._transcribe_status_label.setStyleSheet("color: #9ece6a; font-weight: bold;")
        statusbar.addPermanentWidget(self._transcribe_status_label)
        
        self._status_label = QLabel(tr("ready"))
        statusbar.addWidget(self._status_label)
    
    def _apply_theme(self):
        """Apply current theme"""
        theme = self._config.theme
        self.setStyleSheet(get_theme_stylesheet(theme))
    
    def _setup_system_tray(self):
        """Setup system tray icon and menu"""
        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setToolTip("2TTS - ElevenLabs TTS")
        
        # Set tray icon - handle PyInstaller bundle
        if getattr(sys, 'frozen', False):
            icon_path = Path(sys._MEIPASS) / "resources" / "icon.png"
        else:
            icon_path = Path(__file__).parent.parent / "resources" / "icon.png"
        if icon_path.exists():
            self._tray_icon.setIcon(QIcon(str(icon_path)))
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        start_action = QAction("Start Processing", self)
        start_action.triggered.connect(self._on_start)
        tray_menu.addAction(start_action)
        
        pause_action = QAction("Pause/Resume", self)
        pause_action.triggered.connect(self._on_pause)
        tray_menu.addAction(pause_action)
        
        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self._on_stop)
        tray_menu.addAction(stop_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()
    
    def _on_autosave(self):
        """Auto-save project if it has a path"""
        if self._project.file_path and self._project.lines:
            try:
                self._project.save(self._project.file_path)
                self._log("Auto-saved project")
            except Exception as e:
                self._log(f"Auto-save failed: {e}")
    
    def _on_command_change(self, can_undo: bool, can_redo: bool):
        """Handle command stack change"""
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)
    
    def _on_undo(self):
        """Undo last action"""
        if self._command_manager.undo():
            self._table.load_lines(self._project.lines)
            self._log("Undid last action")
    
    def _on_redo(self):
        """Redo last action"""
        if self._command_manager.redo():
            self._table.load_lines(self._project.lines)
            self._log("Redid last action")
    
    def _on_bulk_voice_assignment(self):
        """Open bulk voice assignment dialog"""
        if not self._project.lines:
            QMessageBox.warning(self, "Warning", "No lines to assign voices to")
            return
        
        dialog = VoiceAssignmentDialog(
            self._project.lines,
            list(self._voices.values()),
            self._config.voice_library,
            self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._table.load_lines(self._project.lines)
            self._log("Applied bulk voice assignment")

    def _on_presets(self):
        """Open preset manager"""
        dialog = PresetManagerDialog(self._preset_manager, self)
        dialog.preset_applied.connect(self._on_preset_applied)
        dialog.exec()
    
    def _on_preset_applied(self, preset_id: str):
        """Handle preset application"""
        preset = self._preset_manager.get_preset(preset_id)
        if not preset:
            return
        
        # Apply voice settings
        if preset.voice_settings:
            # Note: Presets might need to store model/voice ID too
            # For now, we apply settings to currently selected voice
            voice_id = self._voice_combo.currentData()
            if voice_id and voice_id in self._voices:
                voice = self._voices[voice_id]
                voice.settings = preset.voice_settings
                self._voice_settings.set_settings(preset.voice_settings)
                self._log(f"Applied preset '{preset.name}' to current voice")
    
    def _on_audio_processing(self):
        """Open audio processing dialog"""
        dialog = AudioProcessingDialog(self._audio_settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._audio_settings = dialog.get_settings()
            self._log("Audio processing settings updated")
    
    def _on_analytics(self):
        """Open analytics dialog"""
        dialog = AnalyticsDialog(self._analytics, self)
        dialog.exec()
    
    def _on_transcribe_files(self):
        """Switch to transcribe tab"""
        self._tab_widget.setCurrentWidget(self._transcribe_tab)
        # Optionally prompt to import files if empty
        if self._transcribe_tab.is_queue_empty():
             self._transcribe_tab._on_add_files()

    def _on_view_logs(self):
        """Show log dialog/tab"""
        # Switch to status page in toolbox
        self._toolbox.setCurrentIndex(2)

    def _log(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_text.append(f"[{timestamp}] {message}")
    
    def _get_model_display_name(self, model_id: str) -> str:
        """Convert model ID to friendly display name"""
        model_names = {
            "eleven_v3": "v3 Alpha",
            "eleven_multilingual_v2": "Multilingual v2",
            "eleven_turbo_v2_5": "Turbo v2.5",
            "eleven_flash_v2_5": "Flash v2.5",
            "eleven_flash_v2": "Flash v2",
        }
        return model_names.get(model_id, model_id)
    
    def _refresh_voices(self):
        """Refresh voices from API"""
        self._voice_combo.clear()
        self._voices.clear()
        
        api_key = self._config.get_available_api_key()
        if not api_key:
            return
        
        proxy = self._config.get_proxy_for_key(api_key)
        voices = self._api.get_voices(api_key, proxy)
        
        for voice in voices:
            self._voices[voice.voice_id] = voice
            prefix = "🎤 " if voice.is_cloned else ""
            self._voice_combo.addItem(f"{prefix}{voice.name}", voice.voice_id)
        
        self._table.set_voices(voices)
        self._log(f"Loaded {len(voices)} voices")
        
        # Select last used voice if available
        last_voice_id = self._config.last_voice_id
        if last_voice_id:
            index = self._voice_combo.findData(last_voice_id)
            if index >= 0:
                self._voice_combo.setCurrentIndex(index)
    
    def _refresh_credits(self, fetch_from_api: bool = False):
        """Refresh credit display"""
        if fetch_from_api:
            # Fetch latest subscription info from API for all keys
            for key in self._config.api_keys:
                if key.enabled:
                    proxy = self._config.get_proxy_for_key(key)
                    self._api.validate_key(key, proxy)
            self._config._save_api_keys()
        
        total = self._config.get_total_credits()
        self._credit_widget.update_credits(total)
    
    def _update_empty_state(self):
        """Update UI based on whether there are lines"""
        has_lines = len(self._project.lines) > 0
        
        # Show/hide empty state vs table
        self._empty_state.setVisible(not has_lines)
        self._table.setVisible(has_lines)
        self._filter_widget.setVisible(has_lines)
        
        # Switch drop zone to compact mode when lines exist
        self._drop_zone.set_compact(has_lines)
    
    # File operations
    def _on_files_dropped(self, files: list):
        """Handle dropped files"""
        all_lines = []
        errors = []
        
        for file_path in files:
            if os.path.isdir(file_path):
                lines, errs = self._importer.import_folder(file_path)
                all_lines.extend(lines)
                errors.extend(errs)
            elif FileImporter.is_supported(file_path):
                try:
                    lines = self._importer.import_file(file_path)
                    all_lines.extend(lines)
                except Exception as e:
                    errors.append(f"{os.path.basename(file_path)}: {e}")
        
        if all_lines:
            # Auto-split if enabled
            if self._project.settings.auto_split_enabled:
                self._splitter.max_chars = self._project.settings.max_chars
                self._splitter.delimiters = self._project.settings.split_delimiter
                all_lines = self._splitter.split_lines(all_lines)
            
            # Detect language if enabled
            if self._project.settings.auto_language_detect:
                all_lines = self._lang_detector.detect_and_annotate(all_lines)
            
            # Apply default voice
            default_voice_id = self._voice_combo.currentData()
            default_voice_name = self._voice_combo.currentText()
            for line in all_lines:
                if not line.voice_id:
                    line.voice_id = default_voice_id
                    line.voice_name = default_voice_name
            
            # Add to project
            start_index = len(self._project.lines)
            for i, line in enumerate(all_lines):
                line.index = start_index + i
            self._project.lines.extend(all_lines)
            
            self._table.load_lines(self._project.lines)
            self._update_empty_state()
            self._log(f"Imported {len(all_lines)} lines")
        
        if errors:
            QMessageBox.warning(self, "Import Errors", "\n".join(errors[:10]))
    
    def _on_import_files(self):
        """Import files via dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Files", "",
            "Supported Files (*.srt *.txt *.docx);;SRT Files (*.srt);;Text Files (*.txt);;Word Documents (*.docx)"
        )
        if files:
            self._on_files_dropped(files)
    
    def _on_import_folder(self):
        """Import folder"""
        folder = QFileDialog.getExistingDirectory(self, "Import Folder")
        if folder:
            self._on_files_dropped([folder])
    
    def _on_new_project(self):
        """Create new project"""
        if self._project.lines and not self._confirm_discard():
            return
        
        self._project = Project()
        self._project.settings.output_folder = self._config.default_output_folder
        self._table.load_lines([])
        self._update_empty_state()
        self._progress.reset()
        self._log("New project created")
    
    def _on_open_project(self):
        """Open project file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "2TTS Project (*.2tts)"
        )
        if file_path:
            try:
                self._project = Project.load(file_path)
                self._table.load_lines(self._project.lines)
                self._update_empty_state()
                self._config.add_recent_project(file_path)
                self._log(f"Opened project: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project: {e}")
    
    def _on_save_project(self):
        """Save project"""
        if self._project.file_path:
            self._project.save(self._project.file_path)
            self._log("Project saved")
        else:
            self._on_save_project_as()
    
    def _on_save_project_as(self):
        """Save project as"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "2TTS Project (*.2tts)"
        )
        if file_path:
            if not file_path.endswith(".2tts"):
                file_path += ".2tts"
            self._project.save(file_path)
            self._config.add_recent_project(file_path)
            self._log(f"Project saved: {file_path}")
    
    def _on_export_text(self):
        """Export text to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Text", "", "Text File (*.txt)"
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                for line in self._project.lines:
                    f.write(f"{line.text}\n")
            self._log(f"Exported to: {file_path}")
    
    def _confirm_discard(self) -> bool:
        """Confirm discarding changes"""
        reply = QMessageBox.question(
            self, "Confirm",
            "Discard unsaved changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    # Edit operations
    def _on_clear_all(self):
        """Clear all lines"""
        if self._project.lines:
            reply = QMessageBox.question(
                self, "Confirm", "Clear all lines?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._project.lines.clear()
                self._table.load_lines([])
                self._update_empty_state()
                self._log("All lines cleared")
    
    def _on_remove_completed(self):
        """Remove completed lines"""
        self._project.lines = [l for l in self._project.lines if l.status != LineStatus.DONE]
        for i, line in enumerate(self._project.lines):
            line.index = i
        self._table.load_lines(self._project.lines)
        self._update_empty_state()
        self._log("Removed completed lines")
    
    def _on_retry_failed(self):
        """Retry failed lines"""
        for line in self._project.lines:
            if line.status == LineStatus.ERROR:
                line.status = LineStatus.PENDING
                line.error_message = None
        self._table.load_lines(self._project.lines)
        self._log("Reset failed lines for retry")
    
    def _on_lines_reordered(self, line_ids: list):
        """Handle lines reordering from table drag - receives list of line IDs in new order"""
        # Reorder _project.lines based on line_ids order
        id_to_line = {line.id: line for line in self._project.lines}
        reordered = []
        for line_id in line_ids:
            if line_id in id_to_line:
                reordered.append(id_to_line[line_id])
        
        # Add any lines not in the reordered list (shouldn't happen but be safe)
        existing_ids = set(line_ids)
        for line in self._project.lines:
            if line.id not in existing_ids:
                reordered.append(line)
        
        # Update indices
        for i, line in enumerate(reordered):
            line.index = i
        
        self._project.lines = reordered
        self._log("Lines reordered")
    
    def _on_text_edited(self, line_id: str, new_text: str):
        """Handle text edit from table - update project and use edited text for TTS"""
        for line in self._project.lines:
            if line.id == line_id:
                line.text = new_text
                self._log(f"Line {line.index + 1} text updated")
                break
    
    def _on_play_audio(self, line_id: str):
        """Play audio for a completed line"""
        for line in self._project.lines:
            if line.id == line_id:
                if line.output_path and os.path.exists(line.output_path):
                    self._audio_player.setSource(QUrl.fromLocalFile(line.output_path))
                    self._audio_player.play()
                    self._log(f"Playing audio for line {line.index + 1}")
                else:
                    QMessageBox.warning(self, "Warning", "Audio file not found")
                break
    
    def _on_retry_lines(self, line_ids: list):
        """Retry failed lines - receives list of line IDs"""
        count = 0
        for line in self._project.lines:
            if line.id in line_ids:
                line.status = LineStatus.PENDING
                line.error_message = None
                count += 1
        self._table.load_lines(self._project.lines)
        self._log(f"Reset {count} lines for retry")
    
    def _on_delete_lines(self, line_ids: list):
        """Delete selected lines - receives list of line IDs"""
        if not line_ids:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(line_ids)} selected lines?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Convert to set for O(1) lookup
            ids_to_delete = set(line_ids)
            
            # Filter out lines to delete
            self._project.lines = [line for line in self._project.lines if line.id not in ids_to_delete]
            
            # Re-index remaining lines
            for i, line in enumerate(self._project.lines):
                line.index = i
            
            self._table.load_lines(self._project.lines)
            self._update_empty_state()
            self._log(f"Deleted {len(line_ids)} lines")
    
    def _on_filter_changed(self, text: str, status: str):
        """Handle filter change"""
        self._table.set_filter(text, status if status else None)
    
    def _on_split_line(self, line_id: str):
        """Split a line at cursor position or by delimiter - receives line ID"""
        # Find line by ID
        line = None
        line_index = -1
        for i, ln in enumerate(self._project.lines):
            if ln.id == line_id:
                line = ln
                line_index = i
                break
        
        if not line:
            return
        
        text = line.text
        
        # Try to split by common delimiters
        delimiters = ['. ', '? ', '! ', ', ']
        split_pos = -1
        for delim in delimiters:
            pos = text.find(delim)
            if pos > 0 and (split_pos < 0 or pos < split_pos):
                split_pos = pos + len(delim) - 1
        
        if split_pos <= 0:
            # Split in the middle if no delimiter found
            split_pos = len(text) // 2
        
        # Create two new lines
        text1 = text[:split_pos + 1].strip()
        text2 = text[split_pos + 1:].strip()
        
        if not text2:
            QMessageBox.warning(self, "Warning", "Cannot split - text too short")
            return
        
        # Update original line
        line.text = text1
        
        # Create new line
        from core.models import TextLine
        new_line = TextLine(
            index=line_index + 1,
            text=text2,
            voice_id=line.voice_id,
            voice_name=line.voice_name,
            detected_language=line.detected_language
        )
        
        # Insert new line after the original
        self._project.lines.insert(line_index + 1, new_line)
        
        # Re-index all lines
        for i, ln in enumerate(self._project.lines):
            ln.index = i
        
        self._table.load_lines(self._project.lines)
        self._log(f"Split line {line_index + 1} into two lines")
    
    def _on_merge_lines(self, line_ids: list):
        """Merge multiple lines into one - receives list of line IDs"""
        if len(line_ids) < 2:
            return
        
        # Get lines by ID, preserving order by their index
        lines_to_merge = []
        for line in self._project.lines:
            if line.id in line_ids:
                lines_to_merge.append(line)
        
        if len(lines_to_merge) < 2:
            return
        
        # Sort by index to maintain order
        lines_to_merge.sort(key=lambda x: x.index)
        
        # Combine text from all selected lines
        merged_text = " ".join(line.text for line in lines_to_merge)
        
        # Keep first line, update with merged text
        first_line = lines_to_merge[0]
        first_line.text = merged_text
        
        # Delete other lines
        ids_to_delete = set(line.id for line in lines_to_merge[1:])
        self._project.lines = [line for line in self._project.lines if line.id not in ids_to_delete]
        
        # Re-index
        for i, line in enumerate(self._project.lines):
            line.index = i
        
        self._table.load_lines(self._project.lines)
        self._log(f"Merged {len(line_ids)} lines into line {first_line.index + 1}")
    
    def _on_export_log(self):
        """Export log to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", f"2tts_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text File (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self._log_text.toPlainText())
                self._log(f"Log exported to: {file_path}")
                QMessageBox.information(self, "Success", f"Log exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export log: {e}")
    
    # Voice operations
    def _on_voice_changed(self, index: int):
        """Handle voice selection change"""
        voice_id = self._voice_combo.currentData()
        voice_name = self._voice_combo.currentText()
        
        self._project.settings.default_voice_id = voice_id
        self._project.settings.default_voice_name = voice_name
        
        # Save last used voice to config for next session
        if voice_id:
            self._config.set_last_voice(voice_id, voice_name)
        
        # Update voice settings display
        if voice_id and voice_id in self._voices:
            voice = self._voices[voice_id]
            self._voice_settings.set_settings(voice.settings)
    
    def _on_voice_settings_changed(self, settings: VoiceSettings):
        """Handle voice settings change"""
        voice_id = self._voice_combo.currentData()
        if voice_id and voice_id in self._voices:
            self._voices[voice_id].settings = settings
    
    def _on_voice_library(self):
        """Open voice library dialog"""
        api_key = self._config.get_available_api_key()
        proxy = self._config.get_proxy_for_key(api_key) if api_key else None
        
        dialog = VoiceLibraryDialog(
            list(self._voices.values()),
            self._config.voice_library,
            api_key=api_key,
            proxy=proxy,
            parent=self
        )
        dialog.voice_selected.connect(self._on_library_voice_selected)
        dialog.voice_added_by_id.connect(self._on_voice_added_by_id)
        dialog.exec()
        
        # Save updated library
        self._config._save_voice_library()
    
    def _on_library_voice_selected(self, voice: Voice):
        """Handle voice selection from library"""
        index = self._voice_combo.findData(voice.voice_id)
        if index >= 0:
            self._voice_combo.setCurrentIndex(index)
    
    def _on_voice_preview(self):
        """Preview current voice with sample text"""
        voice_id = self._voice_combo.currentData()
        if not voice_id:
            QMessageBox.warning(self, "Warning", "No voice selected")
            return
        
        api_key = self._config.get_available_api_key()
        if not api_key:
            QMessageBox.warning(self, "Warning", "No API key available")
            return
        
        # Get voice settings
        voice = self._voices.get(voice_id)
        settings = voice.settings if voice else VoiceSettings()
        
        # Preview text
        preview_text = "Hello! This is a voice preview sample."
        
        # Generate preview to temp file
        import tempfile
        preview_path = os.path.join(tempfile.gettempdir(), "2tts_preview.mp3")
        
        proxy = self._config.get_proxy_for_key(api_key)
        
        self._log(f"Generating voice preview...")
        success, message, duration = self._api.text_to_speech(
            text=preview_text,
            voice_id=voice_id,
            api_key=api_key,
            output_path=preview_path,
            settings=settings,
            proxy=proxy
        )
        
        if success:
            self._audio_player.setSource(QUrl.fromLocalFile(preview_path))
            self._audio_player.play()
            self._log("Playing voice preview")
        else:
            QMessageBox.warning(self, "Preview Failed", f"Failed to generate preview: {message}")
    
    def _on_apply_voice_to_selected(self):
        """Apply current voice to selected lines"""
        voice_id = self._voice_combo.currentData()
        voice_name = self._voice_combo.currentText()
        
        if not voice_id:
            QMessageBox.warning(self, "Warning", "No voice selected")
            return
        
        selected_line_ids = self._table.get_selected_line_ids()
        if not selected_line_ids:
            QMessageBox.warning(self, "Warning", "No lines selected")
            return
        
        # Convert to set for O(1) lookup
        ids_set = set(selected_line_ids)
        count = 0
        for line in self._project.lines:
            if line.id in ids_set:
                line.voice_id = voice_id
                line.voice_name = voice_name
                count += 1
        
        self._table.load_lines(self._project.lines)
        self._log(f"Applied voice '{voice_name}' to {count} lines")
    
    def _on_apply_voice_to_all(self):
        """Apply current voice to all lines"""
        voice_id = self._voice_combo.currentData()
        voice_name = self._voice_combo.currentText()
        
        if not voice_id:
            QMessageBox.warning(self, "Warning", "No voice selected")
            return
        
        if not self._project.lines:
            QMessageBox.warning(self, "Warning", "No lines to update")
            return
        
        for line in self._project.lines:
            line.voice_id = voice_id
            line.voice_name = voice_name
        
        self._table.load_lines(self._project.lines)
        self._log(f"Applied voice '{voice_name}' to all {len(self._project.lines)} lines")
    
    def _on_voice_added_by_id(self, voice: Voice):
        """Handle voice added by ID from library dialog"""
        # Check if already in combo box
        existing_index = self._voice_combo.findData(voice.voice_id)
        if existing_index >= 0:
            # Voice already exists, just select it
            self._voice_combo.setCurrentIndex(existing_index)
            return
        
        # Add to voices dict
        self._voices[voice.voice_id] = voice
        
        # Add to combo box
        prefix = "🎤 " if voice.is_cloned else "🌐 "
        self._voice_combo.addItem(f"{prefix}{voice.name}", voice.voice_id)
        
        # Select the newly added voice
        new_index = self._voice_combo.findData(voice.voice_id)
        if new_index >= 0:
            self._voice_combo.setCurrentIndex(new_index)
        
        # Add to config library
        self._config.add_voice_to_library(voice)
        
        self._log(f"Added voice: {voice.name} ({voice.voice_id})")
    
    # Processing
    def _on_start(self):
        """Start processing"""
        if not self._project.lines:
            QMessageBox.warning(self, "Warning", "No lines to process")
            return
        
        if not self._config.api_keys:
            QMessageBox.warning(self, "Warning", "No API keys configured")
            return
        
        # Update project settings
        self._project.settings.thread_count = self._threads_spin.value()
        self._project.settings.loop_enabled = self._loop_check.isChecked()
        self._project.settings.loop_count = self._loop_count_spin.value()
        
        # Ensure output folder exists
        os.makedirs(self._project.settings.output_folder, exist_ok=True)
        
        # Create engine
        self._engine = ProcessingEngine(
            api_keys=self._config.api_keys,
            proxies=self._config.proxies,
            voices=self._voices,
            output_folder=self._project.settings.output_folder,
            thread_count=self._project.settings.thread_count,
            max_retries=self._project.settings.max_retries,
            default_voice_id=self._voice_combo.currentData(),
            request_delay=self._project.settings.request_delay,
            on_progress=self._on_processing_progress,
            on_line_update=self._on_line_updated,
            on_log=self._log,
            on_credit_used=self._on_credit_used,
            on_key_removed=self._on_key_removed
        )
        
        # Configure loop mode
        self._engine.set_loop_mode(
            self._project.settings.loop_enabled,
            self._project.settings.loop_count,
            self._project.settings.loop_delay
        )
        
        # Start
        self._engine.start(self._project.lines)
        
        # Update UI
        self._start_btn.setEnabled(False)
        self._pause_btn.setEnabled(True)
        self._stop_btn.setEnabled(True)
        self._progress_timer.start(1000)
        
        # Show current model in status bar
        current_model = self._voice_settings.get_settings().model.value
        model_display = self._get_model_display_name(current_model)
        self._model_status_label.setText(f"Model: {model_display}")
        
        self._log(f"Processing started with model: {current_model}")
    
    def _on_pause(self):
        """Pause/resume processing"""
        if not self._engine:
            return
        
        if self._engine.is_paused:
            self._engine.resume()
            self._pause_btn.setText("⏸ " + tr("pause"))
        else:
            self._engine.pause()
            self._pause_btn.setText("▶ " + tr("resume"))
    
    def _on_stop(self):
        """Stop processing"""
        if self._engine:
            self._engine.stop()
            self._progress_timer.stop()
            
            self._start_btn.setEnabled(True)
            self._pause_btn.setEnabled(False)
            self._pause_btn.setText("⏸ " + tr("pause"))
            self._stop_btn.setEnabled(False)
            self._model_status_label.setText("")  # Clear model indicator
            
            self._log("Processing stopped")
    
    def _on_processing_progress(self, stats: ProcessingStats):
        """Handle progress update from engine"""
        # This is called from worker thread, schedule UI update
        pass
    
    def _on_line_updated(self, line: TextLine):
        """Handle line update from engine"""
        # Update table - called from worker thread
        QApplication.instance().postEvent(self, LineUpdateEvent(line))
    
    def _on_credit_used(self, api_key: APIKey, chars_used: int):
        """Handle credit used"""
        # Update local config
        self._config.update_api_key(api_key)
    
    def _on_key_removed(self, api_key: APIKey, reason: str):
        """Handle API key removal due to low credits (< 500)"""
        # Remove from config
        self._config.remove_api_key(api_key.id)
        self._log(f"API key '{api_key.name or api_key.key[:8]}...' removed from config: {reason}")
    
    def _update_progress_display(self):
        """Update progress display (called by timer)"""
        if self._engine:
            stats = self._engine.stats
            status = "Processing"
            if self._engine.is_paused:
                status = "Paused"
            elif not self._engine.is_running:
                status = "Complete"
                self._progress_timer.stop()
                self._start_btn.setEnabled(True)
                self._pause_btn.setEnabled(False)
                self._stop_btn.setEnabled(False)
                self._thread_status.reset()
                self._model_status_label.setText("")  # Clear model indicator
            
            if stats.current_loop > 1:
                status = f"{status} (Loop {stats.current_loop})"
            
            self._progress.update_progress(
                stats.completed, stats.total,
                stats.elapsed_time, status
            )
            
            # Update thread status display
            self._thread_status.update_status(
                stats.active_threads,
                self._project.settings.thread_count,
                stats.get_thread_display()
            )
            
            self._refresh_credits()
    
    def event(self, event):
        """Handle custom events"""
        if event.type() == LineUpdateEvent.EVENT_TYPE:
            self._table.update_line(event.line)
            return True
        return super().event(event)
    
    # Output operations
    def _on_join_mp3(self):
        """Join all MP3 files"""
        completed_lines = [l for l in self._project.lines if l.status == LineStatus.DONE and l.output_path]
        if not completed_lines:
            QMessageBox.warning(self, "Warning", "No completed audio files to join")
            return
        
        output_path = os.path.join(
            self._project.settings.output_folder,
            f"joined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        )
        
        success, message = self._mp3_concat.concatenate_streaming(
            completed_lines, output_path,
            self._project.settings.silence_gap
        )
        
        if success:
            self._log(f"MP3 joined: {output_path}")
            QMessageBox.information(self, "Success", f"MP3 created: {output_path}")
        else:
            QMessageBox.critical(self, "Error", f"Failed to join MP3: {message}")
    
    def _on_generate_srt(self):
        """Generate SRT file"""
        completed_lines = [l for l in self._project.lines if l.status == LineStatus.DONE]
        if not completed_lines:
            QMessageBox.warning(self, "Warning", "No completed lines for SRT")
            return
        
        output_path = os.path.join(
            self._project.settings.output_folder,
            f"subtitles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.srt"
        )
        
        success = self._srt_generator.generate(
            completed_lines, output_path,
            self._project.settings.silence_gap,
            self._project.settings.timing_offset
        )
        
        if success:
            self._log(f"SRT generated: {output_path}")
            QMessageBox.information(self, "Success", f"SRT created: {output_path}")
        else:
            QMessageBox.critical(self, "Error", "Failed to generate SRT")
    
    def _on_open_folder(self):
        """Open output folder"""
        folder = self._project.settings.output_folder
        if folder and os.path.exists(folder):
            os.startfile(folder)
        else:
            QMessageBox.warning(self, "Warning", "Output folder does not exist")
    
    # Tools dialogs
    def _on_manage_api_keys(self):
        """Open API key manager"""
        dialog = APIKeyDialog(self._config.api_keys, self)
        dialog.keys_updated.connect(self._on_api_keys_updated)
        dialog.exec()
    
    def _on_api_keys_updated(self, keys: list):
        """Handle API keys update"""
        self._config._api_keys = keys
        self._config._save_api_keys()
        self._refresh_voices()
        self._refresh_credits(fetch_from_api=True)
        self._transcribe_tab.refresh_config()
    
    def _on_manage_proxies(self):
        """Open proxy manager"""
        dialog = ProxyDialog(self._config.proxies, self)
        dialog.proxies_updated.connect(self._on_proxies_updated)
        dialog.exec()
    
    def _on_proxies_updated(self, proxies: list):
        """Handle proxies update"""
        self._config._proxies = proxies
        self._config._save_proxies()
        self._transcribe_tab.refresh_config()
    
    def _on_settings(self):
        """Open settings dialog"""
        settings = {
            "thread_count": self._project.settings.thread_count,
            "max_retries": self._project.settings.max_retries,
            "request_delay": self._project.settings.request_delay,
            "auto_split_enabled": self._project.settings.auto_split_enabled,
            "max_chars": self._project.settings.max_chars,
            "split_delimiter": self._project.settings.split_delimiter,
            "silence_gap": self._project.settings.silence_gap,
            "theme": self._config.theme,
            "app_language": self._config.app_language,
            "vn_preprocessing_enabled": self._project.settings.vn_preprocessing_enabled,
            "vn_max_phrase_words": self._project.settings.vn_max_phrase_words,
            "vn_add_micro_pauses": self._project.settings.vn_add_micro_pauses,
            "vn_micro_pause_interval": self._project.settings.vn_micro_pause_interval
        }
        
        dialog = SettingsDialog(settings, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            
            self._project.settings.thread_count = new_settings["thread_count"]
            self._project.settings.max_retries = new_settings["max_retries"]
            self._project.settings.request_delay = new_settings["request_delay"]
            self._project.settings.auto_split_enabled = new_settings["auto_split_enabled"]
            self._project.settings.max_chars = new_settings["max_chars"]
            self._project.settings.split_delimiter = new_settings["split_delimiter"]
            self._project.settings.silence_gap = new_settings["silence_gap"]
            # Vietnamese TTS settings
            self._project.settings.vn_preprocessing_enabled = new_settings["vn_preprocessing_enabled"]
            self._project.settings.vn_max_phrase_words = new_settings["vn_max_phrase_words"]
            self._project.settings.vn_add_micro_pauses = new_settings["vn_add_micro_pauses"]
            self._project.settings.vn_micro_pause_interval = new_settings["vn_micro_pause_interval"]
            
            self._threads_spin.setValue(new_settings["thread_count"])
            
            if new_settings["theme"] != self._config.theme:
                self._config.theme = new_settings["theme"]
                self._apply_theme()
            
            # Check if language changed
            if new_settings.get("app_language") != self._config.app_language:
                self._config.app_language = new_settings["app_language"]
                set_language(new_settings["app_language"])
                QMessageBox.information(
                    self, 
                    tr("info"),
                    "Ngôn ngữ đã được thay đổi. Vui lòng khởi động lại ứng dụng để áp dụng.\n"
                    "Language changed. Please restart the application to apply."
                )
    
    def _on_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About 2TTS",
            "2TTS - ElevenLabs Text-To-Speech Tool\n\n"
            "A powerful tool for batch text-to-speech conversion "
            "using the ElevenLabs API.\n\n"
            "Features:\n"
            "- Multi-file import (SRT, TXT, DOCX)\n"
            "- Multi-voice per project\n"
            "- Multi-account API key rotation\n"
            "- Proxy support\n"
            "- Multi-threaded processing\n"
            "- SRT generation\n"
            "- MP3 concatenation\n"
            "- Voice presets and templates\n"
            "- Undo/Redo support\n"
            "- Audio post-processing"
        )

    def _check_for_updates(self, force: bool = False, show_result: bool = False):
        if self._update_check_in_progress:
            if show_result:
                QMessageBox.information(self, tr("check_updates"), "Update check already in progress")
            return

        self._update_check_in_progress = True
        self._update_user_initiated = show_result

        def _worker():
            available, info, msg = self._update_checker.check_for_updates(force=force)
            self.update_check_result.emit(available, info, msg, show_result)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_update_check_result(self, available: bool, info_obj: object, message: str, show_result: bool):
        self._update_check_in_progress = False

        if not available or not isinstance(info_obj, UpdateInfo):
            if show_result:
                QMessageBox.information(self, tr("check_updates"), message)
            return

        update = info_obj
        self._pending_update_info = update

        ready = self._update_checker.get_ready_update()
        if ready and ready[0].version == update.version:
            self.update_download_result.emit(True, update, ready[1], "Update already downloaded")
            return

        if self._update_download_in_progress:
            if show_result:
                QMessageBox.information(
                    self,
                    tr("check_updates"),
                    f"Update v{update.version} is downloading...",
                )
            return

        self._update_download_in_progress = True

        def _progress_callback(downloaded, total, percent):
            self.update_download_progress.emit(downloaded, total, percent)

        def _dl_worker():
            ok, path, msg = self._update_checker.download_update(update, progress_callback=_progress_callback)
            self.update_download_result.emit(ok, update, path, msg)

        if show_result:
            self._update_progress_dialog = QProgressDialog(
                f"Downloading update v{update.version}...",
                None,
                0,
                100,
                self
            )
            self._update_progress_dialog.setWindowTitle(tr("check_updates"))
            self._update_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self._update_progress_dialog.setMinimumDuration(0)
            self._update_progress_dialog.setValue(0)
            self._update_progress_dialog.show()

        threading.Thread(target=_dl_worker, daemon=True).start()

    def _on_update_download_progress(self, downloaded: int, total: int, percent: int):
        """Handle download progress update"""
        if self._update_progress_dialog:
            self._update_progress_dialog.setValue(percent)
            size_mb = total / (1024 * 1024)
            downloaded_mb = downloaded / (1024 * 1024)
            self._update_progress_dialog.setLabelText(
                f"Downloading update... {downloaded_mb:.1f} / {size_mb:.1f} MB ({percent}%)"
            )

    def _on_update_download_result(self, success: bool, info_obj: object, installer_obj: object, message: str):
        self._update_download_in_progress = False

        if self._update_progress_dialog:
            self._update_progress_dialog.close()
            self._update_progress_dialog = None

        if not success or not isinstance(info_obj, UpdateInfo) or not isinstance(installer_obj, Path):
            if self._update_user_initiated:
                QMessageBox.warning(self, tr("check_updates"), f"Download failed: {message}")
            return
        
        # Download successful
        self._pending_update_info = info_obj
        self._pending_update_installer = installer_obj
        
        reply = QMessageBox.question(
            self,
            tr("check_updates"),
            f"Update v{info_obj.version} is ready to install.\n\nInstall now? (App will close)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._run_installer(installer_obj)
    
    def _run_installer(self, installer_path: Path):
        """Run the installer and exit"""
        import subprocess
        try:
            # Run installer detached
            subprocess.Popen([str(installer_path), "/SILENT"])
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Failed to run installer: {e}")
