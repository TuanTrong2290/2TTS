"""Dialogs for 2TTS application"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QTabWidget,
    QWidget, QMessageBox, QFileDialog, QAbstractItemView,
    QFormLayout, QDialogButtonBox, QScrollArea, QApplication, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Optional

from core.models import APIKey, Proxy, ProxyType, Voice, VoiceSettings
from services.localization import tr, get_localization
from ui.workers import (
    ValidateKeysWorker, TestProxiesWorker, FetchVoiceWorker,
    SearchVoiceLibraryWorker, VoicePreviewWorker, CloneVoiceWorker
)


class APIKeyDialog(QDialog):
    """Dialog for managing API keys"""
    
    keys_updated = pyqtSignal(list)
    
    def __init__(self, keys: List[APIKey], parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Manager")
        self.setMinimumSize(700, 400)
        
        self._keys = [APIKey.from_dict(k.to_dict()) for k in keys]  # Deep copy
        
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Name", "API Key", "Credits", "Limit", "Status", "Proxy"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Key")
        add_btn.clicked.connect(self._add_key)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._remove_key)
        btn_layout.addWidget(remove_btn)
        
        validate_btn = QPushButton("Validate All")
        validate_btn.clicked.connect(self._validate_all)
        btn_layout.addWidget(validate_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self._refresh_table()
    
    def _refresh_table(self):
        self.table.setRowCount(len(self._keys))
        for row, key in enumerate(self._keys):
            self.table.setItem(row, 0, QTableWidgetItem(key.name))
            
            masked_key = key.key[:8] + "..." + key.key[-4:] if len(key.key) > 12 else key.key
            self.table.setItem(row, 1, QTableWidgetItem(masked_key))
            
            self.table.setItem(row, 2, QTableWidgetItem(f"{key.remaining_credits:,}"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{key.character_limit:,}"))
            
            status = "Valid" if key.is_valid else "Not validated"
            self.table.setItem(row, 4, QTableWidgetItem(status))
            
            proxy = key.assigned_proxy_id[:8] + "..." if key.assigned_proxy_id else "None"
            self.table.setItem(row, 5, QTableWidgetItem(proxy))
    
    def _add_key(self):
        dialog = AddAPIKeyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            key = dialog.get_key()
            self._keys.append(key)
            self._refresh_table()
    
    def _remove_key(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if not rows:
            return
        
        for row in sorted(rows, reverse=True):
            del self._keys[row]
        self._refresh_table()
    
    def _validate_all(self):
        if not self._keys:
            QMessageBox.information(self, "Validation", "No keys to validate")
            return
        
        # Create progress dialog
        self._progress_dialog = QProgressDialog(
            "Validating API keys...", "Cancel", 0, len(self._keys), self
        )
        self._progress_dialog.setWindowTitle("Validating")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setMinimumDuration(0)
        
        # Create and start worker
        self._validate_worker = ValidateKeysWorker(self._keys, self)
        self._validate_worker.progress.connect(self._on_validate_progress)
        self._validate_worker.finished.connect(self._on_validate_finished)
        self._progress_dialog.canceled.connect(self._validate_worker.cancel)
        self._validate_worker.start()
    
    def _on_validate_progress(self, current: int, total: int, message: str):
        if hasattr(self, '_progress_dialog') and self._progress_dialog:
            self._progress_dialog.setValue(current)
            self._progress_dialog.setLabelText(message)
    
    def _on_validate_finished(self, validated_count: int, total_count: int):
        if hasattr(self, '_progress_dialog') and self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None
        
        self._refresh_table()
        QMessageBox.information(self, "Validation", f"Validated {validated_count}/{total_count} keys")
    
    def _save(self):
        self.keys_updated.emit(self._keys)
        self.accept()


class AddAPIKeyDialog(QDialog):
    """Dialog for adding a new API key"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add API Key")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("sk_...")
        layout.addRow("API Key:", self.key_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_key(self) -> APIKey:
        key = self.key_edit.text().strip()
        name = key[:8] + "..." if len(key) > 8 else key
        return APIKey(name=name, key=key)


class ProxyDialog(QDialog):
    """Dialog for managing proxies"""
    
    proxies_updated = pyqtSignal(list)
    
    def __init__(self, proxies: List[Proxy], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Proxy Manager")
        self.setMinimumSize(600, 400)
        
        self._proxies = [Proxy.from_dict(p.to_dict()) for p in proxies]
        
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Host", "Port", "Type", "Auth", "Status"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Proxy")
        add_btn.clicked.connect(self._add_proxy)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._remove_proxy)
        btn_layout.addWidget(remove_btn)
        
        test_btn = QPushButton("Test All")
        test_btn.clicked.connect(self._test_all)
        btn_layout.addWidget(test_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        self._refresh_table()
    
    def _refresh_table(self):
        self.table.setRowCount(len(self._proxies))
        for row, proxy in enumerate(self._proxies):
            self.table.setItem(row, 0, QTableWidgetItem(proxy.host))
            self.table.setItem(row, 1, QTableWidgetItem(str(proxy.port)))
            self.table.setItem(row, 2, QTableWidgetItem(proxy.proxy_type.value))
            
            auth = "Yes" if proxy.username else "No"
            self.table.setItem(row, 3, QTableWidgetItem(auth))
            
            status = "Healthy" if proxy.is_healthy else "Down"
            self.table.setItem(row, 4, QTableWidgetItem(status))
    
    def _add_proxy(self):
        dialog = AddProxyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            proxy = dialog.get_proxy()
            self._proxies.append(proxy)
            self._refresh_table()
    
    def _remove_proxy(self):
        rows = set(item.row() for item in self.table.selectedItems())
        for row in sorted(rows, reverse=True):
            del self._proxies[row]
        self._refresh_table()
    
    def _test_all(self):
        if not self._proxies:
            QMessageBox.information(self, "Test", "No proxies to test")
            return
        
        # Create progress dialog
        self._progress_dialog = QProgressDialog(
            "Testing proxies...", "Cancel", 0, len(self._proxies), self
        )
        self._progress_dialog.setWindowTitle("Testing")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setMinimumDuration(0)
        
        # Create and start worker
        self._test_worker = TestProxiesWorker(self._proxies, self)
        self._test_worker.progress.connect(self._on_test_progress)
        self._test_worker.finished.connect(self._on_test_finished)
        self._progress_dialog.canceled.connect(self._test_worker.cancel)
        self._test_worker.start()
    
    def _on_test_progress(self, current: int, total: int, message: str):
        if hasattr(self, '_progress_dialog') and self._progress_dialog:
            self._progress_dialog.setValue(current)
            self._progress_dialog.setLabelText(message)
    
    def _on_test_finished(self, healthy_count: int, total_count: int):
        if hasattr(self, '_progress_dialog') and self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None
        
        self._refresh_table()
        QMessageBox.information(self, "Test", f"Proxy test complete: {healthy_count}/{total_count} healthy")
    
    def _save(self):
        self.proxies_updated.emit(self._proxies)
        self.accept()


class AddProxyDialog(QDialog):
    """Dialog for adding a new proxy"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Proxy")
        self.setMinimumWidth(350)
        
        layout = QFormLayout(self)
        
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("proxy.example.com")
        layout.addRow("Host:", self.host_edit)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(8080)
        layout.addRow("Port:", self.port_spin)
        
        self.type_combo = QComboBox()
        self.type_combo.addItem("HTTP", ProxyType.HTTP)
        self.type_combo.addItem("SOCKS5", ProxyType.SOCKS5)
        layout.addRow("Type:", self.type_combo)
        
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Optional")
        layout.addRow("Username:", self.username_edit)
        
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Optional")
        layout.addRow("Password:", self.password_edit)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_proxy(self) -> Proxy:
        return Proxy(
            host=self.host_edit.text(),
            port=self.port_spin.value(),
            proxy_type=self.type_combo.currentData(),
            username=self.username_edit.text() or None,
            password=self.password_edit.text() or None
        )


class AddVoiceByIdDialog(QDialog):
    """Dialog for adding a voice by ID from ElevenLabs Voice Library"""
    
    voice_added = pyqtSignal(object)  # Voice
    
    def __init__(self, api_key, proxy=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Voice by ID")
        self.setMinimumWidth(500)
        
        self._api_key = api_key
        self._proxy = proxy
        self._fetched_voice = None
        
        layout = QVBoxLayout(self)
        
        # Instructions
        info_label = QLabel(
            "Enter a Voice ID from the ElevenLabs Voice Library.\n"
            "You can find Voice IDs on elevenlabs.io/voice-library"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Voice ID input
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("Voice ID:"))
        self.voice_id_edit = QLineEdit()
        self.voice_id_edit.setPlaceholderText("e.g., 21m00Tcm4TlvDq8ikWAM")
        id_layout.addWidget(self.voice_id_edit)
        
        self.fetch_btn = QPushButton("Fetch")
        self.fetch_btn.clicked.connect(self._fetch_voice)
        id_layout.addWidget(self.fetch_btn)
        layout.addLayout(id_layout)
        
        # Voice info display
        self.info_group = QGroupBox("Voice Info")
        info_layout = QFormLayout(self.info_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Voice name will appear here")
        info_layout.addRow("Name:", self.name_edit)
        
        self.category_label = QLabel("-")
        info_layout.addRow("Category:", self.category_label)
        
        self.id_label = QLabel("-")
        info_layout.addRow("Voice ID:", self.id_label)
        
        self.status_label = QLabel("")
        info_layout.addRow("Status:", self.status_label)
        
        layout.addWidget(self.info_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.add_btn = QPushButton("Add Voice")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self._add_voice)
        btn_layout.addWidget(self.add_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _fetch_voice(self):
        voice_id = self.voice_id_edit.text().strip()
        if not voice_id:
            QMessageBox.warning(self, "Warning", "Please enter a Voice ID")
            return
        
        self.status_label.setText("Fetching...")
        self.status_label.setStyleSheet("")
        self.fetch_btn.setEnabled(False)
        
        # Create and start worker
        self._fetch_worker = FetchVoiceWorker(voice_id, self._api_key, self._proxy, self)
        self._fetch_worker.finished.connect(self._on_fetch_finished)
        self._fetch_worker.error.connect(self._on_fetch_error)
        self._fetch_worker.start()
    
    def _on_fetch_finished(self, voice, message: str):
        self.fetch_btn.setEnabled(True)
        voice_id = self.voice_id_edit.text().strip()
        
        if voice:
            self._fetched_voice = voice
            self.category_label.setText(voice.category or "N/A")
            self.id_label.setText(voice.voice_id)
            
            # Check if it's a placeholder voice (name contains the ID)
            if "Library Voice" in voice.name and voice_id[:8] in voice.name:
                self.name_edit.setText("")
                self.name_edit.setPlaceholderText("Enter a name for this voice")
                self.status_label.setText("Voice ID valid - enter a name and add")
                self.status_label.setStyleSheet("color: orange;")
            else:
                self.name_edit.setText(voice.name)
                self.status_label.setText("Found!")
                self.status_label.setStyleSheet("color: green;")
            self.add_btn.setEnabled(True)
        else:
            self._fetched_voice = None
            self.name_edit.setText("")
            self.name_edit.setPlaceholderText("Voice name will appear here")
            self.category_label.setText("-")
            self.id_label.setText("-")
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: red;")
            self.add_btn.setEnabled(False)
    
    def _on_fetch_error(self, error: str):
        self.fetch_btn.setEnabled(True)
        self._fetched_voice = None
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("color: red;")
        self.add_btn.setEnabled(False)
    
    def _add_voice(self):
        if self._fetched_voice:
            # Use custom name if provided
            custom_name = self.name_edit.text().strip()
            if custom_name:
                self._fetched_voice.name = custom_name
            elif "Library Voice" in self._fetched_voice.name:
                # Generate a default name if user didn't provide one
                self._fetched_voice.name = f"Voice {self._fetched_voice.voice_id[:8]}"
            
            self.voice_added.emit(self._fetched_voice)
            self.accept()


class VoiceLibraryDialog(QDialog):
    """Dialog for voice library management"""
    
    voice_selected = pyqtSignal(object)  # Voice
    voice_added_by_id = pyqtSignal(object)  # Voice - for adding to main voice list
    
    def __init__(self, voices: List[Voice], library: List[Voice], api_key=None, proxy=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Voice Library")
        self.setMinimumSize(650, 550)
        
        self._all_voices = voices
        self._library = library
        self._api_key = api_key
        self._proxy = proxy
        
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        
        # All voices tab
        all_tab = QWidget()
        all_layout = QVBoxLayout(all_tab)
        
        self.all_table = QTableWidget()
        self.all_table.setColumnCount(4)
        self.all_table.setHorizontalHeaderLabels(["Name", "Category", "Clone", "Voice ID"])
        self.all_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.all_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.all_table.doubleClicked.connect(self._select_voice)
        all_layout.addWidget(self.all_table)
        
        all_btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add to Library")
        add_btn.clicked.connect(self._add_to_library)
        all_btn_layout.addWidget(add_btn)
        
        add_default_btn = QPushButton("Set as Default")
        add_default_btn.setToolTip("Add selected voice to default voice list and select it")
        add_default_btn.clicked.connect(self._set_as_default_voice)
        all_btn_layout.addWidget(add_default_btn)
        
        add_by_id_btn = QPushButton("+ Add Voice by ID")
        add_by_id_btn.clicked.connect(self._add_voice_by_id)
        all_btn_layout.addWidget(add_by_id_btn)
        
        clone_voice_btn = QPushButton("🎤 Clone Voice")
        clone_voice_btn.setToolTip("Create a voice clone from audio samples")
        clone_voice_btn.clicked.connect(self._clone_voice)
        all_btn_layout.addWidget(clone_voice_btn)
        
        browse_lib_btn = QPushButton("Browse ElevenLabs Library")
        browse_lib_btn.setObjectName("primaryButton")
        browse_lib_btn.setToolTip("Browse and search the public ElevenLabs voice library")
        browse_lib_btn.clicked.connect(self._browse_voice_library)
        all_btn_layout.addWidget(browse_lib_btn)
        all_btn_layout.addStretch()
        all_layout.addLayout(all_btn_layout)
        
        tabs.addTab(all_tab, "All Voices")
        
        # Library tab
        lib_tab = QWidget()
        lib_layout = QVBoxLayout(lib_tab)
        
        self.lib_table = QTableWidget()
        self.lib_table.setColumnCount(4)
        self.lib_table.setHorizontalHeaderLabels(["Name", "Category", "Clone", "Voice ID"])
        self.lib_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.lib_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.lib_table.doubleClicked.connect(self._select_library_voice)
        lib_layout.addWidget(self.lib_table)
        
        lib_btn_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove from Library")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self._remove_from_library)
        lib_btn_layout.addWidget(remove_btn)
        
        lib_default_btn = QPushButton("Set as Default")
        lib_default_btn.setToolTip("Add selected voice to default voice list and select it")
        lib_default_btn.clicked.connect(self._set_library_voice_as_default)
        lib_btn_layout.addWidget(lib_default_btn)
        
        lib_btn_layout.addStretch()
        lib_layout.addLayout(lib_btn_layout)
        
        tabs.addTab(lib_tab, "My Library")
        
        layout.addWidget(tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self._refresh_tables()
    
    def _refresh_tables(self):
        # All voices
        self.all_table.setRowCount(len(self._all_voices))
        for row, voice in enumerate(self._all_voices):
            self.all_table.setItem(row, 0, QTableWidgetItem(voice.name))
            self.all_table.setItem(row, 1, QTableWidgetItem(voice.category))
            self.all_table.setItem(row, 2, QTableWidgetItem("Yes" if voice.is_cloned else "No"))
            # Show truncated voice ID
            short_id = voice.voice_id[:12] + "..." if len(voice.voice_id) > 12 else voice.voice_id
            id_item = QTableWidgetItem(short_id)
            id_item.setToolTip(voice.voice_id)
            self.all_table.setItem(row, 3, id_item)
        
        # Library
        self.lib_table.setRowCount(len(self._library))
        for row, voice in enumerate(self._library):
            self.lib_table.setItem(row, 0, QTableWidgetItem(voice.name))
            self.lib_table.setItem(row, 1, QTableWidgetItem(voice.category))
            self.lib_table.setItem(row, 2, QTableWidgetItem("Yes" if voice.is_cloned else "No"))
            short_id = voice.voice_id[:12] + "..." if len(voice.voice_id) > 12 else voice.voice_id
            id_item = QTableWidgetItem(short_id)
            id_item.setToolTip(voice.voice_id)
            self.lib_table.setItem(row, 3, id_item)
    
    def _add_to_library(self):
        rows = set(item.row() for item in self.all_table.selectedItems())
        for row in rows:
            voice = self._all_voices[row]
            if voice not in self._library:
                self._library.append(voice)
        self._refresh_tables()
    
    def _set_as_default_voice(self):
        """Set selected voice from All Voices tab as default"""
        rows = set(item.row() for item in self.all_table.selectedItems())
        if not rows:
            QMessageBox.warning(self, "Warning", "Please select a voice first")
            return
        
        voice = self._all_voices[list(rows)[0]]
        self.voice_added_by_id.emit(voice)
        self.voice_selected.emit(voice)
        QMessageBox.information(self, "Success", f"Voice '{voice.name}' set as default")
    
    def _set_library_voice_as_default(self):
        """Set selected voice from My Library tab as default"""
        rows = set(item.row() for item in self.lib_table.selectedItems())
        if not rows:
            QMessageBox.warning(self, "Warning", "Please select a voice first")
            return
        
        voice = self._library[list(rows)[0]]
        self.voice_added_by_id.emit(voice)
        self.voice_selected.emit(voice)
        QMessageBox.information(self, "Success", f"Voice '{voice.name}' set as default")
    
    def _remove_from_library(self):
        rows = set(item.row() for item in self.lib_table.selectedItems())
        for row in sorted(rows, reverse=True):
            del self._library[row]
        self._refresh_tables()
    
    def _add_voice_by_id(self):
        if not self._api_key:
            QMessageBox.warning(self, "Warning", "No API key available. Please add an API key first.")
            return
        
        dialog = AddVoiceByIdDialog(self._api_key, self._proxy, self)
        dialog.voice_added.connect(self._on_voice_fetched_by_id)
        dialog.exec()
    
    def _browse_voice_library(self):
        """Open the voice library browser dialog"""
        if not self._api_key:
            QMessageBox.warning(self, "Warning", "No API key available. Please add an API key first.")
            return
        
        dialog = VoiceLibraryBrowserDialog(self._api_key, self._proxy, self)
        dialog.voice_added.connect(self._on_voice_fetched_by_id)
        dialog.exec()
    
    def _clone_voice(self):
        """Open the voice cloning dialog"""
        if not self._api_key:
            QMessageBox.warning(self, "Warning", "No API key available. Please add an API key first.")
            return
        
        dialog = VoiceCloneDialog(self._api_key, self._proxy, self)
        dialog.voice_cloned.connect(self._on_voice_fetched_by_id)
        dialog.exec()
    
    def _on_voice_fetched_by_id(self, voice: Voice):
        # Check if already exists
        for v in self._all_voices:
            if v.voice_id == voice.voice_id:
                QMessageBox.information(self, "Info", f"Voice '{voice.name}' already exists in your list.")
                return
        
        # Add to all voices and library
        self._all_voices.append(voice)
        self._library.append(voice)
        self._refresh_tables()
        
        # Emit signal to add to main window's voice list
        self.voice_added_by_id.emit(voice)
        
        QMessageBox.information(self, "Success", f"Voice '{voice.name}' added successfully!")
    
    def _select_voice(self):
        rows = set(item.row() for item in self.all_table.selectedItems())
        if rows:
            voice = self._all_voices[list(rows)[0]]
            self.voice_selected.emit(voice)
    
    def _select_library_voice(self):
        rows = set(item.row() for item in self.lib_table.selectedItems())
        if rows:
            voice = self._library[list(rows)[0]]
            self.voice_selected.emit(voice)


class SettingsDialog(QDialog):
    """General settings dialog"""
    
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("settings_title"))
        self.setMinimumWidth(450)
        
        self._settings = settings.copy()
        
        layout = QVBoxLayout(self)
        
        # Create scroll area for settings content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Content widget for scroll area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Processing group
        proc_group = QGroupBox(tr("processing"))
        proc_layout = QFormLayout(proc_group)
        
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 50)
        self.threads_spin.setValue(settings.get("thread_count", 5))
        proc_layout.addRow(tr("thread_count") + ":", self.threads_spin)
        
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 10)
        self.retries_spin.setValue(settings.get("max_retries", 3))
        proc_layout.addRow(tr("max_retries") + ":", self.retries_spin)
        
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 10.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setValue(settings.get("request_delay", 0.5))
        self.delay_spin.setSuffix(" s")
        proc_layout.addRow(tr("request_delay") + ":", self.delay_spin)
        
        content_layout.addWidget(proc_group)
        
        # Text splitting group
        split_group = QGroupBox(tr("text_splitting"))
        split_layout = QFormLayout(split_group)
        
        self.auto_split_check = QCheckBox()
        self.auto_split_check.setChecked(settings.get("auto_split_enabled", True))
        split_layout.addRow(tr("auto_split_long_text") + ":", self.auto_split_check)
        
        self.max_chars_spin = QSpinBox()
        self.max_chars_spin.setRange(100, 10000)
        self.max_chars_spin.setValue(settings.get("max_chars", 5000))
        split_layout.addRow(tr("max_characters") + ":", self.max_chars_spin)
        
        self.delimiter_edit = QLineEdit()
        self.delimiter_edit.setText(settings.get("split_delimiter", ".,?!;"))
        split_layout.addRow(tr("split_delimiters") + ":", self.delimiter_edit)
        
        content_layout.addWidget(split_group)
        
        # Audio group
        audio_group = QGroupBox(tr("audio"))
        audio_layout = QFormLayout(audio_group)
        
        self.silence_spin = QSpinBox()
        self.silence_spin.setRange(0, 5000)
        self.silence_spin.setValue(int(settings.get("silence_gap", 0) * 1000))
        self.silence_spin.setSuffix(" ms")
        audio_layout.addRow(tr("silence_gap") + ":", self.silence_spin)
        
        content_layout.addWidget(audio_group)
        
        # Appearance group
        theme_group = QGroupBox(tr("appearance"))
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(tr("system"), "system")
        self.theme_combo.addItem(tr("dark"), "dark")
        self.theme_combo.addItem(tr("light"), "light")
        current_theme = settings.get("theme", "dark")
        theme_index = {"system": 0, "dark": 1, "light": 2}.get(current_theme, 1)
        self.theme_combo.setCurrentIndex(theme_index)
        theme_layout.addRow(tr("theme") + ":", self.theme_combo)
        
        # Language selection
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Tiếng Việt", "vi")
        current_lang = settings.get("app_language", "vi")
        lang_index = {"en": 0, "vi": 1}.get(current_lang, 1)
        self.language_combo.setCurrentIndex(lang_index)
        theme_layout.addRow(tr("language") + ":", self.language_combo)
        
        content_layout.addWidget(theme_group)
        
        # Automation group
        auto_group = QGroupBox(tr("automation"))
        auto_layout = QFormLayout(auto_group)
        
        self.auto_start_check = QCheckBox()
        self.auto_start_check.setChecked(settings.get("auto_start_on_launch", False))
        auto_layout.addRow(tr("auto_start_on_launch") + ":", self.auto_start_check)
        
        content_layout.addWidget(auto_group)
        
        # Vietnamese TTS group
        vn_group = QGroupBox(tr("vietnamese_tts"))
        vn_layout = QFormLayout(vn_group)
        
        self.vn_enabled_check = QCheckBox()
        self.vn_enabled_check.setChecked(settings.get("vn_preprocessing_enabled", True))
        vn_layout.addRow(tr("enable_preprocessing") + ":", self.vn_enabled_check)
        
        self.vn_phrase_spin = QSpinBox()
        self.vn_phrase_spin.setRange(3, 20)
        self.vn_phrase_spin.setValue(settings.get("vn_max_phrase_words", 8))
        vn_layout.addRow(tr("max_phrase_words") + ":", self.vn_phrase_spin)
        
        self.vn_pause_check = QCheckBox()
        self.vn_pause_check.setChecked(settings.get("vn_add_micro_pauses", True))
        vn_layout.addRow(tr("add_micro_pauses") + ":", self.vn_pause_check)
        
        self.vn_pause_interval_spin = QSpinBox()
        self.vn_pause_interval_spin.setRange(2, 10)
        self.vn_pause_interval_spin.setValue(settings.get("vn_micro_pause_interval", 4))
        vn_layout.addRow(tr("pause_interval") + ":", self.vn_pause_interval_spin)
        
        content_layout.addWidget(vn_group)
        
        # Pause Settings group
        pause_group = QGroupBox(tr("pause_settings"))
        pause_layout = QFormLayout(pause_group)
        
        self.pause_enabled_check = QCheckBox()
        self.pause_enabled_check.setChecked(settings.get("pause_enabled", True))
        pause_layout.addRow(tr("enable_pauses") + ":", self.pause_enabled_check)
        
        self.short_pause_spin = QSpinBox()
        self.short_pause_spin.setRange(0, 2000)
        self.short_pause_spin.setValue(settings.get("short_pause_duration", 300))
        self.short_pause_spin.setSuffix(" ms")
        pause_layout.addRow(tr("short_pause") + ":", self.short_pause_spin)
        
        self.long_pause_spin = QSpinBox()
        self.long_pause_spin.setRange(0, 3000)
        self.long_pause_spin.setValue(settings.get("long_pause_duration", 700))
        self.long_pause_spin.setSuffix(" ms")
        pause_layout.addRow(tr("long_pause") + ":", self.long_pause_spin)
        
        self.short_pause_punct_edit = QLineEdit()
        self.short_pause_punct_edit.setText(settings.get("short_pause_punctuation", ",;:"))
        pause_layout.addRow(tr("short_pause_punctuation") + ":", self.short_pause_punct_edit)
        
        self.long_pause_punct_edit = QLineEdit()
        self.long_pause_punct_edit.setText(settings.get("long_pause_punctuation", ".!?。！？"))
        pause_layout.addRow(tr("long_pause_punctuation") + ":", self.long_pause_punct_edit)
        
        content_layout.addWidget(pause_group)
        
        # Import/Export group
        io_group = QGroupBox(tr("import_export"))
        io_layout = QHBoxLayout(io_group)
        
        import_btn = QPushButton(tr("import_settings"))
        import_btn.clicked.connect(self._import_settings)
        io_layout.addWidget(import_btn)
        
        export_btn = QPushButton(tr("export_settings"))
        export_btn.clicked.connect(self._export_settings)
        io_layout.addWidget(export_btn)
        
        content_layout.addWidget(io_group)
        
        # Set up scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _import_settings(self):
        """Import settings from JSON file"""
        import json
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Settings", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported = json.load(f)
                
                # Apply imported settings to UI
                if "thread_count" in imported:
                    self.threads_spin.setValue(imported["thread_count"])
                if "max_retries" in imported:
                    self.retries_spin.setValue(imported["max_retries"])
                if "request_delay" in imported:
                    self.delay_spin.setValue(imported["request_delay"])
                if "auto_split_enabled" in imported:
                    self.auto_split_check.setChecked(imported["auto_split_enabled"])
                if "max_chars" in imported:
                    self.max_chars_spin.setValue(imported["max_chars"])
                if "split_delimiter" in imported:
                    self.delimiter_edit.setText(imported["split_delimiter"])
                if "silence_gap" in imported:
                    self.silence_spin.setValue(int(imported["silence_gap"] * 1000))
                if "theme" in imported:
                    theme_index = {"system": 0, "dark": 1, "light": 2}.get(imported["theme"], 1)
                    self.theme_combo.setCurrentIndex(theme_index)
                
                QMessageBox.information(self, "Success", "Settings imported successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import settings: {e}")
    
    def _export_settings(self):
        """Export settings to JSON file"""
        import json
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Settings", "2tts_settings.json", "JSON Files (*.json)"
        )
        if file_path:
            try:
                export_data = {
                    "thread_count": self.threads_spin.value(),
                    "max_retries": self.retries_spin.value(),
                    "request_delay": self.delay_spin.value(),
                    "auto_split_enabled": self.auto_split_check.isChecked(),
                    "max_chars": self.max_chars_spin.value(),
                    "split_delimiter": self.delimiter_edit.text(),
                    "silence_gap": self.silence_spin.value() / 1000,
                    "theme": self.theme_combo.currentData()
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                
                QMessageBox.information(self, "Success", f"Settings exported to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export settings: {e}")
    
    def _save(self):
        self._settings["thread_count"] = self.threads_spin.value()
        self._settings["max_retries"] = self.retries_spin.value()
        self._settings["request_delay"] = self.delay_spin.value()
        self._settings["auto_split_enabled"] = self.auto_split_check.isChecked()
        self._settings["max_chars"] = self.max_chars_spin.value()
        self._settings["split_delimiter"] = self.delimiter_edit.text()
        self._settings["silence_gap"] = self.silence_spin.value() / 1000
        self._settings["theme"] = self.theme_combo.currentData()
        self._settings["app_language"] = self.language_combo.currentData()
        self._settings["auto_start_on_launch"] = self.auto_start_check.isChecked()
        # Vietnamese TTS settings
        self._settings["vn_preprocessing_enabled"] = self.vn_enabled_check.isChecked()
        self._settings["vn_max_phrase_words"] = self.vn_phrase_spin.value()
        self._settings["vn_add_micro_pauses"] = self.vn_pause_check.isChecked()
        self._settings["vn_micro_pause_interval"] = self.vn_pause_interval_spin.value()
        # Pause settings
        self._settings["pause_enabled"] = self.pause_enabled_check.isChecked()
        self._settings["short_pause_duration"] = self.short_pause_spin.value()
        self._settings["long_pause_duration"] = self.long_pause_spin.value()
        self._settings["short_pause_punctuation"] = self.short_pause_punct_edit.text()
        self._settings["long_pause_punctuation"] = self.long_pause_punct_edit.text()
        self.accept()
    
    def get_settings(self) -> dict:
        return self._settings


class VoiceCloneDialog(QDialog):
    """Dialog for cloning a voice using audio samples"""
    
    voice_cloned = pyqtSignal(object)  # Voice
    
    def __init__(self, api_key, proxy=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Clone Voice")
        self.setMinimumWidth(550)
        
        self._api_key = api_key
        self._proxy = proxy
        self._selected_files = []
        
        layout = QVBoxLayout(self)
        
        # Instructions
        info_label = QLabel(
            "Create a voice clone from audio samples.\n"
            "Upload 1-25 audio files (MP3, WAV, M4A, etc.) with clear speech.\n"
            "Best results with 1-3 minutes of high-quality audio."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Voice name input
        name_group = QGroupBox("Voice Details")
        name_layout = QFormLayout(name_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter a name for your cloned voice")
        name_layout.addRow("Name*:", self.name_edit)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description")
        name_layout.addRow("Description:", self.description_edit)
        
        layout.addWidget(name_group)
        
        # Audio files selection
        files_group = QGroupBox("Audio Samples")
        files_layout = QVBoxLayout(files_group)
        
        # File list
        self.files_table = QTableWidget()
        self.files_table.setColumnCount(2)
        self.files_table.setHorizontalHeaderLabels(["File Name", "Size"])
        self.files_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_table.setMaximumHeight(150)
        files_layout.addWidget(self.files_table)
        
        # File buttons
        file_btn_layout = QHBoxLayout()
        
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self._add_files)
        file_btn_layout.addWidget(add_files_btn)
        
        remove_files_btn = QPushButton("Remove Selected")
        remove_files_btn.clicked.connect(self._remove_files)
        file_btn_layout.addWidget(remove_files_btn)
        
        clear_files_btn = QPushButton("Clear All")
        clear_files_btn.clicked.connect(self._clear_files)
        file_btn_layout.addWidget(clear_files_btn)
        
        file_btn_layout.addStretch()
        files_layout.addLayout(file_btn_layout)
        
        self.files_status_label = QLabel("No files selected")
        files_layout.addWidget(self.files_status_label)
        
        layout.addWidget(files_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.remove_noise_check = QCheckBox("Remove background noise from samples")
        self.remove_noise_check.setChecked(False)
        options_layout.addWidget(self.remove_noise_check)
        
        layout.addWidget(options_group)
        
        # Status
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.clone_btn = QPushButton("Clone Voice")
        self.clone_btn.setObjectName("primaryButton")
        self.clone_btn.clicked.connect(self._clone_voice)
        btn_layout.addWidget(self.clone_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _add_files(self):
        """Add audio files"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Audio Files", "",
            "Audio Files (*.mp3 *.wav *.m4a *.ogg *.flac *.webm);;All Files (*.*)"
        )
        if files:
            for file_path in files:
                if file_path not in self._selected_files:
                    self._selected_files.append(file_path)
            self._refresh_files_table()
    
    def _remove_files(self):
        """Remove selected files"""
        rows = set(item.row() for item in self.files_table.selectedItems())
        for row in sorted(rows, reverse=True):
            if row < len(self._selected_files):
                del self._selected_files[row]
        self._refresh_files_table()
    
    def _clear_files(self):
        """Clear all files"""
        self._selected_files.clear()
        self._refresh_files_table()
    
    def _refresh_files_table(self):
        """Refresh the files table"""
        import os
        
        self.files_table.setRowCount(len(self._selected_files))
        total_size = 0
        
        for row, file_path in enumerate(self._selected_files):
            # File name
            self.files_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            
            # File size
            try:
                size = os.path.getsize(file_path)
                total_size += size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                self.files_table.setItem(row, 1, QTableWidgetItem(size_str))
            except:
                self.files_table.setItem(row, 1, QTableWidgetItem("?"))
        
        # Update status
        if self._selected_files:
            if total_size < 1024 * 1024:
                total_str = f"{total_size / 1024:.1f} KB"
            else:
                total_str = f"{total_size / (1024 * 1024):.1f} MB"
            self.files_status_label.setText(f"{len(self._selected_files)} file(s) selected ({total_str})")
        else:
            self.files_status_label.setText("No files selected")
    
    def _clone_voice(self):
        """Clone the voice"""
        # Validate inputs
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name for the voice")
            return
        
        if not self._selected_files:
            QMessageBox.warning(self, "Warning", "Please add at least one audio file")
            return
        
        if len(self._selected_files) > 25:
            QMessageBox.warning(self, "Warning", "Maximum 25 audio files allowed")
            return
        
        # Disable UI during cloning
        self.clone_btn.setEnabled(False)
        self.clone_btn.setText("Cloning...")
        self.status_label.setText("Uploading and processing audio samples...")
        self.status_label.setStyleSheet("color: orange;")
        
        description = self.description_edit.text().strip() or None
        remove_noise = self.remove_noise_check.isChecked()
        
        # Create and start worker
        self._clone_worker = CloneVoiceWorker(
            name=name,
            files=self._selected_files,
            api_key=self._api_key,
            description=description,
            remove_noise=remove_noise,
            proxy=self._proxy,
            parent=self
        )
        self._clone_worker.progress.connect(self._on_clone_progress)
        self._clone_worker.finished.connect(self._on_clone_finished)
        self._clone_worker.error.connect(self._on_clone_error)
        self._clone_worker.start()
    
    def _on_clone_progress(self, message: str):
        self.status_label.setText(message)
    
    def _on_clone_finished(self, voice, error: str):
        self.clone_btn.setEnabled(True)
        self.clone_btn.setText("Clone Voice")
        name = self.name_edit.text().strip()
        
        if voice:
            self.status_label.setText(f"Voice '{name}' cloned successfully!")
            self.status_label.setStyleSheet("color: green;")
            self.voice_cloned.emit(voice)
            QMessageBox.information(self, "Success", f"Voice '{name}' has been cloned successfully!")
            self.accept()
        else:
            self.status_label.setText(f"Error: {error}")
            self.status_label.setStyleSheet("color: red;")
            QMessageBox.warning(self, "Clone Failed", f"Failed to clone voice:\n{error}")
    
    def _on_clone_error(self, error: str):
        self.clone_btn.setEnabled(True)
        self.clone_btn.setText("Clone Voice")
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet("color: red;")
        QMessageBox.warning(self, "Clone Failed", f"Clone error: {error}")


