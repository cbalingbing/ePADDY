#!/bin/bash

set -e

# --- Edit boot config ---
echo "Configuring boot config..."
BOOT_CONFIG="/boot/firmware/config.txt"

if [ ! -f "$BOOT_CONFIG" ]; then
    echo "ERROR: Boot config not found at $BOOT_CONFIG"
    echo "Fix: If you are on older Pi OS, try /boot/config.txt instead."
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

echo "Boot config updated successfully."
