"""Transcribe Tab UI for Speech-to-Text functionality"""
import os
from typing import Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QLabel, QPushButton, QComboBox, QCheckBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QTextEdit, QFileDialog,
    QMessageBox, QHeaderView, QAbstractItemView, QMenu,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QTimer, QMetaObject, Q_ARG, Qt as QtCore
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from core.models import TranscriptionJob, JobStatus, TranscriptionResult
from core.config import get_config
from services.transcription import (
    TranscriptionEngine, TranscriptionExporter,
    is_supported_format, SUPPORTED_FORMATS
)
from services.elevenlabs import ElevenLabsAPI
from services.localization import tr


class MediaDropZone(QFrame):
    """Drop zone for media files"""
    files_dropped = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)
        
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 24px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        text_label = QLabel(tr("drop_media_here"))
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setStyleSheet("font-size: 13px; font-weight: 500;")
        layout.addWidget(text_label)
        
        formats_label = QLabel(tr("drop_media_or_browse"))
        formats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formats_label.setStyleSheet("font-size: 11px; color: #6b7280;")
        layout.addWidget(formats_label)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._browse_files()
    
    def _browse_files(self):
        formats = " ".join(f"*{ext}" for ext in SUPPORTED_FORMATS)
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Media Files", "",
            f"Media Files ({formats});;All Files (*.*)"
        )
        if files:
            self.files_dropped.emit(files)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and is_supported_format(path):
                files.append(path)
        if files:
            self.files_dropped.emit(files)


class SpeakerEditorDialog(QWidget):
    """Dialog for editing speaker names"""
    
    def __init__(self, speakers: List, parent=None):
        super().__init__(parent)
        self._speakers = speakers
        self._edits = {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Edit speaker names:"))
        
        for speaker in self._speakers:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"Speaker {speaker.id}:"))
            
            edit = QWidget()
            from PyQt6.QtWidgets import QLineEdit
            line_edit = QLineEdit()
            line_edit.setText(speaker.name if speaker.name else f"Speaker {speaker.id}")
            line_edit.setPlaceholderText(f"Speaker {speaker.id}")
            self._edits[speaker.id] = line_edit
            row.addWidget(line_edit)
            
            layout.addLayout(row)
        
        layout.addStretch()
    
    def get_speaker_names(self) -> dict:
        """Get the edited speaker names"""
        return {sid: edit.text() for sid, edit in self._edits.items()}


