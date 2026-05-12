#!/bin/bash

set -e

# --- Configuration ---
TARGET_DIR="/home/$(whoami)/Desktop/Epaddy"
OWNER_USER="$(whoami)"
VENV_PATH="$TARGET_DIR/.venv"
SCRIPTS_DIR="$TARGET_DIR/scripts"

# --- Install python3-venv if not present ---
echo "Installing python3-venv and python3-pip..."
sudo apt install -y python3-venv python3-pip || { echo "ERROR: Failed to install python3-venv."; exit 1; }

# --- Create venv if it doesn't exist ---
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH" --system-site-packages || { echo "ERROR: Failed to create venv."; exit 1; }
    echo "Virtual environment created at $VENV_PATH"
else
    echo "Virtual environment already exists, skipping."
fi

# --- Check and fix venv ownership ---
VENV_OWNER=$(stat -c '%U' "$VENV_PATH")
if [ "$VENV_OWNER" != "$OWNER_USER" ]; then
    echo "Ownership mismatch ($VENV_OWNER). Fixing..."
    sudo chown -R "$OWNER_USER":"$OWNER_USER" "$VENV_PATH" || { echo "ERROR: chown failed."; exit 1; }
    echo "Ownership corrected."
else
    echo "Ownership is correct ($VENV_OWNER). Continuing..."
fi

# --- Activate venv ---
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate" || { echo "ERROR: Failed to activate venv."; exit 1; }
echo "Done. Active venv: $VIRTUAL_ENV"

# --- Install packages ---
echo "Installing packages from requirements.txt..."
pip install -r "$SCRIPTS_DIR/requirements.txt" || { echo "ERROR: pip install failed. Check requirements.txt in $SCRIPTS_DIR."; exit 1; }
pip3 install --upgrade adafruit-python-shell || { echo "ERROR: Failed to upgrade adafruit-python-shell."; exit 1; }
echo "Packages installed."
