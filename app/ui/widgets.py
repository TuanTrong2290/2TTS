"""Custom widgets for 2TTS application"""
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
    QGroupBox, QPushButton, QLineEdit, QCheckBox, QSizePolicy,
    QMenu, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QAction
from ui.styles import COLORS

from core.models import TextLine, LineStatus, Voice, VoiceSettings
from services.localization import tr


class DropZone(QFrame):
    """Drag and drop zone for file import"""
    
    files_dropped = pyqtSignal(list)  # List of file paths
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(150)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel("📁")
        icon_label.setFont(QFont("Segoe UI", 32))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel(tr("drop_files_title"))
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle_label = QLabel(tr("drop_files_subtitle"))
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._browse_files()
    
    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Files", "",
            "Supported Files (*.srt *.txt *.docx);;SRT Files (*.srt);;Text Files (*.txt);;Word Documents (*.docx);;All Files (*.*)"
        )
        if files:
            self.files_dropped.emit(files)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            c = COLORS["dark"] # Default to dark for drag effect or check system?
            # Ideally we check the current theme, but for now let's use the accent color
            # We can use the transparent/hex values directly
            self.setStyleSheet(f"border-color: {c['accent_primary']}; background-color: {c['bg_tertiary']};")
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
    
    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        files = []
        for url in event.mimeData().urls():
            files.append(url.toLocalFile())
        if files:
            self.files_dropped.emit(files)


