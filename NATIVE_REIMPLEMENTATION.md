# Native Reimplementation — Design Document

Status: **Proposal**. Not yet started. Implementation lives in a sibling repo
(`../MySuperWhisper-rs/`) when work begins.

## Motivation

The current Python implementation depends on a long chain of external tools,
runtimes, and daemons:

- Python 3 + venv + 8 PyPI packages (`faster-whisper`, `sounddevice`, `numpy`,
  `pynput`, `pystray`, `Pillow`, `pyperclip`, `evdev`)
- `ctranslate2` (C++ inference engine used by faster-whisper)
- `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` shipped via pip
- `portaudio` (used by `sounddevice`)
- PulseAudio/PipeWire client tools — `pactl`, `paplay`
- GTK3 + libayatana-appindicator + `python-gi` (system tray)
- `tkinter` (popup dialogs)
- `xclip` / `xsel` / `wl-clipboard` (clipboard)
- `xdotool` / `wtype` / `ydotool` **plus the `ydotoold` daemon and its
  systemd user service** (text injection)
- `notify-send` (libnotify CLI, notifications)

This sprawl is the source of most of the install-time and runtime fragility
the project has hit so far (CUDA cuBLAS not found, `ydotoold` failing to open
`/dev/uinput`, GTK version mismatches, etc.).

A native rewrite would collapse the deployment surface down to:

1. The Linux kernel (`/dev/input/event*` and `/dev/uinput`) — same `input`
   group + udev rule the project already ships.
2. A D-Bus session — universal on modern Linux desktops.
3. CUDA runtime libs from the NVIDIA driver package (`libcuda`, `libnvidia-ml`).
   No separate cuBLAS/cuDNN pip packages.
4. ALSA or PulseAudio/PipeWire for audio capture (dynamically linked).
5. A Whisper model file, downloaded on first run (same as today, different
   format).

The target language is **Rust** with feature parity to the current Python
implementation and a **single statically-linked binary** as the build output.

## Goals

- Match every user-visible feature of the current Python app: tray menu,
  multi-tap hotkeys, multiple record triggers, history popup, shortcut-binding
  popup, mic test mode, voice commands (FR/EN/ES newline + validation),
  language/model/task selection, Bluetooth keyboard reconnect, audio stream
  recovery, USB mic reset.
- Eliminate every external CLI tool and daemon listed above.
- Keep CUDA-accelerated inference. Use `whisper.cpp`'s built-in CUDA backend.
- Use the same config file format and XDG paths so users can switch in place.

## Non-goals

- Cross-platform support (macOS, Windows). Linux only, same as today.
- A bundled GPU runtime — we still rely on the NVIDIA driver being installed.
- A faster transcription engine. Performance should match the current
  ctranslate2-backed build; we are not optimizing the model.

## Crate map — what replaces what

| Today's dependency | Rust replacement | Notes |
|---|---|---|
| Python + venv + pip | (eliminated) | Single binary. |
| `faster-whisper` + `ctranslate2` + nvidia-cublas/cudnn pip | `whisper-rs` (whisper.cpp bindings, `cuda` feature) | whisper.cpp has its own CUDA path. |
| `sounddevice` + portaudio + pactl/paplay | `cpal` (ALSA + PulseAudio backends) | Same backend choice as today (`pulse`), linked directly. |
| Resampling 48 kHz → 16 kHz (numpy) | `rubato` | High-quality SRC. |
| `pynput` + `evdev` (py) | `evdev` crate | Mirrors today's keyboard.py approach. |
| `xdotool` / `wtype` / `ydotool` + `ydotoold` + systemd service | `evdev` crate's uinput support (`evdev::uinput::VirtualDeviceBuilder`) | **In-process /dev/uinput — removes the daemon, the binary, the service unit, and the IPC socket.** Same udev rule. |
| `xclip` / `xsel` / `wl-clipboard` + `pyperclip` | `arboard` | X11 + Wayland in one crate. |
| `pystray` + python-gi + GTK3 + libayatana-appindicator | `ksni` (StatusNotifierItem over D-Bus) | Same GNOME-extension constraint as today's AppIndicator. |
| `notify-send` (CLI) + libnotify | `notify-rust` | D-Bus to `org.freedesktop.Notifications`. |
| `tkinter` (popups) | `egui` + `eframe` (winit) | Shortcut-binding dialog, history list. |
| `Pillow` (tray icon drawing) | Pre-rendered PNGs via `include_bytes!`, optional `tiny-skia` for badges | State colors: green/red/orange/yellow/purple. |
| JSON config | `serde` + `serde_json` + `dirs` | Same XDG paths. |
| Logging (rotating 5 × 1 MB) | `tracing` + `tracing-appender` (rolling file) | |
| Voice command regexes | `regex` | |
| Async loop / channels | `tokio` (current_thread) + `crossbeam-channel` | Recording → transcription → paste pipeline. |

