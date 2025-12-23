"""JSON-RPC method handlers"""
import os
import sys
import uuid
import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .server import JsonRpcServer
from .types import JsonRpcError, ErrorCodes

# Import existing services from the app
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

from core.config import get_config
from core.models import APIKey, Proxy, Voice, VoiceSettings
from services.elevenlabs import ElevenLabsAPI

# Global API instance
_elevenlabs_api: Optional[ElevenLabsAPI] = None

def get_api() -> ElevenLabsAPI:
    global _elevenlabs_api
    if _elevenlabs_api is None:
        _elevenlabs_api = ElevenLabsAPI()
    return _elevenlabs_api


BACKEND_VERSION = "1.2.4"
PROTOCOL_VERSION = 1
MIN_UI_VERSION = "1.0.0"


def register_handlers(server: JsonRpcServer):
    """Register all RPC handlers"""
    
    @server.method("system.handshake")
    def handshake(params: dict, srv: JsonRpcServer) -> dict:
        ui_version = params.get("ui_version", "0.0.0")
        protocol = params.get("protocol_version", 0)
        
        compatible = protocol == PROTOCOL_VERSION
        
        # Track new session in analytics
        try:
            from services.analytics import get_analytics
            analytics = get_analytics()
            analytics._stats.total_sessions += 1
            analytics._force_save_stats()
        except Exception:
            pass
        
        return {
            "ui_version": ui_version,
            "backend_version": BACKEND_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "compatible": compatible,
            "min_ui_version": MIN_UI_VERSION
        }
    
    @server.method("system.shutdown")
    def shutdown(params: dict, srv: JsonRpcServer) -> dict:
        srv._running = False
        return {"status": "shutting_down"}
    
    @server.method("system.export_diagnostics")
    def export_diagnostics(params: dict, srv: JsonRpcServer) -> str:
        config = get_config()
        local_appdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        diagnostics_dir = Path(local_appdata) / "2TTS" / "diagnostics"
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        diag_file = diagnostics_dir / f"diagnostics_{timestamp}.json"
        
        diagnostics = {
            "timestamp": timestamp,
            "versions": {
                "backend": BACKEND_VERSION,
                "protocol": PROTOCOL_VERSION
            },
            "system": {
                "os": platform.system(),
                "os_version": platform.version(),
                "python_version": platform.python_version()
            },
            "config": {
                "theme": config.theme,
                "app_language": config.app_language,
                "thread_count": config.get("thread_count", 5),
                "api_keys_count": len(config.api_keys),
                "proxies_count": len(config.proxies)
            }
        }
        
        with open(diag_file, "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)
        
        return str(diag_file)
    
    @server.method("config.get")
    def config_get(params: dict, srv: JsonRpcServer) -> dict:
        config = get_config()
        return {
            "theme": config.theme,
            "app_language": config.app_language,
            "default_output_folder": config.default_output_folder,
            "thread_count": config.get("thread_count", 5),
            "max_retries": config.get("max_retries", 3),
            "auto_split_enabled": config.get("auto_split_enabled", True),
            "split_delimiter": config.get("split_delimiter", ".,?!;"),
            "max_chars": config.get("max_chars", 5000),
            "silence_gap": config.get("silence_gap", 0.0),
            "low_credit_threshold": config.get("low_credit_threshold", 1000),
            "pause_enabled": config.get("pause_enabled", False),
            "short_pause_duration": config.get("short_pause_duration", 300),
            "long_pause_duration": config.get("long_pause_duration", 700),
            "short_pause_punctuation": config.get("short_pause_punctuation", ",;:"),
            "long_pause_punctuation": config.get("long_pause_punctuation", ".!?。！？")
        }
    
    @server.method("config.set")
    def config_set(params: dict, srv: JsonRpcServer) -> dict:
        key = params.get("key")
        value = params.get("value")
        
        if not key:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Key is required")
        
        config = get_config()
        config.set(key, value)
        
        return {"success": True}
    
    @server.method("apikeys.list")
    def apikeys_list(params: dict, srv: JsonRpcServer) -> List[dict]:
        config = get_config()
        return [
            {
                "id": k.id,
                "name": k.name,
                "key": k.key,
                "remaining_credits": k.remaining_credits,
                "character_count": k.character_count,
                "character_limit": k.character_limit,
                "is_valid": k.is_valid,
                "enabled": k.enabled,
                "assigned_proxy_id": k.assigned_proxy_id
            }
            for k in config.api_keys
        ]
    
    @server.method("apikeys.status")
    def apikeys_status(params: dict, srv: JsonRpcServer) -> dict:
        """Get API key usage status"""
        config = get_config()
        
        all_keys = config.api_keys
        active_key = config.get_available_api_key()
        
        # Get exhausted keys (0 credits or invalid)
        exhausted_keys = [
            {
                "id": k.id,
                "key": f"{k.key[:8]}...{k.key[-4:]}",
                "remaining_credits": k.remaining_credits,
                "is_valid": k.is_valid
            }
            for k in all_keys
            if k.remaining_credits <= 0 or not k.is_valid
        ]
        
        # Get available keys sorted by credits (smallest first)
        available_keys = [
            {
                "id": k.id,
                "key": f"{k.key[:8]}...{k.key[-4:]}",
                "remaining_credits": k.remaining_credits,
                "is_active": active_key and k.id == active_key.id
            }
            for k in sorted(
                [k for k in all_keys if k.is_available],
                key=lambda x: x.remaining_credits
            )
        ]
        
        return {
            "active_key": {
                "id": active_key.id,
                "key": f"{active_key.key[:8]}...{active_key.key[-4:]}",
                "remaining_credits": active_key.remaining_credits
            } if active_key else None,
            "available_keys": available_keys,
            "exhausted_keys": exhausted_keys,
            "total_credits": config.get_total_credits(),
            "total_keys": len(all_keys),
            "available_count": len(available_keys),
            "exhausted_count": len(exhausted_keys)
        }
    
    @server.method("apikeys.add")
    def apikeys_add(params: dict, srv: JsonRpcServer) -> dict:
        name = params.get("name")
        key = params.get("key")
        
        if not name or not key:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Name and key are required")
        
        # Validate key format (ElevenLabs keys start with "sk_")
        key = key.strip()
        if not key.startswith("sk_"):
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Invalid API key format. ElevenLabs keys start with 'sk_'")
        
        if len(key) < 20:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Invalid API key format. Key is too short")
        
        config = get_config()
        
        # Check for duplicate keys
        for existing_key in config.api_keys:
            if existing_key.key == key:
                raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "This API key already exists")
        
        # Create API key object
        api_key = APIKey(
            id=str(uuid.uuid4()),
            name=name,
            key=key,
            is_valid=False,
            assigned_proxy_id=None
        )
        
        # Validate with ElevenLabs API
        api = get_api()
        success, message = api.validate_key(api_key, None)
        
        if not success:
            raise JsonRpcError(ErrorCodes.APP_INVALID_API_KEY, f"API key validation failed: {message}")
        
        # Check credit threshold
        min_credits = config.get("low_credit_threshold", 1000)
        if api_key.remaining_credits < min_credits:
            raise JsonRpcError(
                ErrorCodes.INVALID_PARAMS, 
                f"API key has insufficient credits ({api_key.remaining_credits}). Minimum required: {min_credits}"
            )
        
        # Save the key
        config.add_api_key(api_key)
        
        return {
            "id": api_key.id,
            "name": api_key.name,
            "key": api_key.key,
            "remaining_credits": api_key.remaining_credits,
            "character_count": api_key.character_count,
            "character_limit": api_key.character_limit,
            "is_valid": api_key.is_valid,
            "last_checked": None,
            "assigned_proxy_id": None
        }
    
    @server.method("apikeys.remove")
    def apikeys_remove(params: dict, srv: JsonRpcServer) -> dict:
        key_id = params.get("id")
        if not key_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "ID is required")
        
        config = get_config()
        config.remove_api_key(key_id)
        
        return {"success": True}
    
    @server.method("apikeys.validate")
    def apikeys_validate(params: dict, srv: JsonRpcServer) -> dict:
        key_id = params.get("id")
        if not key_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "ID is required")
        
        config = get_config()
        api = get_api()
        
        for api_key in config.api_keys:
            if api_key.id == key_id:
                # Get proxy if assigned
                proxy = config.get_proxy_for_key(api_key)
                
                # Actually validate with ElevenLabs API
                success, message = api.validate_key(api_key, proxy)
                
                if success:
                    config.update_api_key(api_key)
                
                return {
                    "id": api_key.id,
                    "name": api_key.name,
                    "key": api_key.key,
                    "remaining_credits": api_key.remaining_credits,
                    "character_count": api_key.character_count,
                    "character_limit": api_key.character_limit,
                    "is_valid": api_key.is_valid,
                    "message": message,
                    "assigned_proxy_id": api_key.assigned_proxy_id
                }
        
        raise JsonRpcError(ErrorCodes.APP_INVALID_API_KEY, "API key not found")
    
    @server.method("proxies.list")
    def proxies_list(params: dict, srv: JsonRpcServer) -> List[dict]:
        config = get_config()
        return [
            {
                "id": p.id,
                "name": p.name,
                "host": p.host,
                "port": p.port,
                "username": p.username,
                "password": None,  # Don't expose password
                "proxy_type": p.proxy_type,
                "enabled": p.enabled,
                "is_healthy": p.is_healthy
            }
            for p in config.proxies
        ]
    
    @server.method("proxies.add")
    def proxies_add(params: dict, srv: JsonRpcServer) -> dict:
        name = params.get("name")
        host = params.get("host")
        port = params.get("port", 8080)
        
        if not name or not host:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Name and host are required")
        
        config = get_config()
        proxy = Proxy(
            id=str(uuid.uuid4()),
            name=name,
            host=host,
            port=port,
            username=params.get("username"),
            password=params.get("password"),
            proxy_type=params.get("proxy_type", "http"),
            enabled=params.get("enabled", True),
            is_healthy=True
        )
        config.add_proxy(proxy)
        
        return {
            "id": proxy.id,
            "name": proxy.name,
            "host": proxy.host,
            "port": proxy.port,
            "username": proxy.username,
            "password": None,
            "proxy_type": proxy.proxy_type,
            "enabled": proxy.enabled,
            "is_healthy": proxy.is_healthy
        }
    
    @server.method("proxies.remove")
    def proxies_remove(params: dict, srv: JsonRpcServer) -> dict:
        proxy_id = params.get("id")
        if not proxy_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "ID is required")
        
        config = get_config()
        config.remove_proxy(proxy_id)
        
        return {"success": True}
    
    @server.method("proxies.test")
    def proxies_test(params: dict, srv: JsonRpcServer) -> bool:
        proxy_id = params.get("id")
        if not proxy_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "ID is required")
        
        config = get_config()
        for proxy in config.proxies:
            if proxy.id == proxy_id:
                # TODO: Actually test the proxy
                proxy.is_healthy = True
                config.update_proxy(proxy)
                return True
        
        return False
    
    @server.method("voices.list")
    def voices_list(params: dict, srv: JsonRpcServer) -> List[dict]:
        config = get_config()
        return [
            {
                "voice_id": v.voice_id,
                "name": v.name,
                "category": v.category,
                "labels": v.labels if hasattr(v, 'labels') else {},
                "preview_url": v.preview_url if hasattr(v, 'preview_url') else None,
                "description": v.description if hasattr(v, 'description') else None
            }
            for v in config.voice_library
        ]
    
    @server.method("voices.get")
    def voices_get(params: dict, srv: JsonRpcServer) -> dict:
        voice_id = params.get("voice_id")
        if not voice_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "voice_id is required")
        
        config = get_config()
        for v in config.voice_library:
            if v.voice_id == voice_id:
                return {
                    "voice_id": v.voice_id,
                    "name": v.name,
                    "category": v.category,
                    "labels": v.labels if hasattr(v, 'labels') else {},
                    "preview_url": v.preview_url if hasattr(v, 'preview_url') else None,
                    "description": v.description if hasattr(v, 'description') else None
                }
        
        raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Voice not found")
    
    @server.method("voices.refresh")
    def voices_refresh(params: dict, srv: JsonRpcServer) -> List[dict]:
        config = get_config()
        api = get_api()
        
        # Get first available API key
        api_key = config.get_available_api_key()
        if not api_key:
            raise JsonRpcError(ErrorCodes.APP_INVALID_API_KEY, "No valid API key available")
        
        # Get proxy if assigned
        proxy = config.get_proxy_for_key(api_key)
        
        # Fetch voices from ElevenLabs API
        voices = api.get_voices(api_key, proxy, use_cache=False)
        
        # Update voice library
        for voice in voices:
            config.add_voice_to_library(voice)
        
        return [
            {
                "voice_id": v.voice_id,
                "name": v.name,
                "category": v.category,
                "labels": v.labels if hasattr(v, 'labels') else {},
                "is_cloned": v.is_cloned if hasattr(v, 'is_cloned') else False
            }
            for v in voices
        ]
    
    def sanitize_text(text: str) -> str:
        """Remove invalid Unicode characters (unpaired surrogates, etc.)"""
        import re
        # Remove surrogate pairs and other problematic characters
        # This regex removes characters in the surrogate range
        text = re.sub(r'[\ud800-\udfff]', '', text)
        # Remove other control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        # Encode and decode to ensure valid UTF-8
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        return text.strip()

    def detect_language(text: str) -> str:
        """Detect language of text, returns ISO 639-1 code"""
        try:
            from langdetect import detect, DetectorFactory
            # Make detection deterministic
            DetectorFactory.seed = 0
            lang = detect(text)
            # Map common language codes to ElevenLabs supported codes
            lang_map = {
                'zh-cn': 'zh',
                'zh-tw': 'zh', 
                'pt-br': 'pt',
                'pt-pt': 'pt',
            }
            return lang_map.get(lang, lang)
        except Exception:
            return 'en'  # Default to English if detection fails

    @server.method("tts.start")
    def tts_start(params: dict, srv: JsonRpcServer) -> dict:
        text = params.get("text")
        voice_id = params.get("voice_id")
        output_path = params.get("output_path")
        
        if not text or not voice_id or not output_path:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "text, voice_id, and output_path are required")
        
        # Sanitize text to remove invalid Unicode
        text = sanitize_text(text)
        
        # Auto-detect language (can be overridden by params)
        language_code = params.get("language_code")
        if not language_code:
            language_code = detect_language(text)
        
        config = get_config()
        api = get_api()
        
        # Get available API key
        api_key = config.get_available_api_key()
        if not api_key:
            raise JsonRpcError(ErrorCodes.APP_INVALID_API_KEY, "No valid API key available")
        
        # Get proxy if assigned
        proxy = config.get_proxy_for_key(api_key)
        
        job_id = str(uuid.uuid4())
        
        # Send progress updates
        srv.send_progress(job_id, 10, "Initializing...")
        
        # Build voice settings from params
        settings = VoiceSettings(
            stability=params.get("stability", 0.5),
            similarity_boost=params.get("similarity_boost", 0.75),
            style=params.get("style", 0.0),
            use_speaker_boost=params.get("use_speaker_boost", True),
            speed=params.get("speed", 1.0)
        )
        
        # Set model if provided
        model_id = params.get("model_id")
        if model_id:
            from core.models import TTSModel
            try:
                settings.model = TTSModel(model_id)
            except ValueError:
                pass
        
        srv.send_progress(job_id, 30, "Generating audio...")
        
        # Call ElevenLabs TTS API
        success, message, duration = api.text_to_speech(
            text=text,
            voice_id=voice_id,
            api_key=api_key,
            output_path=output_path,
            settings=settings,
            proxy=proxy,
            language_code=language_code
        )
        
        if not success:
            # Handle rate limit
            if message == "RATE_LIMIT":
                raise JsonRpcError(ErrorCodes.APP_RATE_LIMITED, "Rate limited, please try again later")
            raise JsonRpcError(ErrorCodes.APP_TTS_FAILED, message)
        
        # Update API key usage
        api_key.character_count += len(text)
        config.update_api_key(api_key)
        
        # Track analytics
        try:
            from services.analytics import get_analytics
            analytics = get_analytics()
            analytics.track_tts(len(text), 1, voice_id)
        except Exception:
            pass  # Don't fail if analytics fails
        
        srv.send_progress(job_id, 100, "Complete")
        
        return {
            "job_id": job_id,
            "output_path": output_path,
            "duration_ms": int((duration or 0) * 1000),
            "characters_used": len(text),
            "language_code": language_code
        }
    
    @server.method("jobs.cancel")
    def jobs_cancel(params: dict, srv: JsonRpcServer) -> dict:
        job_id = params.get("job_id")
        if not job_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "job_id is required")
        
        # TODO: Implement job cancellation
        return {"success": True}
    
    @server.method("credits.total")
    def credits_total(params: dict, srv: JsonRpcServer) -> int:
        config = get_config()
        return config.get_total_credits()
    
    # File import handlers
    @server.method("files.import")
    def files_import(params: dict, srv: JsonRpcServer) -> List[dict]:
        """Import files and return list of text lines"""
        file_paths = params.get("file_paths", [])
        auto_split = params.get("auto_split", True)
        max_chars = params.get("max_chars", 5000)
        split_delimiter = params.get("split_delimiter", ".,?!;")
        
        if not file_paths:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "file_paths is required")
        
        from services.file_import import FileImporter, TextSplitter
        
        importer = FileImporter()
        splitter = TextSplitter(max_chars=max_chars, delimiters=split_delimiter)
        
        all_lines = []
        errors = []
        
        for file_path in file_paths:
            try:
                lines = importer.import_file(file_path)
                if auto_split:
                    lines = splitter.split_lines(lines)
                all_lines.extend(lines)
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")
        
        # Re-index all lines
        for i, line in enumerate(all_lines):
            line.index = i
        
        result = [
            {
                "id": line.id,
                "index": line.index,
                "text": line.text,
                "original_text": line.original_text,
                "source_file": line.source_file,
                "start_time": line.start_time,
                "end_time": line.end_time,
            }
            for line in all_lines
        ]
        
        if errors:
            # Return partial results with errors
            return {"lines": result, "errors": errors}
        
        return {"lines": result, "errors": []}
    
    @server.method("files.parse_text")
    def files_parse_text(params: dict, srv: JsonRpcServer) -> List[dict]:
        """Parse raw text into lines"""
        text = params.get("text", "")
        split_by = params.get("split_by", "line")  # "line", "sentence", "paragraph"
        auto_split = params.get("auto_split", True)
        max_chars = params.get("max_chars", 5000)
        
        if not text:
            return {"lines": [], "errors": []}
        
        from services.file_import import TextSplitter
        from core.models import TextLine
        import re
        
        # Split text based on mode
        if split_by == "sentence":
            # Split by sentence-ending punctuation
            raw_lines = re.split(r'(?<=[.!?])\s+', text)
        elif split_by == "paragraph":
            # Split by double newlines
            raw_lines = re.split(r'\n\s*\n', text)
        else:
            # Split by single newlines
            raw_lines = text.split('\n')
        
        lines = []
        for i, line_text in enumerate(raw_lines):
            line_text = line_text.strip()
            if line_text:
                lines.append(TextLine(
                    index=i,
                    text=line_text,
                    original_text=line_text
                ))
        
        # Auto-split long lines
        if auto_split:
            splitter = TextSplitter(max_chars=max_chars)
            lines = splitter.split_lines(lines)
        
        return {
            "lines": [
                {
                    "id": line.id,
                    "index": line.index,
                    "text": line.text,
                    "original_text": line.original_text,
                }
                for line in lines
            ],
            "errors": []
        }
    
    # SRT generation handler
    @server.method("srt.generate")
    def srt_generate(params: dict, srv: JsonRpcServer) -> dict:
        """Generate SRT file from processed lines"""
        lines_data = params.get("lines", [])
        output_path = params.get("output_path")
        gap = params.get("gap", 0.0)
        offset = params.get("offset", 0.0)
        
        if not lines_data or not output_path:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "lines and output_path are required")
        
        from services.audio import SRTGenerator
        from core.models import TextLine
        
        # Convert to TextLine objects
        lines = []
        for data in lines_data:
            line = TextLine(
                index=data.get("index", 0),
                text=data.get("text", ""),
                original_text=data.get("text", ""),
                audio_duration=data.get("audio_duration")
            )
            lines.append(line)
        
        generator = SRTGenerator()
        success = generator.generate(lines, output_path, gap=gap, offset=offset)
        
        if success:
            return {"success": True, "output_path": output_path}
        else:
            raise JsonRpcError(ErrorCodes.INTERNAL_ERROR, "Failed to generate SRT file")
    
    # MP3 concatenation handler
    @server.method("audio.concatenate")
    def audio_concatenate(params: dict, srv: JsonRpcServer) -> dict:
        """Concatenate multiple MP3 files into one"""
        input_files = params.get("input_files", [])
        output_path = params.get("output_path")
        silence_gap = params.get("silence_gap", 0.0)
        
        if not input_files or not output_path:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "input_files and output_path are required")
        
        from services.audio import MP3Concatenator
        
        concatenator = MP3Concatenator()
        success, message = concatenator.concatenate(
            input_files=input_files,
            output_path=output_path,
            silence_gap=silence_gap
        )
        
        if success:
            return {"success": True, "output_path": output_path}
        else:
            raise JsonRpcError(ErrorCodes.INTERNAL_ERROR, f"Failed to concatenate: {message}")
    
    # Project save/load handlers
    @server.method("project.save")
    def project_save(params: dict, srv: JsonRpcServer) -> dict:
        """Save project to file"""
        file_path = params.get("file_path")
        project_data = params.get("project")
        
        if not file_path or not project_data:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "file_path and project are required")
        
        try:
            import json
            from pathlib import Path
            
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            return {"success": True, "file_path": file_path}
        except Exception as e:
            raise JsonRpcError(ErrorCodes.INTERNAL_ERROR, f"Failed to save project: {str(e)}")
    
    @server.method("project.load")
    def project_load(params: dict, srv: JsonRpcServer) -> dict:
        """Load project from file"""
        file_path = params.get("file_path")
        
        if not file_path:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "file_path is required")
        
        try:
            import json
            
            with open(file_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            return {"success": True, "project": project_data}
        except FileNotFoundError:
            raise JsonRpcError(ErrorCodes.APP_FILE_NOT_FOUND, "Project file not found")
        except Exception as e:
            raise JsonRpcError(ErrorCodes.INTERNAL_ERROR, f"Failed to load project: {str(e)}")

    # ============================================
    # TRANSCRIPTION (Speech-to-Text) HANDLERS
    # ============================================
    
    @server.method("transcription.start")
    def transcription_start(params: dict, srv: JsonRpcServer) -> dict:
        """Start transcription job"""
        file_path = params.get("file_path")
        language = params.get("language")  # None for auto-detect
        diarize = params.get("diarize", False)
        num_speakers = params.get("num_speakers")
        
        if not file_path:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "file_path is required")
        
        if not os.path.exists(file_path):
            raise JsonRpcError(ErrorCodes.APP_FILE_NOT_FOUND, "File not found")
        
        config = get_config()
        api = get_api()
        
        api_key = config.get_available_api_key()
        if not api_key:
            raise JsonRpcError(ErrorCodes.APP_INVALID_API_KEY, "No valid API key available")
        
        proxy = config.get_proxy_for_key(api_key)
        job_id = str(uuid.uuid4())
        
        srv.send_progress(job_id, 10, "Starting transcription...")
        
        success, result = api.transcribe_audio(
            file_path=file_path,
            api_key=api_key,
            language=language,
            diarize=diarize,
            num_speakers=num_speakers,
            proxy=proxy
        )
        
        if not success:
            raise JsonRpcError(ErrorCodes.APP_TTS_FAILED, f"Transcription failed: {result}")
        
        srv.send_progress(job_id, 100, "Complete")
        
        return {
            "job_id": job_id,
            "text": result.text,
            "language": result.language,
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "speaker": s.speaker
                }
                for s in result.segments
            ],
            "speakers": [
                {"id": sp.id, "name": sp.name}
                for sp in result.speakers
            ] if result.speakers else []
        }
    
    @server.method("transcription.supported_formats")
    def transcription_formats(params: dict, srv: JsonRpcServer) -> dict:
        """Get supported transcription formats"""
        return {
            "audio": [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"],
            "video": [".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv"]
        }

    # ============================================
    # VOICE PRESETS HANDLERS
    # ============================================
    
    @server.method("presets.list")
    def presets_list(params: dict, srv: JsonRpcServer) -> List[dict]:
        """List all voice presets"""
        from services.preset_manager import get_preset_manager
        pm = get_preset_manager()
        return [p.to_dict() for p in pm.get_presets()]
    
    @server.method("presets.save")
    def presets_save(params: dict, srv: JsonRpcServer) -> dict:
        """Save a voice preset"""
        name = params.get("name")
        voice_id = params.get("voice_id")
        voice_name = params.get("voice_name", "")
        settings = params.get("settings", {})
        description = params.get("description", "")
        tags = params.get("tags", [])
        
        if not name or not voice_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "name and voice_id are required")
        
        from services.preset_manager import get_preset_manager, VoicePreset
        from core.models import VoiceSettings
        
        pm = get_preset_manager()
        preset = VoicePreset(
            id=str(uuid.uuid4()),
            name=name,
            voice_id=voice_id,
            voice_name=voice_name,
            settings=VoiceSettings.from_dict(settings),
            description=description,
            tags=tags
        )
        pm.add_preset(preset)
        return preset.to_dict()
    
    @server.method("presets.delete")
    def presets_delete(params: dict, srv: JsonRpcServer) -> dict:
        """Delete a voice preset"""
        preset_id = params.get("id")
        if not preset_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "id is required")
        
        from services.preset_manager import get_preset_manager
        pm = get_preset_manager()
        pm.remove_preset(preset_id)
        return {"success": True}

    # ============================================
    # VOICE MATCHER HANDLERS
    # ============================================
    
    @server.method("voicematcher.patterns.list")
    def voicematcher_patterns_list(params: dict, srv: JsonRpcServer) -> List[dict]:
        """List voice matching patterns"""
        from services.voice_matcher import get_voice_matcher
        vm = get_voice_matcher()
        return [p.to_dict() for p in vm.get_patterns()]
    
    @server.method("voicematcher.patterns.add")
    def voicematcher_patterns_add(params: dict, srv: JsonRpcServer) -> dict:
        """Add a voice matching pattern"""
        name = params.get("name")
        pattern = params.get("pattern")
        voice_id = params.get("voice_id")
        voice_name = params.get("voice_name", "")
        match_type = params.get("match_type", "contains")
        case_sensitive = params.get("case_sensitive", False)
        priority = params.get("priority", 0)
        
        if not name or not pattern or not voice_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "name, pattern and voice_id are required")
        
        from services.voice_matcher import get_voice_matcher, VoicePattern
        vm = get_voice_matcher()
        
        vp = VoicePattern(
            id=str(uuid.uuid4()),
            name=name,
            pattern=pattern,
            voice_id=voice_id,
            voice_name=voice_name,
            match_type=match_type,
            case_sensitive=case_sensitive,
            priority=priority
        )
        vm.add_pattern(vp)
        return vp.to_dict()
    
    @server.method("voicematcher.patterns.delete")
    def voicematcher_patterns_delete(params: dict, srv: JsonRpcServer) -> dict:
        """Delete a voice matching pattern"""
        pattern_id = params.get("id")
        if not pattern_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "id is required")
        
        from services.voice_matcher import get_voice_matcher
        vm = get_voice_matcher()
        vm.remove_pattern(pattern_id)
        return {"success": True}
    
    @server.method("voicematcher.match")
    def voicematcher_match(params: dict, srv: JsonRpcServer) -> dict:
        """Match text to voice based on patterns"""
        text = params.get("text")
        if not text:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "text is required")
        
        from services.voice_matcher import get_voice_matcher
        vm = get_voice_matcher()
        result = vm.match(text)
        
        if result:
            return {
                "matched": True,
                "voice_id": result.voice_id,
                "voice_name": result.voice_name,
                "pattern_name": result.pattern_name
            }
        return {"matched": False}
    
    @server.method("voicematcher.batch_match")
    def voicematcher_batch_match(params: dict, srv: JsonRpcServer) -> List[dict]:
        """Match multiple texts to voices"""
        lines = params.get("lines", [])
        
        from services.voice_matcher import get_voice_matcher
        vm = get_voice_matcher()
        
        results = []
        for line in lines:
            text = line.get("text", "")
            line_id = line.get("id")
            result = vm.match(text)
            
            if result:
                results.append({
                    "id": line_id,
                    "matched": True,
                    "voice_id": result.voice_id,
                    "voice_name": result.voice_name
                })
            else:
                results.append({"id": line_id, "matched": False})
        
        return results

    # ============================================
    # PAUSE PREPROCESSOR HANDLERS
    # ============================================
    
    @server.method("pause.process")
    def pause_process(params: dict, srv: JsonRpcServer) -> dict:
        """Process text to add pauses"""
        text = params.get("text")
        settings = params.get("settings", {})
        
        if not text:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "text is required")
        
        from services.pause_preprocessor import PausePreprocessor, PauseSettings
        
        pause_settings = PauseSettings.from_dict(settings) if settings else PauseSettings()
        processor = PausePreprocessor(pause_settings)
        processed = processor.process(text)
        
        return {"original": text, "processed": processed}
    
    @server.method("pause.batch_process")
    def pause_batch_process(params: dict, srv: JsonRpcServer) -> List[dict]:
        """Process multiple texts to add pauses"""
        lines = params.get("lines", [])
        settings = params.get("settings", {})
        
        from services.pause_preprocessor import PausePreprocessor, PauseSettings
        
        pause_settings = PauseSettings.from_dict(settings) if settings else PauseSettings()
        processor = PausePreprocessor(pause_settings)
        
        results = []
        for line in lines:
            text = line.get("text", "")
            line_id = line.get("id")
            processed = processor.process(text)
            results.append({
                "id": line_id,
                "original": text,
                "processed": processed
            })
        
        return results

    # ============================================
    # AUDIO POST-PROCESSING HANDLERS
    # ============================================
    
    @server.method("audio.process")
    def audio_process(params: dict, srv: JsonRpcServer) -> dict:
        """Process audio file with effects"""
        input_path = params.get("input_path")
        output_path = params.get("output_path")
        settings = params.get("settings", {})
        
        if not input_path or not output_path:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "input_path and output_path are required")
        
        if not os.path.exists(input_path):
            raise JsonRpcError(ErrorCodes.APP_FILE_NOT_FOUND, "Input file not found")
        
        from services.audio_processor import AudioProcessor, AudioProcessingSettings
        
        proc_settings = AudioProcessingSettings.from_dict(settings)
        processor = AudioProcessor()
        
        success, message = processor.process(input_path, output_path, proc_settings)
        
        if success:
            return {"success": True, "output_path": output_path}
        else:
            raise JsonRpcError(ErrorCodes.INTERNAL_ERROR, f"Audio processing failed: {message}")
    
    @server.method("audio.batch_process")
    def audio_batch_process(params: dict, srv: JsonRpcServer) -> dict:
        """Process multiple audio files"""
        files = params.get("files", [])  # [{input_path, output_path}, ...]
        settings = params.get("settings", {})
        
        from services.audio_processor import AudioProcessor, AudioProcessingSettings
        
        proc_settings = AudioProcessingSettings.from_dict(settings)
        processor = AudioProcessor()
        
        results = []
        success_count = 0
        
        for i, f in enumerate(files):
            input_path = f.get("input_path")
            output_path = f.get("output_path")
            
            if input_path and output_path and os.path.exists(input_path):
                success, message = processor.process(input_path, output_path, proc_settings)
                results.append({
                    "input_path": input_path,
                    "output_path": output_path,
                    "success": success,
                    "message": message
                })
                if success:
                    success_count += 1
            
            srv.send_progress("batch_audio", int((i + 1) / len(files) * 100), f"Processing {i + 1}/{len(files)}")
        
        return {
            "total": len(files),
            "success": success_count,
            "failed": len(files) - success_count,
            "results": results
        }

    # ============================================
    # ANALYTICS HANDLERS
    # ============================================
    
    @server.method("analytics.get_stats")
    def analytics_get_stats(params: dict, srv: JsonRpcServer) -> dict:
        """Get usage statistics"""
        from services.analytics import get_analytics
        analytics = get_analytics()
        stats = analytics.get_stats()
        
        return {
            "total_characters": stats.total_characters,
            "total_lines": stats.total_lines,
            "total_sessions": stats.total_sessions,
            "total_processing_time": stats.total_processing_time,
            "voice_usage": stats.voice_usage,
            "daily_usage": stats.daily_usage,
            "error_count": stats.error_count,
            "first_use": stats.first_use.isoformat() if stats.first_use else None,
            "last_use": stats.last_use.isoformat() if stats.last_use else None
        }
    
    @server.method("analytics.track_usage")
    def analytics_track_usage(params: dict, srv: JsonRpcServer) -> dict:
        """Track usage event"""
        characters = params.get("characters", 0)
        lines = params.get("lines", 0)
        voice_id = params.get("voice_id")
        
        from services.analytics import get_analytics
        analytics = get_analytics()
        analytics.track_tts(characters, lines, voice_id)
        
        return {"success": True}
    
    @server.method("analytics.reset")
    def analytics_reset(params: dict, srv: JsonRpcServer) -> dict:
        """Reset analytics data"""
        from services.analytics import get_analytics
        analytics = get_analytics()
        analytics.reset()
        return {"success": True}

    # ============================================
    # PROXY MANAGEMENT HANDLERS
    # ============================================
    
    @server.method("proxies.list")
    def proxies_list(params: dict, srv: JsonRpcServer) -> List[dict]:
        """List all proxies"""
        config = get_config()
        return [
            {
                "id": p.id,
                "name": p.name,
                "host": p.host,
                "port": p.port,
                "username": p.username,
                "proxy_type": p.proxy_type,
                "is_enabled": p.is_enabled
            }
            for p in config.proxies
        ]
    
    @server.method("proxies.add")
    def proxies_add(params: dict, srv: JsonRpcServer) -> dict:
        """Add a proxy"""
        name = params.get("name")
        host = params.get("host")
        port = params.get("port")
        username = params.get("username", "")
        password = params.get("password", "")
        proxy_type = params.get("proxy_type", "http")
        
        if not name or not host or not port:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "name, host and port are required")
        
        from core.models import Proxy
        
        proxy = Proxy(
            id=str(uuid.uuid4()),
            name=name,
            host=host,
            port=port,
            username=username,
            password=password,
            proxy_type=proxy_type,
            is_enabled=True
        )
        
        config = get_config()
        config.add_proxy(proxy)
        
        return {
            "id": proxy.id,
            "name": proxy.name,
            "host": proxy.host,
            "port": proxy.port,
            "proxy_type": proxy.proxy_type
        }
    
    @server.method("proxies.remove")
    def proxies_remove(params: dict, srv: JsonRpcServer) -> dict:
        """Remove a proxy"""
        proxy_id = params.get("id")
        if not proxy_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "id is required")
        
        config = get_config()
        config.remove_proxy(proxy_id)
        return {"success": True}
    
    @server.method("proxies.test")
    def proxies_test(params: dict, srv: JsonRpcServer) -> dict:
        """Test proxy connection"""
        proxy_id = params.get("id")
        if not proxy_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "id is required")
        
        config = get_config()
        proxy = None
        for p in config.proxies:
            if p.id == proxy_id:
                proxy = p
                break
        
        if not proxy:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Proxy not found")
        
        import requests
        try:
            proxies = {
                "http": f"{proxy.proxy_type}://{proxy.host}:{proxy.port}",
                "https": f"{proxy.proxy_type}://{proxy.host}:{proxy.port}"
            }
            if proxy.username and proxy.password:
                proxies = {
                    "http": f"{proxy.proxy_type}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}",
                    "https": f"{proxy.proxy_type}://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
                }
            
            response = requests.get("https://api.elevenlabs.io/v1/voices", proxies=proxies, timeout=10)
            return {"success": True, "status_code": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @server.method("proxies.assign_to_key")
    def proxies_assign_to_key(params: dict, srv: JsonRpcServer) -> dict:
        """Assign proxy to API key"""
        key_id = params.get("key_id")
        proxy_id = params.get("proxy_id")  # None to unassign
        
        if not key_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "key_id is required")
        
        config = get_config()
        
        for api_key in config.api_keys:
            if api_key.id == key_id:
                api_key.assigned_proxy_id = proxy_id
                config.update_api_key(api_key)
                return {"success": True}
        
        raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "API key not found")

    # ============================================
    # VOICE LIBRARY HANDLERS
    # ============================================
    
    @server.method("voices.search")
    def voices_search(params: dict, srv: JsonRpcServer) -> List[dict]:
        """Search voices with filters"""
        query = params.get("query", "")
        category = params.get("category")
        gender = params.get("gender")
        language = params.get("language")
        use_case = params.get("use_case")
        
        config = get_config()
        api = get_api()
        
        api_key = config.get_available_api_key()
        if not api_key:
            raise JsonRpcError(ErrorCodes.APP_INVALID_API_KEY, "No valid API key available")
        
        proxy = config.get_proxy_for_key(api_key)
        
        voices = api.search_voices(
            api_key=api_key,
            proxy=proxy,
            query=query,
            gender=gender,
            language=language,
            use_case=use_case,
            category=category
        )
        
        return [
            {
                "voice_id": v.voice_id,
                "name": v.name,
                "category": v.category,
                "labels": v.labels,
                "description": v.description,
                "preview_url": v.preview_url
            }
            for v in voices
        ]
    
    @server.method("voices.get_details")
    def voices_get_details(params: dict, srv: JsonRpcServer) -> dict:
        """Get detailed voice info"""
        voice_id = params.get("voice_id")
        if not voice_id:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "voice_id is required")
        
        config = get_config()
        api = get_api()
        
        api_key = config.get_available_api_key()
        if not api_key:
            raise JsonRpcError(ErrorCodes.APP_INVALID_API_KEY, "No valid API key available")
        
        voice = api.get_voice(voice_id, api_key)
        if not voice:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Voice not found")
        
        return {
            "voice_id": voice.voice_id,
            "name": voice.name,
            "category": voice.category,
            "labels": voice.labels if hasattr(voice, 'labels') else {},
            "description": voice.description if hasattr(voice, 'description') else "",
            "preview_url": voice.preview_url if hasattr(voice, 'preview_url') else None,
            "settings": voice.default_settings.to_dict() if hasattr(voice, 'default_settings') and voice.default_settings else None
        }

    # ============================================
    # BATCH TTS (Multi-thread) HANDLERS
    # ============================================
    
    @server.method("tts.batch_start")
    def tts_batch_start(params: dict, srv: JsonRpcServer) -> dict:
        """Start batch TTS processing with multiple threads"""
        lines = params.get("lines", [])
        thread_count = params.get("thread_count", 2)
        settings = params.get("settings", {})
        
        if not lines:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "lines are required")
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        config = get_config()
        api = get_api()
        
        batch_id = str(uuid.uuid4())
        results = []
        completed = 0
        failed = 0
        
        def process_line(line_data):
            nonlocal completed, failed
            
            text = sanitize_text(line_data.get("text", ""))
            voice_id = line_data.get("voice_id")
            output_path = line_data.get("output_path")
            line_id = line_data.get("id")
            
            if not text or not voice_id or not output_path:
                return {"id": line_id, "success": False, "error": "Missing required fields"}
            
            # Detect language
            lang = detect_language(text)
            
            # Get API key
            api_key = config.get_available_api_key()
            if not api_key:
                return {"id": line_id, "success": False, "error": "No API key available"}
            
            proxy = config.get_proxy_for_key(api_key)
            
            # Build settings
            voice_settings = VoiceSettings(
                stability=settings.get("stability", 0.5),
                similarity_boost=settings.get("similarity_boost", 0.75),
                style=settings.get("style", 0.0),
                use_speaker_boost=settings.get("use_speaker_boost", True),
                speed=settings.get("speed", 1.0)
            )
            
            model_id = settings.get("model_id")
            if model_id:
                from core.models import TTSModel
                try:
                    voice_settings.model = TTSModel(model_id)
                except ValueError:
                    pass
            
            success, message, duration = api.text_to_speech(
                text=text,
                voice_id=voice_id,
                api_key=api_key,
                output_path=output_path,
                settings=voice_settings,
                proxy=proxy,
                language_code=lang
            )
            
            if success:
                api_key.character_count += len(text)
                config.update_api_key(api_key)
                return {
                    "id": line_id,
                    "success": True,
                    "output_path": output_path,
                    "duration_ms": int((duration or 0) * 1000),
                    "language_code": lang
                }
            else:
                return {"id": line_id, "success": False, "error": message}
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=min(thread_count, 5)) as executor:
            futures = {executor.submit(process_line, line): line for line in lines}
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                if result.get("success"):
                    completed += 1
                else:
                    failed += 1
                
                srv.send_progress(
                    batch_id, 
                    int((completed + failed) / len(lines) * 100),
                    f"Processed {completed + failed}/{len(lines)}"
                )
        
        return {
            "batch_id": batch_id,
            "total": len(lines),
            "completed": completed,
            "failed": failed,
            "results": results
        }

    # ============================================
    # LOCALIZATION HANDLERS
    # ============================================
    
    @server.method("i18n.get_languages")
    def i18n_get_languages(params: dict, srv: JsonRpcServer) -> List[dict]:
        """Get available languages"""
        return [
            {"code": "en", "name": "English"},
            {"code": "vi", "name": "Tiếng Việt"},
            {"code": "zh", "name": "中文"},
            {"code": "ja", "name": "日本語"},
            {"code": "ko", "name": "한국어"},
            {"code": "fr", "name": "Français"},
            {"code": "de", "name": "Deutsch"},
            {"code": "es", "name": "Español"},
            {"code": "pt", "name": "Português"},
            {"code": "ru", "name": "Русский"}
        ]
    
    @server.method("i18n.get_translations")
    def i18n_get_translations(params: dict, srv: JsonRpcServer) -> dict:
        """Get translations for a language"""
        lang = params.get("language", "en")
        
        from services.localization import get_translations
        return get_translations(lang)
