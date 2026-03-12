# MySuperWhisper

<p align="center">
  <img src="mysuperwhisper.svg" alt="MySuperWhisper Logo" width="128">
</p>

<p align="center">
  <strong>Global Voice Dictation for Linux using Whisper AI</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#voice-commands">Voice Commands</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#contributing">Contributing</a>
</p>

---

MySuperWhisper is a Linux desktop application that provides **global voice-to-text transcription** using OpenAI's Whisper model. Simply press **Double Ctrl** anywhere on your system to start recording, speak, and press **Double Ctrl** again - your speech is transcribed and automatically typed into any application.

## Features

- 🎤 **Global Hotkey** - Double Ctrl works in any application
- 🚀 **GPU Acceleration** - Uses CUDA with INT8 quantization for fast transcription
- 🧠 **Multiple Models** - Choose from tiny to large-v3 based on your needs
- 🗣️ **Voice Commands** - Say "new line" or "enter" to control text formatting
- 📜 **History** - Triple Ctrl opens recent transcriptions for quick re-use
- 🔔 **Notifications** - Audio beeps and system notifications for feedback
- 🌍 **Multi-language** - Voice commands work in French, English, and Spanish
- 🖥️ **System Tray** - Easy access to settings and device selection

## Requirements

- Linux (X11 or Wayland)
- Python 3.8+
- NVIDIA GPU with CUDA (optional, falls back to CPU)
- PulseAudio or PipeWire

## Installation

### Quick Install (Ubuntu/Debian)

```bash
# Clone the repository
git clone https://github.com/oliviermary/MySuperWhisper.git
cd MySuperWhisper

# Run the installer
chmod +x install.sh
./install.sh
```

### Manual Installation

```bash
# System dependencies
sudo apt install python3-venv python3-pip xdotool libnotify-bin pulseaudio-utils

# For Wayland support (optional)
sudo apt install wtype

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Starting the Application

```bash
# Using the virtual environment
./venv/bin/python -m mysuperwhisper

