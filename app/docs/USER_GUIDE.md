# 2TTS User Guide

## Overview

2TTS is a powerful desktop application for batch text-to-speech conversion using the ElevenLabs API. It's designed for content creators, localization teams, and anyone who needs to convert large volumes of text to high-quality speech.

## Installation

### Requirements
- Windows 10/11 (64-bit)
- Internet connection
- ElevenLabs API key(s)
- FFmpeg (for audio concatenation features)

### Installing 2TTS
1. Download the latest `2TTS-Setup.exe` from the releases page
2. Run the installer and follow the prompts
3. Launch 2TTS from the Start Menu or Desktop shortcut

## Getting Started

### Adding Your API Key
1. Go to **Tools > API Key Manager**
2. Click **Add Key**
3. Enter your ElevenLabs API key
4. Optionally add a label (e.g., "Main Account")
5. Click **Validate** to check the key
6. Click **Save**

### Importing Text

#### Supported File Formats
- `.txt` - Plain text files
- `.srt` - Subtitle files
- `.docx` - Microsoft Word documents

#### Import Methods
1. **Drag & Drop**: Drag files directly onto the main window
2. **File Menu**: Go to **File > Import** and select files
3. **Folder Import**: Go to **File > Import Folder** for batch import

### Processing Text

#### Auto-Split Feature
Long texts are automatically split at natural break points:
- Sentence endings (. ? !)
- Commas and semicolons
- Custom delimiters (configurable in Settings)

Maximum ~5000 characters per segment (ElevenLabs API limit).

#### Manual Editing
- Double-click any cell in the Text column to edit
- Right-click for context menu options (Split, Merge, Delete)

### Voice Selection

#### Selecting Voices
1. Click the Voice column dropdown for any row
2. Use the search box to filter voices
3. Select the desired voice

#### Voice Library
- Go to **Voice > Voice Library** to manage voices
- Add favorites for quick access
- Configure per-voice settings (Stability, Similarity, Speed)

#### Model Selection
Available models:
- **eleven_turbo_v2_5** - Fast, good for most languages
- **eleven_multilingual_v2** - Best multilingual support
- **eleven_flash** - Fastest, lower quality

### Generating Audio

#### Starting Conversion
1. Select items to convert (or select all)
2. Set thread count (1-50, higher = faster)
3. Click **Start** button or press F5

#### Monitoring Progress
- Overall progress bar shows completion percentage
- Per-item status: Pending → Processing → Completed/Error
- Time elapsed and remaining estimate displayed in status bar

#### Controlling Processing
- **Pause**: Temporarily stop processing
- **Stop**: Cancel all pending items
- **Retry**: Re-queue failed items

### Output Management

#### Audio Files
- MP3 files saved to configured output folder
- Default: Documents\2TTS\Output
- Naming: `[index]_[first_words].mp3`

#### Opening Output
- Click **Open Output Folder** in status bar
- Or go to **File > Open Output Folder**

#### Audio Concatenation
1. Select items to concatenate
2. Right-click > **Concatenate Selected**
3. Configure silence gap between segments
4. Choose output filename

### SRT Generation

Generate subtitle files with accurate timestamps:

1. Select processed items
2. Go to **File > Export SRT**
3. Adjust timing offset if needed
4. Save the .srt file

### Project Management

#### Saving Projects
- **File > Save Project** (Ctrl+S)
- Projects saved as `.2tts` files
- Includes all items, voices, settings, and progress

#### Loading Projects
- **File > Open Project** (Ctrl+O)
- Recent projects in **File > Recent Projects**

#### Auto-Save
- Enabled by default in Settings
- Saves every 5 minutes (configurable)

## Advanced Features

### Multi-Account Management

#### Adding Multiple Keys
Use multiple API keys to increase throughput and avoid rate limits:
1. Add keys in **Tools > API Key Manager**
2. Enable/disable keys as needed
3. System automatically rotates between active keys

#### Key Rotation
When a key hits quota limit:
1. Key is marked as exhausted
2. System automatically switches to next available key
3. Exhausted key retries after cooldown period

### Proxy Configuration

#### Adding Proxies
1. Go to **Tools > Proxy Manager**
2. Click **Add Proxy**
3. Enter proxy details:
   - Type: HTTP or SOCKS5
   - Host, Port
   - Username/Password (if required)
4. Click **Test** to validate
5. Assign to specific API keys (optional)

#### Proxy Rotation
Enable automatic proxy rotation in Settings for distributed requests.

### Language Detection

Auto-detect language and select appropriate model:
1. Enable in **Settings > Language Detection**
2. Language detected per segment
3. Model automatically selected based on language

Supported languages include: English, Vietnamese, Japanese, Korean, Chinese, Spanish, French, German, and many more.

### Loop Mode

For continuous processing:
1. Enable **Loop Mode** in toolbar
2. Configure loop count (or infinite)
3. Set delay between loops
4. Processing restarts automatically after completion

## Settings

Access settings via **Tools > Settings** or press Ctrl+,

### General
- Output path
- Default voice and model
- Auto-save interval
- Theme (Light/Dark)

### Processing
- Thread count
- Auto-split enabled
- Split delimiters
- Retry attempts

### Audio
- Output format
- Silence gap duration
- Audio preview enabled

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Import Files | Ctrl+I |
| Save Project | Ctrl+S |
| Open Project | Ctrl+O |
| Start Processing | F5 |
| Pause | F6 |
| Stop | F7 |
| Settings | Ctrl+, |
| Select All | Ctrl+A |
| Delete Selected | Delete |
| Play Audio | Space |

## Troubleshooting

### Common Issues

**"Invalid API Key" error**
- Verify key in ElevenLabs dashboard
- Check for extra spaces when pasting
- Ensure key has available quota

**"Rate Limited (429)" error**
- Add more API keys
- Reduce thread count
- Enable proxy rotation

**Audio quality issues**
- Try different model (multilingual_v2 often better)
- Adjust Stability/Similarity settings
- Check voice compatibility with language

**Application won't start**
- Ensure Windows 10/11 64-bit
- Install Visual C++ Redistributable
- Check antivirus isn't blocking

### Log Files

View logs at: **Tools > Log Viewer**

Export logs for support: **Tools > Export Logs**

Log location: `%APPDATA%\2TTS\logs\`

## Support

- GitHub Issues: Report bugs and feature requests
- Documentation: https://github.com/2tts/docs
