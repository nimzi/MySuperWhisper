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
  <a href="#gnome-wayland-setup">GNOME Wayland</a> •
  <a href="#usage">Usage</a> •
  <a href="#voice-commands">Voice Commands</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#contributing">Contributing</a>
</p>

---

MySuperWhisper is a Linux desktop application that provides **global voice-to-text transcription** using OpenAI's Whisper model. Simply press **Double Ctrl** anywhere on your system to start recording, speak, and press **Double Ctrl** again - your speech is transcribed and automatically typed into any application.

## Features

- 🎤 **Global Hotkey** - Fully configurable shortcut works in any application
- 🚀 **GPU Acceleration** - Uses CUDA with float16 for fast transcription
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

# For Wayland support
sudo apt install wl-clipboard ydotool

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## GNOME Wayland Setup

The default install works on **X11 and non-GNOME Wayland compositors** out of the box.
On **GNOME Wayland** (tested on Ubuntu 24.04), three additional steps are required
because mutter does not support the virtual keyboard protocol used by `wtype`.

### Why the default install breaks on GNOME Wayland

| Problem | Root cause | Fix applied |
|---------|-----------|-------------|
| Global hotkey does nothing | `pynput` uses the X11/Xlib backend when `$DISPLAY` is set; only sees events in XWayland windows | Replaced with `evdev` listener reading `/dev/input/event*` directly |
| Text never appears after transcription | `wtype` requires `zwp_virtual_keyboard_v1`, unsupported by mutter | Replaced with `ydotool type` via kernel uinput |
| First 1–2 characters are cut off | Without `ydotoold`, each `ydotool` run creates a fresh uinput device; kernel needs ~300 ms to register it | Run `ydotoold` as a persistent user service |

### Extra steps for GNOME Wayland

**1. Ensure your user is in the `input` group**

The `evdev`-based keyboard listener reads `/dev/input/event*` directly, which requires
membership in the `input` group:

```bash
groups $USER | grep input   # should list 'input'
# If not:
sudo usermod -aG input $USER   # then log out and back in
```

**2. Install `wl-clipboard`**

```bash
sudo apt install wl-clipboard
```

**3. Install `ydotool` ≥ 1.x and enable the `ydotoold` daemon**

Without the `ydotoold` daemon, each `ydotool` invocation creates a fresh uinput
device and the kernel takes ~300 ms to register it — causing the first 1–2
characters of every transcription to be silently dropped. The daemon keeps a
single uinput device alive permanently, so there is zero startup latency.

First check whether your distro already ships a version that includes `ydotoold`:

```bash
apt-cache show ydotool | grep Version
# If Version >= 1.0, just install it:
sudo apt install ydotool
```

On **Ubuntu 24.04**, apt only ships **0.1.8** which does not include `ydotoold`.
Build from source instead (later Ubuntu releases may ship ≥ 1.x, making this unnecessary):

```bash
# Build dependencies
sudo apt install cmake libevdev-dev libudev-dev scdoc

# Build and install
git clone --depth=1 https://github.com/ReimuNotMoe/ydotool.git /tmp/ydotool-src
cmake -B /tmp/ydotool-src/build /tmp/ydotool-src
cmake --build /tmp/ydotool-src/build -j$(nproc)
sudo cmake --install /tmp/ydotool-src/build
```

Either way, enable the daemon as a user systemd service (starts automatically on login):

```bash
systemctl --user enable --now ydotoold
```

After these steps, restart MySuperWhisper — global hotkeys and text typing will work
in all applications including terminals.

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

Keyboard shortcuts are **fully configurable** via the system tray menu under "⌨️ Keyboard Shortcuts". Click "Configure..." to open the shortcut detection popup:

1. **Press your desired shortcut** exactly as you want to use it (e.g., double-tap Ctrl+A, triple Right Ctrl, single F1...)
2. The popup **shows in real-time** what is detected (key, combination, and tap count)
3. Click **OK** to validate

You can use **any key or combination**: modifier keys (Ctrl, Alt, Shift), function keys (F1-F12), regular keys (A-Z, 0-9), or combinations like Ctrl+A, Alt+Space, Shift+F1, etc.

### System Tray

Right-click the tray icon to access:
- Enable/disable notifications
- Configure keyboard shortcuts
- View transcription history
- Test microphone with audio loopback
- Select AI model size
- Select language and transcription task
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
    "record_hotkey": "ctrl_l+a",
    "record_press_count": 2,
    "history_hotkey": "ctrl_l",
    "history_press_count": 3,
    "input_device": "Your Microphone",
    "output_device": "Your Speakers",
    "system_notifications_enabled": true,
    "sound_notifications_enabled": true
}
```

This example configures:
- Double press of Left Ctrl + A for recording
- Triple press of Left Ctrl for history
- English language transcription

### Configuration Options

- **model_size**: Size of Whisper model (see Model Sizes table below)
- **language**: Language code for transcription (`"en"`, `"fr"`, `"es"`, etc.) or `null` for auto-detection
- **task**: Either `"transcribe"` (default) or `"translate"` (translates audio to English)
- **record_hotkey**: Key or combination for recording - any key (`"ctrl_l"`, `"f1"`, `"a"`) or combination (`"ctrl_l+a"`, `"alt+space"`)
- **record_press_count**: Number of presses for recording - `1` (single), `2` (double), or `3` (triple)
- **history_hotkey**: Key or combination for opening history popup
- **history_press_count**: Number of presses for history popup
- **input_device** / **output_device**: Audio device names (set via tray menu)
- **system_notifications_enabled**: Show desktop notifications
- **sound_notifications_enabled**: Play audio beeps

**Tip:** You can configure keyboard shortcuts easily through the system tray menu under "⌨️ Keyboard Shortcuts" — a detection popup lets you set shortcuts by simply pressing them, no manual editing needed.

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

### Microphone privacy indicator stays on

MySuperWhisper opens the microphone stream once at startup and keeps it open for
the lifetime of the process. The audio callback silently discards everything while
you are not actively recording, but the OS has no way to know that — so GNOME (and
other desktops) show the microphone privacy indicator the entire time the app is
running.

This is by design: opening a stream is fast most of the time, but on some hardware
it can introduce a noticeable delay, so the app keeps it open to guarantee an
instant response when you press Double Ctrl.

If the always-on indicator bothers you, the stream could instead be opened on
Double Ctrl (recording start) and closed after transcription finishes. The
trade-off is a small delay (~50 ms on most systems, potentially longer on some
hardware) at the beginning of each recording before audio capture actually starts.

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
- On **GNOME Wayland**, text is typed directly via `ydotool` (uinput) — the clipboard is not used. See [GNOME Wayland Setup](#gnome-wayland-setup).
- On **X11**, transcribed text is copied to the clipboard and pasted with Ctrl+V.

### New line doesn't work in terminal
- On Wayland, `ydotool type` handles newlines natively — no special paste key needed.
- On X11, the app auto-switches to Ctrl+Shift+V in detected terminal windows.

## Dependencies

MySuperWhisper uses these excellent open-source projects:

| Package | Purpose | License |
|---------|---------|---------|
| [faster-whisper](https://github.com/guillaumekln/faster-whisper) | Whisper implementation | MIT |
| [evdev](https://github.com/gvalkov/python-evdev) | Global keyboard monitoring (Wayland) | MIT |
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
