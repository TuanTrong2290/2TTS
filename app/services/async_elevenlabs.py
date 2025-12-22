"""Async ElevenLabs API service using aiohttp"""
import os
import asyncio
import aiohttp
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from core.models import APIKey, Proxy, Voice, VoiceSettings, TTSModel
from services.logger import get_logger


class AsyncResponseCache:
    """Thread-safe async cache for API responses"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._max_size = max_size
        self._ttl = timedelta(seconds=ttl_seconds)
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if datetime.now() - timestamp < self._ttl:
                    return value
                del self._cache[key]
        return None
    
    async def set(self, key: str, value: Any):
        async with self._lock:
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (value, datetime.now())
    
    async def clear(self):
        async with self._lock:
            self._cache.clear()


class AsyncElevenLabsAPI:
    """Async ElevenLabs API client"""
    
    BASE_URL = "https://api.elevenlabs.io/v1"
    
    def __init__(self, cache_enabled: bool = True):
        self._cache_enabled = cache_enabled
        self._cache = AsyncResponseCache(max_size=100, ttl_seconds=300)
        self._logger = get_logger()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=120, connect=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _get_headers(self, api_key: str) -> Dict[str, str]:
        return {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _get_proxy_url(self, proxy: Optional[Proxy]) -> Optional[str]:
        if not proxy:
            return None
        return proxy.get_url()
    
    async def validate_key(self, api_key: APIKey, proxy: Optional[Proxy] = None) -> Tuple[bool, str]:
        """Validate an API key and fetch subscription info"""
        start_time = datetime.now()
        
        try:
            session = await self._get_session()
            proxy_url = self._get_proxy_url(proxy)
            
            async with session.get(
                f"{self.BASE_URL}/user/subscription",
                headers=self._get_headers(api_key.key),
                proxy=proxy_url
            ) as response:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    api_key.character_count = data.get("character_count", 0)
                    api_key.character_limit = data.get("character_limit", 0)
                    api_key.is_valid = True
                    
                    self._logger.api_request("validate_key", "SUCCESS", duration_ms)
                    return True, "Valid"
                elif response.status == 401:
                    api_key.is_valid = False
                    self._logger.api_request("validate_key", "INVALID_KEY", duration_ms)
                    return False, "Invalid API key"
                else:
                    self._logger.api_request("validate_key", f"ERROR_{response.status}", duration_ms)
                    return False, f"Error: {response.status}"
                    
        except asyncio.TimeoutError:
            self._logger.api_request("validate_key", "TIMEOUT", 0)
            return False, "Connection timeout"
        except aiohttp.ClientError as e:
            self._logger.api_request("validate_key", "CONNECTION_ERROR", 0, str(e))
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            self._logger.error(f"Validate key error: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    async def get_voices(
        self,
        api_key: APIKey,
        proxy: Optional[Proxy] = None,
        use_cache: bool = True
    ) -> List[Voice]:
        """Fetch available voices for an API key"""
        cache_key = f"voices_{api_key.key[:8]}"
        
        if use_cache and self._cache_enabled:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached
        
        voices = []
        start_time = datetime.now()
        
        try:
            session = await self._get_session()
            proxy_url = self._get_proxy_url(proxy)
            
            async with session.get(
                f"{self.BASE_URL}/voices",
                headers=self._get_headers(api_key.key),
                proxy=proxy_url
            ) as response:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    data = await response.json()
                    for v in data.get("voices", []):
                        voice = Voice(
                            voice_id=v["voice_id"],
                            name=v["name"],
                            is_cloned=v.get("category") == "cloned",
                            category=v.get("category", ""),
                            labels=v.get("labels", {})
                        )
                        voices.append(voice)
                    
                    if self._cache_enabled:
                        await self._cache.set(cache_key, voices)
                    
                    self._logger.api_request("get_voices", "SUCCESS", duration_ms, f"count={len(voices)}")
                else:
                    self._logger.api_request("get_voices", f"ERROR_{response.status}", duration_ms)
                    
        except Exception as e:
            self._logger.error(f"Get voices error: {e}")
        
        return voices
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: str,
        api_key: APIKey,
        output_path: str,
        settings: Optional[VoiceSettings] = None,
        proxy: Optional[Proxy] = None
    ) -> Tuple[bool, str, Optional[float]]:
        """Convert text to speech asynchronously"""
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
        
        proxy_info = f" via proxy {proxy.host}:{proxy.port}" if proxy else ""
        debug_info = f"[voice={voice_id[:8]}..., model={settings.model.value}, key={api_key.key[:8]}...{proxy_info}]"
        
        start_time = datetime.now()
        
        try:
            session = await self._get_session()
            proxy_url = self._get_proxy_url(proxy)
            
            async with session.post(
                url,
                json=payload,
                headers=headers,
                proxy=proxy_url
            ) as response:
                duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    with open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    audio_duration = await self._get_audio_duration(output_path)
                    
                    self._logger.tts_request(voice_id, len(text), True, duration_ms)
                    return True, "Success", audio_duration
                
                elif response.status == 429:
                    self._logger.tts_request(voice_id, len(text), False, duration_ms, "RATE_LIMIT")
                    return False, "RATE_LIMIT", None
                
                elif response.status == 401:
                    api_key.is_valid = False
                    self._logger.tts_request(voice_id, len(text), False, duration_ms, "INVALID_KEY")
                    return False, f"Invalid API key {debug_info}", None
                
                else:
                    try:
                        error_data = await response.json()
                        if isinstance(error_data.get("detail"), dict):
                            error_msg = error_data["detail"].get("message", str(error_data["detail"]))
                        elif isinstance(error_data.get("detail"), str):
                            error_msg = error_data["detail"]
                        else:
                            error_msg = str(error_data)
                    except:
                        error_msg = await response.text()
                        error_msg = error_msg[:500] if error_msg else "No response body"
                    
                    self._logger.tts_request(voice_id, len(text), False, duration_ms, error_msg[:100])
                    return False, f"HTTP {response.status}: {error_msg} {debug_info}", None
        
        except asyncio.TimeoutError:
            self._logger.tts_request(voice_id, len(text), False, 0, "TIMEOUT")
            return False, f"Request timeout {debug_info}", None
        except aiohttp.ClientProxyConnectionError as e:
            self._logger.tts_request(voice_id, len(text), False, 0, f"PROXY_ERROR: {e}")
            return False, f"Proxy error {debug_info}: {str(e)}", None
        except aiohttp.ClientError as e:
            self._logger.tts_request(voice_id, len(text), False, 0, f"CLIENT_ERROR: {e}")
            return False, f"Connection error {debug_info}: {str(e)}", None
        except Exception as e:
            self._logger.error(f"TTS error: {e}", exc_info=True)
            return False, f"Unexpected error {debug_info}: {str(e)}", None
    
    async def _get_audio_duration(self, file_path: str) -> Optional[float]:
        """Get duration of audio file"""
        try:
            from pydub import AudioSegment
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(None, AudioSegment.from_mp3, file_path)
            return len(audio) / 1000.0
        except:
            try:
                file_size = os.path.getsize(file_path)
                return file_size / (128 * 1024 / 8)
            except:
                return None
    
    async def get_voice_by_id(
        self,
        voice_id: str,
        api_key: APIKey,
        proxy: Optional[Proxy] = None
    ) -> Tuple[Optional[Voice], str]:
        """Fetch a specific voice by ID"""
        try:
            session = await self._get_session()
            proxy_url = self._get_proxy_url(proxy)
            
            async with session.get(
                f"{self.BASE_URL}/voices/{voice_id}",
                headers=self._get_headers(api_key.key),
                proxy=proxy_url
            ) as response:
                if response.status == 200:
                    v = await response.json()
                    voice = Voice(
                        voice_id=v["voice_id"],
                        name=v["name"],
                        is_cloned=v.get("category") == "cloned",
                        category=v.get("category", ""),
                        labels=v.get("labels", {})
                    )
                    return voice, "Success"
                
                elif response.status in (400, 404):
                    voice = Voice(
                        voice_id=voice_id,
                        name=f"Library Voice ({voice_id[:8]}...)",
                        is_cloned=False,
                        category="library",
                        labels={}
                    )
                    return voice, "Success (Voice ID added)"
                
                elif response.status == 401:
                    return None, "Invalid API key"
                else:
                    return None, f"Error: {response.status}"
                    
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    async def preview_voice(
        self,
        voice_id: str,
        api_key: APIKey,
        text: str = "Hello! This is a voice preview sample.",
        settings: Optional[VoiceSettings] = None,
        proxy: Optional[Proxy] = None
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Generate voice preview and return audio bytes"""
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
        
        try:
            session = await self._get_session()
            proxy_url = self._get_proxy_url(proxy)
            
            async with session.post(
                url,
                json=payload,
                headers=headers,
                proxy=proxy_url
            ) as response:
                if response.status == 200:
                    audio_data = await response.read()
                    return True, "Success", audio_data
                else:
                    return False, f"Error: {response.status}", None
                    
        except Exception as e:
            return False, str(e), None


