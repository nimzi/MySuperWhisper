#!/bin/bash
set -e

# Colors for display
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}       MySuperWhisper - Installation            ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Get absolute path of project directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DESKTOP_TEMPLATE="$PROJECT_DIR/mysuperwhisper.desktop"
AUTOSTART_DIR="$HOME/.config/autostart"
APPLICATIONS_DIR="$HOME/.local/share/applications"
DEST_FILE_AUTOSTART="$AUTOSTART_DIR/mysuperwhisper.desktop"
DEST_FILE_APP="$APPLICATIONS_DIR/mysuperwhisper.desktop"
VENV_DIR="$PROJECT_DIR/venv"

echo -e "${GREEN}[1/7]${NC} Project directory: $PROJECT_DIR"

# =============================================================================
# Package manager detection
# =============================================================================
echo ""
echo -e "${GREEN}[2/7]${NC} Detecting system..."

detect_package_manager() {
    if command -v apt &> /dev/null; then
        echo "apt"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    elif command -v pacman &> /dev/null; then
        echo "pacman"
    elif command -v zypper &> /dev/null; then
        echo "zypper"
    else
        echo "unknown"
    fi
}

PKG_MANAGER=$(detect_package_manager)
echo "   Package manager: $PKG_MANAGER"

# Session type detection (X11 or Wayland)
SESSION_TYPE="${XDG_SESSION_TYPE:-x11}"
echo "   Session type: $SESSION_TYPE"

# =============================================================================
# System dependencies installation
# =============================================================================
echo ""
echo -e "${GREEN}[3/7]${NC} Installing system dependencies..."

install_system_deps() {
    case $PKG_MANAGER in
        apt)
            # Base dependencies
            DEPS="python3 python3-pip python3-venv python3-dev"
            # Compilation (required for numpy, etc.)
            DEPS="$DEPS build-essential pkg-config"
            # FFmpeg (required for av/PyAV)
            DEPS="$DEPS libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libavfilter-dev libswscale-dev libswresample-dev"
            # Audio
            DEPS="$DEPS portaudio19-dev libsndfile1"
            # GTK/Tray
            DEPS="$DEPS python3-gi gir1.2-ayatanaappindicator3-0.1 libgirepository1.0-dev"
            # Clipboard
            DEPS="$DEPS xclip xsel"
            # Typing tool based on session
            if [ "$SESSION_TYPE" = "wayland" ]; then
                DEPS="$DEPS wtype wl-clipboard ydotool"
            else
                DEPS="$DEPS xdotool"
            fi
            echo "   Installing via apt..."
            sudo apt update
            sudo apt install -y $DEPS
            ;;
        dnf)
            DEPS="python3 python3-pip python3-devel"
            # Python 3.13 for compatibility (3.14 not yet supported by faster-whisper)
            DEPS="$DEPS python3.13 python3.13-devel"
            # Compilation (required for numpy, av, etc.)
            DEPS="$DEPS gcc-c++ pkg-config"
            # FFmpeg (required for av/PyAV)
            # Use ffmpeg-devel (RPM Fusion) if installed, otherwise ffmpeg-free-devel
            if rpm -q ffmpeg-libs &>/dev/null; then
                DEPS="$DEPS ffmpeg-devel"
            else
                DEPS="$DEPS ffmpeg-free-devel"
            fi
            DEPS="$DEPS portaudio-devel libsndfile"
            # GTK/GObject (+ devel packages to compile PyGObject if needed)
            DEPS="$DEPS python3-gobject gtk3 libappindicator-gtk3"
            DEPS="$DEPS gobject-introspection-devel cairo-gobject-devel cairo-devel"
            DEPS="$DEPS xclip xsel"
            if [ "$SESSION_TYPE" = "wayland" ]; then
                DEPS="$DEPS wtype wl-clipboard ydotool"
            else
                DEPS="$DEPS xdotool"
            fi
            echo "   Installing via dnf..."
            sudo dnf install -y $DEPS
            ;;
        pacman)
            DEPS="python python-pip"
            # Compilation (required for numpy, etc.)
            DEPS="$DEPS base-devel pkgconf"
            # FFmpeg (required for av/PyAV)
            DEPS="$DEPS ffmpeg"
            DEPS="$DEPS portaudio libsndfile"
            DEPS="$DEPS python-gobject gtk3 libappindicator-gtk3"
            DEPS="$DEPS xclip xsel"
            if [ "$SESSION_TYPE" = "wayland" ]; then
                DEPS="$DEPS wtype wl-clipboard ydotool"
            else
                DEPS="$DEPS xdotool"
            fi
            echo "   Installing via pacman..."
            sudo pacman -S --needed --noconfirm $DEPS
            ;;
        zypper)
            DEPS="python3 python3-pip python3-devel"
            # Compilation (required for numpy, etc.)
            DEPS="$DEPS gcc-c++ pkg-config"
            # FFmpeg (required for av/PyAV)
            DEPS="$DEPS ffmpeg-devel"
            DEPS="$DEPS portaudio-devel libsndfile1"
            DEPS="$DEPS python3-gobject gtk3 typelib-1_0-AyatanaAppIndicator3-0_1"
            DEPS="$DEPS xclip xsel"
            if [ "$SESSION_TYPE" = "wayland" ]; then
                DEPS="$DEPS wtype wl-clipboard ydotool"
            else
                DEPS="$DEPS xdotool"
            fi
            echo "   Installing via zypper..."
            sudo zypper install -y $DEPS
            ;;
        *)
            echo -e "${YELLOW}   Unknown package manager.${NC}"
            echo "   Please install the following dependencies manually:"
            echo "   - Python 3, pip, venv, python-dev"
            echo "   - C++ compiler (g++ or clang++), pkg-config"
            echo "   - FFmpeg (dev) - libavformat, libavcodec, etc."
            echo "   - PortAudio (dev)"
            echo "   - GTK3, GObject Introspection, AppIndicator"
            echo "   - xclip or xsel"
            if [ "$SESSION_TYPE" = "wayland" ]; then
                echo "   - wtype (for Wayland)"
            else
                echo "   - xdotool (for X11)"
            fi
            read -p "   Press Enter to continue or Ctrl+C to abort..."
            ;;
    esac
}

install_system_deps

# Install patchelf if missing (for RPATH patch)
if ! command -v patchelf &>/dev/null; then
    echo -e "${GREEN}[3b/7]${NC} Installing patchelf (required for CUDA RPATH patch)..."
    case $PKG_MANAGER in
        apt)
            sudo apt install -y patchelf
            ;;
        dnf)
            sudo dnf install -y patchelf
            ;;
        pacman)
            sudo pacman -S --needed --noconfirm patchelf
            ;;
        zypper)
            sudo zypper install -y patchelf
            ;;
        *)
            echo -e "${YELLOW}   Please install patchelf manually for your distribution.${NC}"
            ;;
    esac
fi

# Enable ydotool service on Wayland (required for keyboard simulation)
if [ "$SESSION_TYPE" = "wayland" ] && command -v ydotool &>/dev/null; then
    echo "   Configuring ydotool for Wayland..."

    # Add user to input group
    if ! groups "$USER" | grep -q '\binput\b'; then
        sudo usermod -aG input "$USER"
        echo -e "${YELLOW}   Added $USER to 'input' group (re-login required)${NC}"
    fi

    # Configure socket permissions (fix for root-owned socket)
    YDOTOOL_OVERRIDE="/etc/systemd/system/ydotool.service.d/override.conf"
    if [ ! -f "$YDOTOOL_OVERRIDE" ]; then
        sudo mkdir -p /etc/systemd/system/ydotool.service.d
        echo '[Service]
ExecStartPost=/bin/sleep 0.5
ExecStartPost=/bin/chmod 666 /tmp/.ydotool_socket' | sudo tee "$YDOTOOL_OVERRIDE" > /dev/null
        sudo systemctl daemon-reload
        echo "   ydotool socket permissions configured."
    fi

    # Enable and restart service
    sudo systemctl enable --now ydotool 2>/dev/null || true
    sudo systemctl restart ydotool 2>/dev/null || true
    echo "   ydotool service enabled."
fi

# =============================================================================
# NVIDIA GPU detection and CUDA installation
# =============================================================================
echo ""
echo -e "${GREEN}[4/7]${NC} Checking for NVIDIA GPU..."

HAS_NVIDIA_GPU=false
CUDA_INSTALLED=false

# Detect NVIDIA GPU
if lspci 2>/dev/null | grep -qi nvidia; then
    HAS_NVIDIA_GPU=true
    echo "   NVIDIA GPU detected."

    # Check if CUDA is already working
    if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
        CUDA_INSTALLED=true
        echo "   CUDA drivers already installed."
        nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null | head -1 | sed 's/^/   /'
        # Install CUDA runtime libraries required by ctranslate2/faster-whisper
        echo "   Installing CUDA runtime libraries for faster-whisper..."
        case $PKG_MANAGER in
            apt)
                sudo apt install -y libcublas-12-0 libcublaslt-12-0 libcudnn9-cuda-12 2>/dev/null || true
                ;;
            dnf)
                # CUDA libs are not in Fedora repos, need NVIDIA CUDA repo
                if ! dnf repolist 2>/dev/null | grep -q cuda-fedora; then
                    echo "   Adding NVIDIA CUDA repository..."
                    # Find latest available Fedora CUDA repo (NVIDIA may not support newest Fedora)
                    for fver in $(rpm -E %fedora) 41 40 39; do
                        if curl -sI "https://developer.download.nvidia.com/compute/cuda/repos/fedora${fver}/x86_64/" 2>/dev/null | grep -q "200"; then
                            REPO_URL="https://developer.download.nvidia.com/compute/cuda/repos/fedora${fver}/x86_64/cuda-fedora${fver}.repo"
                            GPG_KEY="https://developer.download.nvidia.com/compute/cuda/repos/fedora${fver}/x86_64/D42D0685.pub"
                            sudo rpm --import "$GPG_KEY"
                            # dnf5 uses different syntax than dnf4
                            if dnf --version 2>/dev/null | grep -q "dnf5"; then
                                sudo dnf config-manager addrepo --from-repofile="$REPO_URL"
                            else
                                sudo dnf config-manager --add-repo "$REPO_URL"
                            fi
                            break
                        fi
                    done
                fi
                sudo dnf install -y libcublas-12-6 libcudnn9-cuda-12 2>/dev/null || \
                sudo dnf install -y libcublas-12 libcudnn9-cuda-12 2>/dev/null || true
                ;;
            pacman)
                sudo pacman -S --needed --noconfirm cudnn 2>/dev/null || true
                ;;
            zypper)
                sudo zypper install -y libcublas12 libcudnn8 2>/dev/null || true
                ;;
        esac
    else
        echo "   CUDA drivers not installed or not working."
        echo ""
        echo -e "${YELLOW}   GPU acceleration requires NVIDIA drivers and CUDA.${NC}"
        echo "   Without CUDA, the app will run on CPU (slower transcription)."
        echo ""
        read -p "   Install NVIDIA drivers and CUDA? [y/N] " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            case $PKG_MANAGER in
                dnf)
                    # Check if RPM Fusion is enabled
                    if ! rpm -q rpmfusion-free-release &>/dev/null; then
                        echo "   Enabling RPM Fusion repositories..."
                        sudo dnf install -y \
                            https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
                            https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
                    fi
                    # Add NVIDIA CUDA repo for runtime libs
                    if ! dnf repolist 2>/dev/null | grep -q cuda-fedora; then
                        echo "   Adding NVIDIA CUDA repository..."
                        for fver in $(rpm -E %fedora) 41 40 39; do
                            if curl -sI "https://developer.download.nvidia.com/compute/cuda/repos/fedora${fver}/x86_64/" 2>/dev/null | grep -q "200"; then
                                REPO_URL="https://developer.download.nvidia.com/compute/cuda/repos/fedora${fver}/x86_64/cuda-fedora${fver}.repo"
                                GPG_KEY="https://developer.download.nvidia.com/compute/cuda/repos/fedora${fver}/x86_64/D42D0685.pub"
                                sudo rpm --import "$GPG_KEY"
                                if dnf --version 2>/dev/null | grep -q "dnf5"; then
                                    sudo dnf config-manager addrepo --from-repofile="$REPO_URL"
                                else
                                    sudo dnf config-manager --add-repo "$REPO_URL"
                                fi
                                break
                            fi
                        done
                    fi
                    echo "   Installing NVIDIA drivers and CUDA..."
                    sudo dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda libcublas-12-6 libcudnn9-cuda-12 || \
                    sudo dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda libcublas-12 libcudnn9-cuda-12
                    CUDA_INSTALLED=true
                    echo -e "${YELLOW}   NOTE: A reboot may be required for NVIDIA drivers to work.${NC}"
                    ;;
                apt)
                    echo "   Installing NVIDIA drivers and CUDA..."
                    sudo apt update
                    sudo apt install -y nvidia-driver nvidia-cuda-toolkit libcublas-12-0 libcublaslt-12-0 libcudnn9-cuda-12
                    CUDA_INSTALLED=true
                    echo -e "${YELLOW}   NOTE: A reboot may be required for NVIDIA drivers to work.${NC}"
                    ;;
                pacman)
                    echo "   Installing NVIDIA drivers and CUDA..."
                    sudo pacman -S --needed --noconfirm nvidia nvidia-utils cuda cudnn
                    CUDA_INSTALLED=true
                    echo -e "${YELLOW}   NOTE: A reboot may be required for NVIDIA drivers to work.${NC}"
                    ;;
                zypper)
                    echo "   Installing NVIDIA drivers and CUDA..."
                    sudo zypper install -y nvidia-driver nvidia-cuda-toolkit libcublas12 libcudnn8
                    CUDA_INSTALLED=true
                    echo -e "${YELLOW}   NOTE: A reboot may be required for NVIDIA drivers to work.${NC}"
                    ;;
                *)
                    echo -e "${YELLOW}   Please install NVIDIA drivers manually for your distribution.${NC}"
                    ;;
            esac
        else
            echo "   Skipping CUDA installation. App will use CPU mode."
        fi
    fi
