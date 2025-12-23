"""Configuration management for 2TTS"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from core.models import APIKey, Proxy, Voice, VoiceSettings


class Config:
    """Application configuration manager"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".2tts"
        self.config_file = self.config_dir / "config.json"
        self.api_keys_file = self.config_dir / "api_keys.json"
        self.proxies_file = self.config_dir / "proxies.json"
        self.voice_library_file = self.config_dir / "voice_library.json"
        
        self._ensure_config_dir()
        self._api_keys: List[APIKey] = []
        self._proxies: List[Proxy] = []
        self._voice_library: List[Voice] = []
        self._settings: Dict[str, Any] = {}
        
        self.load()
    
    def _ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self):
        """Load all configuration files"""
        self._load_settings()
        self._load_api_keys()
        self._load_proxies()
        self._load_voice_library()
    
    def save(self):
        """Save all configuration files"""
        self._save_settings()
        self._save_api_keys()
        self._save_proxies()
        self._save_voice_library()
    
    def _load_settings(self):
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._settings = json.load(f)
        else:
            self._settings = self._default_settings()
    
    def _save_settings(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._settings, f, indent=2)
    
    def _default_settings(self) -> Dict[str, Any]:
        return {
            "theme": "dark",
            "app_language": "vi",  # Default to Vietnamese
            "default_output_folder": str(Path.home() / "2TTS_Output"),
            "thread_count": 5,
            "max_retries": 3,
            "auto_split_enabled": True,
            "split_delimiter": ".,?!;",
            "max_chars": 5000,
            "silence_gap": 0.0,
            "low_credit_threshold": 1000,
            "window_geometry": None,
            "recent_projects": [],
            "favorite_voices": [],
            "auto_start_on_launch": False,
            "language_voice_mapping": {},
            "language_model_mapping": {},
            "last_voice_id": None,
            "last_voice_name": None,
            # Pause settings
            "pause_enabled": False,
            "short_pause_duration": 300,  # ms
            "long_pause_duration": 700,   # ms
            "short_pause_punctuation": ",;:",
            "long_pause_punctuation": ".!?。！？"
        }
    
    def _load_api_keys(self):
        self._api_keys = []
        if self.api_keys_file.exists():
            with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._api_keys = [APIKey.from_dict(k) for k in data]
    
    def _save_api_keys(self):
        with open(self.api_keys_file, 'w', encoding='utf-8') as f:
            json.dump([k.to_dict() for k in self._api_keys], f, indent=2)
    
    def _load_proxies(self):
        self._proxies = []
        if self.proxies_file.exists():
            with open(self.proxies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._proxies = [Proxy.from_dict(p) for p in data]
    
    def _save_proxies(self):
        with open(self.proxies_file, 'w', encoding='utf-8') as f:
            json.dump([p.to_dict() for p in self._proxies], f, indent=2)
    
    def _load_voice_library(self):
        self._voice_library = []
        if self.voice_library_file.exists():
            with open(self.voice_library_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._voice_library = [Voice.from_dict(v) for v in data]
    
    def _save_voice_library(self):
        with open(self.voice_library_file, 'w', encoding='utf-8') as f:
            json.dump([v.to_dict() for v in self._voice_library], f, indent=2)
    
    # API Keys management
    @property
    def api_keys(self) -> List[APIKey]:
        return self._api_keys
    
    def add_api_key(self, key: APIKey):
        self._api_keys.append(key)
        self._save_api_keys()
    
    def remove_api_key(self, key_id: str):
        self._api_keys = [k for k in self._api_keys if k.id != key_id]
        self._save_api_keys()
    
    def update_api_key(self, key: APIKey):
        for i, k in enumerate(self._api_keys):
            if k.id == key.id:
                self._api_keys[i] = key
                break
        self._save_api_keys()
    
    def get_available_api_key(self) -> Optional[APIKey]:
        """Get the next available API key for use (prioritizes smallest credits first)"""
        available_keys = [k for k in self._api_keys if k.is_available]
        if not available_keys:
            return None
        # Sort by remaining credits ascending (use smallest credits first)
        available_keys.sort(key=lambda k: k.remaining_credits)
        return available_keys[0]
    
    def get_total_credits(self) -> int:
        """Get total remaining credits across all keys"""
        return sum(k.remaining_credits for k in self._api_keys if k.is_valid)
    
    # Proxies management
    @property
    def proxies(self) -> List[Proxy]:
        return self._proxies
    
    def add_proxy(self, proxy: Proxy):
        self._proxies.append(proxy)
        self._save_proxies()
    
    def remove_proxy(self, proxy_id: str):
        self._proxies = [p for p in self._proxies if p.id != proxy_id]
        self._save_proxies()
    
    def update_proxy(self, proxy: Proxy):
        for i, p in enumerate(self._proxies):
            if p.id == proxy.id:
                self._proxies[i] = proxy
                break
        self._save_proxies()
    
    def get_proxy_for_key(self, key: APIKey) -> Optional[Proxy]:
        """Get the proxy assigned to an API key"""
        if not key.assigned_proxy_id:
            return None
        for proxy in self._proxies:
            if proxy.id == key.assigned_proxy_id and proxy.enabled and proxy.is_healthy:
                return proxy
        return None
    
    def get_available_proxy(self) -> Optional[Proxy]:
        """Get an available healthy proxy"""
        for proxy in self._proxies:
            if proxy.enabled and proxy.is_healthy:
                return proxy
        return None
    
    # Voice Library management
    @property
    def voice_library(self) -> List[Voice]:
        return self._voice_library
    
    def add_voice_to_library(self, voice: Voice):
        # Check if already exists
        for v in self._voice_library:
            if v.voice_id == voice.voice_id:
                return
        self._voice_library.append(voice)
        self._save_voice_library()
    
    def remove_voice_from_library(self, voice_id: str):
        self._voice_library = [v for v in self._voice_library if v.voice_id != voice_id]
        self._save_voice_library()
    
    def update_voice_in_library(self, voice: Voice):
        for i, v in enumerate(self._voice_library):
            if v.voice_id == voice.voice_id:
                self._voice_library[i] = voice
                break
        self._save_voice_library()
    
    # Settings accessors
    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Alias for get() method"""
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any):
        self._settings[key] = value
        self._save_settings()
    
    @property
    def theme(self) -> str:
        return self._settings.get("theme", "dark")
    
    @theme.setter
    def theme(self, value: str):
        self._settings["theme"] = value
        self._save_settings()
    
    @property
    def app_language(self) -> str:
        return self._settings.get("app_language", "vi")
    
    @app_language.setter
    def app_language(self, value: str):
        self._settings["app_language"] = value
        self._save_settings()
    
    @property
    def default_output_folder(self) -> str:
        return self._settings.get("default_output_folder", str(Path.home() / "2TTS_Output"))
    
    @default_output_folder.setter
    def default_output_folder(self, value: str):
        self._settings["default_output_folder"] = value
        self._save_settings()
    
    @property
    def recent_projects(self) -> List[str]:
        return self._settings.get("recent_projects", [])
    
    def add_recent_project(self, path: str):
        recent = self.recent_projects
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self._settings["recent_projects"] = recent[:10]  # Keep last 10
        self._save_settings()
    
    # Favorite voices management
    @property
    def favorite_voices(self) -> List[str]:
        return self._settings.get("favorite_voices", [])
    
    def add_favorite_voice(self, voice_id: str):
        favorites = self.favorite_voices
        if voice_id not in favorites:
            favorites.append(voice_id)
            self._settings["favorite_voices"] = favorites
            self._save_settings()
    
    def remove_favorite_voice(self, voice_id: str):
        favorites = self.favorite_voices
        if voice_id in favorites:
            favorites.remove(voice_id)
            self._settings["favorite_voices"] = favorites
            self._save_settings()
    
    def is_favorite_voice(self, voice_id: str) -> bool:
        return voice_id in self.favorite_voices
    
    # Auto-start setting
    @property
    def auto_start_on_launch(self) -> bool:
        return self._settings.get("auto_start_on_launch", False)
    
    @auto_start_on_launch.setter
    def auto_start_on_launch(self, value: bool):
        self._settings["auto_start_on_launch"] = value
        self._save_settings()
    
    # Language-voice mapping
    @property
    def language_voice_mapping(self) -> Dict[str, str]:
        return self._settings.get("language_voice_mapping", {})
    
    def set_language_voice(self, lang_code: str, voice_id: str):
        mapping = self.language_voice_mapping
        mapping[lang_code] = voice_id
        self._settings["language_voice_mapping"] = mapping
        self._save_settings()
    
    def get_voice_for_language(self, lang_code: str) -> Optional[str]:
        return self.language_voice_mapping.get(lang_code)
    
    # Language-model mapping
    @property
    def language_model_mapping(self) -> Dict[str, str]:
        return self._settings.get("language_model_mapping", {})
    
    def set_language_model(self, lang_code: str, model_id: str):
        mapping = self.language_model_mapping
        mapping[lang_code] = model_id
        self._settings["language_model_mapping"] = mapping
        self._save_settings()
    
    def get_model_for_language(self, lang_code: str) -> Optional[str]:
        return self.language_model_mapping.get(lang_code)
    
    # Last used voice
    @property
    def last_voice_id(self) -> Optional[str]:
        return self._settings.get("last_voice_id")
    
    @property
    def last_voice_name(self) -> Optional[str]:
        return self._settings.get("last_voice_name")
    
    def set_last_voice(self, voice_id: str, voice_name: str):
        self._settings["last_voice_id"] = voice_id
        self._settings["last_voice_name"] = voice_name
        self._save_settings()


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