class LineTableWidget(QTableWidget):
    """Table widget for displaying text lines"""
    
    voice_changed = pyqtSignal(int, str, str)  # row, voice_id, voice_name
    lines_reordered = pyqtSignal()  # Emitted when rows are reordered
    text_edited = pyqtSignal(int, str)  # row, new_text
    play_requested = pyqtSignal(int)  # row index to play audio
    retry_requested = pyqtSignal(list)  # list of row indices to retry
    delete_requested = pyqtSignal(list)  # list of row indices to delete
    split_requested = pyqtSignal(int)  # row index to split
    merge_requested = pyqtSignal(list)  # list of row indices to merge
    
    COLUMN_KEYS = ["col_index", "col_text", "col_voice", "col_model", "col_status", "col_duration", "col_language"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        columns = [tr(key) for key in self.COLUMN_KEYS]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # Configure table
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(True)  # Show vertical header for drag handle
        self.setShowGrid(False) # Modern look: no grid lines
        self.setSortingEnabled(True)  # Enable sorting
        
        # Enable drag and drop for row reordering
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.verticalHeader().setSectionsMovable(True)
        self.verticalHeader().setDragEnabled(True)
        self.verticalHeader().setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        # Column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)   # #
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # Text
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)   # Voice
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)   # Model
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)   # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)   # Duration
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)   # Language
        header.setSortIndicatorShown(True)  # Show sort indicator
        
        self.setColumnWidth(0, 50)   # #
        self.setColumnWidth(2, 120)  # Voice
        self.setColumnWidth(3, 100)  # Model
        self.setColumnWidth(4, 80)   # Status
        self.setColumnWidth(5, 70)   # Duration
        self.setColumnWidth(6, 70)   # Language
        
        self._voices = []
        self._lines = []
        self._all_lines = []  # Store all lines for filtering
        self._filter_text = ""
        self._filter_status = None
        self._updating = False  # Prevent recursion during updates
        
        # Connect cell change signal for text editing
        self.cellChanged.connect(self._on_cell_changed)
        
        # Connect vertical header section moved for row reordering
        self.verticalHeader().sectionMoved.connect(self._on_row_moved)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def set_voices(self, voices: list):
        """Set available voices for combo boxes"""
        self._voices = voices
    
    def load_lines(self, lines: list):
        """Load lines into the table"""
        self._updating = True
        self._all_lines = lines
        self._apply_filter()
        self._updating = False
    
    def set_filter(self, text: str = "", status: str = None):
        """Set filter criteria"""
        self._filter_text = text.lower()
        self._filter_status = status
        self._apply_filter()
    
    def _apply_filter(self):
        """Apply current filter to lines"""
        if not self._filter_text and not self._filter_status:
            self._lines = self._all_lines
        else:
            self._lines = []
            for line in self._all_lines:
                # Text filter
                if self._filter_text and self._filter_text not in line.text.lower():
                    continue
                # Status filter
                if self._filter_status and line.status.value != self._filter_status:
                    continue
                self._lines.append(line)
        
        self.setRowCount(len(self._lines))
        for row, line in enumerate(self._lines):
            self._update_row(row, line)
    
    def _update_row(self, row: int, line: TextLine):
        """Update a single row"""
        # Index
        index_item = QTableWidgetItem(str(line.index + 1))
        index_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        index_item.setFlags(index_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 0, index_item)
        
        # Text (editable - show full text for direct editing)
        text_item = QTableWidgetItem(line.text)
        text_item.setToolTip("Double-click to edit text for translation")
        text_item.setFlags(text_item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 1, text_item)
        
        # Voice
        voice_item = QTableWidgetItem(line.voice_name or "Default")
        voice_item.setData(Qt.ItemDataRole.UserRole, line.voice_id)
        self.setItem(row, 2, voice_item)
        
        # Model - show friendly name
        model_display = self._get_model_display_name(line.model_used)
        model_item = QTableWidgetItem(model_display)
        model_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        model_item.setFlags(model_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if line.model_used:
            model_item.setToolTip(f"Model ID: {line.model_used}")
        self.setItem(row, 3, model_item)
        
        # Status
        status_item = QTableWidgetItem(line.status.value)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        
        # Color based on status (Using theme colors)
        c = COLORS["dark"] # Defaulting to dark palette for status colors
        if line.status == LineStatus.DONE:
            status_item.setForeground(QColor(c['success']))
        elif line.status == LineStatus.ERROR:
            status_item.setForeground(QColor(c['error']))
            status_item.setToolTip(line.error_message or "")
        elif line.status == LineStatus.PROCESSING:
            status_item.setForeground(QColor(c['warning']))
        
        self.setItem(row, 4, status_item)
        
        # Duration
        duration_text = f"{line.audio_duration:.1f}s" if line.audio_duration else "-"
        duration_item = QTableWidgetItem(duration_text)
        duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 5, duration_item)
        
        # Language
        lang_item = QTableWidgetItem(line.detected_language or "-")
        lang_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        lang_item.setFlags(lang_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 6, lang_item)
    
    def _get_model_display_name(self, model_id: str) -> str:
        """Convert model ID to friendly display name"""
        if not model_id:
            return "-"
        model_names = {
            "eleven_v3": "v3",
            "eleven_multilingual_v2": "Multi v2",
            "eleven_turbo_v2_5": "Turbo 2.5",
            "eleven_flash_v2_5": "Flash 2.5",
            "eleven_flash_v2": "Flash v2",
        }
        return model_names.get(model_id, model_id[:10])
    
    def update_line(self, line: TextLine):
        """Update a specific line by its id"""
        for row, l in enumerate(self._lines):
            if l.id == line.id:
                self._lines[row] = line
                self._update_row(row, line)
                break
    
    def get_selected_rows(self) -> list:
        """Get selected row indices"""
        return list(set(item.row() for item in self.selectedItems()))
    
    def get_lines(self) -> list:
        """Get all lines"""
        return self._lines
    
    def _on_cell_changed(self, row: int, column: int):
        """Handle cell edit - update underlying data for text column"""
        if self._updating or column != 1:  # Only handle text column
            return
        
        item = self.item(row, column)
        if item and row < len(self._lines):
            new_text = item.text()
            if new_text != self._lines[row].text:
                self._lines[row].text = new_text
                self.text_edited.emit(row, new_text)
    
    def _on_row_moved(self, logical_index: int, old_visual: int, new_visual: int):
        """Handle row drag reordering via vertical header"""
        if self._updating or old_visual == new_visual:
            return
        
        # Reorder the internal lines list
        if old_visual < len(self._lines) and new_visual < len(self._lines):
            line = self._lines.pop(old_visual)
            self._lines.insert(new_visual, line)
            
            # Update indices
            for i, ln in enumerate(self._lines):
                ln.index = i
            
            # Reload to sync display with new order
            self.load_lines(self._lines)
            self.lines_reordered.emit()
    
    def dropEvent(self, event):
        """Handle drop event for row reordering via drag"""
        if event.source() != self:
            event.ignore()
            return
        
        # Get source row from selection
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            event.ignore()
            return
        
        source_row = selected_rows[0]
        drop_indicator = self.dropIndicatorPosition()
        target_row = self.indexAt(event.position().toPoint()).row()
        
        if target_row < 0:
            target_row = self.rowCount() - 1
        
        # Adjust target based on drop indicator
        from PyQt6.QtWidgets import QAbstractItemView
        if drop_indicator == QAbstractItemView.DropIndicatorPosition.BelowItem:
            target_row += 1
        
        if source_row == target_row or source_row < 0:
            event.ignore()
            return
        
        # Perform the move in data
        if source_row < len(self._lines):
            line = self._lines.pop(source_row)
            if target_row > source_row:
                target_row -= 1
            if target_row > len(self._lines):
                target_row = len(self._lines)
            self._lines.insert(target_row, line)
            
            # Update indices
            for i, ln in enumerate(self._lines):
                ln.index = i
            
            # Reload to sync display
            self.load_lines(self._lines)
            self.lines_reordered.emit()
        
        event.accept()
    
    def _show_context_menu(self, position):
        """Show context menu for row operations"""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return
        
        menu = QMenu(self)
        
        # Play action (only for single selection with completed audio)
        if len(selected_rows) == 1:
            row = selected_rows[0]
            if row < len(self._lines) and self._lines[row].status == LineStatus.DONE:
                play_action = QAction("▶ Play Audio", self)
                play_action.triggered.connect(lambda: self.play_requested.emit(row))
                menu.addAction(play_action)
                menu.addSeparator()
        
        # Retry action (for failed lines)
        failed_rows = [r for r in selected_rows if r < len(self._lines) and self._lines[r].status == LineStatus.ERROR]
        if failed_rows:
            retry_action = QAction(f"🔄 Retry Failed ({len(failed_rows)})", self)
            retry_action.triggered.connect(lambda: self.retry_requested.emit(failed_rows))
            menu.addAction(retry_action)
        
        # Reset to pending
        reset_action = QAction(f"↺ Reset to Pending ({len(selected_rows)})", self)
        reset_action.triggered.connect(lambda: self._reset_to_pending(selected_rows))
        menu.addAction(reset_action)
        
        menu.addSeparator()
        
        # Move up/down (single selection)
        if len(selected_rows) == 1:
            row = selected_rows[0]
            if row > 0:
                move_up_action = QAction("↑ Move Up", self)
                move_up_action.triggered.connect(lambda: self._move_row(row, -1))
                menu.addAction(move_up_action)
            if row < len(self._lines) - 1:
                move_down_action = QAction("↓ Move Down", self)
                move_down_action.triggered.connect(lambda: self._move_row(row, 1))
                menu.addAction(move_down_action)
            menu.addSeparator()
        
        # Split action (single selection)
        if len(selected_rows) == 1:
            row = selected_rows[0]
            split_action = QAction("✂ Split Line", self)
            split_action.triggered.connect(lambda: self.split_requested.emit(row))
            menu.addAction(split_action)
        
        # Merge action (multiple selection)
        if len(selected_rows) > 1:
            merge_action = QAction(f"🔗 Merge Lines ({len(selected_rows)})", self)
            merge_action.triggered.connect(lambda: self.merge_requested.emit(selected_rows))
            menu.addAction(merge_action)
        
        menu.addSeparator()
        
        # Delete action
        delete_action = QAction(f"🗑 Delete ({len(selected_rows)})", self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(selected_rows))
        menu.addAction(delete_action)
        
        menu.exec(self.viewport().mapToGlobal(position))
    
    def _reset_to_pending(self, rows: list):
        """Reset selected rows to pending status"""
        for row in rows:
            if row < len(self._lines):
                self._lines[row].status = LineStatus.PENDING
                self._lines[row].error_message = None
        self.load_lines(self._lines)
        self.lines_reordered.emit()
    
    def _move_row(self, row: int, direction: int):
        """Move a row up (-1) or down (+1)"""
        new_row = row + direction
        if 0 <= new_row < len(self._lines):
            self._lines[row], self._lines[new_row] = self._lines[new_row], self._lines[row]
            # Update indices
            self._lines[row].index = row
            self._lines[new_row].index = new_row
            self.load_lines(self._lines)
            # Select the moved row
            self.selectRow(new_row)
            self.lines_reordered.emit()


