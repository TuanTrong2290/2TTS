"""Pytest fixtures for 2TTS tests"""
import pytest
import tempfile
import os
from pathlib import Path

from core.models import TextLine, Voice, APIKey, Proxy, ProxyType, VoiceSettings, Project


@pytest.fixture
def sample_text_lines():
    """Create sample text lines for testing"""
    return [
        TextLine(index=0, text="Hello, this is a test."),
        TextLine(index=1, text="This is another sentence for testing."),
        TextLine(index=2, text="A third line with more content.")
    ]


@pytest.fixture
def sample_voice():
    """Create a sample voice for testing"""
    return Voice(
        voice_id="test_voice_id",
        name="Test Voice",
        is_cloned=False,
        category="test"
    )


@pytest.fixture
def sample_api_key():
    """Create a sample API key for testing"""
    return APIKey(
        key="test_api_key_12345",
        name="Test Key",
        character_limit=10000,
        character_count=5000,
        is_valid=True
    )


@pytest.fixture
def sample_proxy():
    """Create a sample proxy for testing"""
    return Proxy(
        host="127.0.0.1",
        port=8080,
        proxy_type=ProxyType.HTTP
    )


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_project(sample_text_lines):
    """Create a sample project for testing"""
    project = Project(name="Test Project")
    project.lines = sample_text_lines
    return project
