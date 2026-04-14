"""
Text pasting functionality for MySuperWhisper.
Uses clipboard paste (Ctrl+V) for speed and reliability.
"""

import os
import subprocess
import time
import pyperclip
from .config import log


def detect_session_type():
    """Detect if running on Wayland or X11."""
    return os.environ.get("XDG_SESSION_TYPE", "").lower()


def _is_terminal(session_type):
    """
    Check if the active window is a terminal emulator.
    Uses xdotool/xprop on X11 and compatible Wayland environments.
    """
    try:
        # 1. Get Active Window ID
        # Note: xdotool might not work on native Wayland windows, 
        # but often works for XWayland or if disabled security.
        cmd_id = ["xdotool", "getactivewindow"]
        result_id = subprocess.run(cmd_id, capture_output=True, text=True, timeout=0.5)
        
        if result_id.returncode != 0:
            return False
            
        window_id = result_id.stdout.strip()
        if not window_id:
            return False

        # 2. Get Window Class
        cmd_prop = ["xprop", "-id", window_id, "WM_CLASS"]
        result_prop = subprocess.run(cmd_prop, capture_output=True, text=True, timeout=0.5)
        
        if result_prop.returncode != 0:
            return False

        # Check for terminal keywords
        # Common classes: gnome-terminal, xterm, kitty, alacritty, konsole...
        class_info = result_prop.stdout.lower()
        return "term" in class_info or "console" in class_info or "kitty" in class_info

    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        # Tools not installed or other error -> assume not terminal
        return False


def paste_text(text, press_enter=False):
    """
    Paste text into the active application using clipboard.

    Strategy:
    1. Copy text to clipboard
    2. Send Ctrl+V to paste (fast, single operation)
    3. Handle newlines with Shift+Return for soft breaks

    Args:
        text: Text to paste
        press_enter: If True, press Enter after pasting
    """
    session_type = detect_session_type()

    if session_type == "wayland":
        # wtype types text directly — handles newlines and terminals uniformly
        _paste_clipboard(text, session_type)
    elif _is_terminal(session_type):
        _paste_clipboard(text, session_type, force_ctrl_shift_v=True)
    elif '\n' in text:
        _paste_with_newlines(text, session_type)
    else:
        _paste_clipboard(text, session_type)

    if press_enter:
        time.sleep(0.05)
        _press_key("Return", session_type)


def _copy_to_clipboard(text, session_type):
    """Copy text to the correct clipboard for the session type."""
    if session_type == "wayland":
        # wl-copy writes to the native Wayland clipboard
        subprocess.run(["wl-copy"], input=text.encode(), check=True)
    else:
        pyperclip.copy(text)


def _paste_clipboard(text, session_type, force_ctrl_shift_v=False):
    """Paste text into the active application."""
    try:
        if session_type == "wayland":
            _copy_to_clipboard(text, session_type)
            time.sleep(0.05)
            key_combo = "ctrl+shift+v" if force_ctrl_shift_v else "ctrl+v"
            subprocess.run(["ydotool", "key", key_combo],
                           env={**os.environ, "DISPLAY": ""})
        else:
            _copy_to_clipboard(text, session_type)
            time.sleep(0.05)
            key_combo = "ctrl+shift+v" if force_ctrl_shift_v else "ctrl+v"
            subprocess.run(["xdotool", "key", "--clearmodifiers", key_combo])

    except FileNotFoundError as e:
        log(f"Paste tool not found: {e}", "error")


def _paste_with_newlines(text, session_type):
    """Paste text with newlines, using Shift+Return for soft breaks."""
    lines = text.split('\n')

    for i, line in enumerate(lines):
        if line:
            _paste_clipboard(line, session_type)

        # Add soft newline (Shift+Return) between lines
        if i < len(lines) - 1:
            time.sleep(0.03)
            _press_key("shift+Return", session_type)
            time.sleep(0.02)


def _press_key(key, session_type):
    """Press a key or key combination."""
    try:
        if session_type == "wayland":
            if '+' in key:
                # Handle modifier+key combo (e.g., "shift+Return")
                parts = key.split('+')
                modifier = parts[0].lower()
                keyname = parts[1]
                subprocess.run(["wtype", "-M", modifier, "-k", keyname, "-m", modifier])
            else:
                subprocess.run(["wtype", "-k", key])
        else:
            subprocess.run(["xdotool", "key", "--clearmodifiers", key])
    except FileNotFoundError as e:
        log(f"Key press tool not found: {e}", "error")


def press_enter_key():
    """Simulate pressing the Enter key."""
    session_type = detect_session_type()
    _press_key("Return", session_type)
