"""Data models for 2TTS application"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import uuid


class LineStatus(Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    DONE = "Done"
    ERROR = "Error"


class JobStatus(Enum):
    """Status for transcription jobs"""
    PENDING = "Pending"
    PROCESSING = "Processing"
    DONE = "Done"
    ERROR = "Error"


class ProxyType(Enum):
    HTTP = "HTTP"
    SOCKS5 = "SOCKS5"


class TTSModel(Enum):
    V3 = "eleven_v3"  # 70+ langs, 5k chars, most expressive
    MULTILINGUAL_V2 = "eleven_multilingual_v2"  # 29 langs, 10k chars, stable
    TURBO_V25 = "eleven_turbo_v2_5"  # 32 langs, 40k chars, ~250-300ms
    TURBO_V2 = "eleven_turbo_v2"  # English only, 30k chars, ~250-300ms
    FLASH_V25 = "eleven_flash_v2_5"  # 32 langs, 40k chars, ~75ms
    FLASH_V2 = "eleven_flash_v2"  # English only, 30k chars, ~75ms


@dataclass
class VoiceSettings:
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0  # Style exaggeration (0-1), increases latency
    use_speaker_boost: bool = True  # Enhances similarity, increases latency
    speed: float = 1.0
    model: TTSModel = TTSModel.V3
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stability": self.stability,
            "similarity_boost": self.similarity_boost,
            "style": self.style,
            "use_speaker_boost": self.use_speaker_boost,
            "speed": self.speed,
            "model": self.model.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceSettings":
        return cls(
            stability=data.get("stability", 0.5),
            similarity_boost=data.get("similarity_boost", 0.75),
            style=data.get("style", 0.0),
            use_speaker_boost=data.get("use_speaker_boost", True),
            speed=data.get("speed", 1.0),
            model=TTSModel(data.get("model", TTSModel.V3.value))
        )


@dataclass
class Voice:
    voice_id: str
    name: str
    is_cloned: bool = False
    settings: VoiceSettings = field(default_factory=VoiceSettings)
    category: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    preview_url: Optional[str] = None
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "is_cloned": self.is_cloned,
            "settings": self.settings.to_dict(),
            "category": self.category,
            "labels": self.labels,
            "preview_url": self.preview_url,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Voice":
        return cls(
            voice_id=data["voice_id"],
            name=data["name"],
            is_cloned=data.get("is_cloned", False),
            settings=VoiceSettings.from_dict(data.get("settings", {})),
            category=data.get("category", ""),
            labels=data.get("labels", {}),
            preview_url=data.get("preview_url"),
            description=data.get("description", "")
        )


@dataclass
class Proxy:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    host: str = ""
    port: int = 8080
    proxy_type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    enabled: bool = True
    is_healthy: bool = True
    last_check: Optional[datetime] = None
    
    def get_url(self) -> str:
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        protocol = "socks5" if self.proxy_type == ProxyType.SOCKS5 else "http"
        # IPv6 addresses need to be wrapped in brackets
        host = self.host
        if ':' in host and not host.startswith('['):
            host = f"[{host}]"
        return f"{protocol}://{auth}{host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "proxy_type": self.proxy_type.value,
            "username": self.username,
            "password": self.password,
            "enabled": self.enabled,
            "is_healthy": self.is_healthy
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proxy":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            host=data["host"],
            port=data["port"],
            proxy_type=ProxyType(data.get("proxy_type", "HTTP")),
            username=data.get("username"),
            password=data.get("password"),
            enabled=data.get("enabled", True),
            is_healthy=data.get("is_healthy", True)
        )


@dataclass
class APIKey:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    key: str = ""
    name: str = ""
    enabled: bool = True
    character_count: int = 0
    character_limit: int = 0
    is_valid: bool = False
    in_cooldown: bool = False
    cooldown_until: Optional[datetime] = None
    assigned_proxy_id: Optional[str] = None
    
    @property
    def remaining_credits(self) -> int:
        return max(0, self.character_limit - self.character_count)
    
    @property
    def is_available(self) -> bool:
        if not self.enabled or not self.is_valid:
            return False
        if self.in_cooldown and self.cooldown_until:
            if datetime.now() < self.cooldown_until:
                return False
            self.in_cooldown = False
        return self.remaining_credits > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "enabled": self.enabled,
            "character_count": self.character_count,
            "character_limit": self.character_limit,
            "is_valid": self.is_valid,
            "assigned_proxy_id": self.assigned_proxy_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APIKey":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            key=data["key"],
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            character_count=data.get("character_count", 0),
            character_limit=data.get("character_limit", 0),
            is_valid=data.get("is_valid", False),
            assigned_proxy_id=data.get("assigned_proxy_id")
        )


@dataclass
class TextLine:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    index: int = 0
    text: str = ""
    original_text: str = ""
    voice_id: Optional[str] = None
    voice_name: Optional[str] = None
    status: LineStatus = LineStatus.PENDING
    error_message: Optional[str] = None
    source_file: Optional[str] = None
    start_time: Optional[float] = None  # in seconds
    end_time: Optional[float] = None    # in seconds
    audio_duration: Optional[float] = None
    output_path: Optional[str] = None
    retry_count: int = 0
    detected_language: Optional[str] = None
    model_used: Optional[str] = None  # Model ID used for TTS generation
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "index": self.index,
            "text": self.text,
            "original_text": self.original_text,
            "voice_id": self.voice_id,
            "voice_name": self.voice_name,
            "status": self.status.value,
            "error_message": self.error_message,
            "source_file": self.source_file,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "audio_duration": self.audio_duration,
            "output_path": self.output_path,
            "retry_count": self.retry_count,
            "detected_language": self.detected_language,
            "model_used": self.model_used
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextLine":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            index=data.get("index", 0),
            text=data["text"],
            original_text=data.get("original_text", data["text"]),
            voice_id=data.get("voice_id"),
            voice_name=data.get("voice_name"),
            status=LineStatus(data.get("status", "Pending")),
            error_message=data.get("error_message"),
            source_file=data.get("source_file"),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            audio_duration=data.get("audio_duration"),
            output_path=data.get("output_path"),
            retry_count=data.get("retry_count", 0),
            detected_language=data.get("detected_language"),
            model_used=data.get("model_used")
        )


@dataclass
class ProjectSettings:
    default_voice_id: Optional[str] = None
    default_voice_name: Optional[str] = None
    output_folder: str = ""
    thread_count: int = 5
    max_retries: int = 3
    request_delay: float = 0.5  # seconds between requests to avoid rate limiting
    loop_enabled: bool = False
    loop_count: int = 0  # 0 = infinite
    loop_delay: int = 5  # seconds
    silence_gap: float = 0.0  # seconds between segments
    timing_offset: float = 0.0  # global timing offset
    auto_split_enabled: bool = True
    split_delimiter: str = ".,?!;"
    max_chars: int = 5000
    auto_language_detect: bool = True
    auto_assign_voice: bool = False
    theme: str = "dark"
    # Vietnamese TTS settings
    vn_preprocessing_enabled: bool = False
    vn_max_phrase_words: int = 8
    vn_add_micro_pauses: bool = True
    vn_micro_pause_interval: int = 4
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_voice_id": self.default_voice_id,
            "default_voice_name": self.default_voice_name,
            "output_folder": self.output_folder,
            "thread_count": self.thread_count,
            "max_retries": self.max_retries,
            "loop_enabled": self.loop_enabled,
            "loop_count": self.loop_count,
            "loop_delay": self.loop_delay,
            "silence_gap": self.silence_gap,
            "timing_offset": self.timing_offset,
            "auto_split_enabled": self.auto_split_enabled,
            "split_delimiter": self.split_delimiter,
            "max_chars": self.max_chars,
            "auto_language_detect": self.auto_language_detect,
            "auto_assign_voice": self.auto_assign_voice,
            "theme": self.theme,
            "vn_preprocessing_enabled": self.vn_preprocessing_enabled,
            "vn_max_phrase_words": self.vn_max_phrase_words,
            "vn_add_micro_pauses": self.vn_add_micro_pauses,
            "vn_micro_pause_interval": self.vn_micro_pause_interval
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectSettings":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Project:
    name: str = "Untitled"
    file_path: Optional[str] = None
    lines: List[TextLine] = field(default_factory=list)
    settings: ProjectSettings = field(default_factory=ProjectSettings)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "lines": [line.to_dict() for line in self.lines],
            "settings": self.settings.to_dict(),
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        return cls(
            name=data.get("name", "Untitled"),
            lines=[TextLine.from_dict(l) for l in data.get("lines", [])],
            settings=ProjectSettings.from_dict(data.get("settings", {})),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            modified_at=datetime.fromisoformat(data["modified_at"]) if "modified_at" in data else datetime.now()
        )
    
    def save(self, path: str):
        self.file_path = path
        self.modified_at = datetime.now()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: str) -> "Project":
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        project = cls.from_dict(data)
        project.file_path = path
        return project


# Speech-to-Text (Transcription) Models

@dataclass
class WordTimestamp:
    """Word-level timestamp from transcription"""
    text: str
    start: float  # seconds
    end: float    # seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "start": self.start,
            "end": self.end
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WordTimestamp":
        return cls(
            text=data["text"],
            start=data["start"],
            end=data["end"]
        )


@dataclass
class Speaker:
    """Speaker identified during diarization"""
    id: str
    name: str = ""  # Custom name assigned by user
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Speaker":
        return cls(
            id=data["id"],
            name=data.get("name", "")
        )


@dataclass
class TranscriptionSegment:
    """A segment of transcription with timestamps and optional speaker"""
    start: float  # seconds
    end: float    # seconds
    text: str
    speaker_id: Optional[str] = None
    words: List[WordTimestamp] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker_id": self.speaker_id,
            "words": [w.to_dict() for w in self.words]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionSegment":
        return cls(
            start=data["start"],
            end=data["end"],
            text=data["text"],
            speaker_id=data.get("speaker_id"),
            words=[WordTimestamp.from_dict(w) for w in data.get("words", [])]
        )


@dataclass
class TranscriptionResult:
    """Result of a transcription"""
    text: str  # Full transcribed text
    language: str  # Detected or specified language code
    segments: List[TranscriptionSegment] = field(default_factory=list)
    speakers: List[Speaker] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "segments": [s.to_dict() for s in self.segments],
            "speakers": [s.to_dict() for s in self.speakers]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionResult":
        return cls(
            text=data["text"],
            language=data["language"],
            segments=[TranscriptionSegment.from_dict(s) for s in data.get("segments", [])],
            speakers=[Speaker.from_dict(s) for s in data.get("speakers", [])]
        )
    
    def get_speaker_name(self, speaker_id: str) -> str:
        """Get speaker display name"""
        for speaker in self.speakers:
            if speaker.id == speaker_id:
                return speaker.name if speaker.name else f"Speaker {speaker.id}"
        return f"Speaker {speaker_id}"


@dataclass
class TranscriptionJob:
    """A transcription job for a single file"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_path: str = ""
    file_name: str = ""
    file_size: int = 0  # bytes
    duration: Optional[float] = None  # seconds
    language: Optional[str] = None  # None = auto-detect
    num_speakers: Optional[int] = None  # None = auto-detect
    diarize: bool = False
    status: JobStatus = JobStatus.PENDING
    result: Optional[TranscriptionResult] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "input_path": self.input_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "duration": self.duration,
            "language": self.language,
            "num_speakers": self.num_speakers,
            "diarize": self.diarize,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptionJob":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            input_path=data["input_path"],
            file_name=data.get("file_name", ""),
            file_size=data.get("file_size", 0),
            duration=data.get("duration"),
            language=data.get("language"),
            num_speakers=data.get("num_speakers"),
            diarize=data.get("diarize", False),
            status=JobStatus(data.get("status", "Pending")),
            result=TranscriptionResult.from_dict(data["result"]) if data.get("result") else None,
            error=data.get("error"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )
