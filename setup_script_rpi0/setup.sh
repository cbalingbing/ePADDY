#!/bin/bash

set -e

# =============================================================
# ePaddy Setup Script - Raspberry Pi OS (Debian)
# =============================================================

# --- Configuration ---
TARGET_DIR="/home/$(whoami)/Desktop/Epaddy"
OWNER_USER="$(whoami)"
VENV_PATH="$TARGET_DIR/.venv"
SCRIPTS_DIR="/home/$(whoami)/Desktop/Epaddy/scripts"
BOOT_CONFIG="/boot/firmware/config.txt"

# =============================================================
# ERROR HANDLER
# TODO: Edit the suggestions below to match your environment
# =============================================================
handle_error() {
    local EXIT_CODE=$?
    local LINE=$1
    echo ""
    echo "============================================="
    echo " SETUP FAILED at line $LINE (exit code: $EXIT_CODE)"
    echo "============================================="
    case $LINE in
        # TODO: Add or edit line-specific suggestions below
        # Format: line_number) echo "Suggestion message" ;;
        *)
            echo " Suggested fix: Check the error message above."
            echo " - Make sure you are connected to the internet"
            echo " - Make sure you are running this on Raspberry Pi OS (Debian)"
            echo " - Try running: sudo apt update && sudo apt upgrade -y"
            echo " - Check that /boot/firmware/config.txt exists"
            echo "   (older Pi OS may use /boot/config.txt instead)"
            ;;
    esac
    echo "============================================="
    echo " Setup stopped. Fix the issue and re-run."
    echo "============================================="
    exit $EXIT_CODE
}

trap 'handle_error $LINENO' ERR

# =============================================================
# STEP 1 — Auto-Chmod Scripts Folder
# =============================================================
echo ""
echo "[1/8] Setting up scripts folder and auto-chmod..."
sudo apt install -y inotify-tools || { echo "ERROR: Failed to install inotify-tools."; echo "Fix: Check your internet connection and try: sudo apt install -y inotify-tools"; exit 1; }

mkdir -p "$SCRIPTS_DIR"

