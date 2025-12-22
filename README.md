# 2TTS - ElevenLabs Text-To-Speech Tool

A powerful desktop application for batch text-to-speech conversion using the ElevenLabs API.

## Features

- **File Import**: Support for SRT, TXT, and DOCX files with drag-and-drop
- **Auto-Split**: Automatically splits long text at natural break points
- **Multi-Voice**: Assign different voices to individual lines
- **Multi-Account**: Multiple API keys with automatic rotation
- **Proxy Support**: HTTP and SOCKS5 proxies with rotation
- **Multi-Threaded**: Process 1-50 items simultaneously
- **Voice Settings**: Per-voice stability, similarity, speed, and model
- **Voice Library**: Save favorite voices for quick access
- **SRT Generation**: Generate subtitles with accurate timing
- **MP3 Concatenation**: Join all audio into a single file
- **Loop Mode**: Repeat processing for quota farming
- **Auto-Retry**: Automatic retry with exponential backoff
- **Project Save**: Save and resume projects
- **Language Detection**: Auto-detect text language
- **Credit Monitoring**: Track remaining credits across all keys
- **Themes**: Dark and light theme support

## Installation

1. Install Python 3.9+
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python main.py
   ```

## Requirements

- Python 3.9+
- FFmpeg (for MP3 concatenation)
- ElevenLabs API key(s)

## Usage

1. Add your ElevenLabs API key(s) via Tools > API Keys
2. Select a default voice from the dropdown
3. Import files by dragging them onto the drop zone or via File > Import
4. Adjust voice settings as needed
5. Click Start to begin processing
6. Use "Join MP3" to concatenate all audio files
7. Use "Generate SRT" to create subtitles

## Keyboard Shortcuts

- Ctrl+N: New project
- Ctrl+O: Open project
- Ctrl+S: Save project
- Ctrl+I: Import files

## Configuration

Settings are stored in `~/.2tts/`:
- `config.json`: General settings
- `api_keys.json`: API keys
- `proxies.json`: Proxy configuration
- `voice_library.json`: Saved voices
