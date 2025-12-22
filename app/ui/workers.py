"""Worker threads for async operations in UI"""
import threading
from typing import Callable, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread


class WorkerSignals(QObject):
    """Signals for worker threads"""
    started = pyqtSignal()
    finished = pyqtSignal(object)  # result
    error = pyqtSignal(str)  # error message
    progress = pyqtSignal(int, int)  # current, total


class GenericWorker(QThread):
    """Generic worker thread for running tasks off the UI thread"""
    
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self._is_cancelled = False
    
    def run(self):
        self.signals.started.emit()
        try:
            result = self.fn(*self.args, **self.kwargs)
            if not self._is_cancelled:
                self.signals.finished.emit(result)
        except Exception as e:
            if not self._is_cancelled:
                self.signals.error.emit(str(e))
    
    def cancel(self):
        self._is_cancelled = True


class ValidateKeysWorker(QThread):
    """Worker for validating API keys"""
    
    started = pyqtSignal()
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(int, int)  # validated_count, total_count
    error = pyqtSignal(str)
    
    def __init__(self, keys: list, parent=None):
        super().__init__(parent)
        self._keys = keys
        self._is_cancelled = False
    
    def run(self):
        from services.elevenlabs import ElevenLabsAPI
        
        self.started.emit()
        api = ElevenLabsAPI()
        validated_count = 0
        total = len(self._keys)
        
        for i, key in enumerate(self._keys):
            if self._is_cancelled:
                break
            
            self.progress.emit(i + 1, total, f"Validating key {i + 1}/{total}...")
            
            try:
                success, msg = api.validate_key(key)
                if success:
                    validated_count += 1
            except Exception as e:
                pass  # Continue with next key
        
        self.finished.emit(validated_count, total)
    
    def cancel(self):
        self._is_cancelled = True


class TestProxiesWorker(QThread):
    """Worker for testing proxies"""
    
    started = pyqtSignal()
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(int, int)  # healthy_count, total_count
    error = pyqtSignal(str)
    
    def __init__(self, proxies: list, parent=None):
        super().__init__(parent)
        self._proxies = proxies
        self._is_cancelled = False
    
    def run(self):
        import requests
        
        self.started.emit()
        healthy_count = 0
        total = len(self._proxies)
        
        for i, proxy in enumerate(self._proxies):
            if self._is_cancelled:
                break
            
            self.progress.emit(i + 1, total, f"Testing proxy {i + 1}/{total}...")
            
            try:
                proxies = {"http": proxy.get_url(), "https": proxy.get_url()}
                response = requests.get("https://api.ipify.org", proxies=proxies, timeout=10)
                proxy.is_healthy = response.status_code == 200
                if proxy.is_healthy:
                    healthy_count += 1
            except:
                proxy.is_healthy = False
        
        self.finished.emit(healthy_count, total)
    
    def cancel(self):
        self._is_cancelled = True


class FetchVoiceWorker(QThread):
    """Worker for fetching a single voice by ID"""
    
    started = pyqtSignal()
    finished = pyqtSignal(object, str)  # voice or None, message
    error = pyqtSignal(str)
    
    def __init__(self, voice_id: str, api_key, proxy=None, parent=None):
        super().__init__(parent)
        self._voice_id = voice_id
        self._api_key = api_key
        self._proxy = proxy
    
    def run(self):
        from services.elevenlabs import ElevenLabsAPI
        
        self.started.emit()
        api = ElevenLabsAPI()
        
        try:
            voice, message = api.get_voice_by_id(self._voice_id, self._api_key, self._proxy)
            self.finished.emit(voice, message)
        except Exception as e:
            self.error.emit(str(e))