## Remaining external dependencies after rewrite

1. Linux kernel devices (`/dev/input/event*`, `/dev/uinput`) — `input` group +
   udev rule (already shipped).
2. D-Bus session bus.
3. NVIDIA driver (provides `libcuda`).
4. ALSA or PulseAudio/PipeWire for capture.
5. Whisper model file (`~/.cache/whisper/ggml-*.bin`) downloaded on demand.

Eliminated entirely: Python, all PyPI packages, ctranslate2, GTK3, python-gi,
AppIndicator, tkinter, xclip/xsel/wl-clipboard, xdotool/wtype, **ydotool +
ydotoold + systemd unit**, notify-send, pactl/paplay, portaudio dev headers,
nvidia-cublas-cu12, nvidia-cudnn-cu12.

## Repository layout

```
MySuperWhisper-rs/
├── Cargo.toml                # default-features = ["cuda"]
├── build.rs                  # check nvcc availability when "cuda" is enabled
├── assets/
│   ├── tray-{idle,rec,proc,loading,cpu}.png
│   └── beeps/{start,success,error}.wav
├── src/
│   ├── main.rs               # tokio runtime, signal handling, wiring
│   ├── config.rs             # XDG paths, serde JSON, hotkey list
│   ├── audio.rs              # cpal stream, rubato resampler, mic test mode
│   ├── keyboard.rs           # evdev capture, multi-tap state machine,
│   │                         # Bluetooth reconnect
│   ├── uinput.rs             # virtual keyboard: type_string + press_combo
│   ├── transcription.rs      # whisper-rs wrapper, model load/reload
│   ├── paste.rs              # X11/Wayland strategy: clipboard+Ctrl+V vs type
│   ├── voice_commands.rs     # regex post-processing (FR/EN/ES)
│   ├── history.rs            # 20-entry ring buffer, JSON persistence
│   ├── notifications.rs      # notify-rust + cpal-played embedded WAV beeps
│   ├── tray.rs               # ksni handler, menu construction
│   ├── popups.rs             # egui windows for shortcut-bind + history
│   └── icons.rs              # load PNGs + colored status overlay
├── install.sh                # ~30 lines: udev rule, .desktop file
└── README.md
```

## Phased implementation plan

The current Python app keeps working through Phases 1–3; users only switch
once Phase 3 ships.

### Phase 1 — MVP pipeline

Validates the core stack end-to-end before touching any UI.

- `keyboard.rs`: open every `/dev/input/event*` whose capabilities include
  `EV_KEY`, detect a hardcoded double-Ctrl_L trigger. Mirror the multi-tap
  state machine at `mysuperwhisper/keyboard.py:540-680`.
- `audio.rs`: `cpal` default input device, 48 kHz mono f32, resample to 16 kHz
  via `rubato`, buffer until stop. Mirrors `mysuperwhisper/audio.py` recording
  path.
- `transcription.rs`: `whisper-rs` with the `cuda` feature. Model at
  `~/.cache/whisper/ggml-medium.bin`, auto-download from HuggingFace
  (`ggerganov/whisper.cpp`) on first run.
- `uinput.rs`: build a virtual keyboard with `VirtualDeviceBuilder`, expose
  `type_string()` and `press_combo()`. Replaces ydotool entirely.
- `paste.rs`: just `type_string()` for MVP — defer clipboard strategy.
- `main.rs`: tokio runtime, channel-based pipeline
  (`record_signal` → `audio_chunks` → `transcribe` → `paste`).

**Exit criteria**: press double-Ctrl, speak, release, see text typed.

### Phase 2 — Tray, notifications, persistence

- `config.rs`: serde-derived structs matching today's
  `mysuperwhisper/config.py:60-140` so existing `~/.config/mysuperwhisper/config.json`
  files keep working.
- `tray.rs`: `ksni::Handle` + menu items for model size, language, task,
  device, notification toggles, quit. State icons via `icons.rs`.
- `notifications.rs`: `notify_rust::Notification` builder; beeps via `cpal`
  playing embedded WAVs from `assets/beeps/`.
- `paste.rs`: X11/Wayland strategy. On X11 use `arboard` + Ctrl+V via uinput
  with clipboard save/restore to avoid clobbering the user's clipboard.

**Exit criteria**: feature parity with the current tray menu; settings persist.

### Phase 3 — Popups, history, voice commands

