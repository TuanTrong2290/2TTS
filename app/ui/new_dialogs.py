"""New dialogs for enhanced 2TTS features"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox,
    QTabWidget, QWidget, QMessageBox, QFileDialog, QTextEdit,
    QAbstractItemView, QFormLayout, QDialogButtonBox, QSlider,
    QProgressBar, QListWidget, QListWidgetItem, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Optional, Dict

from services.preset_manager import get_preset_manager, VoicePreset, ProjectTemplate
from services.voice_matcher import get_voice_matcher, VoicePattern
from services.audio_processor import AudioProcessingSettings
from services.analytics import get_analytics
from core.models import Voice, VoiceSettings


class PresetManagerDialog(QDialog):
    """Dialog for managing voice presets and project templates"""
    
    preset_selected = pyqtSignal(object)  # VoicePreset
    
    def __init__(self, voices: List[Voice], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preset Manager")
        self.setMinimumSize(700, 500)
        
        self._preset_manager = get_preset_manager()
        self._voices = voices
        
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        
        # Voice Presets Tab
        presets_tab = QWidget()
        presets_layout = QVBoxLayout(presets_tab)
        
        self.presets_table = QTableWidget()
        self.presets_table.setColumnCount(4)
        self.presets_table.setHorizontalHeaderLabels(["Name", "Voice", "Model", "Description"])
        self.presets_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.presets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        presets_layout.addWidget(self.presets_table)
        
        preset_btn_layout = QHBoxLayout()
        
        add_preset_btn = QPushButton("Create Preset")
        add_preset_btn.clicked.connect(self._add_preset)
        preset_btn_layout.addWidget(add_preset_btn)
        
        apply_preset_btn = QPushButton("Apply")
        apply_preset_btn.setObjectName("primaryButton")
        apply_preset_btn.clicked.connect(self._apply_preset)
        preset_btn_layout.addWidget(apply_preset_btn)
        
        delete_preset_btn = QPushButton("Delete")
        delete_preset_btn.setObjectName("dangerButton")
        delete_preset_btn.clicked.connect(self._delete_preset)
        preset_btn_layout.addWidget(delete_preset_btn)
        
        preset_btn_layout.addStretch()
        
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_presets)
        preset_btn_layout.addWidget(export_btn)
        
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self._import_presets)
        preset_btn_layout.addWidget(import_btn)
        
        presets_layout.addLayout(preset_btn_layout)
        tabs.addTab(presets_tab, "Voice Presets")
        
        # Templates Tab
        templates_tab = QWidget()
        templates_layout = QVBoxLayout(templates_tab)
        
        self.templates_table = QTableWidget()
        self.templates_table.setColumnCount(3)
        self.templates_table.setHorizontalHeaderLabels(["Name", "Threads", "Description"])
        self.templates_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.templates_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        templates_layout.addWidget(self.templates_table)
        
        template_btn_layout = QHBoxLayout()
        
        add_template_btn = QPushButton("Create Template")
        add_template_btn.clicked.connect(self._add_template)
        template_btn_layout.addWidget(add_template_btn)
        
        delete_template_btn = QPushButton("Delete")
        delete_template_btn.setObjectName("dangerButton")
        delete_template_btn.clicked.connect(self._delete_template)
        template_btn_layout.addWidget(delete_template_btn)
        
        template_btn_layout.addStretch()
        templates_layout.addLayout(template_btn_layout)
        
        tabs.addTab(templates_tab, "Project Templates")
        
        layout.addWidget(tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self._refresh_tables()
    
    def _refresh_tables(self):
        # Presets
        presets = self._preset_manager.voice_presets
        self.presets_table.setRowCount(len(presets))
        for row, preset in enumerate(presets):
            self.presets_table.setItem(row, 0, QTableWidgetItem(preset.name))
            self.presets_table.setItem(row, 1, QTableWidgetItem(preset.voice_name))
            self.presets_table.setItem(row, 2, QTableWidgetItem(preset.settings.model.value))
            self.presets_table.setItem(row, 3, QTableWidgetItem(preset.description))
        
        # Templates
        templates = self._preset_manager.project_templates
        self.templates_table.setRowCount(len(templates))
        for row, template in enumerate(templates):
            self.templates_table.setItem(row, 0, QTableWidgetItem(template.name))
            self.templates_table.setItem(row, 1, QTableWidgetItem(str(template.settings.thread_count)))
            self.templates_table.setItem(row, 2, QTableWidgetItem(template.description))
    
    def _add_preset(self):
        dialog = CreatePresetDialog(self._voices, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            preset = dialog.get_preset()
            self._preset_manager.add_voice_preset(preset)
            self._refresh_tables()
    
    def _apply_preset(self):
        rows = set(item.row() for item in self.presets_table.selectedItems())
        if rows:
            preset = self._preset_manager.voice_presets[list(rows)[0]]
            self.preset_selected.emit(preset)
    
    def _delete_preset(self):
        rows = set(item.row() for item in self.presets_table.selectedItems())
        for row in sorted(rows, reverse=True):
            preset = self._preset_manager.voice_presets[row]
            self._preset_manager.delete_voice_preset(preset.id)
        self._refresh_tables()
    
    def _add_template(self):
        QMessageBox.information(self, "Info", "Save current project settings as template from File menu")
    
    def _delete_template(self):
        rows = set(item.row() for item in self.templates_table.selectedItems())
        for row in sorted(rows, reverse=True):
            template = self._preset_manager.project_templates[row]
            self._preset_manager.delete_project_template(template.id)
        self._refresh_tables()
    
    def _export_presets(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Presets", "voice_presets.json", "JSON Files (*.json)"
        )
        if file_path:
            if self._preset_manager.export_presets(file_path):
                QMessageBox.information(self, "Success", "Presets exported")
            else:
                QMessageBox.critical(self, "Error", "Export failed")
    
    def _import_presets(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Presets", "", "JSON Files (*.json)"
        )
        if file_path:
            imported, skipped = self._preset_manager.import_presets(file_path)
            QMessageBox.information(self, "Import", f"Imported: {imported}, Skipped: {skipped}")
            self._refresh_tables()


class CreatePresetDialog(QDialog):
    """Dialog for creating a new voice preset"""
    
    def __init__(self, voices: List[Voice], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Voice Preset")
        self.setMinimumWidth(400)
        
        self._voices = voices
        
        layout = QFormLayout(self)
        
        self.name_edit = QLineEdit()
        layout.addRow("Preset Name:", self.name_edit)
        
        self.voice_combo = QComboBox()
        for voice in voices:
            self.voice_combo.addItem(voice.name, voice.voice_id)
        layout.addRow("Voice:", self.voice_combo)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        layout.addRow("Description:", self.description_edit)
        
        # Settings
        self.stability_slider = QSlider(Qt.Orientation.Horizontal)
        self.stability_slider.setRange(0, 100)
        self.stability_slider.setValue(50)
        layout.addRow("Stability:", self.stability_slider)
        
        self.similarity_slider = QSlider(Qt.Orientation.Horizontal)
        self.similarity_slider.setRange(0, 100)
        self.similarity_slider.setValue(75)
        layout.addRow("Similarity:", self.similarity_slider)
        
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 2.0)
        self.speed_spin.setValue(1.0)
        layout.addRow("Speed:", self.speed_spin)
        
        self.model_combo = QComboBox()
        self.model_combo.addItem("Turbo v2.5", "eleven_turbo_v2_5")
        self.model_combo.addItem("Multilingual v2", "eleven_multilingual_v2")
        self.model_combo.addItem("Flash v2.5", "eleven_flash_v2_5")
        layout.addRow("Model:", self.model_combo)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_preset(self) -> VoicePreset:
        import uuid
        from core.models import TTSModel
        
        voice_id = self.voice_combo.currentData()
        voice_name = self.voice_combo.currentText()
        
        settings = VoiceSettings(
            stability=self.stability_slider.value() / 100,
            similarity_boost=self.similarity_slider.value() / 100,
            speed=self.speed_spin.value(),
            model=TTSModel(self.model_combo.currentData())
        )
        
        return VoicePreset(
            id=str(uuid.uuid4()),
            name=self.name_edit.text(),
            voice_id=voice_id,
            voice_name=voice_name,
            settings=settings,
            description=self.description_edit.toPlainText()
        )


class VoiceAssignmentDialog(QDialog):
    """Dialog for batch voice assignment"""
    
    assignments_changed = pyqtSignal(dict)  # speaker -> (voice_id, voice_name)
    
    def __init__(self, lines: list, voices: List[Voice], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice Assignment")
        self.setMinimumSize(700, 500)
        
        self._lines = lines
        self._voices = voices
        self._matcher = get_voice_matcher()
        
        layout = QVBoxLayout(self)
        
        # Detected speakers
        speakers_group = QGroupBox("Detected Speakers")
        speakers_layout = QVBoxLayout(speakers_group)
        
        self.speakers_table = QTableWidget()
        self.speakers_table.setColumnCount(3)
        self.speakers_table.setHorizontalHeaderLabels(["Speaker", "Count", "Assigned Voice"])
        self.speakers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        speakers_layout.addWidget(self.speakers_table)
        
        # Auto-assign buttons
        auto_layout = QHBoxLayout()
        
        round_robin_btn = QPushButton("Auto-Assign (Round Robin)")
        round_robin_btn.clicked.connect(lambda: self._auto_assign("round_robin"))
        auto_layout.addWidget(round_robin_btn)
        
        by_name_btn = QPushButton("Auto-Assign (By Name)")
        by_name_btn.clicked.connect(lambda: self._auto_assign("by_name"))
        auto_layout.addWidget(by_name_btn)
        
        auto_layout.addStretch()
        speakers_layout.addLayout(auto_layout)
        
        layout.addWidget(speakers_group)
        
        # Manual assignment
        manual_group = QGroupBox("Manual Assignment")
        manual_layout = QHBoxLayout(manual_group)
        
        manual_layout.addWidget(QLabel("Assign:"))
        self.voice_combo = QComboBox()
        for voice in voices:
            self.voice_combo.addItem(voice.name, voice.voice_id)
        manual_layout.addWidget(self.voice_combo)
        
        assign_btn = QPushButton("Assign to Selected")
        assign_btn.clicked.connect(self._assign_voice)
        manual_layout.addWidget(assign_btn)
        
        manual_layout.addStretch()
        layout.addWidget(manual_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("primaryButton")
        apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self._detect_speakers()
    
    def _detect_speakers(self):
        speakers = self._matcher.extract_speakers(self._lines)
        self._speakers = speakers
        
        self.speakers_table.setRowCount(len(speakers))
        for row, (speaker, count) in enumerate(speakers.items()):
            self.speakers_table.setItem(row, 0, QTableWidgetItem(speaker))
            self.speakers_table.setItem(row, 1, QTableWidgetItem(str(count)))
            
            voice_info = self._matcher.get_speaker_voice(speaker)
            voice_name = voice_info[1] if voice_info else "Not assigned"
            self.speakers_table.setItem(row, 2, QTableWidgetItem(voice_name))
    
    def _auto_assign(self, strategy: str):
        assignments = self._matcher.auto_assign_speakers(self._lines, self._voices, strategy)
        self._detect_speakers()  # Refresh table
    
    def _assign_voice(self):
        rows = set(item.row() for item in self.speakers_table.selectedItems())
        if not rows:
            return
        
        voice_id = self.voice_combo.currentData()
        voice_name = self.voice_combo.currentText()
        
        speakers = list(self._speakers.keys())
        for row in rows:
            speaker = speakers[row]
            self._matcher.set_speaker_voice(speaker, voice_id, voice_name)
        
        self._detect_speakers()
    
    def _apply(self):
        # Get all assignments
        assignments = {}
        for speaker in self._speakers.keys():
            voice_info = self._matcher.get_speaker_voice(speaker)
            if voice_info:
                assignments[speaker] = voice_info
        
        self.assignments_changed.emit(assignments)
        self.accept()


class AudioProcessingDialog(QDialog):
    """Dialog for audio post-processing settings"""
    
    settings_changed = pyqtSignal(object)  # AudioProcessingSettings
    
    def __init__(self, settings: Optional[AudioProcessingSettings] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Audio Post-Processing")
        self.setMinimumWidth(400)
        
        if settings is None:
            settings = AudioProcessingSettings()
        
        layout = QVBoxLayout(self)
        
        # Normalize
        norm_group = QGroupBox("Normalization")
        norm_layout = QFormLayout(norm_group)
        
        self.normalize_check = QCheckBox()
        self.normalize_check.setChecked(settings.normalize)
        norm_layout.addRow("Enable:", self.normalize_check)
        
        self.normalize_level = QDoubleSpinBox()
        self.normalize_level.setRange(-20, 0)
        self.normalize_level.setValue(settings.normalize_level)
        self.normalize_level.setSuffix(" dB")
        norm_layout.addRow("Level:", self.normalize_level)
        
        layout.addWidget(norm_group)
        
        # Fade
        fade_group = QGroupBox("Fade Effects")
        fade_layout = QFormLayout(fade_group)
        
        self.fade_in_spin = QDoubleSpinBox()
        self.fade_in_spin.setRange(0, 5)
        self.fade_in_spin.setValue(settings.fade_in)
        self.fade_in_spin.setSuffix(" s")
        fade_layout.addRow("Fade In:", self.fade_in_spin)
        
        self.fade_out_spin = QDoubleSpinBox()
        self.fade_out_spin.setRange(0, 5)
        self.fade_out_spin.setValue(settings.fade_out)
        self.fade_out_spin.setSuffix(" s")
        fade_layout.addRow("Fade Out:", self.fade_out_spin)
        
        layout.addWidget(fade_group)
        
        # Padding
        padding_group = QGroupBox("Silence Padding")
        padding_layout = QFormLayout(padding_group)
        
        self.padding_start_spin = QDoubleSpinBox()
        self.padding_start_spin.setRange(0, 10)
        self.padding_start_spin.setValue(settings.silence_padding_start)
        self.padding_start_spin.setSuffix(" s")
        padding_layout.addRow("Start:", self.padding_start_spin)
        
        self.padding_end_spin = QDoubleSpinBox()
        self.padding_end_spin.setRange(0, 10)
        self.padding_end_spin.setValue(settings.silence_padding_end)
        self.padding_end_spin.setSuffix(" s")
        padding_layout.addRow("End:", self.padding_end_spin)
        
        layout.addWidget(padding_group)
        
        # Trim
        trim_group = QGroupBox("Silence Trimming")
        trim_layout = QFormLayout(trim_group)
        
        self.trim_check = QCheckBox()
        self.trim_check.setChecked(settings.trim_silence)
        trim_layout.addRow("Enable:", self.trim_check)
        
        self.trim_threshold = QDoubleSpinBox()
        self.trim_threshold.setRange(-60, -20)
        self.trim_threshold.setValue(settings.trim_threshold)
        self.trim_threshold.setSuffix(" dB")
        trim_layout.addRow("Threshold:", self.trim_threshold)
        
        layout.addWidget(trim_group)
        
        # Speed
        speed_group = QGroupBox("Speed & Pitch")
        speed_layout = QFormLayout(speed_group)
        
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 2.0)
        self.speed_spin.setValue(settings.speed)
        self.speed_spin.setSingleStep(0.1)
        speed_layout.addRow("Speed:", self.speed_spin)
        
        layout.addWidget(speed_group)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _apply(self):
        settings = AudioProcessingSettings(
            normalize=self.normalize_check.isChecked(),
            normalize_level=self.normalize_level.value(),
            fade_in=self.fade_in_spin.value(),
            fade_out=self.fade_out_spin.value(),
            silence_padding_start=self.padding_start_spin.value(),
            silence_padding_end=self.padding_end_spin.value(),
            trim_silence=self.trim_check.isChecked(),
            trim_threshold=self.trim_threshold.value(),
            speed=self.speed_spin.value()
        )
        self.settings_changed.emit(settings)
        self.accept()


class AnalyticsDialog(QDialog):
    """Dialog for viewing usage analytics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Usage Analytics")
        self.setMinimumSize(500, 400)
        
        self._analytics = get_analytics()
        
        layout = QVBoxLayout(self)
        
        # Enable toggle
        enable_layout = QHBoxLayout()
        enable_layout.addWidget(QLabel("Analytics Tracking:"))
        self.enable_check = QCheckBox("Enabled (local only)")
        self.enable_check.setChecked(self._analytics.is_enabled)
        self.enable_check.toggled.connect(self._toggle_analytics)
        enable_layout.addWidget(self.enable_check)
        enable_layout.addStretch()
        layout.addLayout(enable_layout)
        
        # Stats display
        stats_group = QGroupBox("Usage Summary")
        stats_layout = QFormLayout(stats_group)
        
        summary = self._analytics.get_usage_summary()
        
        stats_layout.addRow("Total Characters:", QLabel(f"{summary.get('total_characters', 0):,}"))
        stats_layout.addRow("Total Lines:", QLabel(f"{summary.get('total_lines', 0):,}"))
        stats_layout.addRow("Total Sessions:", QLabel(f"{summary.get('total_sessions', 0):,}"))
        stats_layout.addRow("Processing Time:", QLabel(f"{summary.get('total_processing_hours', 0):.1f} hours"))
        stats_layout.addRow("Days Active:", QLabel(str(summary.get('days_active', 0))))
        stats_layout.addRow("Avg Chars/Day:", QLabel(f"{summary.get('avg_chars_per_day', 0):,}"))
        
        layout.addWidget(stats_group)
        
        # Top voices
        voices_group = QGroupBox("Top Voices")
        voices_layout = QVBoxLayout(voices_group)
        
        top_voices = summary.get('top_voices', [])
        for voice_id, count in top_voices:
            voices_layout.addWidget(QLabel(f"{voice_id[:12]}...: {count} uses"))
        
        if not top_voices:
            voices_layout.addWidget(QLabel("No data yet"))
        
        layout.addWidget(voices_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export Stats")
        export_btn.clicked.connect(self._export)
        btn_layout.addWidget(export_btn)
        
        clear_btn = QPushButton("Clear Data")
        clear_btn.setObjectName("dangerButton")
        clear_btn.clicked.connect(self._clear)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _toggle_analytics(self, enabled: bool):
        if enabled:
            self._analytics.enable()
        else:
            self._analytics.disable()
    
    def _export(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Stats", "2tts_analytics.json", "JSON Files (*.json)"
        )
        if file_path:
            if self._analytics.export_stats(file_path):
                QMessageBox.information(self, "Success", "Statistics exported")
            else:
                QMessageBox.critical(self, "Error", "Export failed")
    
    def _clear(self):
        reply = QMessageBox.question(
            self, "Confirm",
            "Clear all analytics data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._analytics.clear_data()
            self.accept()