class VoiceSettingsWidget(QGroupBox):
    """Widget for voice settings (stability, similarity, speed, model)"""
    
    settings_changed = pyqtSignal(object)  # VoiceSettings
    
    def __init__(self, title: str = None, parent=None):
        super().__init__(title or tr("voice_settings"), parent)
        self.setMinimumHeight(280)  # Ensure content is visible with all settings
        
        layout = QVBoxLayout(self)
        
        # Model (moved to top for better UX)
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel(tr("model") + ":"))
        self.model_combo = QComboBox()
        self.model_combo.addItem("Eleven v3 (Alpha)", "eleven_v3")
        self.model_combo.addItem("Multilingual v2", "eleven_multilingual_v2")
        self.model_combo.addItem("Turbo v2.5", "eleven_turbo_v2_5")
        self.model_combo.addItem("Flash v2.5", "eleven_flash_v2_5")
        self.model_combo.addItem("Flash v2", "eleven_flash_v2")
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        model_layout.addWidget(self.model_combo)
        model_layout.addStretch()
        layout.addLayout(model_layout)
        
        # v3 info label (hidden by default)
        self.v3_info_label = QLabel(tr("v3_audio_tags_hint"))
        self.v3_info_label.setStyleSheet("color: #7aa2f7; font-size: 11px;")
        self.v3_info_label.setWordWrap(True)
        self.v3_info_label.hide()
        layout.addWidget(self.v3_info_label)
        
        # Stability
        stab_layout = QHBoxLayout()
        self.stability_label = QLabel(tr("stability") + ":")
        stab_layout.addWidget(self.stability_label)
        self.stability_slider = QSlider(Qt.Orientation.Horizontal)
        self.stability_slider.setRange(0, 100)
        self.stability_slider.setValue(50)
        self.stability_slider.valueChanged.connect(self._on_settings_changed)
        self.stability_value = QLabel("0.50")
        stab_layout.addWidget(self.stability_slider)
        stab_layout.addWidget(self.stability_value)
        layout.addLayout(stab_layout)
        
        # Stability preset label for v3 (hidden by default)
        self.stability_preset_label = QLabel("Creative ← Natural → Robust")
        self.stability_preset_label.setStyleSheet("color: #888; font-size: 10px;")
        self.stability_preset_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stability_preset_label.hide()
        layout.addWidget(self.stability_preset_label)
        
        # Similarity
        sim_layout = QHBoxLayout()
        sim_layout.addWidget(QLabel(tr("similarity") + ":"))
        self.similarity_slider = QSlider(Qt.Orientation.Horizontal)
        self.similarity_slider.setRange(0, 100)
        self.similarity_slider.setValue(75)
        self.similarity_slider.valueChanged.connect(self._on_settings_changed)
        self.similarity_value = QLabel("0.75")
        sim_layout.addWidget(self.similarity_slider)
        sim_layout.addWidget(self.similarity_value)
        layout.addLayout(sim_layout)
        
        # Style container (can be hidden for v3)
        self.style_container = QWidget()
        style_container_layout = QHBoxLayout(self.style_container)
        style_container_layout.setContentsMargins(0, 0, 0, 0)
        self.style_label = QLabel(tr("style") + ":")
        style_container_layout.addWidget(self.style_label)
        self.style_slider = QSlider(Qt.Orientation.Horizontal)
        self.style_slider.setRange(0, 100)
        self.style_slider.setValue(0)
        self.style_slider.setToolTip("Style exaggeration - amplifies speaker's style (increases latency)")
        self.style_slider.valueChanged.connect(self._on_settings_changed)
        self.style_value = QLabel("0.00")
        style_container_layout.addWidget(self.style_slider)
        style_container_layout.addWidget(self.style_value)
        layout.addWidget(self.style_container)
        
        # Speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel(tr("speed") + ":"))
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 2.0)
        self.speed_spin.setSingleStep(0.1)
        self.speed_spin.setValue(1.0)
        self.speed_spin.valueChanged.connect(self._on_settings_changed)
        speed_layout.addWidget(self.speed_spin)
        speed_layout.addStretch()
        layout.addLayout(speed_layout)
        
        # Speaker boost checkbox
        self.speaker_boost_check = QCheckBox(tr("speaker_boost"))
        self.speaker_boost_check.setChecked(True)
        self.speaker_boost_check.setToolTip("Enhances similarity to original speaker (increases latency)")
        self.speaker_boost_check.stateChanged.connect(self._on_settings_changed)
        layout.addWidget(self.speaker_boost_check)
        
        # Initialize UI based on default model
        self._update_ui_for_model()
    
    def _on_model_changed(self):
        """Handle model selection change"""
        self._update_ui_for_model()
        self._on_settings_changed()
    
    def _update_ui_for_model(self):
        """Update UI elements based on selected model"""
        model_id = self.model_combo.currentData()
        is_v3 = model_id == "eleven_v3"
        
        # Show/hide v3-specific elements
        self.v3_info_label.setVisible(is_v3)
        self.stability_preset_label.setVisible(is_v3)
        
        # For v3: hide style slider (uses audio tags instead)
        self.style_container.setVisible(not is_v3)
        
        # Update stability tooltip based on model
        if is_v3:
            self.stability_slider.setToolTip(
                "v3 Stability:\n"
                "• Low (0-0.3): Creative - More expressive, prone to hallucinations\n"
                "• Mid (0.3-0.7): Natural - Balanced, closest to original\n"
                "• High (0.7-1.0): Robust - Very stable, less responsive to prompts"
            )
            self._update_stability_preset_label()
        else:
            self.stability_slider.setToolTip(
                "Controls voice stability. Lower = more emotional range, Higher = more consistent"
            )
    
    def _update_stability_preset_label(self):
        """Update the stability preset label based on current value"""
        value = self.stability_slider.value() / 100
        if value < 0.3:
            preset = "Creative (expressive)"
        elif value < 0.7:
            preset = "Natural (balanced)"
        else:
            preset = "Robust (stable)"
        self.stability_preset_label.setText(f"Mode: {preset}")
    
    def _on_settings_changed(self):
        self.stability_value.setText(f"{self.stability_slider.value() / 100:.2f}")
        self.similarity_value.setText(f"{self.similarity_slider.value() / 100:.2f}")
        self.style_value.setText(f"{self.style_slider.value() / 100:.2f}")
        
        # Update v3 stability preset label
        if self.model_combo.currentData() == "eleven_v3":
            self._update_stability_preset_label()
        
        self.settings_changed.emit(self.get_settings())
    
    def get_settings(self) -> VoiceSettings:
        from core.models import TTSModel
        return VoiceSettings(
            stability=self.stability_slider.value() / 100,
            similarity_boost=self.similarity_slider.value() / 100,
            style=self.style_slider.value() / 100,
            use_speaker_boost=self.speaker_boost_check.isChecked(),
            speed=self.speed_spin.value(),
            model=TTSModel(self.model_combo.currentData())
        )
    
    def set_settings(self, settings: VoiceSettings):
        self.stability_slider.setValue(int(settings.stability * 100))
        self.similarity_slider.setValue(int(settings.similarity_boost * 100))
        self.style_slider.setValue(int(settings.style * 100))
        self.speaker_boost_check.setChecked(settings.use_speaker_boost)
        self.speed_spin.setValue(settings.speed)
        
        index = self.model_combo.findData(settings.model.value)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        # Update UI for selected model
        self._update_ui_for_model()


