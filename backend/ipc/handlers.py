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


BACKEND_VERSION = "1.0.8"
PROTOCOL_VERSION = 1
MIN_UI_VERSION = "1.0.0"


def register_handlers(server: JsonRpcServer):
    """Register all RPC handlers"""
    
    @server.method("system.handshake")
    def handshake(params: dict, srv: JsonRpcServer) -> dict:
        ui_version = params.get("ui_version", "0.0.0")
        protocol = params.get("protocol_version", 0)
        
        compatible = protocol == PROTOCOL_VERSION
        
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
    
    @server.method("apikeys.add")
    def apikeys_add(params: dict, srv: JsonRpcServer) -> dict:
        name = params.get("name")
        key = params.get("key")
        
        if not name or not key:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "Name and key are required")
        
        config = get_config()
        api_key = APIKey(
            id=str(uuid.uuid4()),
            name=name,
            key=key,
            remaining_credits=0,
            is_valid=True,
            last_checked=None,
            assigned_proxy_id=None
        )
        config.add_api_key(api_key)
        
        return {
            "id": api_key.id,
            "name": api_key.name,
            "key": api_key.key,
            "remaining_credits": api_key.remaining_credits,
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
    
    @server.method("tts.start")
    def tts_start(params: dict, srv: JsonRpcServer) -> dict:
        text = params.get("text")
        voice_id = params.get("voice_id")
        output_path = params.get("output_path")
        
        if not text or not voice_id or not output_path:
            raise JsonRpcError(ErrorCodes.INVALID_PARAMS, "text, voice_id, and output_path are required")
        
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
            proxy=proxy
        )
        
        if not success:
            # Handle rate limit
            if message == "RATE_LIMIT":
                raise JsonRpcError(ErrorCodes.APP_RATE_LIMITED, "Rate limited, please try again later")
            raise JsonRpcError(ErrorCodes.APP_TTS_FAILED, message)
        
        # Update API key usage
        api_key.character_count += len(text)
        config.update_api_key(api_key)
        
        srv.send_progress(job_id, 100, "Complete")
        
        return {
            "job_id": job_id,
            "output_path": output_path,
            "duration_ms": int((duration or 0) * 1000),
            "characters_used": len(text)
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
