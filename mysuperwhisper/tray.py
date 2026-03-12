"""
System tray icon and menu for MySuperWhisper.
Provides visual feedback and configuration access.
"""

import subprocess
import threading
import time
import pystray
from PIL import Image, ImageDraw
from .config import log, config, CONFIG_FILE, LOG_FILE, LOG_DIR
from . import audio
from . import transcription

# Global tray icon instance
_tray_icon = None

# Callbacks (set by main module)
_on_quit_callback = None
_save_config_callback = None


def set_callbacks(on_quit, save_config):
    """Set callback functions for tray actions."""
    global _on_quit_callback, _save_config_callback
    _on_quit_callback = on_quit
    _save_config_callback = save_config


def _create_image(width, height, color, level=0.0):
    """
    Generate tray icon image.

    Args:
        width: Image width
        height: Image height
        color: Main circle color
        level: Audio level for test mode gauge (0.0-1.0)

    Returns:
        PIL.Image: Generated icon
    """
    # Create image with transparent background (RGBA)
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)

    padding = 4

    # Draw audio level gauge in test mode
    if audio.is_testing_mic():
        # Gauge background (light gray)
        dc.rectangle(
            (padding, height - padding - 10, width - padding, height - padding),
            fill=(200, 200, 200),
            outline="black"
        )

        if level > 0:
            # Level bar (green -> red)
            bar_width = int((width - 2 * padding) * min(level, 1.0))
            fill_color = "green" if level < 0.7 else "red"
            if bar_width > 0:
                dc.rectangle(
                    (padding, height - padding - 10, padding + bar_width, height - padding),
                    fill=fill_color
                )

    # Draw main status circle
    circle_height = height - padding - 15 if audio.is_testing_mic() else height - padding
    dc.ellipse((padding, padding, width - padding, circle_height), fill=color, outline="black")

    # CPU mode indicator (warning triangle in bottom right)
    if transcription.is_cpu_mode():
        triangle_size = 18
        tx = width - padding - 2
        ty = circle_height - 2
        triangle_points = [
            (tx - triangle_size, ty),
            (tx, ty),
            (tx - triangle_size // 2, ty - triangle_size),
        ]
        dc.polygon(triangle_points, fill=(255, 140, 0), outline="black")
        # Exclamation mark
        excl_x = tx - triangle_size // 2
        excl_y = ty - triangle_size // 2 - 1
        dc.rectangle((excl_x - 1, excl_y - 4, excl_x + 1, excl_y + 1), fill="black")
        dc.rectangle((excl_x - 1, excl_y + 3, excl_x + 1, excl_y + 5), fill="black")

    return image


def update_tray(status, level=0.0):
    """
    Update tray icon and tooltip based on status.

    Args:
        status: One of 'idle', 'recording', 'processing', 'testing', 'loading'
        level: Audio level for test mode (0.0-1.0)
    """
    if _tray_icon is None:
        return

    # Constant prefix to prevent icon reordering
    prefix = "MySuperWhisper: "
    color = "green"
    detail = ""

    if status == "idle":
        color = "green"
        # Show configured hotkey in tooltip
        from .keyboard import _get_hotkey_description
        hotkey_desc = _get_hotkey_description(config.record_hotkey, config.record_press_count)
        detail = f"Ready ({hotkey_desc})"
    elif status == "recording":
        color = "red"
        detail = "Recording..."
    elif status == "processing":
        color = "orange"
        detail = "Transcribing..."
    elif status == "testing":
        color = "blue"
        detail = "Mic Test"
    elif status == "loading":
        color = "yellow"
        detail = "Loading..."

    if audio.is_testing_mic():
        detail = f"Level: {int(level*100)}%"
        if status == "idle":
            color = "blue"

    # Add CPU mode indicator to tooltip
    if transcription.is_cpu_mode() and status != "loading":
        detail += " [CPU]"

    try:
        _tray_icon.icon = _create_image(64, 64, color, level)
        _tray_icon.title = prefix + detail
    except Exception:
        pass  # Avoid crashes if icon is being closed


def _open_file_with_default_app(filepath):
    """Open a file with the system's default application."""
    try:
        subprocess.Popen(["xdg-open", str(filepath)])
        log(f"Opening: {filepath}")
    except Exception as e:
        log(f"Error opening file {filepath}: {e}", "error")


def _on_open_config(icon, item):
    """Open configuration file in default editor."""
    if not CONFIG_FILE.exists() and _save_config_callback:
        _save_config_callback()
    _open_file_with_default_app(CONFIG_FILE)


def _on_open_logs(icon, item):
    """Open log file in default editor."""
    _open_file_with_default_app(LOG_FILE)


def _on_open_log_folder(icon, item):
    """Open logs folder in file manager."""
    _open_file_with_default_app(LOG_DIR)


def _on_toggle_test(icon, item):
    """Toggle microphone test mode."""
    if audio.is_testing_mic():
        audio.stop_mic_test()
        update_tray("idle")
    else:
        def _update_ui(level):
            update_tray("testing", level)
            
        audio.start_mic_test(_update_ui)


def _on_toggle_system_notifications(icon, item):
    """Toggle system notifications."""
    config.system_notifications_enabled = not config.system_notifications_enabled
    if _save_config_callback:
        _save_config_callback()
    log(f"System notifications: {'enabled' if config.system_notifications_enabled else 'disabled'}")


def _on_toggle_sound_notifications(icon, item):
    """Toggle sound notifications."""
    config.sound_notifications_enabled = not config.sound_notifications_enabled
    if _save_config_callback:
        _save_config_callback()
    log(f"Sound notifications: {'enabled' if config.sound_notifications_enabled else 'disabled'}")


def _on_show_history(icon, item):
    """Open history popup."""
    from . import history
    history.open_history_popup_async()


def _on_open_sound_settings(icon, item):
    """Open system sound settings."""
    try:
        # Try different sound settings commands
        for cmd in [
            ["cinnamon-settings", "sound"],  # Cinnamon
            ["gnome-control-center", "sound"],  # GNOME
            ["pavucontrol"],  # PulseAudio Volume Control
            ["xdg-open", "settings://sound"],  # Generic
        ]:
            try:
                subprocess.Popen(cmd)
                log(f"Opened sound settings: {cmd[0]}")
                return
            except FileNotFoundError:
                continue
        log("Could not find sound settings application", "warning")
    except Exception as e:
        log(f"Error opening sound settings: {e}", "error")


def _on_select_model(name):
    """Create handler for model selection."""
    def wrapper(icon, item):
        if config.model_size != name:
            def _reload():
                update_tray("loading")
                transcription.reload_model(name)
                if _save_config_callback:
                    _save_config_callback()
                update_tray("idle")

            threading.Thread(target=_reload, daemon=True).start()
    return wrapper


def _on_select_source(name):
    """Handler for microphone selection."""
    def wrapper(icon, item):
        # Determine if selecting "System Default" (name=None)
        if name is None:
            config.input_device = None
            config.save()
            audio.restart_stream()
        else:
            audio.set_default_source(name)
        
        # Refresh menu
        icon.menu = _create_menu()
    return wrapper


def _on_select_sink(name):
    """Handler for speaker selection."""
    def wrapper(icon, item):
        if name is None:
            config.output_device = None
            config.save()
        else:
            audio.set_default_sink(name)
            
        icon.menu = _create_menu()
    return wrapper


def _on_refresh_devices(icon, item):
    """Refresh device list."""
    log("Manual device refresh...")
    icon.menu = _create_menu()


def _on_select_record_key(key_name):
    """Handler for record hotkey selection."""
    def wrapper(icon, item):
        if config.record_hotkey != key_name:
            config.record_hotkey = key_name
            if _save_config_callback:
                _save_config_callback()

            from .keyboard import _get_hotkey_description
            desc = _get_hotkey_description(config.record_hotkey, config.record_press_count)
            log(f"Record hotkey changed to: {desc}")

            # Refresh menu
            icon.menu = _create_menu()
            update_tray("idle")
    return wrapper


def _on_select_record_count(count):
    """Handler for record press count selection."""
    def wrapper(icon, item):
        if config.record_press_count != count:
            config.record_press_count = count
            if _save_config_callback:
                _save_config_callback()

            from .keyboard import _get_hotkey_description
            desc = _get_hotkey_description(config.record_hotkey, config.record_press_count)
            log(f"Record hotkey changed to: {desc}")

            # Refresh menu
            icon.menu = _create_menu()
            update_tray("idle")
    return wrapper


def _on_select_history_key(key_name):
    """Handler for history hotkey selection."""
    def wrapper(icon, item):
        if config.history_hotkey != key_name:
            config.history_hotkey = key_name
            if _save_config_callback:
                _save_config_callback()

            from .keyboard import _get_hotkey_description
            desc = _get_hotkey_description(config.history_hotkey, config.history_press_count)
            log(f"History hotkey changed to: {desc}")

            # Refresh menu
            icon.menu = _create_menu()
    return wrapper


def _on_select_history_count(count):
    """Handler for history press count selection."""
    def wrapper(icon, item):
        if config.history_press_count != count:
            config.history_press_count = count
            if _save_config_callback:
                _save_config_callback()

            from .keyboard import _get_hotkey_description
            desc = _get_hotkey_description(config.history_hotkey, config.history_press_count)
            log(f"History hotkey changed to: {desc}")

            # Refresh menu
            icon.menu = _create_menu()
    return wrapper


def _on_quit(icon, item):
    """Quit application."""
    icon.stop()
    if _on_quit_callback:
        _on_quit_callback()


def _generate_device_menu(devices, current_device_id, on_select_callback):
    """Generate a submenu for device selection."""
    items = []

    # System default option
    items.append(pystray.MenuItem(
        "Use System Default",
        on_select_callback(None),
        checked=lambda item: current_device_id is None,
        radio=True
    ))
    items.append(pystray.Menu.SEPARATOR)

    for device in devices:
        # Truncate long descriptions
        desc = device['description']
        if len(desc) > 50:
            desc = desc[:47] + "..."

        items.append(pystray.MenuItem(
            desc,
            on_select_callback(device['name']),
            checked=lambda item, name=device['name']: current_device_id == name,
            radio=True
        ))
    return pystray.Menu(*items)


def _create_menu():
    """Create the main tray menu."""
    sources = audio.get_pulse_sources()
    sinks = audio.get_pulse_sinks()

    # Determine label for Microphone
    current_mic_bg = "Unknown"
    is_mic_default = config.input_device is None
    
    if is_mic_default:
        for s in sources:
            if s['is_default']:
                current_mic_bg = s['description']
                break
    else:
        for s in sources:
            if s['name'] == config.input_device:
                current_mic_bg = s['description']
                break
        else:
            current_mic_bg = config.input_device

    if len(current_mic_bg) > 30:
        current_mic_bg = current_mic_bg[:27] + "..."
    
    mic_label = f"🎤 {current_mic_bg}" + (" (Default)" if is_mic_default else "")


    # Determine label for Speaker
    current_spk_bg = "Unknown"
    is_spk_default = config.output_device is None

    if is_spk_default:
        for s in sinks:
            if s['is_default']:
                current_spk_bg = s['description']
                break
    else:
        for s in sinks:
            if s['name'] == config.output_device:
                current_spk_bg = s['description']
                break
        else:
            current_spk_bg = config.output_device

    if len(current_spk_bg) > 30:
        current_spk_bg = current_spk_bg[:27] + "..."

    spk_label = f"🔊 {current_spk_bg}" + (" (Default)" if is_spk_default else "")


    # Model menu
    model_menu = pystray.Menu(
        pystray.MenuItem(
            "Tiny (Very fast, less accurate)",
            _on_select_model("tiny"),
            checked=lambda item: config.model_size == "tiny",
            radio=True
        ),
        pystray.MenuItem(
            "Base (Fast)",
            _on_select_model("base"),
            checked=lambda item: config.model_size == "base",
            radio=True
        ),
        pystray.MenuItem(
            "Small (Balanced)",
            _on_select_model("small"),
            checked=lambda item: config.model_size == "small",
            radio=True
        ),
        pystray.MenuItem(
            "Medium (Standard, <2GB VRAM)",
            _on_select_model("medium"),
            checked=lambda item: config.model_size == "medium",
            radio=True
        ),
        pystray.MenuItem(
            "Large-v3 (Best, ~3.3GB VRAM)",
            _on_select_model("large-v3"),
            checked=lambda item: config.model_size == "large-v3",
            radio=True
        )
    )

    # Hotkey configuration menu
    from .keyboard import _get_hotkey_description

    # Record hotkey submenu
    record_key_menu = pystray.Menu(
        pystray.MenuItem("Right Alt", _on_select_record_key("alt_r"),
                        checked=lambda item: config.record_hotkey == "alt_r", radio=True),
        pystray.MenuItem("Right Ctrl", _on_select_record_key("ctrl_r"),
                        checked=lambda item: config.record_hotkey == "ctrl_r", radio=True),
        pystray.MenuItem("Right Shift", _on_select_record_key("shift_r"),
                        checked=lambda item: config.record_hotkey == "shift_r", radio=True),
        pystray.MenuItem("Left Ctrl", _on_select_record_key("ctrl_l"),
                        checked=lambda item: config.record_hotkey == "ctrl_l", radio=True),
        pystray.MenuItem("Left Alt", _on_select_record_key("alt_l"),
                        checked=lambda item: config.record_hotkey == "alt_l", radio=True),
    )

    record_count_menu = pystray.Menu(
        pystray.MenuItem("Single press", _on_select_record_count(1),
                        checked=lambda item: config.record_press_count == 1, radio=True),
        pystray.MenuItem("Double press", _on_select_record_count(2),
                        checked=lambda item: config.record_press_count == 2, radio=True),
        pystray.MenuItem("Triple press", _on_select_record_count(3),
                        checked=lambda item: config.record_press_count == 3, radio=True),
    )

    # History hotkey submenu
    history_key_menu = pystray.Menu(
        pystray.MenuItem("Right Alt", _on_select_history_key("alt_r"),
                        checked=lambda item: config.history_hotkey == "alt_r", radio=True),
        pystray.MenuItem("Right Ctrl", _on_select_history_key("ctrl_r"),
                        checked=lambda item: config.history_hotkey == "ctrl_r", radio=True),
        pystray.MenuItem("Right Shift", _on_select_history_key("shift_r"),
                        checked=lambda item: config.history_hotkey == "shift_r", radio=True),
        pystray.MenuItem("Left Ctrl", _on_select_history_key("ctrl_l"),
                        checked=lambda item: config.history_hotkey == "ctrl_l", radio=True),
        pystray.MenuItem("Left Alt", _on_select_history_key("alt_l"),
                        checked=lambda item: config.history_hotkey == "alt_l", radio=True),
    )

    history_count_menu = pystray.Menu(
        pystray.MenuItem("Single press", _on_select_history_count(1),
                        checked=lambda item: config.history_press_count == 1, radio=True),
        pystray.MenuItem("Double press", _on_select_history_count(2),
                        checked=lambda item: config.history_press_count == 2, radio=True),
        pystray.MenuItem("Triple press", _on_select_history_count(3),
                        checked=lambda item: config.history_press_count == 3, radio=True),
    )

    # Hotkeys submenu
    record_desc = _get_hotkey_description(config.record_hotkey, config.record_press_count)
    history_desc = _get_hotkey_description(config.history_hotkey, config.history_press_count)

    hotkeys_menu = pystray.Menu(
        pystray.MenuItem(f"🎤 Record: {record_desc}", pystray.Menu(
            pystray.MenuItem("Key", record_key_menu),
            pystray.MenuItem("Press count", record_count_menu),
        )),
        pystray.MenuItem(f"📜 History: {history_desc}", pystray.Menu(
            pystray.MenuItem("Key", history_key_menu),
            pystray.MenuItem("Press count", history_count_menu),
        )),
    )

    # Files submenu
    files_menu = pystray.Menu(
        pystray.MenuItem("Open configuration", _on_open_config),
        pystray.MenuItem("Open log file", _on_open_logs),
        pystray.MenuItem("Open logs folder", _on_open_log_folder)
    )

    menu = pystray.Menu(
        pystray.MenuItem(
            "System notifications",
            _on_toggle_system_notifications,
            checked=lambda item: config.system_notifications_enabled
        ),
        pystray.MenuItem(
            "Sound notifications",
            _on_toggle_sound_notifications,
            checked=lambda item: config.sound_notifications_enabled
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("⌨️ Keyboard Shortcuts", hotkeys_menu),
        pystray.MenuItem("History", _on_show_history),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Mic Test (audio loopback + gauge)",
            _on_toggle_test,
            checked=lambda item: audio.is_testing_mic()
        ),
        pystray.MenuItem("AI Model", model_menu),
        pystray.Menu.SEPARATOR,
        
        # Audio Devices
        pystray.MenuItem(mic_label, _generate_device_menu(sources, config.input_device, _on_select_source)),
        pystray.MenuItem(spk_label, _generate_device_menu(sinks, config.output_device, _on_select_sink)),
        
        pystray.MenuItem("Sound Settings...", _on_open_sound_settings),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Files", files_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _on_quit)
    )

    return menu


def create_tray_icon():
    """
    Create and return the tray icon.

    Returns:
        pystray.Icon: The tray icon instance
    """
    global _tray_icon

    menu = _create_menu()
    image = _create_image(64, 64, "yellow")  # Yellow for loading
    _tray_icon = pystray.Icon("MySuperWhisper", image, "MySuperWhisper: Loading...", menu)

    return _tray_icon


def run_tray():
    """Run the tray icon event loop (blocking)."""
    if _tray_icon:
        _tray_icon.run()


def device_monitor_worker():
    """Monitor for audio device changes and update menu."""
    last_device_signature = None

    while True:
        try:
            sources = audio.get_pulse_sources()
            sinks = audio.get_pulse_sinks()

            # Signature based on device names
            current_signature = str([
                (s['name'], s['description']) for s in sources
            ] + [
                (s['name'], s['description']) for s in sinks
            ])

            if last_device_signature is not None and current_signature != last_device_signature:
                log("Audio device change detected: Updating menu...")
                if _tray_icon:
                    try:
                        _tray_icon.menu = _create_menu()
                    except Exception as e:
                        log(f"Menu update error: {e}", "error")

            last_device_signature = current_signature
        except Exception as e:
            log(f"Device monitor error: {e}", "error")

        time.sleep(3)