class SearchVoiceLibraryWorker(QThread):
    """Worker for searching voice library"""
    
    started = pyqtSignal()
    finished = pyqtSignal(list, bool, str)  # voices, has_more, error_message
    error = pyqtSignal(str)
    
    def __init__(self, api_key, proxy, search_params: dict, parent=None):
        super().__init__(parent)
        self._api_key = api_key
        self._proxy = proxy
        self._search_params = search_params
    
    def run(self):
        from services.elevenlabs import ElevenLabsAPI
        
        self.started.emit()
        api = ElevenLabsAPI()
        
        try:
            voices, has_more, error = api.browse_voice_library(
                api_key=self._api_key,
                proxy=self._proxy,
                **self._search_params
            )
            self.finished.emit(voices, has_more, error or "")
        except Exception as e:
            self.error.emit(str(e))


class RefreshVoicesWorker(QThread):
    """Worker for refreshing voices list"""
    
    started = pyqtSignal()
    finished = pyqtSignal(list)  # list of voices
    error = pyqtSignal(str)
    
    def __init__(self, api_key, proxy=None, parent=None):
        super().__init__(parent)
        self._api_key = api_key
        self._proxy = proxy
    
    def run(self):
        from services.elevenlabs import ElevenLabsAPI
        
        self.started.emit()
        api = ElevenLabsAPI()
        
        try:
            voices = api.get_voices(self._api_key, self._proxy)
            self.finished.emit(voices)
        except Exception as e:
            self.error.emit(str(e))


class RefreshCreditsWorker(QThread):
    """Worker for refreshing credits for all API keys"""
    
    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, api_keys: list, get_proxy_fn: Callable, parent=None):
        super().__init__(parent)
        self._api_keys = api_keys
        self._get_proxy_fn = get_proxy_fn
    
    def run(self):
        from services.elevenlabs import ElevenLabsAPI
        
        self.started.emit()
        api = ElevenLabsAPI()
        
        try:
            for key in self._api_keys:
                if key.enabled:
                    proxy = self._get_proxy_fn(key)
                    api.validate_key(key, proxy)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class VoicePreviewWorker(QThread):
    """Worker for generating voice preview audio"""
    
    started = pyqtSignal()
    finished = pyqtSignal(bool, str, str)  # success, output_path, message
    error = pyqtSignal(str)
    
    def __init__(self, text: str, voice_id: str, api_key, output_path: str,
                 settings=None, proxy=None, parent=None):
        super().__init__(parent)
        self._text = text
        self._voice_id = voice_id
        self._api_key = api_key
        self._output_path = output_path
        self._settings = settings
        self._proxy = proxy
    
    def run(self):
        from services.elevenlabs import ElevenLabsAPI
        from core.models import VoiceSettings
        
        self.started.emit()
        api = ElevenLabsAPI()
        
        settings = self._settings or VoiceSettings()
        
        try:
            success, message, duration = api.text_to_speech(
                text=self._text,
                voice_id=self._voice_id,
                api_key=self._api_key,
                output_path=self._output_path,
                settings=settings,
                proxy=self._proxy
            )
            self.finished.emit(success, self._output_path if success else "", message)
        except Exception as e:
            self.error.emit(str(e))


class CloneVoiceWorker(QThread):
    """Worker for cloning a voice"""
    
    started = pyqtSignal()
    progress = pyqtSignal(str)  # status message
    finished = pyqtSignal(object, str)  # voice or None, error message
    error = pyqtSignal(str)
    
    def __init__(self, name: str, files: list, api_key, description: str = None,
                 remove_noise: bool = False, proxy=None, parent=None):
        super().__init__(parent)
        self._name = name
        self._files = files
        self._api_key = api_key
        self._description = description
        self._remove_noise = remove_noise
        self._proxy = proxy
    
    def run(self):
        from services.elevenlabs import ElevenLabsAPI
        
        self.started.emit()
        self.progress.emit("Uploading and processing audio samples...")
        
        api = ElevenLabsAPI()
        
        try:
            voice, error = api.clone_voice(
                name=self._name,
                files=self._files,
                api_key=self._api_key,
                description=self._description,
                remove_background_noise=self._remove_noise,
                proxy=self._proxy
            )
            self.finished.emit(voice, error or "")
        except Exception as e:
            self.error.emit(str(e))
