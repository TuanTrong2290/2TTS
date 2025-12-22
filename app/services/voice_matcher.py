"""Voice matching and batch assignment service"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

from core.models import TextLine, Voice


@dataclass
class VoicePattern:
    """Pattern for automatic voice assignment"""
    id: str
    name: str
    pattern: str  # Regex pattern
    voice_id: str
    voice_name: str
    priority: int = 0
    is_regex: bool = True
    case_sensitive: bool = False
    match_type: str = "contains"  # contains, starts_with, ends_with, exact, regex
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "pattern": self.pattern,
            "voice_id": self.voice_id,
            "voice_name": self.voice_name,
            "priority": self.priority,
            "is_regex": self.is_regex,
            "case_sensitive": self.case_sensitive,
            "match_type": self.match_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VoicePattern':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SpeakerDetectionResult:
    """Result of speaker detection"""
    speaker_name: str
    confidence: float
    pattern_matched: Optional[str] = None
    suggested_voice_id: Optional[str] = None


class VoiceMatcher:
    """Matches voices to text lines based on patterns"""
    
    # Common speaker pattern formats
    SPEAKER_PATTERNS = [
        r'^([A-Z][A-Za-z\s]+):\s*',           # "John: hello"
        r'^\[([^\]]+)\]\s*',                   # "[John] hello"
        r'^<([^>]+)>\s*',                      # "<John> hello"
        r'^\(([^)]+)\)\s*',                    # "(John) hello"
        r'^【([^】]+)】\s*',                    # "【John】 hello" (CJK)
        r'^「([^」]+)」\s*',                    # "「John」 hello" (CJK)
        r'^([A-Z]{2,}):\s*',                   # "JOHN: hello" (all caps)
        r'^([A-Za-z]+\s*#\d+):\s*',           # "Speaker #1: hello"
    ]
    
    def __init__(self):
        self._patterns: List[VoicePattern] = []
        self._speaker_voice_map: Dict[str, Tuple[str, str]] = {}  # speaker -> (voice_id, voice_name)
    
    @property
    def patterns(self) -> List[VoicePattern]:
        return sorted(self._patterns, key=lambda p: -p.priority)
    
    def add_pattern(self, pattern: VoicePattern):
        self._patterns.append(pattern)
    
    def remove_pattern(self, pattern_id: str):
        self._patterns = [p for p in self._patterns if p.id != pattern_id]
    
    def clear_patterns(self):
        self._patterns.clear()
    
    def set_speaker_voice(self, speaker: str, voice_id: str, voice_name: str):
        self._speaker_voice_map[speaker.lower()] = (voice_id, voice_name)
    
    def get_speaker_voice(self, speaker: str) -> Optional[Tuple[str, str]]:
        return self._speaker_voice_map.get(speaker.lower())
    
    def clear_speaker_map(self):
        self._speaker_voice_map.clear()
    
    def detect_speaker(self, text: str) -> Optional[SpeakerDetectionResult]:
        """Detect speaker name from text"""
        for pattern in self.SPEAKER_PATTERNS:
            match = re.match(pattern, text)
            if match:
                speaker = match.group(1).strip()
                return SpeakerDetectionResult(
                    speaker_name=speaker,
                    confidence=0.9,
                    pattern_matched=pattern
                )
        return None
    
    def extract_speakers(self, lines: List[TextLine]) -> Dict[str, int]:
        """Extract all unique speakers from lines"""
        speakers = {}
        for line in lines:
            result = self.detect_speaker(line.text)
            if result:
                speaker = result.speaker_name.lower()
                speakers[speaker] = speakers.get(speaker, 0) + 1
        return speakers
    
    def match_pattern(self, text: str, pattern: VoicePattern) -> bool:
        """Check if text matches a voice pattern"""
        try:
            search_text = text if pattern.case_sensitive else text.lower()
            search_pattern = pattern.pattern if pattern.case_sensitive else pattern.pattern.lower()
            
            if pattern.match_type == "exact":
                return search_text == search_pattern
            elif pattern.match_type == "starts_with":
                return search_text.startswith(search_pattern)
            elif pattern.match_type == "ends_with":
                return search_text.endswith(search_pattern)
            elif pattern.match_type == "contains":
                return search_pattern in search_text
            elif pattern.match_type == "regex" or pattern.is_regex:
                flags = 0 if pattern.case_sensitive else re.IGNORECASE
                return bool(re.search(pattern.pattern, text, flags))
            
            return False
        except:
            return False
    
    def find_matching_voice(self, text: str) -> Optional[Tuple[str, str]]:
        """Find voice ID and name for text based on patterns"""
        # First check speaker detection
        speaker_result = self.detect_speaker(text)
        if speaker_result:
            voice_info = self.get_speaker_voice(speaker_result.speaker_name)
            if voice_info:
                return voice_info
        
        # Then check custom patterns
        for pattern in self.patterns:
            if self.match_pattern(text, pattern):
                return (pattern.voice_id, pattern.voice_name)
        
        return None
    
    def assign_voices(
        self,
        lines: List[TextLine],
        default_voice_id: Optional[str] = None,
        default_voice_name: Optional[str] = None
    ) -> List[TextLine]:
        """Assign voices to lines based on patterns and speaker detection"""
        for line in lines:
            # Skip if already has voice and not pending
            if line.voice_id and line.voice_id != default_voice_id:
                continue
            
            voice_info = self.find_matching_voice(line.text)
            if voice_info:
                line.voice_id, line.voice_name = voice_info
            elif default_voice_id:
                line.voice_id = default_voice_id
                line.voice_name = default_voice_name
        
        return lines
    
    def auto_assign_speakers(
        self,
        lines: List[TextLine],
        voices: List[Voice],
        strategy: str = "round_robin"
    ) -> Dict[str, Tuple[str, str]]:
        """
        Auto-assign voices to detected speakers
        
        Strategies:
        - round_robin: Assign voices in sequence
        - random: Random assignment
        - by_name: Try to match speaker name to voice name
        """
        speakers = self.extract_speakers(lines)
        
        if not speakers or not voices:
            return {}
        
        assignments = {}
        
        if strategy == "by_name":
            # Try to match speaker names to voice names
            for speaker in speakers:
                best_match = None
                best_score = 0
                
                for voice in voices:
                    score = self._name_similarity(speaker, voice.name)
                    if score > best_score:
                        best_score = score
                        best_match = voice
                
                if best_match and best_score > 0.3:
                    assignments[speaker] = (best_match.voice_id, best_match.name)
            
            # Fill remaining with round robin
            remaining_speakers = [s for s in speakers if s not in assignments]
            remaining_voices = [v for v in voices if v.voice_id not in [a[0] for a in assignments.values()]]
            
            for i, speaker in enumerate(remaining_speakers):
                if remaining_voices:
                    voice = remaining_voices[i % len(remaining_voices)]
                    assignments[speaker] = (voice.voice_id, voice.name)
        
        elif strategy == "random":
            import random
            shuffled = list(voices)
            random.shuffle(shuffled)
            
            for i, speaker in enumerate(speakers):
                voice = shuffled[i % len(shuffled)]
                assignments[speaker] = (voice.voice_id, voice.name)
        
        else:  # round_robin
            for i, speaker in enumerate(speakers):
                voice = voices[i % len(voices)]
                assignments[speaker] = (voice.voice_id, voice.name)
        
        # Update internal map
        for speaker, voice_info in assignments.items():
            self.set_speaker_voice(speaker, voice_info[0], voice_info[1])
        
        return assignments
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate simple similarity between two names"""
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        if name1 == name2:
            return 1.0
        
        if name1 in name2 or name2 in name1:
            return 0.7
        
        # Check for word overlap
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if words1 & words2:
            overlap = len(words1 & words2)
            total = len(words1 | words2)
            return overlap / total
        
        return 0.0
    
    def remove_speaker_prefix(self, text: str) -> str:
        """Remove speaker prefix from text"""
        for pattern in self.SPEAKER_PATTERNS:
            text = re.sub(pattern, '', text)
        return text.strip()
    
    def get_clean_text(self, line: TextLine) -> str:
        """Get text with speaker prefix removed"""
        return self.remove_speaker_prefix(line.text)


_voice_matcher: Optional[VoiceMatcher] = None


def get_voice_matcher() -> VoiceMatcher:
    global _voice_matcher
    if _voice_matcher is None:
        _voice_matcher = VoiceMatcher()
    return _voice_matcher
