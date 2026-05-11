#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}       MySuperWhisper - Installation            ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DESKTOP_TEMPLATE="$PROJECT_DIR/mysuperwhisper.desktop"
AUTOSTART_DIR="$HOME/.config/autostart"
APPLICATIONS_DIR="$HOME/.local/share/applications"
DEST_FILE_AUTOSTART="$AUTOSTART_DIR/mysuperwhisper.desktop"
DEST_FILE_APP="$APPLICATIONS_DIR/mysuperwhisper.desktop"
VENV_DIR="$PROJECT_DIR/venv"

echo -e "${GREEN}[1/7]${NC} Project directory: $PROJECT_DIR"

# =============================================================================
# System detection
# =============================================================================
echo ""
echo -e "${GREEN}[2/7]${NC} Detecting system..."

detect_package_manager() {
    if command -v apt &>/dev/null; then echo "apt"
    elif command -v dnf &>/dev/null; then echo "dnf"
    elif command -v pacman &>/dev/null; then echo "pacman"
    elif command -v zypper &>/dev/null; then echo "zypper"
    else echo "unknown"
    fi
}

PKG_MANAGER=$(detect_package_manager)
SESSION_TYPE="${XDG_SESSION_TYPE:-x11}"

IS_GNOME_WAYLAND=false
if [ "$SESSION_TYPE" = "wayland" ] && echo "${XDG_CURRENT_DESKTOP:-}" | grep -qi "gnome"; then
    IS_GNOME_WAYLAND=true
fi

echo "   Package manager : $PKG_MANAGER"
echo "   Session type    : $SESSION_TYPE"
echo "   Desktop         : ${XDG_CURRENT_DESKTOP:-unknown}"
if [ "$IS_GNOME_WAYLAND" = true ]; then
    echo -e "   ${YELLOW}GNOME Wayland detected — extra setup will be performed${NC}"
fi

# =============================================================================
# System dependencies
# =============================================================================
echo ""
echo -e "${GREEN}[3/7]${NC} Installing system dependencies..."

install_system_deps() {
    case $PKG_MANAGER in
        apt)
            # Core
            DEPS="python3 python3-pip python3-venv python3-dev python3-tk"
            # Audio (portaudio for sounddevice, pulseaudio-utils for pactl/paplay)
            DEPS="$DEPS portaudio19-dev libsndfile1 pulseaudio-utils"
            # Tray / GTK
            DEPS="$DEPS python3-gi gir1.2-ayatanaappindicator3-0.1 libgirepository1.0-dev"
            # Clipboard / notifications
            DEPS="$DEPS xclip xsel libnotify-bin"
            # Typing tool and clipboard — session-specific
            if [ "$SESSION_TYPE" = "wayland" ]; then
                DEPS="$DEPS wl-clipboard"
                if [ "$IS_GNOME_WAYLAND" = false ]; then
                    DEPS="$DEPS wtype"
                fi
                # ydotool for GNOME Wayland is handled separately (needs >= 1.x)
            else
                DEPS="$DEPS xdotool"
            fi
            echo "   Installing via apt..."
            sudo apt update
            sudo apt install -y $DEPS
            ;;
        dnf)
            DEPS="python3 python3-pip python3-devel python3-tkinter"
            DEPS="$DEPS portaudio-devel libsndfile pulseaudio-utils"
            DEPS="$DEPS python3-gobject gtk3 libappindicator-gtk3"
            DEPS="$DEPS xclip xsel libnotify"
            if [ "$SESSION_TYPE" = "wayland" ]; then
                DEPS="$DEPS wl-clipboard"
                if [ "$IS_GNOME_WAYLAND" = false ]; then
                    DEPS="$DEPS wtype"
                fi
            else
                DEPS="$DEPS xdotool"
            fi
            echo "   Installing via dnf..."
            sudo dnf install -y $DEPS
            ;;
        pacman)
            DEPS="python python-pip tk"
            DEPS="$DEPS portaudio libsndfile libpulse"
            DEPS="$DEPS python-gobject gtk3 libappindicator-gtk3"
            DEPS="$DEPS xclip xsel libnotify"
            if [ "$SESSION_TYPE" = "wayland" ]; then
                DEPS="$DEPS wl-clipboard"
                if [ "$IS_GNOME_WAYLAND" = false ]; then
                    DEPS="$DEPS wtype"
                fi
            else
                DEPS="$DEPS xdotool"
            fi
            echo "   Installing via pacman..."
            sudo pacman -S --needed --noconfirm $DEPS
            ;;
        zypper)
            DEPS="python3 python3-pip python3-devel python3-tk"
            DEPS="$DEPS portaudio-devel libsndfile1 pulseaudio-utils"
            DEPS="$DEPS python3-gobject gtk3 typelib-1_0-AyatanaAppIndicator3-0_1"
            DEPS="$DEPS xclip xsel libnotify-tools"
            if [ "$SESSION_TYPE" = "wayland" ]; then
                DEPS="$DEPS wl-clipboard"
                if [ "$IS_GNOME_WAYLAND" = false ]; then
                    DEPS="$DEPS wtype"
                fi
            else
                DEPS="$DEPS xdotool"
            fi
            echo "   Installing via zypper..."
            sudo zypper install -y $DEPS
            ;;
        *)
            echo -e "${YELLOW}   Unknown package manager.${NC}"
            echo "   Please install manually:"
            echo "   - Python 3, pip, venv, tkinter"
            echo "   - PortAudio (dev), libsndfile, pulseaudio-utils"
            echo "   - GTK3, GObject Introspection, AppIndicator"
            echo "   - xclip or xsel, libnotify"
            if [ "$SESSION_TYPE" = "wayland" ]; then
                echo "   - wl-clipboard"
                if [ "$IS_GNOME_WAYLAND" = true ]; then
                    echo "   - ydotool >= 1.x + ydotoold daemon"
                else
                    echo "   - wtype"
                fi
            else
                echo "   - xdotool"
            fi
            read -p "   Press Enter to continue or Ctrl+C to cancel..."
            ;;
    esac
}

