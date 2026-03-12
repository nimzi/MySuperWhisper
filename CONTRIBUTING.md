# Contributing to MySuperWhisper

Thank you for your interest in contributing to MySuperWhisper! This document provides guidelines and information for contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/oliviermary/MySuperWhisper/issues)
2. If not, create a new issue with:
   - A clear, descriptive title
   - Steps to reproduce the bug
   - Expected behavior vs actual behavior
   - Your environment (OS, Python version, GPU if applicable)
   - Relevant log output from `~/.local/share/mysuperwhisper/logs/`

### Suggesting Features

1. Check existing issues for similar suggestions
2. Create a new issue with the "enhancement" label
3. Describe the feature and its use case clearly

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/OlivierMary/MySuperWhisper.git
cd MySuperWhisper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt install xdotool libnotify-bin pulseaudio-utils

# Run the application
python -m mysuperwhisper
```

## Code Style

- Follow PEP 8 guidelines
- Use descriptive variable and function names
- Add docstrings to functions and classes
- Keep comments in English for international collaboration
- Maximum line length: 100 characters

## Project Structure

```
mysuperwhisper/
├── __init__.py          # Package initialization
├── __main__.py          # Entry point for python -m
├── main.py              # Main application logic
├── config.py            # Configuration management
├── audio.py             # Audio capture and processing
├── transcription.py     # Whisper model and transcription
├── voice_commands.py    # Voice command processing
├── paste.py             # Text pasting (xdotool/wtype)
├── notifications.py     # System and sound notifications
├── keyboard.py          # Keyboard shortcut handling
├── history.py           # Transcription history
└── tray.py              # System tray icon and menu
```

## Adding Voice Commands

Voice commands are defined in `voice_commands.py`. To add new commands:

1. Add patterns to `NEWLINE_PATTERNS` or create new pattern lists
2. Support multiple languages (French, English, Spanish at minimum)
3. Test with various pronunciations and accents

## Testing

Before submitting a PR, test:

1. Recording and transcription in multiple applications
2. Voice commands in different languages
3. History popup (Triple Ctrl)
4. System tray menu options
5. Both GPU and CPU modes

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue for any questions about contributing.
