"""
Text pasting functionality for MySuperWhisper.
Uses clipboard paste (Ctrl+V) for speed and reliability.
"""

import os
import shutil
import subprocess
import time
import pyperclip
from .config import log


def detect_session_type():
    """Detect if running on Wayland or X11."""
    return os.environ.get("XDG_SESSION_TYPE", "").lower()


def _has_ydotool():
    """Check if ydotool is available and working."""
    if not shutil.which("ydotool"):
        return False
    # Check if ydotoold daemon is running
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "ydotool"],
            capture_output=True, text=True, timeout=1
        )
        return result.stdout.strip() == "active"
    except:
        # Try anyway - maybe running manually
        return True


def _ydotool_env():
    """Get environment for ydotool with correct socket path."""
    env = os.environ.copy()
    # System service creates socket in /tmp, not user runtime dir
    env["YDOTOOL_SOCKET"] = "/tmp/.ydotool_socket"
    return env


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
    
    # Check if we are in a terminal
    if _is_terminal(session_type):
        # Terminals (mostly) use Ctrl+Shift+V for paste
        # and handle multiline paste better as a single block.
        _paste_clipboard(text, session_type, force_ctrl_shift_v=True)
    else:
        # Standard GUI App logic
        has_newlines = '\n' in text

        if has_newlines:
            # For text with newlines, paste line by line with Shift+Return
            # This prevents validation in chat apps
            _paste_with_newlines(text, session_type)
        else:
            # Simple text: clipboard paste (Ctrl+V)
            _paste_clipboard(text, session_type)

    if press_enter:
        time.sleep(0.05)
        _press_key("Return", session_type)


def _copy_to_clipboard(text, session_type):
    """Copy text to clipboard using the appropriate tool."""
    if session_type == "wayland":
        # Use wl-copy on Wayland for native clipboard support
        try:
            subprocess.run(["wl-copy", text], check=True)
            return True
        except FileNotFoundError:
            log("wl-copy not found, falling back to pyperclip", "warning")
        except subprocess.CalledProcessError as e:
            log(f"wl-copy error: {e}", "warning")

    # Fallback to pyperclip (X11 or if wl-copy fails)
    pyperclip.copy(text)
    return True


def _paste_clipboard(text, session_type, force_ctrl_shift_v=False):
    """Paste text using clipboard (Ctrl+V or Ctrl+Shift+V)."""
    # Copy to clipboard
    _copy_to_clipboard(text, session_type)
    time.sleep(0.05)  # Slightly increased delay for reliability

    try:
        if session_type == "wayland":
            # Try ydotool first (works on KDE and other compositors)
            if _has_ydotool():
                if force_ctrl_shift_v:
                    # Ctrl+Shift+V: key codes - ctrl=29, shift=42, v=47
                    subprocess.run(["ydotool", "key", "29:1", "42:1", "47:1", "47:0", "42:0", "29:0"], env=_ydotool_env())
                else:
                    # Ctrl+V: key codes - ctrl=29, v=47
                    subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], env=_ydotool_env())
            else:
                # Fallback to wtype (works on sway/wlroots)
                if force_ctrl_shift_v:
                    subprocess.run(["wtype", "-M", "ctrl", "-M", "shift", "-k", "v", "-m", "shift", "-m", "ctrl"])
                else:
                    subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"])
        else:
            key_combo = "ctrl+shift+v" if force_ctrl_shift_v else "ctrl+v"
            # X11
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
    # Key code mappings for ydotool
    YDOTOOL_KEYCODES = {
        "return": 28, "Return": 28, "enter": 28, "Enter": 28,
        "shift": 42, "Shift": 42,
        "ctrl": 29, "Ctrl": 29, "control": 29, "Control": 29,
        "alt": 56, "Alt": 56,
    }

    try:
        if session_type == "wayland":
            if _has_ydotool():
                if '+' in key:
                    # Handle modifier+key combo (e.g., "shift+Return")
                    parts = key.split('+')
                    modifier = parts[0].lower()
                    keyname = parts[1]
                    mod_code = YDOTOOL_KEYCODES.get(modifier, 42)  # default shift
                    key_code = YDOTOOL_KEYCODES.get(keyname, 28)  # default return
                    subprocess.run(["ydotool", "key", f"{mod_code}:1", f"{key_code}:1", f"{key_code}:0", f"{mod_code}:0"], env=_ydotool_env())
                else:
                    key_code = YDOTOOL_KEYCODES.get(key, 28)
                    subprocess.run(["ydotool", "key", f"{key_code}:1", f"{key_code}:0"], env=_ydotool_env())
            else:
                # Fallback to wtype
                if '+' in key:
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