install_system_deps

# =============================================================================
# Input group (evdev reads /dev/input/event* — required on all sessions)
# =============================================================================
echo ""
echo -e "${GREEN}[4/7]${NC} Checking input group membership..."

NEEDS_RELOGIN=false
if groups "$USER" | grep -qw input; then
    echo "   $USER is already in the input group."
else
    echo "   Adding $USER to the input group (required for global hotkeys)..."
    sudo usermod -aG input "$USER"
    NEEDS_RELOGIN=true
    echo -e "   ${YELLOW}You must log out and back in for this to take effect.${NC}"
fi

# =============================================================================
# Python virtual environment
# =============================================================================
echo ""
echo -e "${GREEN}[5/7]${NC} Setting up Python environment..."

VENV_NEEDS_RECREATE=false
if [ -d "$VENV_DIR" ]; then
    if [ -f "$VENV_DIR/pyvenv.cfg" ]; then
        if ! grep -q "include-system-site-packages = true" "$VENV_DIR/pyvenv.cfg"; then
            echo -e "${YELLOW}   Existing venv lacks --system-site-packages, recreating...${NC}"
            VENV_NEEDS_RECREATE=true
        fi
    else
        VENV_NEEDS_RECREATE=true
    fi
fi

if [ ! -d "$VENV_DIR" ] || [ "$VENV_NEEDS_RECREATE" = true ]; then
    [ -d "$VENV_DIR" ] && rm -rf "$VENV_DIR"
    echo "   Creating virtual environment..."
    python3 -m venv --system-site-packages "$VENV_DIR"
else
    echo "   Existing virtual environment OK."
fi

VENV_PIP="$VENV_DIR/bin/pip"
echo "   Updating pip..."
"$VENV_PIP" install --upgrade pip --quiet

# =============================================================================
# Python dependencies
# =============================================================================
echo ""
echo -e "${GREEN}[6/7]${NC} Installing Python dependencies..."

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "   Installing from requirements.txt..."
    "$VENV_PIP" install --upgrade -r "$PROJECT_DIR/requirements.txt"
else
    echo -e "${YELLOW}   requirements.txt not found, installing manually...${NC}"
    "$VENV_PIP" install --upgrade faster-whisper sounddevice numpy pynput pystray Pillow pyperclip evdev
fi

# CUDA runtime libs (needed by ctranslate2/faster-whisper for GPU inference)
if command -v nvidia-smi &>/dev/null; then
    echo "   NVIDIA GPU detected — installing CUDA runtime libraries..."
    "$VENV_PIP" install --upgrade nvidia-cublas-cu12 nvidia-cudnn-cu12
    echo "   CUDA runtime libraries installed."
else
    echo "   No NVIDIA GPU detected, skipping CUDA runtime libraries."
fi

