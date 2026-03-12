"""
Keyboard shortcut handling for MySuperWhisper.
Manages configurable hotkeys for recording and history.
Supports key combinations (e.g., Ctrl+A), solo keys, and multi-tap detection.
"""

import threading
import time
from pynput import keyboard
from .config import log, config

# Callback functions (set by main module)
_on_record_hotkey = None
_on_history_hotkey = None
_is_recording_callback = None

# State for hotkey detection
_last_press_time = {}  # Dict to track last press time per key
_press_count = {}  # Dict to track press count per key
_action_timer = {}  # Dict to track action timers per key

# Currently held keys (for combo detection)
_held_keys = set()

# Known modifier key names
MODIFIER_KEYS = frozenset({
    "ctrl", "ctrl_l", "ctrl_r",
    "alt", "alt_l", "alt_r", "alt_gr",
    "shift", "shift_l", "shift_r",
    "cmd", "cmd_l", "cmd_r",
})


def set_callbacks(on_record_hotkey, on_history_hotkey, is_recording):
    """Set callback functions for keyboard shortcuts."""
    global _on_record_hotkey, _on_history_hotkey, _is_recording_callback
    _on_record_hotkey = on_record_hotkey
    _on_history_hotkey = on_history_hotkey
    _is_recording_callback = is_recording


def _get_key_name(key):
    """Convert pynput key to string name. Handles both special and character keys."""
    if hasattr(key, 'name') and key.name:
        return key.name
    if hasattr(key, 'char') and key.char:
        return key.char.lower()
    if hasattr(key, 'vk') and key.vk:
        return f"vk_{key.vk}"
    return None


def _parse_hotkey(hotkey_string):
    """
    Parse a hotkey config string into modifiers and trigger key.

    Returns:
        (set of modifier names, trigger key name)

    Examples:
        "ctrl_l+a"     -> ({"ctrl_l"}, "a")
        "ctrl_l"       -> (set(), "ctrl_l")
        "shift+f1"     -> ({"shift"}, "f1")
        "ctrl_l+alt+a" -> ({"ctrl_l", "alt"}, "a")
    """
    parts = hotkey_string.split('+')
    trigger = parts[-1]
    modifiers = set(parts[:-1]) if len(parts) > 1 else set()
    return modifiers, trigger


def _build_combo_string(held_modifiers, trigger_key):
    """Build a combo config string from held modifiers and a trigger key."""
    if held_modifiers:
        sorted_mods = sorted(held_modifiers)
        return '+'.join(sorted_mods) + '+' + trigger_key
    return trigger_key


# On Linux, pynput often reports the "left" modifier as the generic name
# (e.g., "ctrl" instead of "ctrl_l") while tkinter always uses specific names.
# This maps config names to the set of pynput names that should match.
_KEY_ALIASES = {
    "ctrl_l": ("ctrl_l", "ctrl"),
    "alt_l": ("alt_l", "alt"),
    "shift_l": ("shift_l", "shift"),
    "cmd_l": ("cmd_l", "cmd"),
    "alt_r": ("alt_r", "alt_gr"),
    "alt_gr": ("alt_gr", "alt_r"),
}


def _key_matches_name(key_name, config_name):
    """Check if a pynput key name matches a config key name (with aliases)."""
    if key_name == config_name:
        return True
    aliases = _KEY_ALIASES.get(config_name)
    return aliases is not None and key_name in aliases


def _matches_hotkey(key, hotkey_config):
    """Check if a key release matches the configured hotkey (with modifier support)."""
    key_name = _get_key_name(key)
    if not key_name:
        return False

    modifiers, trigger = _parse_hotkey(hotkey_config)

    # The released key must be the trigger
    if not _key_matches_name(key_name, trigger):
        return False

    # No modifiers required -> solo key
    if not modifiers:
        return True

    # Check all required modifiers are currently held (with alias support)
    for mod in modifiers:
        found = False
        for held in _held_keys:
            if _key_matches_name(held, mod):
                found = True
                break
        if not found:
            return False
    return True


