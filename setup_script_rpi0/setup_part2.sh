#!/bin/bash

set -e

# =============================================================
# ePaddy Setup Script — PART 2 of 2
# Raspberry Pi Zero / Raspberry Pi OS (Debian)
# =============================================================
# Covers:
#   [1/2] Edit Boot Config (I2C, SPI, Google Voice HAT)
#   [2/2] Configure ALSA Sound
#   → Cleans up auto-resume service then reboots.
# =============================================================
# Can be run:
#   A) Automatically — triggered by epaddy-resume.service after reboot
#   B) Manually      — source ./setup_part2.sh
# =============================================================

# --- Configuration ---
TARGET_DIR="/home/$(whoami)/Desktop/Epaddy"
BOOT_CONFIG="/boot/firmware/config.txt"
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
    echo " PART 2 FAILED at line $LINE (exit code: $EXIT_CODE)"
    echo "============================================="
    case $LINE in
        # TODO: Add line-specific suggestions here
        # Format: line_number) echo "Suggestion" ;;
        *)
            echo " Suggested fix: Check the error message above."
            echo " - Check that /boot/firmware/config.txt exists"
            echo "   (older Pi OS may use /boot/config.txt instead)"
            echo " - Make sure you are running on Raspberry Pi OS (Debian)"
            echo " - Re-run manually: source $TARGET_DIR/setup_part2.sh"
            ;;
    esac
    echo "============================================="
    echo " Setup stopped. Fix the issue and re-run Part 2."
    echo "============================================="
    exit $EXIT_CODE
}

trap 'handle_error $LINENO' ERR

echo ""
echo "============================================="
echo " ePaddy Setup — Part 2 of 2"
echo "============================================="

# =============================================================
# STEP 1 — Edit Boot Config
# =============================================================
echo ""
echo "[1/2] Configuring boot config..."

if [ ! -f "$BOOT_CONFIG" ]; then
    # TODO: Change path if you are on older Raspberry Pi OS
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
# STEP 2 — Configure ALSA Sound
# =============================================================
echo ""
echo "[2/2] Writing ALSA sound config..."

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
# CLEANUP — Remove flag file and disable auto-resume service
# =============================================================
echo ""
echo "Cleaning up auto-resume service..."

if [ -f "$FLAG_FILE" ]; then
    sudo rm -f "$FLAG_FILE"
    echo "Flag file removed."
fi

if systemctl is-enabled "$SERVICE_NAME" &>/dev/null; then
    sudo systemctl disable "$SERVICE_NAME"
    sudo rm -f /etc/systemd/system/$SERVICE_NAME.service
    sudo systemctl daemon-reload
    echo "Auto-resume service removed."
fi

# =============================================================
# DONE — Reboot
# =============================================================
echo ""
echo "============================================="
echo " Setup complete! Full setup finished."
echo " Rebooting in 10 seconds... CTRL+C to cancel."
echo "============================================="
sleep 10
sudo reboot