else
    echo "   No NVIDIA GPU detected. App will use CPU mode."
fi

# =============================================================================
# Python virtual environment creation
# =============================================================================
echo ""
echo -e "${GREEN}[5/7]${NC} Configuring Python environment..."

# Find a compatible Python version (3.10-3.13)
# Python 3.14+ is not yet supported by faster-whisper dependencies (onnxruntime, av)
find_compatible_python() {
    for py in python3.13 python3.12 python3.11 python3.10 python3; do
        if command -v "$py" &>/dev/null; then
            version=$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ] && [ "$minor" -le 13 ]; then
                echo "$py"
                return 0
            fi
        fi
    done
    echo ""
    return 1
}

PYTHON_CMD=$(find_compatible_python)
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}   Error: No compatible Python version found (3.10-3.13 required)${NC}"
    echo "   Python 3.14+ is not yet supported by faster-whisper dependencies."
    echo "   Please install Python 3.13:"
    case $PKG_MANAGER in
        dnf) echo "     sudo dnf install python3.13" ;;
        apt) echo "     sudo apt install python3.13" ;;
        pacman) echo "     sudo pacman -S python313" ;;
        *) echo "     Install Python 3.13 from your package manager" ;;
    esac
    exit 1
fi
echo "   Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

VENV_NEEDS_RECREATE=false

if [ -d "$VENV_DIR" ]; then
    # Check if venv was created with --system-site-packages
    if [ -f "$VENV_DIR/pyvenv.cfg" ]; then
        if ! grep -q "include-system-site-packages = true" "$VENV_DIR/pyvenv.cfg"; then
            echo -e "${YELLOW}   Existing venv without system access, recreation needed...${NC}"
            VENV_NEEDS_RECREATE=true
        fi
    else
        VENV_NEEDS_RECREATE=true
    fi
    # Check if venv uses the correct Python version
    VENV_PYTHON_VERSION=$("$VENV_DIR/bin/python" --version 2>/dev/null | cut -d' ' -f2 | cut -d'.' -f1,2)
    EXPECTED_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [ "$VENV_PYTHON_VERSION" != "$EXPECTED_VERSION" ]; then
        echo -e "${YELLOW}   Venv uses Python $VENV_PYTHON_VERSION, recreating for $EXPECTED_VERSION...${NC}"
        VENV_NEEDS_RECREATE=true
    fi
fi

if [ ! -d "$VENV_DIR" ] || [ "$VENV_NEEDS_RECREATE" = true ]; then
    if [ -d "$VENV_DIR" ]; then
        echo "   Removing old venv..."
        rm -rf "$VENV_DIR"
    fi
    echo "   Creating virtual environment..."
    # --system-site-packages allows access to system python3-gi
    # But only if using the system default Python version
    SYSTEM_PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    VENV_PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ "$SYSTEM_PYTHON_VERSION" = "$VENV_PYTHON_VERSION" ]; then
        $PYTHON_CMD -m venv --system-site-packages "$VENV_DIR"
    else
        echo "   (without system-site-packages - different Python version)"
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi
else
    echo "   Existing virtual environment OK."
fi

# Direct use of venv pip (no need to activate)
VENV_PIP="$VENV_DIR/bin/pip"

# Update pip
echo "   Updating pip..."
"$VENV_PIP" install --upgrade pip --quiet

# Install PyGObject if not using system-site-packages
if ! "$VENV_DIR/bin/python" -c "import gi" 2>/dev/null; then
    echo "   Installing PyGObject..."
    "$VENV_PIP" install PyGObject --quiet
fi

# =============================================================================
# Python dependencies installation
# =============================================================================
echo ""
echo -e "${GREEN}[6/7]${NC} Installing Python dependencies..."

