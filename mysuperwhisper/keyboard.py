"""
Keyboard shortcut handling for MySuperWhisper.
Manages configurable hotkeys for recording and history.
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


def set_callbacks(on_record_hotkey, on_history_hotkey, is_recording):
    """
    Set callback functions for keyboard shortcuts.

    Args:
        on_record_hotkey: Function to call on record hotkey
        on_history_hotkey: Function to call on history hotkey
        is_recording: Function that returns True if currently recording
    """
    global _on_record_hotkey, _on_history_hotkey, _is_recording_callback
    _on_record_hotkey = on_record_hotkey
    _on_history_hotkey = on_history_hotkey
    _is_recording_callback = is_recording


def _get_key_name(key):
    """Convert pynput key to string name."""
    if hasattr(key, 'name'):
        return key.name
    return None


def _matches_hotkey(key, hotkey_config):
    """Check if a key matches the configured hotkey."""
    key_name = _get_key_name(key)
    if not key_name:
        return False

    # Exact match
    if key_name == hotkey_config:
        return True

    # Support generic "ctrl", "alt", "shift" matching both left and right
    if hotkey_config in ["ctrl", "alt", "shift", "cmd"]:
        if key_name in [hotkey_config, f"{hotkey_config}_l", f"{hotkey_config}_r"]:
            return True

    return False


def _execute_hotkey_action(hotkey_name, target_count, callback):
    """Execute hotkey action after waiting period."""
    global _press_count, _action_timer

    # Check that press count matches and we have a callback
    if _press_count.get(hotkey_name, 0) == target_count and callback:
        callback()

    _press_count[hotkey_name] = 0
    if hotkey_name in _action_timer:
        _action_timer[hotkey_name] = None


def _on_key_release(key):
    """Handle key release events."""
    global _last_press_time, _press_count, _action_timer

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


def _handle_hotkey_press(hotkey_name, target_count, callback):
    """Handle a hotkey press with configurable press count."""
    global _last_press_time, _press_count, _action_timer

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


def start_listener():
    """
    Start the keyboard listener.

    Returns:
        keyboard.Listener: The listener instance
    """
    listener = keyboard.Listener(on_release=_on_key_release)
    listener.start()

    # Log configured hotkeys
    record_desc = _get_hotkey_description(config.record_hotkey, config.record_press_count)
    history_desc = _get_hotkey_description(config.history_hotkey, config.history_press_count)
    log(f"Keyboard listener started - Record: {record_desc}, History: {history_desc}")

    return listener


def _get_hotkey_description(key, count):
    """Get human-readable hotkey description."""
    key_display = {
        "ctrl_r": "Right Ctrl",
        "ctrl_l": "Left Ctrl",
        "ctrl": "Ctrl (any)",  # Backward compatibility
        "alt_r": "Right Alt",
        "alt_l": "Left Alt",
        "alt": "Alt (any)",  # Backward compatibility
        "alt_gr": "AltGr",
        "shift_r": "Right Shift",
        "shift_l": "Left Shift",
        "shift": "Shift (any)",  # Backward compatibility
        "cmd_r": "Right Cmd",
        "cmd_l": "Left Cmd",
        "cmd": "Cmd (any)"  # Backward compatibility
    }.get(key, key.capitalize())

    press_desc = {1: "Single", 2: "Double", 3: "Triple"}.get(count, f"{count}x")
    return f"{press_desc} {key_display}"


def stop_listener(listener):
    """
    Stop the keyboard listener.

    Args:
        listener: The listener instance to stop
    """
    if listener:
        listener.stop()
        log("Keyboard listener stopped")