if ls "$SCRIPTS_DIR"/*.sh &>/dev/null; then
    chmod +x "$SCRIPTS_DIR"/*.sh
    echo "Made $(ls "$SCRIPTS_DIR"/*.sh | wc -l) script(s) executable."
else
    echo "No .sh files found in $SCRIPTS_DIR yet."
fi

# Auto-chmod systemd service
sudo tee /etc/systemd/system/auto-chmod.service > /dev/null << EOF
[Unit]
Description=Auto chmod scripts dropped into $SCRIPTS_DIR
After=network.target

[Service]
ExecStart=/bin/bash -c 'inotifywait -m $SCRIPTS_DIR -e create -e moved_to | while read dir action file; do if [[ "\$file" == *.sh ]]; then chmod +x $SCRIPTS_DIR/\$file; fi; done'
Restart=always
User=$(whoami)

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable auto-chmod
sudo systemctl start auto-chmod
echo "Auto-chmod service running."

# =============================================================
# STEP 2 — System Update
# =============================================================
echo ""
echo "[2/8] Updating system packages..."
sudo apt update || { echo "ERROR: apt update failed. Check your internet connection."; exit 1; }
sudo apt upgrade -y || { echo "ERROR: apt upgrade failed."; exit 1; }
sudo apt install -y python3-venv python3-pip || { echo "ERROR: Failed to install python3-venv or python3-pip."; exit 1; }
echo "System update complete."

# =============================================================
# STEP 3 — Verify Project Directory
# =============================================================
echo ""
echo "[3/8] Checking project directory: $TARGET_DIR"

if [ ! -d "$TARGET_DIR" ]; then
    echo "Directory not found. Creating $TARGET_DIR..."
    mkdir -p "$TARGET_DIR" || { echo "ERROR: Could not create $TARGET_DIR."; echo "Fix: Check that ~/Desktop exists and you have write permission."; exit 1; }
    echo "Directory created."
else
    echo "Directory already exists, skipping creation."
fi

# Check and fix ownership
CURRENT_OWNER=$(stat -c '%U' "$TARGET_DIR")
if [ "$CURRENT_OWNER" != "$OWNER_USER" ]; then
    echo "Ownership mismatch (current: $CURRENT_OWNER, expected: $OWNER_USER). Fixing..."
    sudo chown "$OWNER_USER":"$OWNER_USER" "$TARGET_DIR" || { echo "ERROR: chown failed on $TARGET_DIR."; echo "Fix: Run manually: sudo chown $OWNER_USER:$OWNER_USER $TARGET_DIR"; exit 1; }
    echo "Ownership corrected."
else
    echo "Ownership is correct ($CURRENT_OWNER). Continuing..."
fi

cd "$TARGET_DIR"
echo "Working in: $(pwd)"

# =============================================================
# STEP 4 — Virtual Environment
# =============================================================
echo ""
echo "[4/8] Setting up virtual environment..."
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH" || { echo "ERROR: Failed to create virtual environment."; echo "Fix: Try running: sudo apt install -y python3-venv"; exit 1; }
    echo "Virtual environment created."
else
    echo "Virtual environment already exists, skipping."
fi

source "$VENV_PATH/bin/activate" || { echo "ERROR: Failed to activate virtual environment at $VENV_PATH."; exit 1; }
echo "Active venv: $VIRTUAL_ENV"

# =============================================================
# STEP 5 — Install Python Packages
# =============================================================
echo ""
echo "[5/8] Installing Python packages..."

# TODO: Add or remove pip install lines as needed
pip install -r "$TARGET_DIR/requirements.txt" || { echo "ERROR: pip install from requirements.txt failed."; echo "Fix: Check that requirements.txt exists in $TARGET_DIR and packages are spelled correctly."; exit 1; }
pip3 install --upgrade adafruit-python-shell || { echo "ERROR: Failed to upgrade adafruit-python-shell."; exit 1; }
echo "Python packages installed."

# =============================================================
# STEP 6 — Download and Run Adafruit Blinka
# =============================================================
echo ""
echo "[6/8] Downloading Adafruit Blinka installer..."
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py \
    || { echo "ERROR: wget failed. Check your internet connection."; echo "Fix: Try manually downloading raspi-blinka.py from Adafruit's GitHub."; exit 1; }

echo "Running Blinka installer..."
sudo "$VENV_PATH/bin/python3" raspi-blinka.py || { echo "ERROR: raspi-blinka.py failed."; echo "Fix: Check that I2C and SPI are enabled, and that your Pi is supported."; exit 1; }

# =============================================================
# STEP 7 — Edit Boot Config
# =============================================================
echo ""
echo "[7/8] Configuring boot config..."

if [ ! -f "$BOOT_CONFIG" ]; then
    # TODO: Change path below if you are on older Raspberry Pi OS
    echo "ERROR: Boot config not found at $BOOT_CONFIG"
    echo "Fix: If you are on older Pi OS, change BOOT_CONFIG to /boot/config.txt"
    exit 1
fi

# Enable I2C
sudo sed -i 's/#dtparam=i2c_arm=on/dtparam=i2c_arm=on/' "$BOOT_CONFIG"
grep -qxF 'dtparam=i2c_arm=on' "$BOOT_CONFIG" || echo 'dtparam=i2c_arm=on' | sudo tee -a "$BOOT_CONFIG"

# Enable SPI
sudo sed -i 's/#dtparam=spi=on/dtparam=spi=on/' "$BOOT_CONFIG"
grep -qxF 'dtparam=spi=on' "$BOOT_CONFIG" || echo 'dtparam=spi=on' | sudo tee -a "$BOOT_CONFIG"

# Enable Google Voice HAT overlay
sudo sed -i 's/#dtoverlay=googlevoicehat-soundcard/dtoverlay=googlevoicehat-soundcard/' "$BOOT_CONFIG"
grep -qxF 'dtoverlay=googlevoicehat-soundcard' "$BOOT_CONFIG" || echo 'dtoverlay=googlevoicehat-soundcard' | sudo tee -a "$BOOT_CONFIG"

echo "Boot config updated."

# =============================================================
# STEP 8 — Configure ALSA Sound
# =============================================================
echo ""
echo "[8/8] Writing ALSA sound config..."

sudo tee /etc/asound.conf > /dev/null << 'EOF'
pcm.dmic_hw {
    type hw
    card sndrpii2scard
    channels 2
    format S32_LE
}

pcm.dmic_sv {
    type softvol
    slave.pcm dmic_hw
    control {
        name "Mic Capture Volume"
        card sndrpii2scard
    }
}

pcm.!default {
    type asym
    playback.pcm "plughw:0"
    capture.pcm "dmic_sv"
}

ctl.!default {
    type hw
    card 0
}
EOF

echo "ALSA config written."
echo "Available sound cards:"
arecord -l

# =============================================================
# DONE — Reboot
# =============================================================
echo ""
echo "============================================="
echo " Setup complete! Rebooting in 10 seconds..."
echo " Press CTRL+C to cancel reboot."
echo "============================================="
sleep 10
sudo reboot
