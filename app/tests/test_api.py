"""Tests for API integration"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.elevenlabs import ElevenLabsAPI, APIKeyManager
from core.models import APIKey, Voice, VoiceSettings


class TestAPIKeyManager:
    """Tests for APIKeyManager class"""
    
    def test_get_next_available_key(self):
        """Test getting next available key"""
        keys = [
            APIKey(key="key1", is_valid=True, enabled=True, character_limit=1000, character_count=0),
            APIKey(key="key2", is_valid=True, enabled=True, character_limit=1000, character_count=0)
        ]
        manager = APIKeyManager(keys)
        
        key = manager.get_next_available_key()
        assert key is not None
        assert key.key in ["key1", "key2"]
    
    def test_no_available_keys(self):
        """Test when no keys are available"""
        keys = [
            APIKey(key="key1", is_valid=False, enabled=True),
            APIKey(key="key2", is_valid=True, enabled=False)
        ]
        manager = APIKeyManager(keys)
        
        key = manager.get_next_available_key()
        assert key is None
    
    def test_mark_key_exhausted(self):
        """Test marking a key as exhausted"""
        keys = [APIKey(key="key1", is_valid=True, enabled=True, character_limit=1000, character_count=0)]
        manager = APIKeyManager(keys)
        
        manager.mark_key_exhausted(keys[0])
        assert keys[0].character_count == keys[0].character_limit
    
    def test_all_keys_exhausted(self):
        """Test checking if all keys are exhausted"""
        keys = [
            APIKey(key="key1", is_valid=True, enabled=True, character_limit=1000, character_count=1000)
        ]
        manager = APIKeyManager(keys)
        
        assert manager.all_keys_exhausted()


class TestElevenLabsAPI:
    """Tests for ElevenLabsAPI class"""
    
    def test_get_headers(self):
        """Test generating API headers"""
        api = ElevenLabsAPI()
        headers = api._get_headers("test_key")
        
        assert headers["xi-api-key"] == "test_key"
        assert "Content-Type" in headers
    
    @patch('services.elevenlabs.requests.Session')
    def test_validate_key_success(self, mock_session_class):
        """Test successful key validation"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "character_count": 5000,
            "character_limit": 10000
        }
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        api = ElevenLabsAPI()
        api._session = mock_session
        
        key = APIKey(key="test_key")
        success, msg = api.validate_key(key)
        
        assert success
        assert key.is_valid
        assert key.character_count == 5000
    
    @patch('services.elevenlabs.requests.Session')
    def test_validate_key_invalid(self, mock_session_class):
        """Test invalid key validation"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        api = ElevenLabsAPI()
        api._session = mock_session
        
        key = APIKey(key="invalid_key")
        success, msg = api.validate_key(key)
        
        assert not success
        assert not key.is_valid


class TestVoiceModel:
    """Tests for Voice model"""
    
    def test_voice_creation(self, sample_voice):
        """Test creating a voice"""
        assert sample_voice.voice_id == "test_voice_id"
        assert sample_voice.name == "Test Voice"
    
    def test_voice_settings(self):
        """Test voice settings"""
        settings = VoiceSettings(stability=0.8, similarity_boost=0.9, speed=1.2)
        
        assert settings.stability == 0.8
        assert settings.similarity_boost == 0.9
        assert settings.speed == 1.2
    
    def test_voice_to_dict(self, sample_voice):
        """Test serializing voice to dict"""
        data = sample_voice.to_dict()
        
        assert data["voice_id"] == "test_voice_id"
        assert data["name"] == "Test Voice"