class TranscriptEditorWidget(QWidget):
    """Widget for viewing and editing transcription results"""
    segment_clicked = pyqtSignal(float)  # Emit start time when segment clicked
    speaker_renamed = pyqtSignal(str, str)  # speaker_id, new_name
    speakers_updated = pyqtSignal()  # Emitted when speakers are renamed
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._result: Optional[TranscriptionResult] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self._lang_label = QLabel(tr("language") + ": -")
        toolbar.addWidget(self._lang_label)
        
        toolbar.addStretch()
        
        self._speakers_label = QLabel(tr("speakers") + ": -")
        toolbar.addWidget(self._speakers_label)
        
        self._edit_speakers_btn = QPushButton(tr("edit_speakers"))
        self._edit_speakers_btn.setFixedWidth(100)
        self._edit_speakers_btn.clicked.connect(self._on_edit_speakers)
        self._edit_speakers_btn.setEnabled(False)
        toolbar.addWidget(self._edit_speakers_btn)
        
        layout.addLayout(toolbar)
        
        # Transcript text (using QTextBrowser for clickable links)
        from PyQt6.QtWidgets import QTextBrowser
        self._text_edit = QTextBrowser()
        self._text_edit.setObjectName("sttTranscript")
        self._text_edit.setReadOnly(True)
        self._text_edit.setOpenLinks(False)  # Handle clicks ourselves
        self._text_edit.anchorClicked.connect(self._on_anchor_clicked)
        layout.addWidget(self._text_edit)
    
    def set_result(self, result: Optional[TranscriptionResult]):
        """Set the transcription result to display"""
        self._result = result
        
        if not result:
            self._text_edit.clear()
            self._lang_label.setText(tr("language") + ": -")
            self._speakers_label.setText(tr("speakers") + ": -")
            self._edit_speakers_btn.setEnabled(False)
            return
        
        self._lang_label.setText(f"{tr('language')}: {result.language}")
        num_speakers = len(result.speakers) if result.speakers else 0
        self._speakers_label.setText(f"{tr('speakers')}: {num_speakers if num_speakers > 0 else 1}")
        self._edit_speakers_btn.setEnabled(num_speakers > 0)
        
        # Format transcript with segments
        html_parts = []
        
        if result.segments:
            for i, segment in enumerate(result.segments):
                time_str = self._format_time(segment.start)
                
                speaker_str = ""
                if segment.speaker_id:
                    speaker_name = result.get_speaker_name(segment.speaker_id)
                    speaker_str = f'<span style="color: #7aa2f7; font-weight: bold;">[{speaker_name}]</span> '
                
                # Make timestamp clickable with segment start time
                html_parts.append(
                    f'<p id="seg_{i}"><a href="seek:{segment.start}" style="color: #565f89; font-size: 11px;">{time_str}</a><br/>'
                    f'{speaker_str}{segment.text}</p>'
                )
        elif result.text:
            # Fallback: display full text if no segments
            html_parts.append(f'<p>{result.text}</p>')
        
        if html_parts:
            self._text_edit.setHtml("".join(html_parts))
        else:
            self._text_edit.setPlainText(tr("no_result"))
    
    def _format_time(self, seconds: float) -> str:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    
    def _on_anchor_clicked(self, url: QUrl):
        """Handle click on timestamp link"""
        url_str = url.toString()
        if url_str.startswith("seek:"):
            try:
                time_sec = float(url_str[5:])
                self.segment_clicked.emit(time_sec)
            except ValueError:
                pass
    
    def get_plain_text(self) -> str:
        """Get transcript as plain text"""
        if not self._result:
            return ""
        return self._result.text
    
    def _on_edit_speakers(self):
        """Open speaker editor dialog"""
        if not self._result or not self._result.speakers:
            return
        
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("edit_speaker_names"))
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(tr("assign_speaker_names")))
        
        edits = {}
        for speaker in self._result.speakers:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{tr('speaker')} {speaker.id}:"))
            
            line_edit = QLineEdit()
            line_edit.setText(speaker.name if speaker.name else "")
            line_edit.setPlaceholderText(f"Speaker {speaker.id}")
            edits[speaker.id] = line_edit
            row.addWidget(line_edit)
            
            layout.addLayout(row)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update speaker names
            for speaker in self._result.speakers:
                new_name = edits[speaker.id].text().strip()
                if new_name:
                    speaker.name = new_name
                    self.speaker_renamed.emit(speaker.id, new_name)
            
            # Refresh display
            self._refresh_display()
            self.speakers_updated.emit()
    
    def _refresh_display(self):
        """Refresh the transcript display with current result"""
        if self._result:
            self.set_result(self._result)


