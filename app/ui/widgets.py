"""Custom widgets for 2TTS application"""
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QProgressBar, QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
    QGroupBox, QPushButton, QLineEdit, QCheckBox, QSizePolicy,
    QMenu, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QAction, QPalette
from ui.styles import COLORS

from core.models import TextLine, LineStatus, Voice, VoiceSettings
from services.localization import tr


def get_current_theme_colors():
    """Get colors based on current application palette (light or dark)"""
    app = QApplication.instance()
    if app:
        palette = app.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        # Check if background is dark (luminance < 128)
        is_dark = window_color.lightness() < 128
        return COLORS["dark" if is_dark else "light"]
    return COLORS["dark"]


class DropZone(QFrame):
    """Drag and drop zone for file import - supports full and compact modes"""
    
    files_dropped = pyqtSignal(list)  # List of file paths
    
    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._compact = compact
        
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.setSpacing(10)
        
        # Icon
        self._icon_label = QLabel("☁️")
        self._icon_label.setFont(QFont("Segoe UI Emoji", 48 if not compact else 20))
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
        self._title_label = QLabel(tr("drop_files_title"))
        self._title_label.setObjectName("titleLabel")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setFont(QFont("Segoe UI", 12 if not compact else 10, QFont.Weight.Bold))
        
        # Subtitle
        self._subtitle_label = QLabel(tr("drop_files_subtitle"))
        self._subtitle_label.setObjectName("subtitleLabel")
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._layout.addWidget(self._icon_label)
        self._layout.addWidget(self._title_label)
        self._layout.addWidget(self._subtitle_label)
        
        self._apply_mode()
    
    def _apply_mode(self):
        """Apply compact or full mode styling"""
        if self._compact:
            self.setMinimumHeight(50)
            self.setMaximumHeight(50)
            self._icon_label.hide()
            self._subtitle_label.hide()
            self._layout.setContentsMargins(10, 5, 10, 5)
        else:
            self.setMinimumHeight(140)
            self.setMaximumHeight(200)
            self._icon_label.show()
            self._subtitle_label.show()
            self._layout.setContentsMargins(10, 10, 10, 10)
    
    def set_compact(self, compact: bool):
        """Switch between compact and full mode"""
        if self._compact != compact:
            self._compact = compact
            self._icon_label.setFont(QFont("Segoe UI Emoji", 20 if compact else 48))
            self._title_label.setFont(QFont("Segoe UI", 10 if compact else 12, QFont.Weight.Bold))
            self._apply_mode()
    
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
            # Visual feedback is handled by stylesheet :hover state, 
            # but we can force update if needed.
            # Here we just rely on the hover style defined in styles.py
    
    def dragLeaveEvent(self, event):
        pass
    
    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            files.append(url.toLocalFile())
        if files:
            self.files_dropped.emit(files)


class TableEmptyState(QWidget):
    """Empty state widget shown when table has no data"""
    
    import_clicked = pyqtSignal()  # Emitted when import button is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tableEmptyState")
        
        # Get theme colors
        c = get_current_theme_colors()
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)
        
        # Icon
        icon_label = QLabel("📄")
        icon_label.setFont(QFont("Segoe UI Emoji", 48))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Title
        self._title_label = QLabel(tr("empty_state_title"))
        self._title_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {c['accent_primary']};")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)
        
        # Description
        self._desc_label = QLabel(tr("empty_state_desc"))
        self._desc_label.setStyleSheet(f"color: {c['fg_tertiary']}; font-size: 12px;")
        self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._desc_label.setWordWrap(True)
        layout.addWidget(self._desc_label)
        
        # Import button
        import_btn = QPushButton("📂 " + tr("import_files"))
        import_btn.setObjectName("primaryButton")
        import_btn.setMinimumWidth(150)
        import_btn.setMinimumHeight(40)
        import_btn.clicked.connect(self.import_clicked.emit)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(import_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Tips
        self._tips_label = QLabel(tr("empty_state_tip"))
        self._tips_label.setStyleSheet(f"color: {c['fg_tertiary']}; font-size: 11px; margin-top: 10px;")
        self._tips_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._tips_label)