REQUIREMENTS_HASH_FILE="$VENV_DIR/.requirements_hash"

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    CURRENT_HASH=$(sha256sum "$PROJECT_DIR/requirements.txt" | cut -d' ' -f1)
    STORED_HASH=""
    if [ -f "$REQUIREMENTS_HASH_FILE" ]; then
        STORED_HASH=$(cat "$REQUIREMENTS_HASH_FILE")
    fi

    if [ "$CURRENT_HASH" != "$STORED_HASH" ] || [ "$VENV_NEEDS_RECREATE" = true ]; then
        echo "   Installing from requirements.txt..."
        "$VENV_PIP" install --upgrade -r "$PROJECT_DIR/requirements.txt"
        echo "$CURRENT_HASH" > "$REQUIREMENTS_HASH_FILE"
    else
        echo "   Python dependencies already up to date."
    fi
else
    echo -e "${YELLOW}   requirements.txt not found, manual installation...${NC}"
    "$VENV_PIP" install --upgrade faster-whisper sounddevice numpy pynput pystray Pillow pyperclip
fi

# =============================================================================
# Desktop files configuration
# =============================================================================
echo ""
echo -e "${GREEN}[7/7]${NC} Configuring autostart..."

PYTHON_EXEC="$VENV_DIR/bin/python"

# Create launcher script (no LD_LIBRARY_PATH logic)
LAUNCHER_SCRIPT="$PROJECT_DIR/run.sh"
cat > "$LAUNCHER_SCRIPT" << 'LAUNCHER_EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"
exec "$VENV_DIR/bin/python" -m mysuperwhisper "$@"
LAUNCHER_EOF
chmod +x "$LAUNCHER_SCRIPT"

# Patch all CUDA .so files in venv to add RPATH $ORIGIN
SITE_PACKAGES=$(find "$VENV_DIR/lib" -maxdepth 1 -name "python*" -type d | head -1)/site-packages
if command -v patchelf &>/dev/null; then
    echo "   Patching CUDA .so files with RPATH..."
    for lib in "$SITE_PACKAGES"/nvidia/*/lib/*.so*; do
        if [ -f "$lib" ]; then
            patchelf --set-rpath "\$ORIGIN" "$lib" 2>/dev/null || true
        fi
    done
else
    echo -e "${YELLOW}   patchelf not found, skipping RPATH patch. CUDA may not work via menu/Wayland.${NC}"
fi

# Create Autostart directory if it doesn't exist
if [ ! -d "$AUTOSTART_DIR" ]; then
    mkdir -p "$AUTOSTART_DIR"
fi

# Create Applications directory if it doesn't exist
if [ ! -d "$APPLICATIONS_DIR" ]; then
    mkdir -p "$APPLICATIONS_DIR"
fi

# Generate .desktop files
if [ -f "$DESKTOP_TEMPLATE" ]; then
    sed -e "s|__PYTHON_EXEC__|$PYTHON_EXEC|g" \
        -e "s|__SCRIPT_PATH__|-m mysuperwhisper|g" \
        -e "s|__WORK_DIR__|$PROJECT_DIR/|g" \
        -e "s|__ICON_PATH__|$PROJECT_DIR/mysuperwhisper.svg|g" \
        "$DESKTOP_TEMPLATE" > "$DEST_FILE_AUTOSTART"

    cp "$DEST_FILE_AUTOSTART" "$DEST_FILE_APP"
    chmod +x "$DEST_FILE_AUTOSTART"
    chmod +x "$DEST_FILE_APP"

    echo "   Desktop files created:"
    echo "   - $DEST_FILE_AUTOSTART"
    echo "   - $DEST_FILE_APP"
else
    echo -e "${YELLOW}   Desktop template not found, skipping...${NC}"
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
if [ "$SESSION_TYPE" = "wayland" ]; then
    echo "  - Typing tool : wtype"
else
    echo "  - Typing tool : xdotool"
fi
echo "  - Python      : $PYTHON_EXEC"
if [ "$HAS_NVIDIA_GPU" = true ]; then
    if [ "$CUDA_INSTALLED" = true ]; then
        echo "  - GPU         : NVIDIA (CUDA enabled)"
    else
        echo "  - GPU         : NVIDIA (CUDA not installed - CPU mode)"
    fi
else
    echo "  - GPU         : None detected (CPU mode)"
fi
echo ""
echo "To run manually:"
echo "  cd $PROJECT_DIR && $PYTHON_EXEC -m mysuperwhisper"
echo ""
echo "The program will start automatically at next session."
echo "It is also available in the applications menu."
echo ""
