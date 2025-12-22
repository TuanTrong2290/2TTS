# -*- coding: utf-8 -*-
"""Pause preprocessor for inserting pauses after punctuation marks"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PauseSettings:
    """Settings for pause insertion"""
    enabled: bool = True
    short_pause_duration: int = 300  # ms
    long_pause_duration: int = 700   # ms
    short_pause_punctuation: str = ",;:"
    long_pause_punctuation: str = ".!?。！？"
    
    def to_dict(self) -> dict:
        return {
            "pause_enabled": self.enabled,
            "short_pause_duration": self.short_pause_duration,
            "long_pause_duration": self.long_pause_duration,
            "short_pause_punctuation": self.short_pause_punctuation,
            "long_pause_punctuation": self.long_pause_punctuation
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PauseSettings":
        return cls(
            enabled=data.get("pause_enabled", True),
            short_pause_duration=data.get("short_pause_duration", 300),
            long_pause_duration=data.get("long_pause_duration", 700),
            short_pause_punctuation=data.get("short_pause_punctuation", ",;:"),
            long_pause_punctuation=data.get("long_pause_punctuation", ".!?。！？")
        )


class PausePreprocessor:
    """
    Preprocessor for inserting pauses after punctuation marks.
    
    Uses dashes/ellipses for pauses as SSML break tags are not reliably 
    supported by ElevenLabs models (they get read literally).
    """
    
    def __init__(self, settings: Optional[PauseSettings] = None):
        self._settings = settings or PauseSettings()
    
    def update_settings(self, settings: PauseSettings):
        """Update preprocessor settings"""
        self._settings = settings
    
    def preprocess(self, text: str) -> str:
        """
        Insert pause markers after punctuation marks using dashes.
        
        ElevenLabs reliably interprets dashes (-) and ellipses (...) as pauses,
        unlike SSML break tags which get read literally on some models.
        
        Args:
            text: Input text
            
        Returns:
            Text with pause markers inserted
        """
        if not self._settings.enabled:
            return text
        
        if not text:
            return text
        
        result = text
        
        # Calculate dash counts based on duration (approx 100-150ms per dash)
        # Short pause: 300ms = 2-3 dashes, Long pause: 700ms = 5-6 dashes
        short_dashes = max(2, self._settings.short_pause_duration // 100)
        long_dashes = max(3, self._settings.long_pause_duration // 100)
        
        # Use regular hyphens for pauses (more compatible than em-dashes)
        # ElevenLabs interprets multiple hyphens as pauses
        short_pause_marker = ' ' + '-' * short_dashes + ' '
        long_pause_marker = ' ' + '-' * long_dashes + ' '
        
        # Process long pauses first (to avoid double-processing)
        if self._settings.long_pause_punctuation and self._settings.long_pause_duration > 0:
            for punct in self._settings.long_pause_punctuation:
                escaped_punct = re.escape(punct)
                # Match punctuation followed by space or end of string, but not already followed by dashes
                pattern = f'({escaped_punct})(?!\\s*--)(?=\\s|$)'
                result = re.sub(pattern, f'\\1{long_pause_marker}', result)
        
        # Process short pauses
        if self._settings.short_pause_punctuation and self._settings.short_pause_duration > 0:
            for punct in self._settings.short_pause_punctuation:
                escaped_punct = re.escape(punct)
                # Match punctuation followed by space, but not already followed by dashes
                pattern = f'({escaped_punct})(?!\\s*--)(?=\\s)'
                result = re.sub(pattern, f'\\1{short_pause_marker}', result)
        
        return result
    
    def remove_pause_tags(self, text: str) -> str:
        """Remove all pause markers from text (both SSML tags and dash markers)"""
        # Remove SSML break tags (legacy)
        text = re.sub(r'\s*<break\s+time="[^"]*"\s*/>\s*', ' ', text)
        # Remove consecutive hyphens used as pause markers (2 or more)
        text = re.sub(r'\s*-{2,}\s*', ' ', text)
        # Clean up multiple spaces
        text = re.sub(r' +', ' ', text)
        return text.strip()


# Global instance
_pause_preprocessor: Optional[PausePreprocessor] = None


def get_pause_preprocessor() -> PausePreprocessor:
    """Get the global pause preprocessor instance"""
    global _pause_preprocessor
    if _pause_preprocessor is None:
        _pause_preprocessor = PausePreprocessor()
    return _pause_preprocessor