class AsyncAPIKeyManager:
    """Manages multiple API keys with async rotation"""
    
    def __init__(self, api_keys: List[APIKey]):
        self._keys = api_keys
        self._current_index = 0
        self._api = AsyncElevenLabsAPI()
        self._lock = asyncio.Lock()
    
    @property
    def keys(self) -> List[APIKey]:
        return self._keys
    
    async def get_next_available_key(self) -> Optional[APIKey]:
        async with self._lock:
            if not self._keys:
                return None
            
            for _ in range(len(self._keys)):
                key = self._keys[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._keys)
                
                if key.is_available:
                    return key
            
            return None
    
    def mark_key_rate_limited(self, key: APIKey, cooldown_seconds: int = 60):
        key.in_cooldown = True
        key.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
    
    def mark_key_exhausted(self, key: APIKey):
        key.character_count = key.character_limit
    
    def get_total_credits(self) -> int:
        return sum(k.remaining_credits for k in self._keys if k.is_valid and k.enabled)
    
    async def refresh_all_keys(self, proxies: Optional[List[Proxy]] = None) -> List[Tuple[APIKey, bool, str]]:
        results = []
        proxy_map = {}
        
        if proxies:
            for p in proxies:
                proxy_map[p.id] = p
        
        for key in self._keys:
            proxy = proxy_map.get(key.assigned_proxy_id) if key.assigned_proxy_id else None
            success, msg = await self._api.validate_key(key, proxy)
            results.append((key, success, msg))
        
        return results
    
    def all_keys_exhausted(self) -> bool:
        return all(not k.is_available for k in self._keys)
    
    async def close(self):
        await self._api.close()
