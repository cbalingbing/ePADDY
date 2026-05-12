#!/bin/bash

set -e

# --- Configuration ---
TARGET_DIR="/home/$(whoami)/Desktop/Epaddy"
OWNER_USER="$(whoami)"
VENV_PATH="$TARGET_DIR/.venv"

# --- Update system ---
echo "Updating package lists..."
sudo apt update

echo "Upgrading packages..."
sudo apt upgrade -y

# Install python3-venv if not already present
sudo apt install -y python3-venv python3-pip

# --- Create directory and set ownership ---
echo "Creating directory: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
sudo chown "$OWNER_USER":"$OWNER_USER" "$TARGET_DIR"

# --- Change into it ---
cd "$TARGET_DIR"
echo "Working in: $(pwd)"

# --- Create venv if it doesn't exist ---
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# --- Activate venv ---
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

echo "Done. Active venv: $VIRTUAL_ENV"

# --- Install packages ---
echo "Installing packages..."
pip install -r requirements.txt
pip3 install --upgrade adafruit-python-shell


# --- Download Adafruit Blinka installer ---
echo "Downloading raspi-blinka.py..."
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
sudo -E venv PATH=$VENV_PATH python3 raspi-blinka.py
