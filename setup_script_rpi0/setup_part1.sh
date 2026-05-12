#!/bin/bash

set -e

# =============================================================
# ePaddy Setup Script — PART 1 of 2
# Raspberry Pi Zero / Raspberry Pi OS (Debian)
# =============================================================
# Covers:
#   [1/6] Auto-Chmod Scripts Folder
#   [2/6] System Update
#   [3/6] Create Project Directory
#   [4/6] Virtual Environment
#   [5/6] Install Python Packages
#   [6/6] Adafruit Blinka
#   → Reboots. Part 2 auto-resumes via systemd OR run manually.
# =============================================================

# --- Configuration ---
TARGET_DIR="/home/$(whoami)/Desktop/Epaddy"
OWNER_USER="$(whoami)"
VENV_PATH="$TARGET_DIR/.venv"
SCRIPTS_DIR="$TARGET_DIR/scripts"
PART2_SCRIPT="$TARGET_DIR/scripts/setup_part2.sh"
FLAG_FILE="/var/tmp/epaddy_resume_part2"
SERVICE_NAME="epaddy-resume"

# =============================================================
# ERROR HANDLER
# TODO: Edit suggestions to match your environment
# =============================================================
handle_error() {
    local EXIT_CODE=$?
    local LINE=$1
    echo ""
    echo "============================================="
    echo " PART 1 FAILED at line $LINE (exit code: $EXIT_CODE)"
    echo "============================================="
    case $LINE in
        # TODO: Add line-specific suggestions here
        # Format: line_number) echo "Suggestion" ;;
        *)
            echo " Suggested fix: Check the error message above."
            echo " - Make sure you are connected to the internet"
            echo " - Make sure you are on Raspberry Pi OS (Debian)"
            echo " - Try: sudo apt update && sudo apt upgrade -y"
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
echo "[1/6] Setting up scripts folder and auto-chmod..."

# Run apt update first so package installs don't fail on fresh Pi
sudo apt update || { echo "ERROR: apt update failed. Check your internet connection."; exit 1; }
sudo apt install -y inotify-tools || { echo "ERROR: Failed to install inotify-tools."; echo "Fix: Check your internet connection."; exit 1; }

mkdir -p "$SCRIPTS_DIR"

if ls "$SCRIPTS_DIR"/*.sh &>/dev/null; then
    chmod +x "$SCRIPTS_DIR"/*.sh
    echo "Made $(ls "$SCRIPTS_DIR"/*.sh | wc -l) script(s) executable."
else
    echo "No .sh files found in $SCRIPTS_DIR yet."
fi

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
echo "[2/6] Updating system packages..."
sudo apt upgrade -y || { echo "ERROR: apt upgrade failed."; exit 1; }
sudo apt install -y python3-venv python3-pip || { echo "ERROR: Failed to install python3-venv or python3-pip."; exit 1; }

# Install network and file sharing tools
sudo apt install -y cifs-utils samba smbclient || { echo "ERROR: Failed to install cifs-utils, samba, or smbclient."; echo "Fix: Check your internet connection and try: sudo apt install -y cifs-utils samba smbclient"; exit 1; }

# Install Tailscale
echo "Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh || { echo "ERROR: Tailscale install failed."; echo "Fix: Check your internet connection or install manually from https://tailscale.com/download/linux"; exit 1; }
echo "Tailscale installed. Run 'sudo tailscale up' manually after setup to connect."

echo "System update complete."

# =============================================================
# STEP 3 — Verify Project Directory
# =============================================================
echo ""
echo "[3/6] Checking project directory: $TARGET_DIR"

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

cd "$SCRIPTS_DIR"
echo "Working in: $(pwd)"

# =============================================================
# STEP 4 — Virtual Environment
# =============================================================
echo ""
echo "[4/6] Setting up virtual environment..."
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH" --system-site-packages || { echo "ERROR: Failed to create venv."; echo "Fix: sudo apt install -y python3-venv"; exit 1; }
    echo "Virtual environment created."
else
    echo "Virtual environment already exists, skipping."
fi

# Check and fix venv ownership
VENV_OWNER=$(stat -c '%U' "$VENV_PATH")
if [ "$VENV_OWNER" != "$OWNER_USER" ]; then
    echo "Venv ownership mismatch (current: $VENV_OWNER, expected: $OWNER_USER). Fixing..."
    sudo chown -R "$OWNER_USER":"$OWNER_USER" "$VENV_PATH" || { echo "ERROR: chown failed on $VENV_PATH."; echo "Fix: Run manually: sudo chown -R $OWNER_USER:$OWNER_USER $VENV_PATH"; exit 1; }
    echo "Venv ownership corrected."
else
    echo "Venv ownership is correct ($VENV_OWNER). Continuing..."
fi

source "$VENV_PATH/bin/activate" || { echo "ERROR: Failed to activate venv at $VENV_PATH."; exit 1; }
echo "Active venv: $VIRTUAL_ENV"

# =============================================================
# STEP 5 — Install Python Packages
# =============================================================
echo ""
echo "[5/6] Installing Python packages..."

# TODO: Add or remove pip install lines as needed
pip install -r "$SCRIPTS_DIR/requirements.txt" || { echo "ERROR: pip install failed."; echo "Fix: Check requirements.txt exists in $SCRIPTS_DIR."; exit 1; }
pip3 install --upgrade adafruit-python-shell || { echo "ERROR: Failed to upgrade adafruit-python-shell."; exit 1; }
echo "Python packages installed."

# =============================================================
# STEP 6 — Download and Run Adafruit Blinka
# =============================================================
echo ""
echo "[6/6] Downloading Adafruit Blinka installer..."
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py \
    -O "$SCRIPTS_DIR/raspi-blinka.py" \
    || { echo "ERROR: wget failed. Check your internet connection."; exit 1; }

echo "Running Blinka installer..."
echo "NOTE: Blinka will request a reboot. Part 2 will auto-resume after reboot."
sudo "$VENV_PATH/bin/python3" "$SCRIPTS_DIR/raspi-blinka.py" || { echo "ERROR: raspi-blinka.py failed."; echo "Fix: Check I2C and SPI are enabled and your Pi is supported."; exit 1; }

# =============================================================
# SET UP AUTO-RESUME FOR PART 2
# =============================================================
echo ""
echo "Setting up auto-resume for Part 2 after reboot..."

# Create flag file so Part 2 knows to run
touch "$FLAG_FILE"

# Copy Part 2 to TARGET_DIR if not already there
if [ ! -f "$PART2_SCRIPT" ]; then
    cp "$(dirname "$0")/setup_part2.sh" "$PART2_SCRIPT" 2>/dev/null || echo "Note: Could not copy setup_part2.sh — make sure it is in $TARGET_DIR before reboot."
fi
chmod +x "$PART2_SCRIPT"

# Create systemd service to auto-run Part 2 on next boot
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null << EOF
[Unit]
Description=ePaddy Setup Resume - Part 2
After=network.target
ConditionPathExists=$FLAG_FILE

[Service]
Type=oneshot
ExecStart=/bin/bash $PART2_SCRIPT
User=root
StandardOutput=journal
StandardError=journal
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
echo "Auto-resume service registered."

# =============================================================
# DONE PART 1 — Reboot
# =============================================================
echo ""
echo "============================================="
echo " Part 1 complete!"
echo " After reboot, Part 2 will run automatically."
echo " Or run manually: source $PART2_SCRIPT"
echo " Rebooting in 10 seconds... CTRL+C to cancel."
echo "============================================="
sleep 10
sudo reboot
