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
    QDialog, QTabWidget
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
    ProgressWidget, CreditWidget, FilterWidget, ThreadStatusWidget
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


class MainWindow(QMainWindow):
    """Main application window"""

    update_check_result = pyqtSignal(bool, object, str, bool)  # available, UpdateInfo|None, message, show_result
    update_download_result = pyqtSignal(bool, object, object, str)  # success, UpdateInfo, Path|None, message
    
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

        self.update_check_result.connect(self._on_update_check_result)
        self.update_download_result.connect(self._on_update_download_result)

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
        tts_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - main content
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)
        
        # Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        left_layout.addWidget(self._drop_zone)
        
        # Filter widget
        self._filter_widget = FilterWidget()
        self._filter_widget.filter_changed.connect(self._on_filter_changed)
        left_layout.addWidget(self._filter_widget)
        
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
        
        # Progress
        self._progress = ProgressWidget()
        left_layout.addWidget(self._progress)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("▶ " + tr("start"))
        self._start_btn.setObjectName("primaryButton")
        self._start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self._start_btn)
        
        self._pause_btn = QPushButton("⏸ " + tr("pause"))
        self._pause_btn.clicked.connect(self._on_pause)
        self._pause_btn.setEnabled(False)
        btn_layout.addWidget(self._pause_btn)
        
        self._stop_btn = QPushButton("⏹ " + tr("stop"))
        self._stop_btn.setObjectName("dangerButton")
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)
        btn_layout.addWidget(self._stop_btn)
        
        btn_layout.addStretch()
        
        self._join_btn = QPushButton(tr("join_mp3"))
        self._join_btn.clicked.connect(self._on_join_mp3)
        btn_layout.addWidget(self._join_btn)
        
        self._srt_btn = QPushButton(tr("generate_srt"))
        self._srt_btn.clicked.connect(self._on_generate_srt)
        btn_layout.addWidget(self._srt_btn)
        
        self._folder_btn = QPushButton("📂 " + tr("open_folder"))
        self._folder_btn.clicked.connect(self._on_open_folder)
        btn_layout.addWidget(self._folder_btn)
        
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_panel)
        
        # Right panel - settings (scrollable)
        from PyQt6.QtWidgets import QScrollArea
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setMaximumWidth(370)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)
        
        # Voice selection
        voice_group = QGroupBox("Voice")
        voice_layout = QVBoxLayout(voice_group)
        
        voice_select_layout = QHBoxLayout()
        voice_select_layout.addWidget(QLabel(tr("default_voice") + ":"))
        self._voice_combo = QComboBox()
        self._voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        voice_select_layout.addWidget(self._voice_combo)
        
        self._voice_lib_btn = QPushButton("📚")
        self._voice_lib_btn.setFixedWidth(40)
        self._voice_lib_btn.setToolTip("Voice Library")
        self._voice_lib_btn.clicked.connect(self._on_voice_library)
        voice_select_layout.addWidget(self._voice_lib_btn)
        
        self._voice_preview_btn = QPushButton("🔊")
        self._voice_preview_btn.setFixedWidth(40)
        self._voice_preview_btn.setToolTip("Preview Voice")
        self._voice_preview_btn.clicked.connect(self._on_voice_preview)
        voice_select_layout.addWidget(self._voice_preview_btn)
        voice_layout.addLayout(voice_select_layout)
        
        # Apply voice to selected lines button
        apply_voice_layout = QHBoxLayout()
        self._apply_voice_btn = QPushButton(tr("apply_to_selected"))
        self._apply_voice_btn.setToolTip("Apply selected voice to selected lines")
        self._apply_voice_btn.clicked.connect(self._on_apply_voice_to_selected)
        apply_voice_layout.addWidget(self._apply_voice_btn)
        
        self._apply_voice_all_btn = QPushButton(tr("apply_to_all"))
        self._apply_voice_all_btn.setToolTip("Apply selected voice to all lines")
        self._apply_voice_all_btn.clicked.connect(self._on_apply_voice_to_all)
        apply_voice_layout.addWidget(self._apply_voice_all_btn)
        voice_layout.addLayout(apply_voice_layout)
        
        right_layout.addWidget(voice_group)
        
        # Voice settings (separate group to avoid nesting)
        self._voice_settings = VoiceSettingsWidget()
        self._voice_settings.settings_changed.connect(self._on_voice_settings_changed)
        right_layout.addWidget(self._voice_settings)
        
        # Processing options
        proc_group = QGroupBox(tr("processing"))
        proc_layout = QVBoxLayout(proc_group)
        
        threads_layout = QHBoxLayout()
        threads_layout.addWidget(QLabel(tr("threads") + ":"))
        self._threads_spin = QSpinBox()
        self._threads_spin.setRange(1, 50)
        self._threads_spin.setValue(self._project.settings.thread_count)
        threads_layout.addWidget(self._threads_spin)
        proc_layout.addLayout(threads_layout)
        
        self._loop_check = QCheckBox(tr("loop_mode"))
        self._loop_check.setChecked(self._project.settings.loop_enabled)
        proc_layout.addWidget(self._loop_check)
        
        loop_layout = QHBoxLayout()
        loop_layout.addWidget(QLabel(tr("loop_count_label") + ":"))
        self._loop_count_spin = QSpinBox()
        self._loop_count_spin.setRange(0, 1000)
        self._loop_count_spin.setValue(self._project.settings.loop_count)
        loop_layout.addWidget(self._loop_count_spin)
        proc_layout.addLayout(loop_layout)
        
        right_layout.addWidget(proc_group)
        
        # Thread status
        self._thread_status = ThreadStatusWidget(max_threads=10)
        right_layout.addWidget(self._thread_status)
        
        # Log
        log_group = QGroupBox(tr("log"))
        log_layout = QVBoxLayout(log_group)
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(200)
        log_layout.addWidget(self._log_text)
        
        # Log export button
        export_log_btn = QPushButton(tr("export_log"))
        export_log_btn.clicked.connect(self._on_export_log)
        log_layout.addWidget(export_log_btn)
        
        right_layout.addWidget(log_group)
        
        right_layout.addStretch()
        
        right_scroll.setWidget(right_panel)
        splitter.addWidget(right_scroll)
        splitter.setSizes([800, 370])
        
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
                self._log("All lines cleared")
    
    def _on_remove_completed(self):
        """Remove completed lines"""
        self._project.lines = [l for l in self._project.lines if l.status != LineStatus.DONE]
        for i, line in enumerate(self._project.lines):
            line.index = i
        self._table.load_lines(self._project.lines)
        self._log("Removed completed lines")
    
    def _on_retry_failed(self):
        """Retry failed lines"""
        for line in self._project.lines:
            if line.status == LineStatus.ERROR:
                line.status = LineStatus.PENDING
                line.error_message = None
        self._table.load_lines(self._project.lines)
        self._log("Reset failed lines for retry")
    
    def _on_lines_reordered(self):
        """Handle lines reordering from table drag"""
        self._project.lines = self._table.get_lines()
        self._log("Lines reordered")
    
    def _on_text_edited(self, row: int, new_text: str):
        """Handle text edit from table - update project and use edited text for TTS"""
        if row < len(self._project.lines):
            self._project.lines[row].text = new_text
            self._log(f"Line {row + 1} text updated")
    
    def _on_play_audio(self, row: int):
        """Play audio for a completed line"""
        if row < len(self._project.lines):
            line = self._project.lines[row]
            if line.output_path and os.path.exists(line.output_path):
                self._audio_player.setSource(QUrl.fromLocalFile(line.output_path))
                self._audio_player.play()
                self._log(f"Playing audio for line {row + 1}")
            else:
                QMessageBox.warning(self, "Warning", "Audio file not found")
    
    def _on_retry_lines(self, rows: list):
        """Retry failed lines"""
        for row in rows:
            if row < len(self._project.lines):
                self._project.lines[row].status = LineStatus.PENDING
                self._project.lines[row].error_message = None
        self._table.load_lines(self._project.lines)
        self._log(f"Reset {len(rows)} lines for retry")
    
    def _on_delete_lines(self, rows: list):
        """Delete selected lines"""
        if not rows:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(rows)} selected lines?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Delete in reverse order to maintain indices
            for row in sorted(rows, reverse=True):
                if row < len(self._project.lines):
                    del self._project.lines[row]
            
            # Re-index remaining lines
            for i, line in enumerate(self._project.lines):
                line.index = i
            
            self._table.load_lines(self._project.lines)
            self._log(f"Deleted {len(rows)} lines")
    
    def _on_filter_changed(self, text: str, status: str):
        """Handle filter change"""
        self._table.set_filter(text, status if status else None)
    
    def _on_split_line(self, row: int):
        """Split a line at cursor position or by delimiter"""
        if row >= len(self._project.lines):
            return
        
        line = self._project.lines[row]
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
            index=row + 1,
            text=text2,
            voice_id=line.voice_id,
            voice_name=line.voice_name,
            detected_language=line.detected_language
        )
        
        # Insert new line
        self._project.lines.insert(row + 1, new_line)
        
        # Re-index all lines
        for i, ln in enumerate(self._project.lines):
            ln.index = i
        
        self._table.load_lines(self._project.lines)
        self._log(f"Split line {row + 1} into two lines")
    
    def _on_merge_lines(self, rows: list):
        """Merge multiple lines into one"""
        if len(rows) < 2:
            return
        
        rows = sorted(rows)
        
        # Combine text from all selected lines
        texts = []
        for row in rows:
            if row < len(self._project.lines):
                texts.append(self._project.lines[row].text)
        
        merged_text = " ".join(texts)
        
        # Keep first line, update with merged text
        first_row = rows[0]
        self._project.lines[first_row].text = merged_text
        
        # Delete other lines (in reverse order)
        for row in sorted(rows[1:], reverse=True):
            if row < len(self._project.lines):
                del self._project.lines[row]
        
        # Re-index
        for i, line in enumerate(self._project.lines):
            line.index = i
        
        self._table.load_lines(self._project.lines)
        self._log(f"Merged {len(rows)} lines into line {first_row + 1}")
    
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
        
        selected_rows = self._table.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "No lines selected")
            return
        
        for row in selected_rows:
            if row < len(self._project.lines):
                self._project.lines[row].voice_id = voice_id
                self._project.lines[row].voice_name = voice_name
        
        self._table.load_lines(self._project.lines)
        self._log(f"Applied voice '{voice_name}' to {len(selected_rows)} lines")
    
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

        def _dl_worker():
            ok, path, msg = self._update_checker.download_update(update)
            self.update_download_result.emit(ok, update, path, msg)

        threading.Thread(target=_dl_worker, daemon=True).start()

        if show_result:
            QMessageBox.information(
                self,
                tr("check_updates"),
                f"Found update v{update.version}. Downloading in background...",
            )

    def _on_update_download_result(self, success: bool, info_obj: object, installer_obj: object, message: str):
        self._update_download_in_progress = False

        if not success or not isinstance(info_obj, UpdateInfo) or not isinstance(installer_obj, Path):
            if self._update_user_initiated:
                QMessageBox.warning(self, tr("check_updates"), message)
            return

        update = info_obj
        installer_path = installer_obj

        self._pending_update_info = update
        self._pending_update_installer = installer_path

        if self._tray_icon:
            try:
                self._tray_icon.showMessage(
                    "2TTS",
                    f"Update v{update.version} downloaded. It will install when you exit.",
                )
            except Exception:
                pass

        if self._update_user_initiated:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(tr("check_updates"))
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(
                f"Đã tải xong bản cập nhật v{update.version}.\n\n"
                "Cài đặt ngay (silent) hay để tự cài khi thoát ứng dụng?"
            )
            btn_now = msg_box.addButton("Update", QMessageBox.ButtonRole.AcceptRole)
            msg_box.addButton("Later", QMessageBox.ButtonRole.RejectRole)
            msg_box.exec()
            if msg_box.clickedButton() == btn_now:
                self._install_update_now()

    def _install_update_now(self):
        if self._update_install_scheduled:
            return
        if not self._pending_update_installer or not self._pending_update_installer.exists():
            QMessageBox.warning(self, tr("check_updates"), "No downloaded update found")
            return

        ok, msg = self._update_checker.schedule_install(
            self._pending_update_installer,
            relaunch_path=sys.executable,
            wait_pid=os.getpid(),
        )
        if not ok:
            QMessageBox.critical(self, tr("check_updates"), msg)
            return

        self._update_install_scheduled = True
        self._update_checker.clear_ready_update(delete_file=False)
        self.close()
    
    # New feature handlers
    def _on_undo(self):
        """Undo last action"""
        desc = self._command_manager.undo()
        if desc:
            self._table.load_lines(self._project.lines)
            self._log(f"Undone: {desc}")
    
    def _on_redo(self):
        """Redo last undone action"""
        desc = self._command_manager.redo()
        if desc:
            self._table.load_lines(self._project.lines)
            self._log(f"Redone: {desc}")
    
    def _on_command_change(self):
        """Update undo/redo menu items"""
        self._undo_action.setEnabled(self._command_manager.can_undo())
        self._redo_action.setEnabled(self._command_manager.can_redo())
        
        undo_desc = self._command_manager.get_undo_description()
        redo_desc = self._command_manager.get_redo_description()
        
        self._undo_action.setText(f"Undo {undo_desc}" if undo_desc else "Undo")
        self._redo_action.setText(f"Redo {redo_desc}" if redo_desc else "Redo")
    
    def _on_bulk_voice_assignment(self):
        """Open bulk voice assignment dialog"""
        if not self._project.lines:
            QMessageBox.warning(self, "Warning", "No lines to assign")
            return
        
        dialog = VoiceAssignmentDialog(
            self._project.lines,
            list(self._voices.values()),
            self
        )
        dialog.assignments_changed.connect(self._apply_voice_assignments)
        dialog.exec()
    
    def _apply_voice_assignments(self, assignments: dict):
        """Apply voice assignments from dialog"""
        self._voice_matcher.assign_voices(
            self._project.lines,
            self._voice_combo.currentData(),
            self._voice_combo.currentText()
        )
        self._table.load_lines(self._project.lines)
        self._log(f"Applied voice assignments to {len(self._project.lines)} lines")
    
    def _on_presets(self):
        """Open preset manager dialog"""
        dialog = PresetManagerDialog(list(self._voices.values()), self)
        dialog.preset_selected.connect(self._apply_preset)
        dialog.exec()
    
    def _apply_preset(self, preset):
        """Apply a voice preset"""
        index = self._voice_combo.findData(preset.voice_id)
        if index >= 0:
            self._voice_combo.setCurrentIndex(index)
        self._voice_settings.set_settings(preset.settings)
        self._log(f"Applied preset: {preset.name}")
    
    def _on_audio_processing(self):
        """Open audio processing settings dialog"""
        dialog = AudioProcessingDialog(self._audio_settings, self)
        dialog.settings_changed.connect(self._on_audio_settings_changed)
        dialog.exec()
    
    def _on_audio_settings_changed(self, settings):
        """Handle audio processing settings change"""
        self._audio_settings = settings
        self._log("Audio processing settings updated")
    

    
    def _on_analytics(self):
        """Open analytics dialog"""
        dialog = AnalyticsDialog(self)
        dialog.exec()
    
    def _on_transcribe_files(self):
        """Switch to transcribe tab and optionally import files"""
        # Switch to transcribe tab
        self._tab_widget.setCurrentWidget(self._transcribe_tab)
        
        # Open file dialog
        from services.transcription import SUPPORTED_FORMATS
        formats = " ".join(f"*{ext}" for ext in SUPPORTED_FORMATS)
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio/Video Files", "",
            f"Media Files ({formats});;All Files (*.*)"
        )
        if files:
            self._transcribe_tab._on_files_dropped(files)
    
    def _on_view_logs(self):
        """View application logs"""
        log_content = self._logger.get_recent_logs(500)
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Application Logs")
        dialog.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(dialog)
        
        text = QTextEdit()
        text.setPlainText(log_content)
        text.setReadOnly(True)
        layout.addWidget(text)
        
        btn_layout = QHBoxLayout()
        
        open_folder_btn = QPushButton("Open Log Folder")
        open_folder_btn.clicked.connect(lambda: os.startfile(str(self._logger.log_dir)))
        btn_layout.addWidget(open_folder_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        dialog.exec()
    
    def closeEvent(self, event):
        """Handle window close"""
        if self._engine and self._engine.is_running:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Processing is in progress. Stop and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            self._engine.stop()
        
        # Auto-save if there are unsaved changes
        if self._project.lines and not self._project.file_path:
            reply = QMessageBox.question(
                self, "Save Project",
                "Save project before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_save_project_as()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        # End analytics session
        if (
            self._pending_update_installer
            and not self._update_install_scheduled
            and self._pending_update_installer.exists()
        ):
            ok, msg = self._update_checker.schedule_install(
                self._pending_update_installer,
                relaunch_path=sys.executable,
                wait_pid=os.getpid(),
            )
            if ok:
                self._update_install_scheduled = True
                self._update_checker.clear_ready_update(delete_file=False)
            else:
                self._logger.warning(f"Update install not scheduled: {msg}")

        self._analytics.end_session()
        self._logger.info("Application closed")
        
        event.accept()


class LineUpdateEvent(QEvent):
    """Custom event for line updates from worker thread"""
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, line: TextLine):
        super().__init__(self.EVENT_TYPE)
        self.line = line
