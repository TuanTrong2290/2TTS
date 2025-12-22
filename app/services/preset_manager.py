"""Preset management for voice settings and project templates"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from core.models import VoiceSettings, Voice, ProjectSettings


@dataclass
class VoicePreset:
    """Voice configuration preset"""
    id: str
    name: str
    voice_id: str
    voice_name: str
    settings: VoiceSettings
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "voice_id": self.voice_id,
            "voice_name": self.voice_name,
            "settings": self.settings.to_dict(),
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VoicePreset':
        return cls(
            id=data["id"],
            name=data["name"],
            voice_id=data["voice_id"],
            voice_name=data.get("voice_name", ""),
            settings=VoiceSettings.from_dict(data.get("settings", {})),
            description=data.get("description", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            tags=data.get("tags", [])
        )


@dataclass
class ProjectTemplate:
    """Project template with default settings"""
    id: str
    name: str
    description: str = ""
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    default_voice_preset_id: Optional[str] = None
    voice_assignments: Dict[str, str] = field(default_factory=dict)  # pattern -> voice_preset_id
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "settings": self.settings.to_dict(),
            "default_voice_preset_id": self.default_voice_preset_id,
            "voice_assignments": self.voice_assignments,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectTemplate':
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            settings=ProjectSettings.from_dict(data.get("settings", {})),
            default_voice_preset_id=data.get("default_voice_preset_id"),
            voice_assignments=data.get("voice_assignments", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            tags=data.get("tags", [])
        )


class PresetManager:
    """Manages voice presets and project templates"""
    
    def __init__(self):
        self._config_dir = Path.home() / ".2tts"
        self._presets_file = self._config_dir / "voice_presets.json"
        self._templates_file = self._config_dir / "project_templates.json"
        
        self._voice_presets: List[VoicePreset] = []
        self._project_templates: List[ProjectTemplate] = []
        
        self._load()
    
    def _load(self):
        self._config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load voice presets
        if self._presets_file.exists():
            try:
                with open(self._presets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._voice_presets = [VoicePreset.from_dict(p) for p in data]
            except:
                self._voice_presets = []
        
        # Load project templates
        if self._templates_file.exists():
            try:
                with open(self._templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._project_templates = [ProjectTemplate.from_dict(t) for t in data]
            except:
                self._project_templates = []
    
    def _save_presets(self):
        with open(self._presets_file, 'w', encoding='utf-8') as f:
            json.dump([p.to_dict() for p in self._voice_presets], f, indent=2)
    
    def _save_templates(self):
        with open(self._templates_file, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in self._project_templates], f, indent=2)
    
    # Voice Presets
    @property
    def voice_presets(self) -> List[VoicePreset]:
        return self._voice_presets
    
    def add_voice_preset(self, preset: VoicePreset) -> bool:
        for existing in self._voice_presets:
            if existing.id == preset.id:
                return False
        self._voice_presets.append(preset)
        self._save_presets()
        return True
    
    def update_voice_preset(self, preset: VoicePreset) -> bool:
        for i, existing in enumerate(self._voice_presets):
            if existing.id == preset.id:
                self._voice_presets[i] = preset
                self._save_presets()
                return True
        return False
    
    def delete_voice_preset(self, preset_id: str) -> bool:
        for i, preset in enumerate(self._voice_presets):
            if preset.id == preset_id:
                del self._voice_presets[i]
                self._save_presets()
                return True
        return False
    
    def get_voice_preset(self, preset_id: str) -> Optional[VoicePreset]:
        for preset in self._voice_presets:
            if preset.id == preset_id:
                return preset
        return None
    
    def get_presets_by_tag(self, tag: str) -> List[VoicePreset]:
        return [p for p in self._voice_presets if tag in p.tags]
    
    def create_preset_from_voice(self, voice: Voice, name: str, description: str = "") -> VoicePreset:
        import uuid
        preset = VoicePreset(
            id=str(uuid.uuid4()),
            name=name,
            voice_id=voice.voice_id,
            voice_name=voice.name,
            settings=voice.settings,
            description=description
        )
        self.add_voice_preset(preset)
        return preset
    
    # Project Templates
    @property
    def project_templates(self) -> List[ProjectTemplate]:
        return self._project_templates
    
    def add_project_template(self, template: ProjectTemplate) -> bool:
        for existing in self._project_templates:
            if existing.id == template.id:
                return False
        self._project_templates.append(template)
        self._save_templates()
        return True
    
    def update_project_template(self, template: ProjectTemplate) -> bool:
        for i, existing in enumerate(self._project_templates):
            if existing.id == template.id:
                self._project_templates[i] = template
                self._save_templates()
                return True
        return False
    
    def delete_project_template(self, template_id: str) -> bool:
        for i, template in enumerate(self._project_templates):
            if template.id == template_id:
                del self._project_templates[i]
                self._save_templates()
                return True
        return False
    
    def get_project_template(self, template_id: str) -> Optional[ProjectTemplate]:
        for template in self._project_templates:
            if template.id == template_id:
                return template
        return None
    
    def create_template_from_project(self, project, name: str, description: str = "") -> ProjectTemplate:
        import uuid
        template = ProjectTemplate(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            settings=project.settings
        )
        self.add_project_template(template)
        return template
    
    # Export/Import
    def export_presets(self, file_path: str, preset_ids: Optional[List[str]] = None) -> bool:
        try:
            presets = self._voice_presets
            if preset_ids:
                presets = [p for p in presets if p.id in preset_ids]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "type": "2tts_voice_presets",
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "presets": [p.to_dict() for p in presets]
                }, f, indent=2)
            return True
        except:
            return False
    
    def import_presets(self, file_path: str, overwrite: bool = False) -> tuple[int, int]:
        """Import presets from file. Returns (imported_count, skipped_count)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get("type") != "2tts_voice_presets":
                return 0, 0
            
            presets = [VoicePreset.from_dict(p) for p in data.get("presets", [])]
            imported = 0
            skipped = 0
            
            for preset in presets:
                existing = self.get_voice_preset(preset.id)
                if existing:
                    if overwrite:
                        self.update_voice_preset(preset)
                        imported += 1
                    else:
                        skipped += 1
                else:
                    self.add_voice_preset(preset)
                    imported += 1
            
            return imported, skipped
        except:
            return 0, 0
    
    def export_templates(self, file_path: str, template_ids: Optional[List[str]] = None) -> bool:
        try:
            templates = self._project_templates
            if template_ids:
                templates = [t for t in templates if t.id in template_ids]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "type": "2tts_project_templates",
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "templates": [t.to_dict() for t in templates]
                }, f, indent=2)
            return True
        except:
            return False
    
    def import_templates(self, file_path: str, overwrite: bool = False) -> tuple[int, int]:
        """Import templates from file. Returns (imported_count, skipped_count)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get("type") != "2tts_project_templates":
                return 0, 0
            
            templates = [ProjectTemplate.from_dict(t) for t in data.get("templates", [])]
            imported = 0
            skipped = 0
            
            for template in templates:
                existing = self.get_project_template(template.id)
                if existing:
                    if overwrite:
                        self.update_project_template(template)
                        imported += 1
                    else:
                        skipped += 1
                else:
                    self.add_project_template(template)
                    imported += 1
            
            return imported, skipped
        except:
            return 0, 0


_preset_manager: Optional[PresetManager] = None


def get_preset_manager() -> PresetManager:
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = PresetManager()
    return _preset_manager
