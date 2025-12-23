"""Usage analytics service for 2TTS (opt-in)"""
import os
import json
import uuid
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class SessionStats:
    """Statistics for a single session"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    characters_processed: int = 0
    lines_processed: int = 0
    files_imported: int = 0
    voices_used: List[str] = field(default_factory=list)
    api_calls: int = 0
    errors: int = 0
    processing_time_seconds: float = 0.0


@dataclass
class UsageStats:
    """Aggregated usage statistics"""
    total_characters: int = 0
    total_lines: int = 0
    total_sessions: int = 0
    total_processing_time: float = 0.0
    voice_usage: Dict[str, int] = field(default_factory=dict)
    daily_usage: Dict[str, int] = field(default_factory=dict)  # date -> chars
    error_count: int = 0
    first_use: Optional[datetime] = None
    last_use: Optional[datetime] = None


class AnalyticsService:
    """Local analytics tracking (opt-in, privacy-focused)"""
    
    def __init__(self):
        self._config_dir = Path.home() / ".2tts"
        self._analytics_file = self._config_dir / "analytics.json"
        self._settings_file = self._config_dir / "analytics_settings.json"
        
        self._enabled = False
        self._anonymous_id: Optional[str] = None
        self._current_session: Optional[SessionStats] = None
        self._stats = UsageStats()
        
        self._load_settings()
        self._load_stats()
    
    def _load_settings(self):
        try:
            if self._settings_file.exists():
                with open(self._settings_file, 'r') as f:
                    data = json.load(f)
                    self._enabled = data.get("enabled", False)
                    self._anonymous_id = data.get("anonymous_id")
        except:
            pass
        
        if not self._anonymous_id:
            self._anonymous_id = str(uuid.uuid4())
            self._save_settings()
    
    def _save_settings(self):
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._settings_file, 'w') as f:
                json.dump({
                    "enabled": self._enabled,
                    "anonymous_id": self._anonymous_id
                }, f, indent=2)
        except:
            pass
    
    def _load_stats(self):
        try:
            if self._analytics_file.exists():
                with open(self._analytics_file, 'r') as f:
                    data = json.load(f)
                    
                    self._stats = UsageStats(
                        total_characters=data.get("total_characters", 0),
                        total_lines=data.get("total_lines", 0),
                        total_sessions=data.get("total_sessions", 0),
                        total_processing_time=data.get("total_processing_time", 0.0),
                        voice_usage=data.get("voice_usage", {}),
                        daily_usage=data.get("daily_usage", {}),
                        error_count=data.get("error_count", 0),
                        first_use=datetime.fromisoformat(data["first_use"]) if data.get("first_use") else None,
                        last_use=datetime.fromisoformat(data["last_use"]) if data.get("last_use") else None
                    )
        except:
            self._stats = UsageStats()
    
    def _save_stats(self):
        if not self._enabled:
            return
        
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._analytics_file, 'w') as f:
                json.dump({
                    "total_characters": self._stats.total_characters,
                    "total_lines": self._stats.total_lines,
                    "total_sessions": self._stats.total_sessions,
                    "total_processing_time": self._stats.total_processing_time,
                    "voice_usage": self._stats.voice_usage,
                    "daily_usage": self._stats.daily_usage,
                    "error_count": self._stats.error_count,
                    "first_use": self._stats.first_use.isoformat() if self._stats.first_use else None,
                    "last_use": self._stats.last_use.isoformat() if self._stats.last_use else None
                }, f, indent=2)
        except:
            pass
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    def enable(self):
        """Enable analytics tracking"""
        self._enabled = True
        self._save_settings()
    
    def disable(self):
        """Disable analytics tracking"""
        self._enabled = False
        self._save_settings()
    
    def clear_data(self):
        """Clear all collected analytics data"""
        self._stats = UsageStats()
        try:
            if self._analytics_file.exists():
                self._analytics_file.unlink()
        except:
            pass
    
    def reset(self):
        """Alias for clear_data"""
        self.clear_data()
    
    def track_tts(self, characters: int, lines: int = 1, voice_id: Optional[str] = None):
        """Simple tracking method for TTS usage (always tracks, regardless of session)"""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        # Update stats directly
        self._stats.total_characters += characters
        self._stats.total_lines += lines
        
        if not self._stats.first_use:
            self._stats.first_use = now
        self._stats.last_use = now
        
        # Update daily usage
        self._stats.daily_usage[today] = self._stats.daily_usage.get(today, 0) + characters
        
        # Update voice usage
        if voice_id:
            self._stats.voice_usage[voice_id] = self._stats.voice_usage.get(voice_id, 0) + 1
        
        # Always save (force save regardless of enabled flag)
        self._force_save_stats()
    
    def _force_save_stats(self):
        """Save stats regardless of enabled flag"""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._analytics_file, 'w') as f:
                json.dump({
                    "total_characters": self._stats.total_characters,
                    "total_lines": self._stats.total_lines,
                    "total_sessions": self._stats.total_sessions,
                    "total_processing_time": self._stats.total_processing_time,
                    "voice_usage": self._stats.voice_usage,
                    "daily_usage": self._stats.daily_usage,
                    "error_count": self._stats.error_count,
                    "first_use": self._stats.first_use.isoformat() if self._stats.first_use else None,
                    "last_use": self._stats.last_use.isoformat() if self._stats.last_use else None
                }, f, indent=2)
        except:
            pass
    
    # Session management
    def start_session(self):
        """Start a new analytics session"""
        if not self._enabled:
            return
        
        self._current_session = SessionStats(
            session_id=str(uuid.uuid4()),
            start_time=datetime.now()
        )
        
        self._stats.total_sessions += 1
        if not self._stats.first_use:
            self._stats.first_use = datetime.now()
    
    def end_session(self):
        """End current analytics session"""
        if not self._enabled or not self._current_session:
            return
        
        self._current_session.end_time = datetime.now()
        self._stats.last_use = datetime.now()
        
        # Update stats
        self._stats.total_characters += self._current_session.characters_processed
        self._stats.total_lines += self._current_session.lines_processed
        self._stats.total_processing_time += self._current_session.processing_time_seconds
        self._stats.error_count += self._current_session.errors
        
        # Update voice usage
        for voice_id in self._current_session.voices_used:
            self._stats.voice_usage[voice_id] = self._stats.voice_usage.get(voice_id, 0) + 1
        
        # Update daily usage
        today = datetime.now().strftime("%Y-%m-%d")
        self._stats.daily_usage[today] = self._stats.daily_usage.get(today, 0) + self._current_session.characters_processed
        
        self._save_stats()
        self._current_session = None
    
    # Event tracking
    def track_tts_request(self, voice_id: str, characters: int, success: bool, duration_seconds: float):
        """Track a TTS request"""
        if not self._enabled or not self._current_session:
            return
        
        self._current_session.api_calls += 1
        self._current_session.characters_processed += characters
        self._current_session.processing_time_seconds += duration_seconds
        
        if voice_id not in self._current_session.voices_used:
            self._current_session.voices_used.append(voice_id)
        
        if not success:
            self._current_session.errors += 1
    
    def track_line_processed(self, count: int = 1):
        """Track lines processed"""
        if not self._enabled or not self._current_session:
            return
        self._current_session.lines_processed += count
    
    def track_file_import(self, count: int = 1):
        """Track files imported"""
        if not self._enabled or not self._current_session:
            return
        self._current_session.files_imported += count
    
    def track_error(self):
        """Track an error occurrence"""
        if not self._enabled or not self._current_session:
            return
        self._current_session.errors += 1
    
    # Statistics retrieval
    def get_stats(self) -> UsageStats:
        """Get current usage statistics"""
        return self._stats
    
    def get_session_stats(self) -> Optional[SessionStats]:
        """Get current session statistics"""
        return self._current_session
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get a summary of usage statistics"""
        return {
            "total_characters": self._stats.total_characters,
            "total_lines": self._stats.total_lines,
            "total_sessions": self._stats.total_sessions,
            "total_processing_hours": round(self._stats.total_processing_time / 3600, 2),
            "error_rate": round(self._stats.error_count / max(self._stats.total_lines, 1) * 100, 2),
            "top_voices": self._get_top_voices(5),
            "days_active": len(self._stats.daily_usage),
            "avg_chars_per_day": self._get_average_daily_usage()
        }
    
    def _get_top_voices(self, n: int) -> List[tuple]:
        """Get top N most used voices"""
        sorted_voices = sorted(
            self._stats.voice_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_voices[:n]
    
    def _get_average_daily_usage(self) -> int:
        """Get average daily character usage"""
        if not self._stats.daily_usage:
            return 0
        return int(sum(self._stats.daily_usage.values()) / len(self._stats.daily_usage))
    
    def get_daily_usage(self, days: int = 30) -> Dict[str, int]:
        """Get daily usage for the last N days"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return {
            date: chars
            for date, chars in self._stats.daily_usage.items()
            if date >= cutoff
        }
    
    def export_stats(self, file_path: str) -> bool:
        """Export statistics to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump({
                    "exported_at": datetime.now().isoformat(),
                    "summary": self.get_usage_summary(),
                    "daily_usage": self._stats.daily_usage,
                    "voice_usage": self._stats.voice_usage,
                    "total_stats": {
                        "characters": self._stats.total_characters,
                        "lines": self._stats.total_lines,
                        "sessions": self._stats.total_sessions,
                        "processing_time_seconds": self._stats.total_processing_time,
                        "errors": self._stats.error_count,
                        "first_use": self._stats.first_use.isoformat() if self._stats.first_use else None,
                        "last_use": self._stats.last_use.isoformat() if self._stats.last_use else None
                    }
                }, f, indent=2)
            return True
        except:
            return False


_analytics_service: Optional[AnalyticsService] = None


def get_analytics() -> AnalyticsService:
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service