# =============================================================================
# GNOME Wayland: ydotool >= 1.x + ydotoold daemon
# =============================================================================
if [ "$IS_GNOME_WAYLAND" = true ]; then
    echo ""
    echo -e "${GREEN}[GNOME Wayland]${NC} Setting up ydotool..."

    _install_ydotool_from_source() {
        echo "   Building ydotool >= 1.x from source (apt only ships 0.x)..."
        sudo apt install -y cmake libevdev-dev libudev-dev scdoc git
        BUILD_DIR=$(mktemp -d)
        git clone --depth=1 https://github.com/ReimuNotMoe/ydotool.git "$BUILD_DIR/src"
        cmake -B "$BUILD_DIR/build" "$BUILD_DIR/src"
        cmake --build "$BUILD_DIR/build" -j"$(nproc)"
        sudo cmake --install "$BUILD_DIR/build"
        rm -rf "$BUILD_DIR"
        echo "   ydotool built and installed."
    }

    need_build=false
    if command -v ydotool &>/dev/null; then
        INSTALLED_MAJOR=$(ydotool --version 2>&1 | grep -oP '\d+' | head -1)
        if [ "${INSTALLED_MAJOR:-0}" -ge 1 ] 2>/dev/null; then
            echo "   ydotool $(ydotool --version 2>&1 | head -1) already installed."
        else
            echo "   Installed ydotool is < 1.x, replacing..."
            need_build=true
        fi
    else
        APT_MAJOR=$(apt-cache show ydotool 2>/dev/null | awk '/^Version:/{print $2; exit}' | cut -d. -f1)
        if [ -n "$APT_MAJOR" ] && [ "$APT_MAJOR" -ge 1 ] 2>/dev/null; then
            echo "   Installing ydotool from apt..."
            sudo apt install -y ydotool
        else
            need_build=true
        fi
    fi

    [ "$need_build" = true ] && _install_ydotool_from_source

    if command -v ydotoold &>/dev/null; then
        echo "   Enabling ydotoold user service..."
        systemctl --user enable --now ydotoold
        echo "   ydotoold is running."
    else
        echo -e "   ${YELLOW}Warning: ydotoold not found — first characters of transcriptions may be dropped.${NC}"
    fi
fi

# =============================================================================
# Desktop files (.desktop for autostart and app launcher)
# =============================================================================
echo ""
echo -e "${GREEN}[7/7]${NC} Configuring autostart..."

PYTHON_EXEC="$VENV_DIR/bin/python"
mkdir -p "$AUTOSTART_DIR" "$APPLICATIONS_DIR"

if [ -f "$DESKTOP_TEMPLATE" ]; then
    sed -e "s|__PYTHON_EXEC__|$PYTHON_EXEC|g" \
        -e "s|__SCRIPT_PATH__|-m mysuperwhisper|g" \
        -e "s|__WORK_DIR__|$PROJECT_DIR/|g" \
        -e "s|__ICON_PATH__|$PROJECT_DIR/mysuperwhisper.svg|g" \
        "$DESKTOP_TEMPLATE" > "$DEST_FILE_AUTOSTART"
    cp "$DEST_FILE_AUTOSTART" "$DEST_FILE_APP"
    chmod +x "$DEST_FILE_AUTOSTART" "$DEST_FILE_APP"
    echo "   Desktop files created:"
    echo "   - $DEST_FILE_AUTOSTART"
    echo "   - $DEST_FILE_APP"
else
    echo -e "${YELLOW}   Desktop template not found, skipping.${NC}"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Configuration:"
echo "  - Session     : $SESSION_TYPE"
echo "  - Desktop     : ${XDG_CURRENT_DESKTOP:-unknown}"
if [ "$SESSION_TYPE" = "wayland" ]; then
    if [ "$IS_GNOME_WAYLAND" = true ]; then
        echo "  - Typing tool : ydotool (uinput)"
    else
        echo "  - Typing tool : wtype"
    fi
else
    echo "  - Typing tool : xdotool"
fi
echo "  - Python      : $PYTHON_EXEC"
echo ""

if [ "$NEEDS_RELOGIN" = true ]; then
    echo -e "${YELLOW}IMPORTANT: Log out and back in before using MySuperWhisper.${NC}"
    echo -e "${YELLOW}Global hotkeys require the input group change to take effect.${NC}"
    echo ""
fi

echo "To start manually:"
echo "  cd $PROJECT_DIR && $PYTHON_EXEC -m mysuperwhisper"
echo ""
echo "The application will start automatically at next login."
echo ""