def reset_hotkey_state():
    """Reset all hotkey press tracking state. Call when hotkey config changes."""
    _last_press_time.clear()
    _press_count.clear()
    for timer in _action_timer.values():
        if timer:
            timer.cancel()
    _action_timer.clear()


# --- Key detection mode ---
_detect_callback = None
_detect_combo = None  # The combo string being detected
_detect_count = 0
_detect_last_time = 0
_detect_timer = None


def start_key_detection(callback):
    """
    Start listening for key presses to detect shortcut.
    Calls callback(combo_string, display_name, press_count) on each tap.
    Call stop_key_detection() to end detection mode.
    """
    global _detect_callback, _detect_combo, _detect_count, _detect_last_time
    global _detect_timer

    # Cancel any leftover timer from a previous detection session
    if _detect_timer:
        _detect_timer.cancel()
        _detect_timer = None

    # Clear held keys to avoid stale state
    _held_keys.clear()
    _held_keys_time.clear()

    # Force restart the listener to guarantee a fresh X11 connection
    # (tkinter popup creation/destruction can corrupt pynput's Xlib state)
    _restart_listener()

    _detect_callback = callback
    _detect_combo = None
    _detect_count = 0
    _detect_last_time = 0
    log("Key detection started - press your shortcut...")


def stop_key_detection():
    """Stop key detection mode and restart listener for clean state."""
    global _detect_callback, _detect_timer
    _detect_callback = None
    if _detect_timer:
        _detect_timer.cancel()
        _detect_timer = None
    _held_keys.clear()
    _held_keys_time.clear()
    # Restart listener to ensure clean X11 state after tkinter popup
    _restart_listener()
    log("Key detection stopped")


def _finalize_detection():
    """Called after inactivity timeout to report the detected shortcut."""
    global _detect_timer
    _detect_timer = None
    if _detect_callback and _detect_combo:
        display = _get_key_display_name(_detect_combo)
        log(f"Shortcut detected: {_detect_count}x {_detect_combo} ({display})")
        _detect_callback(_detect_combo, display, _detect_count)


# --- Display names ---

_SINGLE_KEY_DISPLAY = {
    "ctrl_r": "Right Ctrl",
    "ctrl_l": "Left Ctrl",
    "ctrl": "Left Ctrl",
    "alt_r": "Right Alt",
    "alt_l": "Left Alt",
    "alt": "Left Alt",
    "alt_gr": "AltGr",
    "shift_r": "Right Shift",
    "shift_l": "Left Shift",
    "shift": "Left Shift",
    "cmd_r": "Right Cmd",
    "cmd_l": "Left Cmd",
    "cmd": "Left Cmd",
    "space": "Space",
    "tab": "Tab",
    "backspace": "Backspace",
    "enter": "Enter",
    "esc": "Esc",
    "caps_lock": "Caps Lock",
    "num_lock": "Num Lock",
    "scroll_lock": "Scroll Lock",
    "insert": "Insert",
    "delete": "Delete",
    "home": "Home",
    "end": "End",
    "page_up": "Page Up",
    "page_down": "Page Down",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "print_screen": "Print Screen",
    "pause": "Pause",
    "menu": "Menu",
}


def _get_single_key_display(key_name):
    """Get human-readable name for a single key."""
    # Check known keys
    if key_name in _SINGLE_KEY_DISPLAY:
        return _SINGLE_KEY_DISPLAY[key_name]
    # Function keys (f1, f2, ...)
    if key_name.startswith('f') and key_name[1:].isdigit():
        return key_name.upper()
    # Regular character keys
    if len(key_name) == 1:
        return key_name.upper()
    # Virtual key codes
    if key_name.startswith('vk_'):
        return key_name
    return key_name.capitalize()