# Or with the legacy script
./venv/bin/python mysuperwhisper.py
```

### Keyboard Shortcuts

**Default shortcuts:**

| Shortcut | Action |
|----------|--------|
| **Double Left Ctrl** | Start/Stop recording |
| **Triple Left Ctrl** | Open transcription history |

**Note:** Keyboard shortcuts are fully configurable via the system tray menu. You can change both the key (Left/Right Ctrl, Alt, Shift) and the number of presses (single, double, or triple) for each action.

### System Tray

Right-click the tray icon to access:
- Enable/disable notifications
- View transcription history
- Test microphone with audio loopback
- Select AI model size
- Choose input/output audio devices
- Open configuration files

### Tray Icon Colors

| Color | Status |
|-------|--------|
| 🟡 Yellow | Loading model |
| 🟢 Green | Ready |
| 🔴 Red | Recording |
| 🟠 Orange | Transcribing |
| 🔵 Blue | Mic test mode |

## Voice Commands

MySuperWhisper recognizes voice commands in multiple languages:

### New Line Commands
| Language | Commands |
|----------|----------|
| English | "new line", "newline", "line break", "next line" |
| French | "retour à la ligne", "nouvelle ligne", "à la ligne" |
| Spanish | "nueva línea", "salto de línea", "línea siguiente" |

### Validation Commands (Press Enter)
| Language | Commands |
|----------|----------|
| English | "enter", "submit", "validate", "send", "confirm" |
| French | "valider", "entrée", "entrer" |
| Spanish | "enviar", "validar", "confirmar", "entrar" |

### Example

Say: *"Hello new line How are you enter"*

Result: Types "Hello", creates a new line, types "How are you", then presses Enter.

> **Note**: In standard applications, "new line" uses `Shift+Enter` (soft line break). In **terminal emulators**, it intelligently switches to `Ctrl+Shift+V` to paste the text with actual newlines, ensuring correct behavior.

## Configuration

Configuration is stored in `~/.config/mysuperwhisper/config.json`:

```json
{
    "model_size": "medium",
    "language": "en",
    "task": "transcribe",
    "record_hotkey": "alt_r",
    "record_press_count": 1,
    "history_hotkey": "ctrl_l",
    "history_press_count": 3,
    "input_device": "Your Microphone",
    "output_device": "Your Speakers",
    "system_notifications_enabled": true,
    "sound_notifications_enabled": true
}
```

This example configures:
- Single press of Right Alt for recording
- Triple press of Left Ctrl for history
- English language transcription

### Configuration Options

- **model_size**: Size of Whisper model (see Model Sizes table below)
- **language**: Language code for transcription (`"en"`, `"fr"`, `"es"`, etc.) or `null` for auto-detection
- **task**: Either `"transcribe"` (default) or `"translate"` (translates audio to English)
- **record_hotkey**: Key for recording - `"ctrl_l"`, `"ctrl_r"`, `"alt_l"`, `"alt_r"`, `"shift_r"`
- **record_press_count**: Number of presses for recording - `1` (single), `2` (double), or `3` (triple)
- **history_hotkey**: Key for opening history popup
- **history_press_count**: Number of presses for history popup
- **input_device** / **output_device**: Audio device names (set via tray menu)
- **system_notifications_enabled**: Show desktop notifications
- **sound_notifications_enabled**: Play audio beeps

**Tip:** You can configure keyboard shortcuts easily through the system tray menu under "⌨️ Keyboard Shortcuts" without manually editing the config file.

### Model Sizes

| Model | VRAM | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | ~1GB | Fastest | Basic |
| base | ~1GB | Fast | Good |
| small | ~2GB | Medium | Better |
| **medium** | ~2GB | Standard | **Recommended** |
| large-v3 | ~3.3GB | Slow | Best |

## File Locations

| File | Location |
|------|----------|
| Configuration | `~/.config/mysuperwhisper/config.json` |
| Logs | `~/.local/share/mysuperwhisper/logs/` |
| History | `~/.local/share/mysuperwhisper/history.json` |

## Project Structure

```
MySuperWhisper/
├── mysuperwhisper/          # Main package
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── main.py              # Application logic
│   ├── config.py            # Configuration management
│   ├── audio.py             # Audio capture
│   ├── transcription.py     # Whisper integration
│   ├── voice_commands.py    # Voice command processing
│   ├── paste.py             # Text input simulation
│   ├── notifications.py     # Notifications
│   ├── keyboard.py          # Hotkey handling
│   ├── history.py           # History management
│   └── tray.py              # System tray
├── install.sh               # Installation script
├── requirements.txt         # Python dependencies
├── LICENSE                  # MIT License
├── CONTRIBUTING.md          # Contribution guidelines
└── README.md                # This file
```

## Troubleshooting

### No audio input
- Check microphone permissions
- Verify correct input device in tray menu
- Use "Mic Test" to verify audio is being captured

### Slow transcription
- Ensure CUDA is available for GPU acceleration
- Try a smaller model (tiny, base, small)
- Check if running in CPU mode (indicated in tray tooltip with [CPU])

### GPU issues after driver update
- If you recently updated your NVIDIA drivers, the app might fallback to CPU mode or fail to load the model.
- **Solution:** Restart your computer to ensure the new drivers are correctly loaded.

### Text not typed in some applications
- Some applications may not accept simulated keyboard input
- **Workaround:** The transcribed text is **always copied to your clipboard**. If automated typing fails, you can simply paste it manually (Ctrl+V).

### New line doesn't work in terminal
- This should be handled automatically now (auto-switch to Ctrl+Shift+V)
- If not, try pasting manually using Ctrl+Shift+V

## Dependencies

MySuperWhisper uses these excellent open-source projects:

| Package | Purpose | License |
|---------|---------|---------|
| [faster-whisper](https://github.com/guillaumekln/faster-whisper) | Whisper implementation | MIT |
| [pynput](https://github.com/moses-palmer/pynput) | Keyboard monitoring | LGPL-3.0 |
| [pystray](https://github.com/moses-palmer/pystray) | System tray | LGPL-3.0 |
| [sounddevice](https://python-sounddevice.readthedocs.io/) | Audio capture | MIT |
| [numpy](https://numpy.org/) | Numerical processing | BSD |
| [Pillow](https://pillow.readthedocs.io/) | Image processing | HPND |
| [pyperclip](https://github.com/asweigart/pyperclip) | Clipboard access | BSD |

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for the Whisper model
- The faster-whisper team for the optimized implementation
- All contributors and users of this project

---

<p align="center">
  Made with ❤️ for the Linux community
</p>