class ProgressWidget(QWidget):
    """Widget for displaying processing progress"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Stats row
        stats_layout = QHBoxLayout()
        
        self.progress_label = QLabel(tr("lines_progress", completed=0, total=0))
        stats_layout.addWidget(self.progress_label)
        
        stats_layout.addStretch()
        
        self.time_label = QLabel(f"{tr('elapsed')}: 00:00:00")
        stats_layout.addWidget(self.time_label)
        
        stats_layout.addStretch()
        
        self.eta_label = QLabel(f"{tr('eta')}: --:--:--")
        stats_layout.addWidget(self.eta_label)
        
        stats_layout.addStretch()
        
        self.status_label = QLabel(tr("ready"))
        stats_layout.addWidget(self.status_label)
        
        layout.addLayout(stats_layout)
    
    def update_progress(self, completed: int, total: int, elapsed_seconds: float, status: str = ""):
        if total > 0:
            percent = int((completed / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"{tr('lines_progress', completed=completed, total=total)} ({percent}%)")
            
            # Calculate ETA
            if completed > 0:
                avg_time_per_item = elapsed_seconds / completed
                remaining_items = total - completed
                eta_seconds = avg_time_per_item * remaining_items
                self.eta_label.setText(f"{tr('eta')}: {self._format_time(eta_seconds)}")
            else:
                self.eta_label.setText(f"{tr('eta')}: --:--:--")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText(tr("lines_progress", completed=0, total=0))
            self.eta_label.setText(f"{tr('eta')}: --:--:--")
        
        # Format elapsed time
        self.time_label.setText(f"{tr('elapsed')}: {self._format_time(elapsed_seconds)}")
        
        if status:
            self.status_label.setText(status)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def reset(self):
        self.progress_bar.setValue(0)
        self.progress_label.setText(tr("lines_progress", completed=0, total=0))
        self.time_label.setText(f"{tr('elapsed')}: 00:00:00")
        self.eta_label.setText(f"{tr('eta')}: --:--:--")
        self.status_label.setText(tr("ready"))


class CreditWidget(QWidget):
    """Widget for displaying credit information"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.credit_label = QLabel(f"{tr('credits')}: -")
        layout.addWidget(self.credit_label)
        
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedWidth(30)
        layout.addWidget(self.refresh_btn)
    
    def update_credits(self, total: int, warning_threshold: int = 1000):
        self.credit_label.setText(f"{tr('credits')}: {total:,}")
        
        if total < warning_threshold:
            self.credit_label.setObjectName("warningLabel")
        else:
            self.credit_label.setObjectName("")
        
        # Force style refresh
        self.credit_label.style().unpolish(self.credit_label)
        self.credit_label.style().polish(self.credit_label)