def _get_key_display_name(combo_string):
    """Get human-readable name for a combo string (e.g., 'ctrl_l+a' -> 'Left Ctrl + A')."""
    if '+' in combo_string:
        parts = combo_string.split('+')
        return ' + '.join(_get_single_key_display(p) for p in parts)
    return _get_single_key_display(combo_string)


def _get_hotkey_description(key, count):
    """Get human-readable hotkey description including tap count."""
    key_display = _get_key_display_name(key)
    press_desc = {1: "Single", 2: "Double", 3: "Triple"}.get(count, f"{count}x")
    return f"{press_desc} {key_display}"


# --- Key event handlers ---

def _execute_hotkey_action(hotkey_name, target_count, callback):
    """Execute hotkey action after waiting period."""
    if _press_count.get(hotkey_name, 0) == target_count and callback:
        callback()

    _press_count[hotkey_name] = 0
    if hotkey_name in _action_timer:
        _action_timer[hotkey_name] = None


# Timestamp for each held key (for stale key cleanup)
_held_keys_time = {}

# Max time a key can be "held" before being considered stale (seconds)
_HELD_KEY_MAX_AGE = 10.0


def _cleanup_stale_keys():
    """Remove keys that have been 'held' for too long (missed release event)."""
    now = time.time()
    stale = [k for k, t in _held_keys_time.items() if now - t > _HELD_KEY_MAX_AGE]
    for k in stale:
        _held_keys.discard(k)
        _held_keys_time.pop(k, None)
        log(f"Cleaned up stale held key: {k}", "debug")


def _on_key_press(key):
    """Track currently held keys."""
    try:
        key_name = _get_key_name(key)
        if key_name:
            _held_keys.add(key_name)
            _held_keys_time[key_name] = time.time()
            _cleanup_stale_keys()
    except Exception as e:
        log(f"Error in key press handler: {e}", "error")


def _on_key_release(key):
    """Handle key release events."""
    try:
        _on_key_release_inner(key)
    except Exception as e:
        log(f"Error in key release handler: {e}", "error")


def _on_key_release_inner(key):
    """Inner key release handler (wrapped by _on_key_release for safety)."""
    key_name = _get_key_name(key)
    if not key_name:
        return

    # --- Key detection mode ---
    if _detect_callback:
        global _detect_combo, _detect_count, _detect_last_time, _detect_timer

        # Build the combo from currently held modifiers + released key
        is_modifier = key_name in MODIFIER_KEYS
        held_mods = {k for k in _held_keys if k in MODIFIER_KEYS and k != key_name}

        # Skip trailing modifier release after a combo
        # e.g., user did Ctrl+A, now releasing Ctrl -> ignore
        if is_modifier and _detect_combo and '+' in _detect_combo:
            _held_keys.discard(key_name)
            _held_keys_time.pop(key_name, None)
            return

        combo = _build_combo_string(held_mods, key_name)
        current_time = time.time()

        # Cancel pending finalization timer
        if _detect_timer:
            _detect_timer.cancel()
            _detect_timer = None

        # Same combo pressed quickly -> increment count
        if combo == _detect_combo and current_time - _detect_last_time < 0.5:
            _detect_count += 1
        else:
            _detect_combo = combo
            _detect_count = 1

        _detect_last_time = current_time

        # Report immediately for live feedback
        display = _get_key_display_name(combo)
        _detect_callback(combo, display, _detect_count)

        # Start timer to finalize after 0.6s of inactivity
        _detect_timer = threading.Timer(0.6, _finalize_detection)
        _detect_timer.start()

        _held_keys.discard(key_name)
        _held_keys_time.pop(key_name, None)
        return

    # --- Normal hotkey matching ---
    # Check for record hotkey
    if _matches_hotkey(key, config.record_hotkey):
        _handle_hotkey_press(
            "record",
            config.record_press_count,
            _on_record_hotkey
        )

    # Check for history hotkey (only if not recording)
    if _matches_hotkey(key, config.history_hotkey):
        if not _is_recording_callback or not _is_recording_callback():
            _handle_hotkey_press(
                "history",
                config.history_press_count,
                _on_history_hotkey
            )

    # Remove from held keys after matching
    _held_keys.discard(key_name)
    _held_keys_time.pop(key_name, None)