- `popups.rs`: `eframe::run_native` in a separate thread for the
  shortcut-binding dialog (mirrors `tray.py:308-485`) and history list
  (mirrors `mysuperwhisper/history.py`). Pause the keyboard listener while a
  popup has focus — same pattern as today.
- `history.rs`: 20-entry ring buffer in
  `~/.local/share/mysuperwhisper/history.json`.
- `voice_commands.rs`: port the regex rules from
  `mysuperwhisper/voice_commands.py` (FR/EN/ES newline + validation triggers).
- Multiple record triggers (matches commit `5c99175`).
- Mic test mode with live level gauge in the tray icon (mirrors
  `audio.py:is_testing_mic`).

**Exit criteria**: a current Python user can switch binaries and not notice
any missing feature.

### Phase 4 — Polish and packaging

- `build.rs` checks `nvcc --version` and surfaces a clear error when CUDA
  toolkit is missing.
- Static linking where possible; document remaining dynamic deps
  (`libasound`, `libcuda`).
- New `install.sh` shrinks to ~30 lines: install CUDA toolkit (if building
  from source), ship the udev rule, register `.desktop` file. The entire
  ydotool/ydotoold/wtype/xclip/xsel/wl-clipboard/notify-send/pactl/paplay/GTK3/
  python-gi/AppIndicator/portaudio/tkinter installation blocks are gone.
- GitHub Actions release builds for x86_64 and aarch64 with prebuilt binaries
  so end users can skip the toolchain entirely.

## Critical files to mirror

The Rust modules are new code, but the *logic* of each comes from a Python
counterpart in this repo. Reference points while porting:

- Multi-tap hotkey state machine: `mysuperwhisper/keyboard.py:540-680`
- Bluetooth reconnect (commit `b7e2a7e`): `mysuperwhisper/keyboard.py`
- Audio stream recovery and USB mic reset (commit `b7e2a7e`):
  `mysuperwhisper/audio.py`
- Paste-vs-type decision tree: `mysuperwhisper/paste.py`
- Voice command regex rules: `mysuperwhisper/voice_commands.py`
- History UI behavior (arrow keys, Enter to select):
  `mysuperwhisper/history.py`
- Tray menu structure to match in `ksni`:
  `mysuperwhisper/tray.py:700-770`

## Risks and open questions

1. **GNOME Wayland tray support**: `ksni` produces an SNI; GNOME still needs
   the AppIndicator/KStatusNotifierItem extension. Same constraint as today —
   no better, no worse.
2. **whisper.cpp CUDA build**: needs `nvcc` at build time. Users who build
   from source need the CUDA toolkit (not just the driver). Shipping prebuilt
   binaries via GitHub Releases hides this for everyone but maintainers.
3. **`egui` popup startup time**: `winit` + Vulkan/GL initialization can
   flash a frame on first open. tkinter has the same problem today; should
   be acceptable.
4. **Model file format mismatch**: faster-whisper uses ctranslate2's
   converted format; whisper.cpp uses `ggml-*.bin`. First-run download fetches
   from a different URL (`huggingface.co/ggerganov/whisper.cpp`).
5. **whisper.cpp accuracy parity**: faster-whisper applies VAD + beam-search
   defaults differently. Tune `whisper-rs`'s `FullParams` to match before
   declaring parity.

## Verification strategy

Per phase, run the Rust binary alongside the Python app and compare:

- **Phase 1**: `cargo run --release --features cuda`, press double-Ctrl,
  speak "the quick brown fox", confirm text appears. Compare transcription
  latency to the Python build.
- **Phase 2**: right-click tray icon, toggle each setting, kill the binary,
  restart, confirm settings persisted. Diff `config.json` against the Python
  version's file.
- **Phase 3**: trigger the shortcut-binding popup, rebind to triple-Caps,
  verify it works. Open history popup, press ↑↓ then Enter, confirm paste.
- **Phase 4**: on a fresh VM with only the NVIDIA driver + base GNOME
  installed, run `./install.sh` and confirm the app launches and transcribes
  without pulling Python, GTK, ydotool, etc.

## Alternative: surgical wins without a rewrite

If a full rewrite isn't justified, two targeted changes capture most of the
fragility reduction at a tiny fraction of the cost:

1. **Replace ydotool + ydotoold with in-process uinput in Python.** A ~150-line
   module using the existing `evdev` dependency. Removes the daemon, the
   `ydotool` binary, the systemd user unit, and the IPC socket. Same udev
   rule.
2. **Vendor CUDA libs via `requirements.txt`** rather than as an install-time
   side step. Already partially done in commit `1ac6aba`; moving them out of
   `install.sh` and into `requirements.txt` makes the dependency declarative.

These two changes leave Python in place but eliminate the two most fragile
parts of the current stack.