class FilterWidget(QWidget):
    """Widget for filtering table content"""
    
    filter_changed = pyqtSignal(str, str)  # text, status
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel(tr("filter") + ":"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(tr("search_placeholder"))
        self.search_edit.textChanged.connect(self._on_filter_changed)
        layout.addWidget(self.search_edit)
        
        self.status_combo = QComboBox()
        self.status_combo.addItem(tr("all_status"), None)
        self.status_combo.addItem(tr("pending"), "Pending")
        self.status_combo.addItem(tr("processing"), "Processing")
        self.status_combo.addItem(tr("done"), "Done")
        self.status_combo.addItem(tr("error"), "Error")
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self.status_combo)
        
        clear_btn = QPushButton(tr("clear"))
        clear_btn.clicked.connect(self._clear_filter)
        layout.addWidget(clear_btn)
    
    def _on_filter_changed(self):
        text = self.search_edit.text()
        status = self.status_combo.currentData()
        self.filter_changed.emit(text, status or "")
    
    def _clear_filter(self):
        self.search_edit.clear()
        self.status_combo.setCurrentIndex(0)


class ThreadStatusWidget(QGroupBox):
    """Widget for displaying thread status"""
    
    def __init__(self, max_threads: int = 10, parent=None):
        super().__init__(tr("thread_status"), parent)
        
        self._max_threads = max_threads
        self._thread_labels = []
        
        layout = QVBoxLayout(self)
        
        # Thread count display
        self.count_label = QLabel(tr("active_threads", active=0, total=0))
        layout.addWidget(self.count_label)
        
        # Thread indicators (horizontal layout)
        self._thread_layout = QHBoxLayout()
        for i in range(max_threads):
            label = QLabel("○")
            label.setToolTip(f"Thread {i + 1}: Idle")
            label.setStyleSheet("color: gray;")
            self._thread_labels.append(label)
            self._thread_layout.addWidget(label)
        self._thread_layout.addStretch()
        layout.addLayout(self._thread_layout)
    
    def update_status(self, active_count: int, total_threads: int, thread_info: dict = None):
        """Update thread status display"""
        self.count_label.setText(tr("active_threads", active=active_count, total=total_threads))
        
        # Update indicators
        for i, label in enumerate(self._thread_labels):
            if i < total_threads:
                if thread_info and i in thread_info:
                    label.setText("●")
                    label.setStyleSheet("color: #4CAF50;")  # Green for active
                    label.setToolTip(f"Thread {i + 1}: {thread_info[i]}")
                elif i < active_count:
                    label.setText("●")
                    label.setStyleSheet("color: #2196F3;")  # Blue for working
                    label.setToolTip(f"Thread {i + 1}: Working")
                else:
                    label.setText("○")
                    label.setStyleSheet("color: gray;")
                    label.setToolTip(f"Thread {i + 1}: Idle")
                label.setVisible(True)
            else:
                label.setVisible(False)
    
    def reset(self):
        """Reset all thread indicators"""
        for label in self._thread_labels:
            label.setText("○")
            label.setStyleSheet("color: gray;")
            label.setToolTip("Idle")