def _handle_hotkey_press(hotkey_name, target_count, callback):
    """Handle a hotkey press with configurable press count."""
    current_time = time.time()
    last_time = _last_press_time.get(hotkey_name, 0)

    # If delay between releases is < 0.5s -> increment counter
    if current_time - last_time < 0.5:
        _press_count[hotkey_name] = _press_count.get(hotkey_name, 0) + 1

        # If we reached the target count
        if _press_count[hotkey_name] == target_count:
            # For single press, execute immediately
            if target_count == 1:
                if callback:
                    callback()
                _press_count[hotkey_name] = 0
            else:
                # For multiple presses, wait to see if more presses come
                if hotkey_name in _action_timer and _action_timer[hotkey_name]:
                    _action_timer[hotkey_name].cancel()
                _action_timer[hotkey_name] = threading.Timer(
                    0.3,
                    lambda: _execute_hotkey_action(hotkey_name, target_count, callback)
                )
                _action_timer[hotkey_name].start()

        elif _press_count[hotkey_name] > target_count:
            # Too many presses, cancel any pending action
            if hotkey_name in _action_timer and _action_timer[hotkey_name]:
                _action_timer[hotkey_name].cancel()
                _action_timer[hotkey_name] = None
            _press_count[hotkey_name] = 0
    else:
        # Reset counter if too much time between presses
        if hotkey_name in _action_timer and _action_timer[hotkey_name]:
            _action_timer[hotkey_name].cancel()
            _action_timer[hotkey_name] = None
        _press_count[hotkey_name] = 1

        # If target is single press, execute immediately
        if target_count == 1 and callback:
            callback()
            _press_count[hotkey_name] = 0

    _last_press_time[hotkey_name] = current_time


_listener = None
_listener_should_run = False
_watchdog_running = False


def _create_listener():
    """Create a new keyboard listener."""
    return keyboard.Listener(
        on_press=_on_key_press,
        on_release=_on_key_release
    )


def _restart_listener():
    """Stop the current listener and start a fresh one."""
    global _listener
    try:
        if _listener:
            try:
                _listener.stop()
            except Exception:
                pass
        _listener = _create_listener()
        _listener.start()
        log("Keyboard listener restarted")
    except Exception as e:
        log(f"Failed to restart keyboard listener: {e}", "error")


def _listener_watchdog():
    """Monitor the keyboard listener and restart it if it dies."""
    while _listener_should_run:
        time.sleep(5)
        if _listener_should_run and _listener and not _listener.is_alive():
            log("Keyboard listener died, restarting...", "warning")
            _held_keys.clear()
            _held_keys_time.clear()
            _restart_listener()


def start_listener():
    """Start the keyboard listener with auto-restart watchdog."""
    global _listener, _listener_should_run, _watchdog_running

    _listener = _create_listener()
    _listener.start()
    _listener_should_run = True

    # Start watchdog thread (only once)
    if not _watchdog_running:
        _watchdog_running = True
        threading.Thread(target=_listener_watchdog, daemon=True).start()

    record_desc = _get_hotkey_description(config.record_hotkey, config.record_press_count)
    history_desc = _get_hotkey_description(config.history_hotkey, config.history_press_count)
    log(f"Keyboard listener started - Record: {record_desc}, History: {history_desc}")

    return _listener


def stop_listener(listener=None):
    """Stop the keyboard listener and watchdog."""
    global _listener_should_run
    _listener_should_run = False
    target = listener or _listener
    if target:
        target.stop()
        log("Keyboard listener stopped")