class VoiceLibraryBrowserDialog(QDialog):
    """Dialog for browsing the ElevenLabs public voice library"""
    
    voice_added = pyqtSignal(object)  # Voice
    
    def __init__(self, api_key, proxy=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Browse Voice Library")
        self.setMinimumSize(900, 650)
        
        self._api_key = api_key
        self._proxy = proxy
        self._voices_data = []
        self._selected_voice = None
        
        layout = QVBoxLayout(self)
        
        # Search and filters
        filter_group = QGroupBox("Search & Filters")
        filter_layout = QVBoxLayout(filter_group)
        
        # Search row
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by voice name...")
        self.search_edit.returnPressed.connect(self._search)
        search_layout.addWidget(self.search_edit)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._search)
        search_layout.addWidget(self.search_btn)
        filter_layout.addLayout(search_layout)
        
        # Filter row
        filters_layout = QHBoxLayout()
        
        filters_layout.addWidget(QLabel("Gender:"))
        self.gender_combo = QComboBox()
        self.gender_combo.addItem("All", "")
        self.gender_combo.addItem("Male", "male")
        self.gender_combo.addItem("Female", "female")
        self.gender_combo.addItem("Neutral", "neutral")
        filters_layout.addWidget(self.gender_combo)
        
        filters_layout.addWidget(QLabel("Age:"))
        self.age_combo = QComboBox()
        self.age_combo.addItem("All", "")
        self.age_combo.addItem("Young", "young")
        self.age_combo.addItem("Middle Aged", "middle_aged")
        self.age_combo.addItem("Old", "old")
        filters_layout.addWidget(self.age_combo)
        
        filters_layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("All", "")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Vietnamese", "vi")
        self.language_combo.addItem("Spanish", "es")
        self.language_combo.addItem("French", "fr")
        self.language_combo.addItem("German", "de")
        self.language_combo.addItem("Chinese", "zh")
        self.language_combo.addItem("Japanese", "ja")
        self.language_combo.addItem("Korean", "ko")
        self.language_combo.addItem("Portuguese", "pt")
        self.language_combo.addItem("Italian", "it")
        filters_layout.addWidget(self.language_combo)
        
        filters_layout.addWidget(QLabel("Use Case:"))
        self.use_case_combo = QComboBox()
        self.use_case_combo.addItem("All", "")
        self.use_case_combo.addItem("Narration", "narration")
        self.use_case_combo.addItem("Conversational", "conversational")
        self.use_case_combo.addItem("News", "news")
        self.use_case_combo.addItem("Characters", "characters")
        self.use_case_combo.addItem("Social Media", "social_media")
        filters_layout.addWidget(self.use_case_combo)
        
        filter_layout.addLayout(filters_layout)
        
        # Sort row
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Trending", "trending")
        self.sort_combo.addItem("Latest", "latest")
        self.sort_combo.addItem("Most Used (Year)", "usage_character_count_1y")
        self.sort_combo.addItem("Most Used (Month)", "usage_character_count_30d")
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        
        self.results_label = QLabel("")
        sort_layout.addWidget(self.results_label)
        filter_layout.addLayout(sort_layout)
        
        layout.addWidget(filter_group)
        
        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Gender", "Age", "Accent", "Use Case", "Plays", "Voice ID"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)
        
        # Voice details panel
        details_group = QGroupBox("Voice Details")
        details_layout = QFormLayout(details_group)
        
        self.detail_name = QLabel("-")
        self.detail_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        details_layout.addRow("Name:", self.detail_name)
        
        self.detail_description = QLabel("-")
        self.detail_description.setWordWrap(True)
        details_layout.addRow("Description:", self.detail_description)
        
        self.detail_labels = QLabel("-")
        details_layout.addRow("Labels:", self.detail_labels)
        
        layout.addWidget(details_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self._preview_voice)
        btn_layout.addWidget(self.preview_btn)
        
        btn_layout.addStretch()
        
        self.add_btn = QPushButton("Add to My Voices")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self._add_voice)
        btn_layout.addWidget(self.add_btn)
        
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Load initial results
        self._search()
    
    def _search(self):
        """Search voice library"""
        self.search_btn.setEnabled(False)
        self.search_btn.setText("Loading...")
        self.table.setRowCount(0)
        self.results_label.setText("Searching...")
        
        search_params = {
            "page_size": 50,
            "search": self.search_edit.text() or None,
            "gender": self.gender_combo.currentData() or None,
            "age": self.age_combo.currentData() or None,
            "language": self.language_combo.currentData() or None,
            "use_case": self.use_case_combo.currentData() or None,
            "sort": self.sort_combo.currentData() or None
        }
        
        # Create and start worker
        self._search_worker = SearchVoiceLibraryWorker(
            self._api_key, self._proxy, search_params, self
        )
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.start()
    
    def _on_search_finished(self, voices: list, has_more: bool, error: str):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")
        
        if error:
            QMessageBox.warning(self, "Error", f"Failed to load voices: {error}")
            self.results_label.setText("Search failed")
            return
        
        self._voices_data = voices
        self._populate_table()
        
        more_text = " (more available)" if has_more else ""
        self.results_label.setText(f"Found {len(voices)} voices{more_text}")
    
    def _on_search_error(self, error: str):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Search")
        QMessageBox.warning(self, "Error", f"Search failed: {error}")
        self.results_label.setText("Search failed")
    
    def _populate_table(self):
        """Populate table with voice data"""
        self.table.setRowCount(len(self._voices_data))
        
        for row, voice in enumerate(self._voices_data):
            # Name
            name = voice.get("name", "Unknown")
            self.table.setItem(row, 0, QTableWidgetItem(name))
            
            # Gender
            labels = voice.get("labels", {})
            gender = labels.get("gender", voice.get("gender", "-"))
            self.table.setItem(row, 1, QTableWidgetItem(gender.title() if gender else "-"))
            
            # Age
            age = labels.get("age", voice.get("age", "-"))
            self.table.setItem(row, 2, QTableWidgetItem(age.replace("_", " ").title() if age else "-"))
            
            # Accent
            accent = labels.get("accent", voice.get("accent", "-"))
            self.table.setItem(row, 3, QTableWidgetItem(accent.title() if accent else "-"))
            
            # Use case
            use_case = labels.get("use_case", voice.get("use_case", "-"))
            self.table.setItem(row, 4, QTableWidgetItem(use_case.replace("_", " ").title() if use_case else "-"))
            
            # Play count
            plays = voice.get("cloned_by_count", voice.get("usage_character_count_1y", 0))
            self.table.setItem(row, 5, QTableWidgetItem(f"{plays:,}" if plays else "-"))
            
            # Voice ID (truncated)
            voice_id = voice.get("voice_id", "")
            short_id = voice_id[:12] + "..." if len(voice_id) > 12 else voice_id
            id_item = QTableWidgetItem(short_id)
            id_item.setToolTip(voice_id)
            self.table.setItem(row, 6, id_item)
    
    def _on_selection_changed(self):
        """Handle table selection change"""
        rows = self.table.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            if row < len(self._voices_data):
                self._selected_voice = self._voices_data[row]
                self._update_details()
                self.add_btn.setEnabled(True)
                self.preview_btn.setEnabled(True)
        else:
            self._selected_voice = None
            self.add_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
    
    def _update_details(self):
        """Update voice details panel"""
        if not self._selected_voice:
            self.detail_name.setText("-")
            self.detail_description.setText("-")
            self.detail_labels.setText("-")
            return
        
        self.detail_name.setText(self._selected_voice.get("name", "Unknown"))
        
        description = self._selected_voice.get("description", "")
        self.detail_description.setText(description if description else "No description available")
        
        labels = self._selected_voice.get("labels", {})
        label_strs = [f"{k}: {v}" for k, v in labels.items() if v]
        self.detail_labels.setText(", ".join(label_strs) if label_strs else "-")
    
    def _on_double_click(self):
        """Handle double click on table row"""
        if self._selected_voice:
            self._add_voice()
    
    def _preview_voice(self):
        """Preview selected voice"""
        if not self._selected_voice:
            return
        
        voice_id = self._selected_voice.get("voice_id")
        if not voice_id:
            QMessageBox.warning(self, "Error", "No voice ID available")
            return
        
        import tempfile
        import os
        
        preview_text = "Hello! This is a voice preview sample from the ElevenLabs voice library."
        preview_path = os.path.join(tempfile.gettempdir(), "2tts_library_preview.mp3")
        
        self.preview_btn.setEnabled(False)
        self.preview_btn.setText("Loading...")
        
        # Create and start worker
        self._preview_worker = VoicePreviewWorker(
            preview_text, voice_id, self._api_key, preview_path, None, self._proxy, self
        )
        self._preview_worker.finished.connect(self._on_preview_finished)
        self._preview_worker.error.connect(self._on_preview_error)
        self._preview_worker.start()
    
    def _on_preview_finished(self, success: bool, output_path: str, message: str):
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("Preview")
        
        if success and output_path:
            from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PyQt6.QtCore import QUrl
            
            if not hasattr(self, '_audio_player'):
                self._audio_player = QMediaPlayer()
                self._audio_output = QAudioOutput()
                self._audio_player.setAudioOutput(self._audio_output)
            
            self._audio_player.setSource(QUrl.fromLocalFile(output_path))
            self._audio_player.play()
        else:
            QMessageBox.warning(self, "Preview Failed", f"Failed to generate preview: {message}")
    
    def _on_preview_error(self, error: str):
        self.preview_btn.setEnabled(True)
        self.preview_btn.setText("Preview")
        QMessageBox.warning(self, "Preview Failed", f"Preview error: {error}")
    
    def _add_voice(self):
        """Add selected voice to user's account"""
        if not self._selected_voice:
            return
        
        voice_id = self._selected_voice.get("voice_id")
        voice_name = self._selected_voice.get("name", "Library Voice")
        public_user_id = self._selected_voice.get("public_owner_id", "")
        
        if not voice_id:
            QMessageBox.warning(self, "Error", "No voice ID available")
            return
        
        from services.elevenlabs import ElevenLabsAPI
        from core.models import Voice
        
        api = ElevenLabsAPI()
        
        # Try to add via API if we have public_user_id
        if public_user_id:
            voice, error = api.add_shared_voice(
                public_user_id=public_user_id,
                voice_id=voice_id,
                new_name=voice_name,
                api_key=self._api_key,
                proxy=self._proxy
            )
            
            if voice:
                self.voice_added.emit(voice)
                QMessageBox.information(self, "Success", f"Voice '{voice_name}' added to your account!")
                return
            elif "already" not in error.lower():
                QMessageBox.warning(self, "Note", f"Could not add to account: {error}\nVoice will be added locally.")
        
        # Fallback: create voice object for local use (voice ID still works for TTS)
        voice = Voice(
            voice_id=voice_id,
            name=voice_name,
            is_cloned=False,
            category="library",
            labels=self._selected_voice.get("labels", {})
        )
        self.voice_added.emit(voice)
        QMessageBox.information(self, "Success", f"Voice '{voice_name}' added!")
