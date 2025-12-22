"""ElevenLabs API service"""
import os
import time
import requests
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from datetime import datetime, timedelta
from pathlib import Path

from core.models import (
    APIKey, Proxy, Voice, VoiceSettings, TTSModel,
    TranscriptionResult, TranscriptionSegment, WordTimestamp, Speaker
)


class ResponseCache:
    """Simple in-memory cache for API responses"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._max_size = max_size
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if exists and not expired"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._ttl:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Cache a value"""
        # Evict oldest entries if cache is full
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        self._cache[key] = (value, datetime.now())
    
    def clear(self):
        """Clear the cache"""
        self._cache.clear()
    
    def invalidate(self, key: str):
        """Remove a specific key from cache"""
        if key in self._cache:
            del self._cache[key]


class ElevenLabsAPI:
    """ElevenLabs API client with proxy support and caching"""
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    def __init__(self, cache_enabled: bool = True):
        self._session = requests.Session()
        self._cache_enabled = cache_enabled
        self._cache = ResponseCache(max_size=100, ttl_seconds=300)
    
    def enable_cache(self, enabled: bool = True):
        """Enable or disable response caching"""
        self._cache_enabled = enabled
    
    def clear_cache(self):
        """Clear the response cache"""
        self._cache.clear()
    
    def _get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _get_proxies(self, proxy: Optional[Proxy]) -> Optional[Dict[str, str]]:
        if not proxy:
            return None
        proxy_url = proxy.get_url()
        return {"http": proxy_url, "https": proxy_url}
    
    def validate_key(self, api_key: APIKey, proxy: Optional[Proxy] = None) -> Tuple[bool, str]:
        """Validate an API key and fetch subscription info"""
        try:
            response = self._session.get(
                f"{self.BASE_URL}/user/subscription",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                api_key.character_count = data.get("character_count", 0)
                api_key.character_limit = data.get("character_limit", 0)
                api_key.is_valid = True
                return True, "Valid"
            elif response.status_code == 401:
                api_key.is_valid = False
                return False, "Invalid API key"
            else:
                return False, f"Error: {response.status_code}"
        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}"
    
    def get_voices(self, api_key: APIKey, proxy: Optional[Proxy] = None, use_cache: bool = True) -> List[Voice]:
        """Fetch available voices for an API key"""
        # Check cache first
        cache_key = f"voices_{api_key.key[:8]}"
        if use_cache and self._cache_enabled:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
        
        voices = []
        
        try:
            response = self._session.get(
                f"{self.BASE_URL}/voices",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                for v in data.get("voices", []):
                    voice = Voice(
                        voice_id=v["voice_id"],
                        name=v["name"],
                        is_cloned=v.get("category") == "cloned",
                        category=v.get("category", ""),
                        labels=v.get("labels", {})
                    )
                    voices.append(voice)
                
                # Cache the result
                if self._cache_enabled:
                    self._cache.set(cache_key, voices)
        except requests.RequestException:
            pass
        
        return voices
    
    def get_voice_by_id(self, voice_id: str, api_key: APIKey, proxy: Optional[Proxy] = None) -> Tuple[Optional[Voice], str]:
        """
        Fetch a specific voice by ID from ElevenLabs Voice Library
        Returns: (Voice or None, error message)
        """
        try:
            # First try to get the voice directly (works for voices in your account)
            response = self._session.get(
                f"{self.BASE_URL}/voices/{voice_id}",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                timeout=30
            )
            
            if response.status_code == 200:
                v = response.json()
                voice = Voice(
                    voice_id=v["voice_id"],
                    name=v["name"],
                    is_cloned=v.get("category") == "cloned",
                    category=v.get("category", ""),
                    labels=v.get("labels", {})
                )
                return voice, "Success"
            
            # If not found or error, try to add from Voice Library
            if response.status_code in (400, 404):
                return self._add_voice_from_library(voice_id, api_key, proxy)
            elif response.status_code == 401:
                return None, "Invalid API key"
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", str(error_msg))
                    return None, f"Error: {error_msg}"
                except:
                    return None, f"Error: {response.status_code}"
        except requests.RequestException as e:
            return None, f"Connection error: {str(e)}"
    
    def _add_voice_from_library(self, voice_id: str, api_key: APIKey, proxy: Optional[Proxy] = None) -> Tuple[Optional[Voice], str]:
        """
        Add a voice from the public Voice Library to the user's account
        """
        try:
            # Try to add the voice from the library
            # ElevenLabs endpoint: POST /v1/voices/add/{public_user_id}/{voice_id}
            # But we can also use the simpler approach of just using the voice ID directly
            
            # First, let's try to get voice info from shared voices endpoint
            response = self._session.get(
                f"{self.BASE_URL}/shared-voices",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                params={"search": voice_id, "page_size": 100},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                voices = data.get("voices", [])
                for v in voices:
                    if v.get("voice_id") == voice_id or v.get("public_owner_id") == voice_id:
                        voice = Voice(
                            voice_id=v.get("voice_id", voice_id),
                            name=v.get("name", "Library Voice"),
                            is_cloned=False,
                            category=v.get("category", "library"),
                            labels=v.get("labels", {})
                        )
                        return voice, "Success"
            
            # If still not found, create a placeholder voice that can be used directly
            # ElevenLabs allows using voice IDs from the library directly for TTS
            voice = Voice(
                voice_id=voice_id,
                name=f"Library Voice ({voice_id[:8]}...)",
                is_cloned=False,
                category="library",
                labels={}
            )
            return voice, "Success (Voice ID added - name may be updated after first use)"
            
        except requests.RequestException as e:
            return None, f"Connection error: {str(e)}"
    
    def search_voices(self, api_key: APIKey, proxy: Optional[Proxy] = None) -> List[Voice]:
        """Fetch voices from ElevenLabs public voice library"""
        voices = []
        
        try:
            # Get shared/public voices
            response = self._session.get(
                f"{self.BASE_URL}/shared-voices",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                params={"page_size": 100},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                for v in data.get("voices", []):
                    voice = Voice(
                        voice_id=v.get("voice_id", v.get("public_owner_id", "")),
                        name=v.get("name", "Unknown"),
                        is_cloned=False,
                        category=v.get("category", "library"),
                        labels=v.get("labels", {})
                    )
                    voices.append(voice)
        except requests.RequestException:
            pass
        
        return voices
    
    def browse_voice_library(
        self,
        api_key: APIKey,
        proxy: Optional[Proxy] = None,
        page_size: int = 30,
        search: Optional[str] = None,
        gender: Optional[str] = None,
        age: Optional[str] = None,
        accent: Optional[str] = None,
        language: Optional[str] = None,
        use_case: Optional[str] = None,
        category: Optional[str] = None,
        sort: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], bool, str]:
        """
        Browse the ElevenLabs public voice library with filtering options.
        
        Args:
            api_key: API key to use
            proxy: Optional proxy
            page_size: Number of results (max 100)
            search: Search query for voice name
            gender: Filter by gender (male, female, neutral)
            age: Filter by age (young, middle_aged, old)
            accent: Filter by accent (e.g., american, british)
            language: Filter by language code (e.g., en, es)
            use_case: Filter by use case (e.g., narration, conversational)
            category: Filter by category (e.g., professional, high_quality)
            sort: Sort order (e.g., trending, latest, usage_character_count_1y)
            
        Returns: (list of voice dicts, has_more, error_message)
        """
        voices = []
        
        params = {"page_size": min(page_size, 100)}
        
        if search:
            params["search"] = search
        if gender:
            params["gender"] = gender
        if age:
            params["age"] = age
        if accent:
            params["accent"] = accent
        if language:
            params["language"] = language
        if use_case:
            params["use_cases"] = use_case
        if category:
            params["category"] = category
        if sort:
            params["sort"] = sort
        
        try:
            response = self._session.get(
                f"{self.BASE_URL}/shared-voices",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                voices = data.get("voices", [])
                has_more = data.get("has_more", False)
                return voices, has_more, ""
            elif response.status_code == 401:
                return [], False, "Invalid API key"
            else:
                return [], False, f"HTTP {response.status_code}"
        except requests.RequestException as e:
            return [], False, f"Connection error: {str(e)}"
    
    def add_shared_voice(
        self,
        public_user_id: str,
        voice_id: str,
        new_name: str,
        api_key: APIKey,
        proxy: Optional[Proxy] = None
    ) -> Tuple[Optional[Voice], str]:
        """
        Add a voice from the public library to the user's account.
        
        Args:
            public_user_id: The public user ID of the voice owner
            voice_id: The voice ID to add
            new_name: Name for the voice in your account
            api_key: API key to use
            proxy: Optional proxy
            
        Returns: (Voice or None, error_message)
        """
        try:
            response = self._session.post(
                f"{self.BASE_URL}/voices/add/{public_user_id}/{voice_id}",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                json={"new_name": new_name},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                voice = Voice(
                    voice_id=data.get("voice_id", voice_id),
                    name=new_name,
                    is_cloned=False,
                    category="library",
                    labels={}
                )
                # Invalidate voices cache
                self._cache.invalidate(f"voices_{api_key.key[:8]}")
                return voice, "Success"
            elif response.status_code == 401:
                return None, "Invalid API key"
            elif response.status_code == 422:
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", {})
                    if isinstance(detail, dict):
                        return None, detail.get("message", "Voice already added or invalid")
                    return None, str(detail)
                except:
                    return None, "Voice already added or invalid"
            else:
                return None, f"HTTP {response.status_code}"
        except requests.RequestException as e:
            return None, f"Connection error: {str(e)}"
    
    def get_models(self, api_key: APIKey, proxy: Optional[Proxy] = None) -> List[Dict[str, Any]]:
        """Fetch available models"""
        models = []
        
        try:
            response = self._session.get(
                f"{self.BASE_URL}/models",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                timeout=30
            )
            
            if response.status_code == 200:
                models = response.json()
        except requests.RequestException:
            pass
        
        return models
    
    def clone_voice(
        self,
        name: str,
        files: List[str],
        api_key: APIKey,
        description: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        remove_background_noise: bool = False,
        proxy: Optional[Proxy] = None
    ) -> Tuple[Optional[Voice], str]:
        """
        Clone a voice using ElevenLabs Instant Voice Cloning (IVC) API.
        
        Args:
            name: Name for the cloned voice
            files: List of file paths to audio samples (supports mp3, wav, m4a, etc.)
            api_key: API key to use
            description: Optional description for the voice
            labels: Optional dictionary of labels/tags for the voice
            remove_background_noise: Whether to remove background noise from samples
            proxy: Optional proxy to use
            
        Returns: (Voice or None, error_message)
        """
        url = f"{self.BASE_URL}/voices/add"
        
        # Validate files exist
        for file_path in files:
            if not os.path.exists(file_path):
                return None, f"File not found: {file_path}"
        
        headers = {"xi-api-key": api_key.key}
        
        try:
            # Prepare multipart form data
            form_files = []
            opened_files = []
            
            for file_path in files:
                f = open(file_path, 'rb')
                opened_files.append(f)
                form_files.append(('files', (os.path.basename(file_path), f)))
            
            data = {
                'name': name,
                'remove_background_noise': str(remove_background_noise).lower()
            }
            
            if description:
                data['description'] = description
            
            if labels:
                import json
                data['labels'] = json.dumps(labels)
            
            response = self._session.post(
                url,
                headers=headers,
                files=form_files,
                data=data,
                proxies=self._get_proxies(proxy),
                timeout=120
            )
            
            # Close all opened files
            for f in opened_files:
                f.close()
            
            if response.status_code == 200:
                result = response.json()
                voice_id = result.get("voice_id")
                
                voice = Voice(
                    voice_id=voice_id,
                    name=name,
                    is_cloned=True,
                    category="cloned",
                    labels=labels or {}
                )
                
                # Invalidate voices cache
                self._cache.invalidate(f"voices_{api_key.key[:8]}")
                
                return voice, "Success"
            
            elif response.status_code == 401:
                return None, "Invalid API key"
            
            elif response.status_code == 422:
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", {})
                    if isinstance(detail, dict):
                        return None, detail.get("message", "Invalid request - check audio files")
                    elif isinstance(detail, list) and detail:
                        return None, str(detail[0].get("msg", detail))
                    return None, str(detail)
                except:
                    return None, "Invalid request - check audio files format and quality"
            
            elif response.status_code == 429:
                return None, "Rate limited - please try again later"
            
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", str(error_msg))
                    return None, f"HTTP {response.status_code}: {error_msg}"
                except:
                    return None, f"HTTP {response.status_code}"
                    
        except requests.Timeout:
            return None, "Request timeout - files may be too large"
        except requests.RequestException as e:
            return None, f"Connection error: {str(e)}"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"
        finally:
            # Ensure files are closed even on error
            for f in opened_files:
                try:
                    f.close()
                except:
                    pass
    
    def delete_voice(
        self,
        voice_id: str,
        api_key: APIKey,
        proxy: Optional[Proxy] = None
    ) -> Tuple[bool, str]:
        """
        Delete a voice from the account.
        
        Args:
            voice_id: ID of the voice to delete
            api_key: API key to use
            proxy: Optional proxy to use
            
        Returns: (success, error_message)
        """
        url = f"{self.BASE_URL}/voices/{voice_id}"
        
        try:
            response = self._session.delete(
                url,
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                timeout=30
            )
            
            if response.status_code == 200:
                # Invalidate voices cache
                self._cache.invalidate(f"voices_{api_key.key[:8]}")
                return True, "Success"
            
            elif response.status_code == 401:
                return False, "Invalid API key"
            
            elif response.status_code == 404:
                return False, "Voice not found"
            
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", str(error_msg))
                    return False, f"HTTP {response.status_code}: {error_msg}"
                except:
                    return False, f"HTTP {response.status_code}"
                    
        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}"
    
    def edit_voice(
        self,
        voice_id: str,
        api_key: APIKey,
        name: Optional[str] = None,
        description: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        files: Optional[List[str]] = None,
        remove_background_noise: bool = False,
        proxy: Optional[Proxy] = None
    ) -> Tuple[bool, str]:
        """
        Edit an existing voice (update name, description, labels, or add more samples).
        
        Args:
            voice_id: ID of the voice to edit
            api_key: API key to use
            name: New name for the voice (optional)
            description: New description (optional)
            labels: New labels dictionary (optional)
            files: Additional audio files to add (optional)
            remove_background_noise: Whether to remove background noise from new samples
            proxy: Optional proxy to use
            
        Returns: (success, error_message)
        """
        url = f"{self.BASE_URL}/voices/{voice_id}/edit"
        
        headers = {"xi-api-key": api_key.key}
        opened_files = []
        
        try:
            data = {}
            form_files = []
            
            if name:
                data['name'] = name
            if description:
                data['description'] = description
            if labels:
                import json
                data['labels'] = json.dumps(labels)
            
            if files:
                data['remove_background_noise'] = str(remove_background_noise).lower()
                for file_path in files:
                    if not os.path.exists(file_path):
                        return False, f"File not found: {file_path}"
                    f = open(file_path, 'rb')
                    opened_files.append(f)
                    form_files.append(('files', (os.path.basename(file_path), f)))
            
            response = self._session.post(
                url,
                headers=headers,
                files=form_files if form_files else None,
                data=data,
                proxies=self._get_proxies(proxy),
                timeout=120
            )
            
            # Close all opened files
            for f in opened_files:
                f.close()
            
            if response.status_code == 200:
                # Invalidate voices cache
                self._cache.invalidate(f"voices_{api_key.key[:8]}")
                return True, "Success"
            
            elif response.status_code == 401:
                return False, "Invalid API key"
            
            elif response.status_code == 404:
                return False, "Voice not found"
            
            elif response.status_code == 422:
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", {})
                    if isinstance(detail, dict):
                        return False, detail.get("message", "Invalid request")
                    return False, str(detail)
                except:
                    return False, "Invalid request"
            
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("detail", {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get("message", str(error_msg))
                    return False, f"HTTP {response.status_code}: {error_msg}"
                except:
                    return False, f"HTTP {response.status_code}"
                    
        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}"
        finally:
            for f in opened_files:
                try:
                    f.close()
                except:
                    pass
    
    def text_to_speech(
        self,
        text: str,
        voice_id: str,
        api_key: APIKey,
        output_path: str,
        settings: Optional[VoiceSettings] = None,
        proxy: Optional[Proxy] = None
    ) -> Tuple[bool, str, Optional[float]]:
        """
        Convert text to speech
        Returns: (success, message, audio_duration)
        """
        if settings is None:
            settings = VoiceSettings()
        
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        
        payload = {
            "text": text,
            "model_id": settings.model.value,
            "voice_settings": {
                "stability": settings.stability,
                "similarity_boost": settings.similarity_boost,
                "style": settings.style,
                "use_speaker_boost": settings.use_speaker_boost,
                "speed": settings.speed
            }
        }
        
        headers = self._get_headers(api_key.key)
        headers["Accept"] = "audio/mpeg"
        
        # Build debug info
        proxy_info = f" via proxy {proxy.host}:{proxy.port}" if proxy else ""
        debug_info = f"[voice={voice_id}, model={settings.model.value}, key={api_key.key[:8]}...{proxy_info}]"
        
        try:
            response = self._session.post(
                url,
                json=payload,
                headers=headers,
                proxies=self._get_proxies(proxy),
                timeout=120,
                stream=True
            )
            
            if response.status_code == 200:
                # Save audio file
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Get audio duration
                duration = self._get_audio_duration(output_path)
                
                return True, "Success", duration
            
            elif response.status_code == 429:
                return False, "RATE_LIMIT", None
            
            elif response.status_code == 401:
                api_key.is_valid = False
                return False, f"Invalid API key {debug_info}", None
            
            else:
                try:
                    error_data = response.json()
                    if isinstance(error_data.get("detail"), dict):
                        error_msg = error_data["detail"].get("message", str(error_data["detail"]))
                    elif isinstance(error_data.get("detail"), str):
                        error_msg = error_data["detail"]
                    else:
                        error_msg = str(error_data)
                except:
                    error_msg = response.text[:500] if response.text else "No response body"
                return False, f"HTTP {response.status_code}: {error_msg} {debug_info}", None
                
        except requests.Timeout as e:
            return False, f"Request timeout after 120s {debug_info}: {type(e).__name__}", None
        except requests.exceptions.ProxyError as e:
            return False, f"Proxy error {debug_info}: {type(e).__name__} - {str(e)}", None
        except requests.exceptions.SSLError as e:
            return False, f"SSL error {debug_info}: {type(e).__name__} - {str(e)}", None
        except requests.exceptions.ConnectionError as e:
            return False, f"Connection error {debug_info}: {type(e).__name__} - {str(e)}", None
        except requests.RequestException as e:
            return False, f"Request error {debug_info}: {type(e).__name__} - {str(e)}", None
        except Exception as e:
            return False, f"Unexpected error {debug_info}: {type(e).__name__} - {str(e)}", None
    
    def _get_audio_duration(self, file_path: str) -> Optional[float]:
        """Get duration of audio file in seconds"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(file_path)
            return len(audio) / 1000.0  # Convert ms to seconds
        except:
            # Fallback: estimate from file size (rough approximation)
            try:
                file_size = os.path.getsize(file_path)
                # Assume ~128kbps MP3
                return file_size / (128 * 1024 / 8)
            except:
                return None
    
    def refresh_subscription(self, api_key: APIKey, proxy: Optional[Proxy] = None) -> bool:
        """Refresh subscription info for an API key"""
        success, _ = self.validate_key(api_key, proxy)
        return success
    
    # Speech-to-Text (Scribe) Methods
    
    def transcribe(
        self,
        file_path: str,
        api_key: APIKey,
        language: Optional[str] = None,
        diarize: bool = False,
        num_speakers: Optional[int] = None,
        proxy: Optional[Proxy] = None
    ) -> Tuple[bool, str, Optional[TranscriptionResult]]:
        """
        Transcribe audio/video file using ElevenLabs Scribe API
        
        Args:
            file_path: Path to audio/video file
            api_key: API key to use
            language: Language code (e.g., 'en', 'vi') or None for auto-detect
            diarize: Enable speaker diarization
            num_speakers: Expected number of speakers (None for auto-detect)
            proxy: Optional proxy to use
            
        Returns: (success, message, TranscriptionResult or None)
        """
        url = f"{self.BASE_URL}/speech-to-text"
        
        # Validate file size (3GB limit)
        file_size = os.path.getsize(file_path)
        max_size = 3 * 1024 * 1024 * 1024  # 3GB
        if file_size > max_size:
            return False, f"File too large: {file_size / (1024**3):.2f}GB exceeds 3GB limit", None
        
        headers = {"xi-api-key": api_key.key}
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                
                data = {
                    'model_id': 'scribe_v1',
                    'timestamps_granularity': 'word'
                }
                
                if language:
                    data['language_code'] = language
                
                if diarize:
                    data['diarize'] = 'true'
                    if num_speakers:
                        data['num_speakers'] = str(num_speakers)
                
                response = self._session.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    proxies=self._get_proxies(proxy),
                    timeout=600  # 10 min timeout for large files
                )
            
            if response.status_code == 200:
                result_data = response.json()
                result = self._parse_transcription_result(result_data)
                return True, "Success", result
            
            elif response.status_code == 401:
                api_key.is_valid = False
                return False, "Invalid API key", None
            
            elif response.status_code == 429:
                return False, "RATE_LIMIT", None
            
            else:
                try:
                    error_data = response.json()
                    if isinstance(error_data.get("detail"), dict):
                        error_msg = error_data["detail"].get("message", str(error_data["detail"]))
                    elif isinstance(error_data.get("detail"), str):
                        error_msg = error_data["detail"]
                    else:
                        error_msg = str(error_data)
                except:
                    error_msg = response.text[:500] if response.text else "No response body"
                return False, f"HTTP {response.status_code}: {error_msg}", None
                
        except requests.Timeout:
            return False, "Request timeout - file may be too large", None
        except requests.RequestException as e:
            return False, f"Request error: {str(e)}", None
        except Exception as e:
            return False, f"Unexpected error: {str(e)}", None
    
    def _parse_transcription_result(self, data: Dict[str, Any]) -> TranscriptionResult:
        """Parse API response into TranscriptionResult"""
        segments = []
        speakers_dict = {}
        
        # Get full text first (always present in response)
        full_text = data.get("text", "")
        language = data.get("language_code", data.get("detected_language", "unknown"))
        
        # Parse words with timestamps if available
        words_data = data.get("words", [])
        
        if words_data:
            # Group words into segments (by sentence or speaker change)
            current_segment_words = []
            current_speaker = None
            segment_start = 0.0
            
            for word_data in words_data:
                word = WordTimestamp(
                    text=word_data.get("text", word_data.get("word", "")),
                    start=word_data.get("start", 0.0),
                    end=word_data.get("end", 0.0)
                )
                
                word_speaker = word_data.get("speaker_id", word_data.get("speaker"))
                
                # Track speakers
                if word_speaker and word_speaker not in speakers_dict:
                    speakers_dict[word_speaker] = Speaker(id=str(word_speaker))
                
                # Check for segment boundary (speaker change or long pause)
                should_break = False
                if current_segment_words:
                    last_word = current_segment_words[-1]
                    gap = word.start - last_word.end
                    # Break on speaker change or >1s pause
                    if (word_speaker != current_speaker and current_speaker is not None) or gap > 1.0:
                        should_break = True
                
                if should_break and current_segment_words:
                    # Create segment from accumulated words
                    segment_text = " ".join(w.text for w in current_segment_words)
                    segments.append(TranscriptionSegment(
                        start=segment_start,
                        end=current_segment_words[-1].end,
                        text=segment_text.strip(),
                        speaker_id=str(current_speaker) if current_speaker else None,
                        words=current_segment_words
                    ))
                    current_segment_words = []
                    segment_start = word.start
                
                if not current_segment_words:
                    segment_start = word.start
                    current_speaker = word_speaker
                
                current_segment_words.append(word)
            
            # Add final segment
            if current_segment_words:
                segment_text = " ".join(w.text for w in current_segment_words)
                segments.append(TranscriptionSegment(
                    start=segment_start,
                    end=current_segment_words[-1].end,
                    text=segment_text.strip(),
                    speaker_id=str(current_speaker) if current_speaker else None,
                    words=current_segment_words
                ))
        else:
            # No word-level timestamps, create single segment from full text
            if full_text:
                segments.append(TranscriptionSegment(
                    start=0.0,
                    end=0.0,
                    text=full_text,
                    speaker_id=None,
                    words=[]
                ))
        
        return TranscriptionResult(
            text=full_text,
            language=language,
            segments=segments,
            speakers=list(speakers_dict.values())
        )
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages for STT"""
        return [
            {"code": "en", "name": "English"},
            {"code": "vi", "name": "Vietnamese"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ko", "name": "Korean"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "it", "name": "Italian"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "ru", "name": "Russian"},
            {"code": "ar", "name": "Arabic"},
            {"code": "hi", "name": "Hindi"},
            {"code": "th", "name": "Thai"},
            {"code": "id", "name": "Indonesian"},
            {"code": "nl", "name": "Dutch"},
            {"code": "pl", "name": "Polish"},
            {"code": "sv", "name": "Swedish"},
            {"code": "tr", "name": "Turkish"},
            {"code": "uk", "name": "Ukrainian"},
        ]
    
    def get_transcription_usage(self, api_key: APIKey, proxy: Optional[Proxy] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Get STT usage information for an API key
        
        Returns: (success, usage_data)
        usage_data contains: {
            'stt_characters_used': int,
            'stt_characters_limit': int,
            'stt_characters_remaining': int
        }
        """
        try:
            response = self._session.get(
                f"{self.BASE_URL}/user/subscription",
                headers=self._get_headers(api_key.key),
                proxies=self._get_proxies(proxy),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract STT-specific usage if available
                usage = {
                    'stt_characters_used': data.get('stt_character_count', 0),
                    'stt_characters_limit': data.get('stt_character_limit', 0),
                    'stt_characters_remaining': max(0, data.get('stt_character_limit', 0) - data.get('stt_character_count', 0)),
                    'tts_characters_used': data.get('character_count', 0),
                    'tts_characters_limit': data.get('character_limit', 0),
                    'tier': data.get('tier', 'unknown')
                }
                return True, usage
            else:
                return False, {'error': f'HTTP {response.status_code}'}
        except requests.RequestException as e:
            return False, {'error': str(e)}


class APIKeyManager:
    """Manages multiple API keys with rotation"""
    
    MIN_CREDIT_THRESHOLD = 500  # Minimum credits required to use a key
    
    def __init__(self, api_keys: List[APIKey], on_key_removed: Optional[callable] = None):
        self._keys = api_keys
        self._current_index = 0
        self._api = ElevenLabsAPI()
        self._on_key_removed = on_key_removed  # Callback when key is removed due to low credits
    
    @property
    def keys(self) -> List[APIKey]:
        return self._keys
    
    def check_and_remove_low_credit_keys(self) -> List[APIKey]:
        """Check all keys and remove those with credits below threshold.
        Returns list of removed keys."""
        removed_keys = []
        keys_to_keep = []
        
        for key in self._keys:
            if key.is_valid and key.remaining_credits < self.MIN_CREDIT_THRESHOLD:
                removed_keys.append(key)
                if self._on_key_removed:
                    self._on_key_removed(key, f"Credits below {self.MIN_CREDIT_THRESHOLD} (has {key.remaining_credits})")
            else:
                keys_to_keep.append(key)
        
        self._keys = keys_to_keep
        
        # Reset index if needed
        if self._current_index >= len(self._keys):
            self._current_index = 0
        
        return removed_keys
    
    def get_next_available_key(self) -> Optional[APIKey]:
        """Get the next available API key with at least MIN_CREDIT_THRESHOLD credits.
        Keys with less than threshold credits are automatically removed."""
        if not self._keys:
            return None
        
        # First, check and remove keys with low credits
        self.check_and_remove_low_credit_keys()
        
        if not self._keys:
            return None
        
        # Try starting from current index
        for _ in range(len(self._keys)):
            key = self._keys[self._current_index]
            self._current_index = (self._current_index + 1) % len(self._keys)
            
            # Check if key is available and has enough credits
            if key.is_available and key.remaining_credits >= self.MIN_CREDIT_THRESHOLD:
                return key
        
        return None
    
    def mark_key_rate_limited(self, key: APIKey, cooldown_seconds: int = 60):
        """Mark a key as rate limited"""
        key.in_cooldown = True
        key.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
    
    def mark_key_exhausted(self, key: APIKey):
        """Mark a key as quota exhausted"""
        key.character_count = key.character_limit
    
    def get_total_credits(self) -> int:
        """Get total remaining credits across all keys"""
        return sum(k.remaining_credits for k in self._keys if k.is_valid and k.enabled)
    
    def refresh_all_keys(self, proxies: Optional[List[Proxy]] = None) -> List[Tuple[APIKey, bool, str]]:
        """Refresh subscription info for all keys"""
        results = []
        proxy_map = {}
        
        if proxies:
            for p in proxies:
                proxy_map[p.id] = p
        
        for key in self._keys:
            proxy = proxy_map.get(key.assigned_proxy_id) if key.assigned_proxy_id else None
            success, msg = self._api.validate_key(key, proxy)
            results.append((key, success, msg))
        
        return results
    
    def all_keys_exhausted(self) -> bool:
        """Check if all keys are exhausted or unavailable"""
        return all(not k.is_available for k in self._keys)