class TranscribeTab(QWidget):
    """Main transcription tab widget"""
    
    # Signal for thread-safe job updates
    job_updated = pyqtSignal(object)  # TranscriptionJob
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._config = get_config()
        self._api = ElevenLabsAPI()
        self._engine: Optional[TranscriptionEngine] = None
        self._current_job: Optional[TranscriptionJob] = None
        
        # Audio player
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        
        self._setup_ui()
        self._setup_engine()
        
        # Connect job update signal for thread-safe UI updates
        self.job_updated.connect(self._handle_job_update)
        
        # Connect player signals for position/duration updates
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player_duration = 0
        
        # Progress timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_progress)
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        
        # Left panel - Queue and settings
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(16)
        
        # Drop zone
        self._drop_zone = MediaDropZone()
        self._drop_zone.setObjectName("sttDropZone")
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        left_layout.addWidget(self._drop_zone)
        
        # Settings
        settings_group = QGroupBox(tr("transcription_settings"))
        settings_group.setObjectName("sttGroup")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(12)
        
        # Language
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(tr("language") + ":"))
        self._lang_combo = QComboBox()
        self._lang_combo.addItem(tr("auto_detect"), None)
        for lang in self._api.get_supported_languages():
            self._lang_combo.addItem(lang["name"], lang["code"])
        lang_layout.addWidget(self._lang_combo)
        settings_layout.addLayout(lang_layout)
        
        # Diarization
        self._diarize_check = QCheckBox(tr("identify_speakers"))
        settings_layout.addWidget(self._diarize_check)
        
        speakers_layout = QHBoxLayout()
        speakers_layout.addWidget(QLabel(tr("expected_speakers") + ":"))
        self._speakers_spin = QSpinBox()
        self._speakers_spin.setRange(0, 32)
        self._speakers_spin.setValue(0)
        self._speakers_spin.setSpecialValueText(tr("auto_detect"))
        speakers_layout.addWidget(self._speakers_spin)
        settings_layout.addLayout(speakers_layout)
        
        left_layout.addWidget(settings_group)
        
        # Queue table
        queue_group = QGroupBox(tr("transcription_queue"))
        queue_group.setObjectName("sttGroup")
        queue_layout = QVBoxLayout(queue_group)
        queue_layout.setSpacing(12)
        
        self._queue_table = QTableWidget()
        self._queue_table.setObjectName("sttQueue")
        self._queue_table.setAlternatingRowColors(True)
        self._queue_table.setColumnCount(3)
        self._queue_table.setHorizontalHeaderLabels([tr("file"), tr("size"), tr("status")])
        self._queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._queue_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._queue_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._queue_table.itemSelectionChanged.connect(self._on_queue_selection_changed)
        self._queue_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._queue_table.customContextMenuRequested.connect(self._show_queue_context_menu)
        queue_layout.addWidget(self._queue_table)
        
        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        queue_layout.addWidget(self._progress_bar)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self._start_btn = QPushButton("▶ " + tr("start"))
        self._start_btn.setObjectName("sttStartBtn")
        self._start_btn.clicked.connect(self._on_start)
        btn_layout.addWidget(self._start_btn)
        
        self._stop_btn = QPushButton("⏹ " + tr("stop"))
        self._stop_btn.setObjectName("sttStopBtn")
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)
        btn_layout.addWidget(self._stop_btn)
        
        btn_layout.addStretch()
        
        self._clear_btn = QPushButton(tr("clear_completed"))
        self._clear_btn.setObjectName("sttClearBtn")
        self._clear_btn.clicked.connect(self._on_clear_completed)
        btn_layout.addWidget(self._clear_btn)
        
        queue_layout.addLayout(btn_layout)
        
        left_layout.addWidget(queue_group)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(16)
        
        # Transcript editor
        results_group = QGroupBox(tr("transcription_result"))
        results_group.setObjectName("sttGroup")
        results_layout = QVBoxLayout(results_group)
        results_layout.setSpacing(16)
        
        self._editor = TranscriptEditorWidget()
        self._editor.segment_clicked.connect(self._on_segment_clicked)
        results_layout.addWidget(self._editor)
        
        # Audio preview
        preview_layout = QHBoxLayout()
        preview_layout.setSpacing(12)
        
        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedWidth(44)
        self._play_btn.setFixedHeight(36)
        self._play_btn.clicked.connect(self._on_play_pause)
        preview_layout.addWidget(self._play_btn)
        
        self._time_label = QLabel("00:00 / 00:00")
        preview_layout.addWidget(self._time_label)
        
        preview_layout.addStretch()
        results_layout.addLayout(preview_layout)
        
        right_layout.addWidget(results_group)
        
        # Export buttons - smaller, secondary style
        export_group = QGroupBox(tr("export"))
        export_group.setObjectName("sttGroup")
        export_layout = QHBoxLayout(export_group)
        export_layout.setSpacing(8)
        
        self._export_srt_btn = QPushButton("SRT")
        self._export_srt_btn.setObjectName("sttExportBtn")
        self._export_srt_btn.clicked.connect(lambda: self._on_export("srt"))
        export_layout.addWidget(self._export_srt_btn)
        
        self._export_vtt_btn = QPushButton("VTT")
        self._export_vtt_btn.setObjectName("sttExportBtn")
        self._export_vtt_btn.clicked.connect(lambda: self._on_export("vtt"))
        export_layout.addWidget(self._export_vtt_btn)
        
        self._export_txt_btn = QPushButton("TXT")
        self._export_txt_btn.setObjectName("sttExportBtn")
        self._export_txt_btn.clicked.connect(lambda: self._on_export("txt"))
        export_layout.addWidget(self._export_txt_btn)
        
        self._export_json_btn = QPushButton("JSON")
        self._export_json_btn.setObjectName("sttExportBtn")
        self._export_json_btn.clicked.connect(lambda: self._on_export("json"))
        export_layout.addWidget(self._export_json_btn)
        
        export_layout.addStretch()  # Push buttons to left, don't stretch them
        
        right_layout.addWidget(export_group)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
    
    def _setup_engine(self):
        """Initialize the transcription engine"""
        self._engine = TranscriptionEngine(
            api_keys=self._config.api_keys,
            proxies=self._config.proxies,
            on_progress=self._on_job_progress,
            on_log=self._on_log
        )
    
    def _on_log(self, message: str):
        """Handle log messages"""
        # Could emit to main window log
        print(f"[Transcribe] {message}")
    
    def _on_files_dropped(self, files: list):
        """Handle dropped files"""
        language = self._lang_combo.currentData()
        diarize = self._diarize_check.isChecked()
        num_speakers = self._speakers_spin.value() if self._speakers_spin.value() > 0 else None
        
        for file_path in files:
            job = self._engine.add_job(
                file_path=file_path,
                language=language,
                diarize=diarize,
                num_speakers=num_speakers
            )
            if job:
                self._add_job_to_table(job)
    
    def _add_job_to_table(self, job: TranscriptionJob):
        """Add job to queue table"""
        row = self._queue_table.rowCount()
        self._queue_table.insertRow(row)
        
        # File name
        name_item = QTableWidgetItem(job.file_name)
        name_item.setData(Qt.ItemDataRole.UserRole, job.id)
        self._queue_table.setItem(row, 0, name_item)
        
        # File size
        size_mb = job.file_size / (1024 * 1024)
        size_item = QTableWidgetItem(f"{size_mb:.1f} MB")
        self._queue_table.setItem(row, 1, size_item)
        
        # Status
        status_item = QTableWidgetItem(job.status.value)
        self._queue_table.setItem(row, 2, status_item)
    
    def _update_job_in_table(self, job: TranscriptionJob):
        """Update job status in table"""
        for row in range(self._queue_table.rowCount()):
            item = self._queue_table.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == job.id:
                status_item = self._queue_table.item(row, 2)
                if status_item:
                    status_item.setText(job.status.value)
                    if job.status == JobStatus.DONE:
                        status_item.setForeground(Qt.GlobalColor.green)
                    elif job.status == JobStatus.ERROR:
                        status_item.setForeground(Qt.GlobalColor.red)
                    elif job.status == JobStatus.PROCESSING:
                        status_item.setForeground(Qt.GlobalColor.yellow)
                break
    
    def _on_job_progress(self, job: TranscriptionJob):
        """Handle job progress update - called from worker thread"""
        # Emit signal to update UI on main thread
        self.job_updated.emit(job)
    
    def _handle_job_update(self, job: TranscriptionJob):
        """Handle job update on main thread - slot for job_updated signal"""
        self._update_job_in_table(job)
        
        # Auto-select and show result when job completes
        if job.status == JobStatus.DONE:
            self._on_log(f"Job completed: {job.file_name}")
            
            # Find and select the completed job row
            for row in range(self._queue_table.rowCount()):
                item = self._queue_table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == job.id:
                    self._queue_table.selectRow(row)
                    break
            
            self._current_job = job
            
            if job.result:
                self._on_log(f"Result: {len(job.result.segments)} segments, lang={job.result.language}")
                self._editor.set_result(job.result)
            else:
                self._on_log("No result in completed job")
                self._editor.set_result(None)
            
            # Setup player for this file
            if os.path.exists(job.input_path):
                self._player.setSource(QUrl.fromLocalFile(job.input_path))
        elif job.status == JobStatus.ERROR:
            self._on_log(f"Job failed: {job.file_name} - {job.error}")
    
    def _on_queue_selection_changed(self):
        """Handle queue selection change"""
        selected = self._queue_table.selectedItems()
        if not selected:
            self._current_job = None
            self._editor.set_result(None)
            return
        
        row = selected[0].row()
        job_id = self._queue_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        for job in self._engine.jobs:
            if job.id == job_id:
                self._current_job = job
                if job.result:
                    self._editor.set_result(job.result)
                else:
                    self._editor.set_result(None)
                
                # Setup player for this file
                if os.path.exists(job.input_path):
                    self._player.setSource(QUrl.fromLocalFile(job.input_path))
                break
    
    def _show_queue_context_menu(self, pos):
        """Show context menu for queue"""
        item = self._queue_table.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        remove_action = QAction(tr("remove"), self)
        remove_action.triggered.connect(self._on_remove_selected)
        menu.addAction(remove_action)
        
        menu.exec(self._queue_table.mapToGlobal(pos))
    
    def _on_remove_selected(self):
        """Remove selected job"""
        selected = self._queue_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        job_id = self._queue_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if self._engine.remove_job(job_id):
            self._queue_table.removeRow(row)
    
    def _on_start(self):
        """Start processing"""
        if not self._engine.jobs:
            QMessageBox.warning(self, tr("warning"), tr("no_files_in_queue"))
            return
        
        if not self._config.api_keys:
            QMessageBox.warning(self, tr("warning"), tr("no_api_keys"))
            return
        
        self._engine.start()
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 0)  # Indeterminate
        self._timer.start(500)
    
    def _on_stop(self):
        """Stop processing"""
        self._engine.stop()
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setVisible(False)
        self._timer.stop()
    
    def _update_progress(self):
        """Update progress display"""
        if not self._engine.is_running:
            self._on_stop()
    
    def _on_clear_completed(self):
        """Clear completed jobs"""
        self._engine.clear_completed()
        
        # Remove from table
        rows_to_remove = []
        for row in range(self._queue_table.rowCount()):
            status_item = self._queue_table.item(row, 2)
            if status_item and status_item.text() in ("Done", "Error"):
                rows_to_remove.append(row)
        
        for row in sorted(rows_to_remove, reverse=True):
            self._queue_table.removeRow(row)
    
    def _on_play_pause(self):
        """Toggle audio playback"""
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
            self._play_btn.setText("▶")
        else:
            self._player.play()
            self._play_btn.setText("⏸")
    
    def _on_segment_clicked(self, time_sec: float):
        """Seek to segment start time when clicked"""
        # Convert seconds to milliseconds
        position_ms = int(time_sec * 1000)
        self._player.setPosition(position_ms)
        
        # Start playback if not already playing
        if self._player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self._player.play()
            self._play_btn.setText("⏸")
        
        self._on_log(f"Seeking to {self._format_time(time_sec)}")
    
    def _on_position_changed(self, position_ms: int):
        """Update time label when playback position changes"""
        position_sec = position_ms / 1000.0
        duration_sec = self._player_duration / 1000.0
        self._time_label.setText(f"{self._format_time(position_sec)} / {self._format_time(duration_sec)}")
    
    def _on_duration_changed(self, duration_ms: int):
        """Update duration when media loads"""
        self._player_duration = duration_ms
        duration_sec = duration_ms / 1000.0
        self._time_label.setText(f"00:00 / {self._format_time(duration_sec)}")
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    
    def _on_export(self, format_type: str):
        """Export current transcription"""
        if not self._current_job or not self._current_job.result:
            QMessageBox.warning(self, tr("warning"), tr("no_transcription_result"))
            return
        
        base_name = os.path.splitext(self._current_job.file_name)[0]
        
        extensions = {
            "srt": "SRT Files (*.srt)",
            "vtt": "WebVTT Files (*.vtt)",
            "txt": "Text Files (*.txt)",
            "json": "JSON Files (*.json)"
        }
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("export_transcription"),
            f"{base_name}.{format_type}",
            extensions.get(format_type, "All Files (*.*)")
        )
        
        if not file_path:
            return
        
        result = self._current_job.result
        success = False
        
        if format_type == "srt":
            success = TranscriptionExporter.export_srt(result, file_path)
        elif format_type == "vtt":
            success = TranscriptionExporter.export_vtt(result, file_path)
        elif format_type == "txt":
            success = TranscriptionExporter.export_txt(result, file_path)
        elif format_type == "json":
            success = TranscriptionExporter.export_json(result, file_path)
        
        if success:
            QMessageBox.information(self, tr("success"), f"{tr('export_success')}: {file_path}")
        else:
            QMessageBox.critical(self, tr("error"), tr("export_error"))
    
    def refresh_config(self):
        """Refresh configuration (called when API keys/proxies change)"""
        self._setup_engine()