class LineTableWidget(QTableWidget):
    """Table widget for displaying text lines"""
    
    # Signals now emit line IDs instead of row indices for correctness under filtering/sorting
    voice_changed = pyqtSignal(str, str, str)  # line_id, voice_id, voice_name
    lines_reordered = pyqtSignal(list)  # Emitted with list of line IDs in new order
    text_edited = pyqtSignal(str, str)  # line_id, new_text
    play_requested = pyqtSignal(str)  # line_id to play audio
    retry_requested = pyqtSignal(list)  # list of line IDs to retry
    delete_requested = pyqtSignal(list)  # list of line IDs to delete
    split_requested = pyqtSignal(str)  # line_id to split
    merge_requested = pyqtSignal(list)  # list of line IDs to merge
    
    # Custom role for storing line ID in table items
    LineIdRole = Qt.ItemDataRole.UserRole + 1
    
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
        self.verticalHeader().setVisible(True)
        self.verticalHeader().setDefaultSectionSize(40) # Taller rows for better touch/click targets
        self.setShowGrid(False) # No grid lines for cleaner look
        self.setSortingEnabled(True)
        
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
        header.setSortIndicatorShown(True)
        
        self.setColumnWidth(0, 50)   # #
        self.setColumnWidth(2, 140)  # Voice
        self.setColumnWidth(3, 100)  # Model
        self.setColumnWidth(4, 90)   # Status
        self.setColumnWidth(5, 70)   # Duration
        self.setColumnWidth(6, 70)   # Language
        
        self._voices = []
        self._lines = []
        self._all_lines = []
        self._filter_text = ""
        self._filter_status = None
        self._updating = False
        self._sort_column = -1  # Track current sort column (-1 = no sort)
        self._sort_order = Qt.SortOrder.AscendingOrder
        
        self.cellChanged.connect(self._on_cell_changed)
        self.verticalHeader().sectionMoved.connect(self._on_row_moved)
        self.horizontalHeader().sortIndicatorChanged.connect(self._on_sort_changed)
        
        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
    
    def set_voices(self, voices: list):
        self._voices = voices
    
    def load_lines(self, lines: list):
        self._updating = True
        self._all_lines = lines
        self._apply_filter()
        self._updating = False
    
    def set_filter(self, text: str = "", status: str = None):
        self._filter_text = text.lower()
        self._filter_status = status
        self._apply_filter()
    
    def _apply_filter(self):
        if not self._filter_text and not self._filter_status:
            self._lines = self._all_lines
        else:
            self._lines = []
            for line in self._all_lines:
                if self._filter_text and self._filter_text not in line.text.lower():
                    continue
                if self._filter_status and line.status.value != self._filter_status:
                    continue
                self._lines.append(line)
        
        self.setRowCount(len(self._lines))
        for row, line in enumerate(self._lines):
            self._update_row(row, line)
    
    def _update_row(self, row: int, line: TextLine):
        # Index - store line.id in LineIdRole for all items in this row
        index_item = QTableWidgetItem(str(line.index + 1))
        index_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        index_item.setFlags(index_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        index_item.setData(self.LineIdRole, line.id)
        self.setItem(row, 0, index_item)
        
        # Text
        text_item = QTableWidgetItem(line.text)
        text_item.setToolTip("Double-click to edit text")
        text_item.setFlags(text_item.flags() | Qt.ItemFlag.ItemIsEditable)
        text_item.setData(self.LineIdRole, line.id)
        self.setItem(row, 1, text_item)
        
        # Voice
        voice_item = QTableWidgetItem(line.voice_name or "Default")
        voice_item.setData(Qt.ItemDataRole.UserRole, line.voice_id)
        voice_item.setData(self.LineIdRole, line.id)
        self.setItem(row, 2, voice_item)
        
        # Model
        model_display = self._get_model_display_name(line.model_used)
        model_item = QTableWidgetItem(model_display)
        model_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        model_item.setFlags(model_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        model_item.setData(self.LineIdRole, line.id)
        if line.model_used:
            model_item.setToolTip(f"Model ID: {line.model_used}")
        self.setItem(row, 3, model_item)
        
        # Status - Theme-aware colors with translated text
        status_text = self._get_translated_status(line.status)
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        status_item.setData(self.LineIdRole, line.id)
        
        # Use dynamic theme colors
        c = get_current_theme_colors()
        if line.status == LineStatus.DONE:
            status_item.setForeground(QColor(c['success']))
        elif line.status == LineStatus.ERROR:
            status_item.setForeground(QColor(c['error']))
            status_item.setToolTip(line.error_message or "")
        elif line.status == LineStatus.PROCESSING:
            status_item.setForeground(QColor(c['warning']))
        elif line.status == LineStatus.PENDING:
            status_item.setForeground(QColor(c['fg_secondary']))
            
        self.setItem(row, 4, status_item)
        
        # Duration
        duration_text = f"{line.audio_duration:.1f}s" if line.audio_duration else "-"
        duration_item = QTableWidgetItem(duration_text)
        duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        duration_item.setData(self.LineIdRole, line.id)
        self.setItem(row, 5, duration_item)
        
        # Language
        lang_item = QTableWidgetItem(line.detected_language or "-")
        lang_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        lang_item.setFlags(lang_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        lang_item.setData(self.LineIdRole, line.id)
        self.setItem(row, 6, lang_item)
    
    def _get_model_display_name(self, model_id: str) -> str:
        if not model_id:
            return "-"
        model_names = {
            "eleven_v3": "v3 Alpha",
            "eleven_multilingual_v2": "Multi v2",
            "eleven_turbo_v2_5": "Turbo 2.5",
            "eleven_flash_v2_5": "Flash 2.5",
            "eleven_flash_v2": "Flash v2",
        }
        return model_names.get(model_id, model_id[:10])
    
    def _get_translated_status(self, status: LineStatus) -> str:
        """Get translated status text"""
        status_keys = {
            LineStatus.PENDING: "status_pending",
            LineStatus.PROCESSING: "status_processing",
            LineStatus.DONE: "status_done",
            LineStatus.ERROR: "status_error",
        }
        return tr(status_keys.get(status, "unknown"))
    
    def update_line(self, line: TextLine):
        for row, l in enumerate(self._lines):
            if l.id == line.id:
                self._lines[row] = line
                self._update_row(row, line)
                break
    
    def get_selected_rows(self) -> list:
        return list(set(item.row() for item in self.selectedItems()))
    
    def get_selected_line_ids(self) -> list:
        """Get list of line IDs for selected rows"""
        line_ids = []
        for row in self.get_selected_rows():
            item = self.item(row, 0)
            if item:
                line_id = item.data(self.LineIdRole)
                if line_id:
                    line_ids.append(line_id)
        return line_ids
    
    def get_line_id_at_row(self, row: int) -> str:
        """Get the line ID for a given row"""
        item = self.item(row, 0)
        if item:
            return item.data(self.LineIdRole)
        return None
    
    def _get_line_by_id(self, line_id: str) -> TextLine:
        """Find a line by its ID in _all_lines"""
        for line in self._all_lines:
            if line.id == line_id:
                return line
        return None
    
    def _get_line_index_by_id(self, line_id: str) -> int:
        """Get the index of a line in _all_lines by its ID"""
        for i, line in enumerate(self._all_lines):
            if line.id == line_id:
                return i
        return -1
    
    def get_lines(self) -> list:
        return self._lines
    
    def get_all_lines(self) -> list:
        """Return all lines (unfiltered)"""
        return self._all_lines
    
    def get_line_ids_in_display_order(self) -> list:
        """Get line IDs in the current display order"""
        line_ids = []
        for row in range(self.rowCount()):
            line_id = self.get_line_id_at_row(row)
            if line_id:
                line_ids.append(line_id)
        return line_ids
    
    def _on_cell_changed(self, row: int, column: int):
        if self._updating or column != 1:
            return
        
        item = self.item(row, column)
        if item:
            line_id = item.data(self.LineIdRole)
            if line_id:
                line = self._get_line_by_id(line_id)
                if line:
                    new_text = item.text()
                    if new_text != line.text:
                        line.text = new_text
                        self.text_edited.emit(line_id, new_text)
    
    def _on_row_moved(self, logical_index: int, old_visual: int, new_visual: int):
        if self._updating or old_visual == new_visual:
            return
        
        # Don't allow reorder while sorting is active
        if self._sort_column >= 0:
            return
        
        if old_visual < len(self._lines) and new_visual < len(self._lines):
            line = self._lines.pop(old_visual)
            self._lines.insert(new_visual, line)
            
            for i, ln in enumerate(self._lines):
                ln.index = i
            
            # Update _all_lines order to match
            self._all_lines = self._lines.copy()
            
            self.load_lines(self._all_lines)
            self.lines_reordered.emit(self.get_line_ids_in_display_order())
    
    def _on_sort_changed(self, column: int, order: Qt.SortOrder):
        """Track sort state and disable drag when sorting is active"""
        self._sort_column = column
        self._sort_order = order
        
        # Disable drag-reorder when any sorting is active
        has_sort = column >= 0
        self.setDragEnabled(not has_sort)
        self.verticalHeader().setDragEnabled(not has_sort)
    
    def clear_sort(self):
        """Clear sorting and restore natural order"""
        self._sort_column = -1
        self.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.setDragEnabled(True)
        self.verticalHeader().setDragEnabled(True)
        self.load_lines(self._all_lines)
    
    def dropEvent(self, event):
        if event.source() != self:
            event.ignore()
            return
        
        # Don't allow reorder while sorting is active
        if self._sort_column >= 0:
            event.ignore()
            return
        
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            event.ignore()
            return
        
        source_row = selected_rows[0]
        drop_indicator = self.dropIndicatorPosition()
        target_row = self.indexAt(event.position().toPoint()).row()
        
        if target_row < 0:
            target_row = self.rowCount() - 1
        
        if drop_indicator == QAbstractItemView.DropIndicatorPosition.BelowItem:
            target_row += 1
        
        if source_row == target_row or source_row < 0:
            event.ignore()
            return
        
        if source_row < len(self._lines):
            line = self._lines.pop(source_row)
            if target_row > source_row:
                target_row -= 1
            if target_row > len(self._lines):
                target_row = len(self._lines)
            self._lines.insert(target_row, line)
            
            for i, ln in enumerate(self._lines):
                ln.index = i
            
            # Update _all_lines order to match
            self._all_lines = self._lines.copy()
            
            self.load_lines(self._all_lines)
            self.lines_reordered.emit(self.get_line_ids_in_display_order())
        
        event.accept()
    
    def _show_context_menu(self, position):
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return
        
        # Get line IDs for selected rows
        selected_line_ids = self.get_selected_line_ids()
        if not selected_line_ids:
            return
        
        menu = QMenu(self)
        
        if len(selected_rows) == 1:
            row = selected_rows[0]
            line_id = self.get_line_id_at_row(row)
            line = self._get_line_by_id(line_id) if line_id else None
            if line and line.status == LineStatus.DONE:
                play_action = QAction("▶ " + tr("play_audio"), self)
                play_action.triggered.connect(lambda: self.play_requested.emit(line_id))
                menu.addAction(play_action)
                menu.addSeparator()
        
        # Get failed line IDs
        failed_line_ids = []
        for line_id in selected_line_ids:
            line = self._get_line_by_id(line_id)
            if line and line.status == LineStatus.ERROR:
                failed_line_ids.append(line_id)
        
        if failed_line_ids:
            retry_action = QAction("🔄 " + tr("retry_failed_count", count=len(failed_line_ids)), self)
            retry_action.triggered.connect(lambda: self.retry_requested.emit(failed_line_ids))
            menu.addAction(retry_action)
        
        reset_action = QAction("↺ " + tr("reset_to_pending") + f" ({len(selected_line_ids)})", self)
        reset_action.triggered.connect(lambda: self._reset_to_pending(selected_line_ids))
        menu.addAction(reset_action)
        
        menu.addSeparator()
        
        # Only show move options when sorting is not active
        if len(selected_rows) == 1 and self._sort_column < 0:
            row = selected_rows[0]
            if row > 0:
                move_up_action = QAction("↑ " + tr("move_up"), self)
                move_up_action.triggered.connect(lambda: self._move_row(row, -1))
                menu.addAction(move_up_action)
            if row < self.rowCount() - 1:
                move_down_action = QAction("↓ " + tr("move_down"), self)
                move_down_action.triggered.connect(lambda: self._move_row(row, 1))
                menu.addAction(move_down_action)
            menu.addSeparator()
        
        if len(selected_rows) == 1:
            line_id = selected_line_ids[0]
            split_action = QAction("✂ " + tr("split_line"), self)
            split_action.triggered.connect(lambda: self.split_requested.emit(line_id))
            menu.addAction(split_action)
        
        if len(selected_rows) > 1:
            merge_action = QAction("🔗 " + tr("merge_lines", count=len(selected_line_ids)), self)
            merge_action.triggered.connect(lambda: self.merge_requested.emit(selected_line_ids))
            menu.addAction(merge_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑 " + tr("delete_count", count=len(selected_line_ids)), self)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(selected_line_ids))
        menu.addAction(delete_action)
        
        menu.exec(self.viewport().mapToGlobal(position))
    
    def _reset_to_pending(self, line_ids: list):
        """Reset lines to pending status by their IDs"""
        for line_id in line_ids:
            line = self._get_line_by_id(line_id)
            if line:
                line.status = LineStatus.PENDING
                line.error_message = None
        self.load_lines(self._all_lines)
        self.retry_requested.emit(line_ids)
    
    def _move_row(self, row: int, direction: int):
        """Move a row up or down (only works when sorting is not active)"""
        if self._sort_column >= 0:
            return
        
        new_row = row + direction
        if 0 <= new_row < len(self._lines):
            # Get line IDs for both rows
            source_id = self.get_line_id_at_row(row)
            target_id = self.get_line_id_at_row(new_row)
            
            # Find indices in _all_lines
            source_idx = self._get_line_index_by_id(source_id)
            target_idx = self._get_line_index_by_id(target_id)
            
            if source_idx >= 0 and target_idx >= 0:
                # Swap in _all_lines
                self._all_lines[source_idx], self._all_lines[target_idx] = \
                    self._all_lines[target_idx], self._all_lines[source_idx]
                
                # Update indices
                self._all_lines[source_idx].index = source_idx
                self._all_lines[target_idx].index = target_idx
                
                self.load_lines(self._all_lines)
                self.selectRow(new_row)
                self.lines_reordered.emit(self.get_line_ids_in_display_order())


class VoiceSettingsWidget(QGroupBox):
    """Widget for voice settings (stability, similarity, speed, model)"""
    
    settings_changed = pyqtSignal(object)  # VoiceSettings
    
    def __init__(self, title: str = None, parent=None):
        super().__init__(title or tr("voice_settings"), parent)
        self.setMinimumHeight(280)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12) # Increased spacing
        
        # Model
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
        
        # v3 info label
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
        
        # Stability preset label
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
        
        # Style
        self.style_container = QWidget()
        style_container_layout = QHBoxLayout(self.style_container)
        style_container_layout.setContentsMargins(0, 0, 0, 0)
        self.style_label = QLabel(tr("style") + ":")
        style_container_layout.addWidget(self.style_label)
        self.style_slider = QSlider(Qt.Orientation.Horizontal)
        self.style_slider.setRange(0, 100)
        self.style_slider.setValue(0)
        self.style_slider.setToolTip("Style exaggeration")
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
        
        # Speaker boost
        self.speaker_boost_check = QCheckBox(tr("speaker_boost"))
        self.speaker_boost_check.setChecked(True)
        self.speaker_boost_check.stateChanged.connect(self._on_settings_changed)
        layout.addWidget(self.speaker_boost_check)
        
        self._update_ui_for_model()
    
    def _on_model_changed(self):
        self._update_ui_for_model()
        self._on_settings_changed()
    
    def _update_ui_for_model(self):
        model_id = self.model_combo.currentData()
        is_v3 = model_id == "eleven_v3"
        
        self.v3_info_label.setVisible(is_v3)
        self.stability_preset_label.setVisible(is_v3)
        self.style_container.setVisible(not is_v3)
        
        if is_v3:
            self.stability_slider.setToolTip("v3 Stability: Low=Creative, High=Robust")
            self._update_stability_preset_label()
        else:
            self.stability_slider.setToolTip("Controls voice stability")
    
    def _update_stability_preset_label(self):
        value = self.stability_slider.value() / 100
        if value < 0.3:
            preset = "Creative"
        elif value < 0.7:
            preset = "Natural"
        else:
            preset = "Robust"
        self.stability_preset_label.setText(f"Mode: {preset}")
    
    def _on_settings_changed(self):
        self.stability_value.setText(f"{self.stability_slider.value() / 100:.2f}")
        self.similarity_value.setText(f"{self.similarity_slider.value() / 100:.2f}")
        self.style_value.setText(f"{self.style_slider.value() / 100:.2f}")
        
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
        
        self._update_ui_for_model()


class ProgressWidget(QWidget):
    """Widget for displaying processing progress"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12) # Sleek bar
        layout.addWidget(self.progress_bar)
        
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
        
        self.time_label.setText(f"{tr('elapsed')}: {self._format_time(elapsed_seconds)}")
        
        if status:
            self.status_label.setText(status)
    
    def _format_time(self, seconds: float) -> str:
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
        layout.setSpacing(5)
        
        self.credit_label = QLabel(f"{tr('credits')}: -")
        layout.addWidget(self.credit_label)
        
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(20, 20) # Smaller button
        self.refresh_btn.setStyleSheet("padding: 0px;")
        layout.addWidget(self.refresh_btn)
    
    def update_credits(self, total: int, warning_threshold: int = 1000):
        self.credit_label.setText(f"{tr('credits')}: {total:,}")
        
        c = get_current_theme_colors()
        if total < warning_threshold:
            self.credit_label.setStyleSheet(f"color: {c['error']}; font-weight: bold;")
        else:
            self.credit_label.setStyleSheet("")


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
        layout.setSpacing(10)
        
        # Thread count display
        self.count_label = QLabel(tr("active_threads", active=0, total=0))
        layout.addWidget(self.count_label)
        
        # Thread indicators (horizontal layout)
        self._thread_layout = QHBoxLayout()
        self._thread_layout.setSpacing(4)
        c = get_current_theme_colors()
        for i in range(max_threads):
            label = QLabel("○")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedSize(16, 16)
            label.setToolTip(f"Thread {i + 1}: Idle")
            label.setStyleSheet(f"color: {c['fg_tertiary']}; font-size: 14px;")
            self._thread_labels.append(label)
            self._thread_layout.addWidget(label)
        self._thread_layout.addStretch()
        layout.addLayout(self._thread_layout)
    
    def update_status(self, active_count: int, total_threads: int, thread_info: dict = None):
        """Update thread status display"""
        self.count_label.setText(tr("active_threads", active=active_count, total=total_threads))
        
        # Get theme colors
        c = get_current_theme_colors()
        
        # Update indicators
        for i, label in enumerate(self._thread_labels):
            if i < total_threads:
                if thread_info and i in thread_info:
                    label.setText("●")
                    label.setStyleSheet(f"color: {c['success']}; font-size: 14px;")
                    label.setToolTip(f"Thread {i + 1}: {thread_info[i]}")
                elif i < active_count:
                    label.setText("●")
                    label.setStyleSheet(f"color: {c['accent_primary']}; font-size: 14px;")
                    label.setToolTip(f"Thread {i + 1}: Working")
                else:
                    label.setText("○")
                    label.setStyleSheet(f"color: {c['fg_tertiary']}; font-size: 14px;")
                    label.setToolTip(f"Thread {i + 1}: Idle")
                label.setVisible(True)
            else:
                label.setVisible(False)
    
    def reset(self):
        """Reset all thread indicators"""
        c = get_current_theme_colors()
        for label in self._thread_labels:
            label.setText("○")
            label.setStyleSheet(f"color: {c['fg_tertiary']}; font-size: 14px;")
            label.setToolTip("Idle")
