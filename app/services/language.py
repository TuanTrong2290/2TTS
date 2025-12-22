"""Language detection service"""
from typing import Optional, Dict, List
from core.models import TextLine


class LanguageDetector:
    """Automatic language detection for text"""
    
    # Language to recommended voice/model mapping
    LANGUAGE_SUGGESTIONS: Dict[str, Dict[str, str]] = {
        "en": {"model": "eleven_turbo_v2_5", "category": "english"},
        "vi": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "ja": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "ko": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "zh-cn": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "zh-tw": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "es": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "fr": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "de": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "it": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "pt": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "ru": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "ar": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "hi": {"model": "eleven_multilingual_v2", "category": "multilingual"},
        "th": {"model": "eleven_multilingual_v2", "category": "multilingual"},
    }
    
    LANGUAGE_NAMES: Dict[str, str] = {
        "en": "English",
        "vi": "Vietnamese",
        "ja": "Japanese",
        "ko": "Korean",
        "zh-cn": "Chinese (Simplified)",
        "zh-tw": "Chinese (Traditional)",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ar": "Arabic",
        "hi": "Hindi",
        "th": "Thai",
    }
    
    def __init__(self):
        self._detector = None
        self._init_detector()
    
    def _init_detector(self):
        """Initialize language detection library"""
        try:
            import langdetect
            self._detector = langdetect
        except ImportError:
            self._detector = None
    
    def detect(self, text: str) -> Optional[str]:
        """
        Detect language of text
        Returns language code (e.g., 'en', 'vi', 'ja')
        """
        if not text or not self._detector:
            return None
        
        try:
            # Clean text for better detection
            clean_text = text.strip()
            if len(clean_text) < 10:
                return None
            
            lang = self._detector.detect(clean_text)
            return lang
        except:
            return None
    
    def detect_with_confidence(self, text: str) -> List[Dict[str, any]]:
        """
        Detect language with confidence scores
        Returns list of {lang: str, prob: float}
        """
        if not text or not self._detector:
            return []
        
        try:
            clean_text = text.strip()
            if len(clean_text) < 10:
                return []
            
            results = self._detector.detect_langs(clean_text)
            return [{"lang": r.lang, "prob": r.prob} for r in results]
        except:
            return []
    
    def get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name"""
        return self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())
    
    def get_suggested_model(self, lang_code: str) -> str:
        """Get suggested TTS model for language"""
        suggestion = self.LANGUAGE_SUGGESTIONS.get(lang_code, {})
        return suggestion.get("model", "eleven_multilingual_v2")
    
    def get_voice_for_language(self, lang_code: str, voice_mapping: dict = None, voices: list = None) -> Optional[str]:
        """
        Get recommended voice ID for a language
        First checks custom mapping, then looks for native-speaking voices
        """
        # Check custom mapping first
        if voice_mapping and lang_code in voice_mapping:
            return voice_mapping[lang_code]
        
        # Try to find a voice with matching language label
        if voices:
            for voice in voices:
                labels = voice.labels if hasattr(voice, 'labels') else {}
                if labels.get('language', '').lower() == lang_code.lower():
                    return voice.voice_id
                # Check accent label
                if labels.get('accent', '').lower().startswith(lang_code.lower()):
                    return voice.voice_id
        
        return None
    
    def get_model_for_language(self, lang_code: str, model_mapping: dict = None) -> str:
        """
        Get recommended model for a language
        Checks custom mapping first, then falls back to suggestions
        """
        # Check custom mapping first
        if model_mapping and lang_code in model_mapping:
            return model_mapping[lang_code]
        
        # Fall back to default suggestions
        return self.get_suggested_model(lang_code)
    
    def detect_and_annotate(self, lines: List[TextLine], manual_override: str = None) -> List[TextLine]:
        """
        Detect language for all lines and annotate them
        
        Args:
            lines: List of TextLine objects
            manual_override: If set, use this language for all lines instead of detection
        """
        for line in lines:
            if manual_override:
                line.detected_language = manual_override
            elif line.text:
                lang = self.detect(line.text)
                line.detected_language = lang
        return lines
    
    def set_language_override(self, lines: List[TextLine], lang_code: str) -> List[TextLine]:
        """
        Manually set language for all lines (override detection)
        """
        for line in lines:
            line.detected_language = lang_code
        return lines
    
    def is_available(self) -> bool:
        """Check if language detection is available"""
        return self._detector is not None
    
    def get_all_languages(self) -> List[dict]:
        """Get list of all supported languages with names and codes"""
        return [
            {"code": code, "name": name}
            for code, name in self.LANGUAGE_NAMES.items()
        ]
