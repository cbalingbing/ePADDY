#!/bin/bash

set -e

# =============================================================
# ePaddy Bootstrap
# Run this FIRST before anything else.
# Creates the project directory and downloads all setup scripts.
# =============================================================

TARGET_DIR="/home/$(whoami)/Desktop/Epaddy"
SCRIPTS_DIR="$TARGET_DIR/scripts"

REPO_RAW_URL="https://raw.githubusercontent.com/cbalingbing/ePADDY/main/setup_script_rpi0"

echo "Creating project directories..."
sudo mkdir -p "$SCRIPTS_DIR"
cd "$SCRIPTS_DIR"

echo "Downloading setup scripts into $SCRIPTS_DIR ..."

wget -q "$REPO_RAW_URL/bootstrap.sh"        -O bootstrap.sh
wget -q "$REPO_RAW_URL/setup.sh"              -O setup.sh
wget -q "$REPO_RAW_URL/setup_part1.sh"        -O setup_part1.sh
wget -q "$REPO_RAW_URL/setup_part2.sh"        -O setup_part2.sh
wget -q "$REPO_RAW_URL/requirements.txt"      -O requirements.txt
wget -q "$REPO_RAW_URL/edit_boot_config.sh"   -O edit_boot_config.sh
wget -q "$REPO_RAW_URL/sound_card_setup.sh"   -O sound_card_setup.sh
wget -q "$REPO_RAW_URL/auto_chmod.sh"         -O auto_chmod.sh
wget -q "$REPO_RAW_URL/setup_venv.sh"         -O setup_venv.sh
wget -q "$REPO_RAW_URL/blinka_test.py"        -O blinka_test.py
wget -q "$REPO_RAW_URL/new_recording_script.sh"        -O new_recording_script.sh
wget -q "$REPO_RAW_URL/recordv2.py"        -O recordv2.py
wget -q "$REPO_RAW_URL/config.txt"        -O config.txt
wget -q "$REPO_RAW_URL/README.md"             -O README.md

echo "Making scripts executable..."
chmod +x setup.sh setup_part1.sh setup_part2.sh auto_chmod.sh setup_venv.sh edit_boot_config.sh sound_card_setup.sh

echo ""
echo "============================================="
echo " Bootstrap complete!"
echo " Files downloaded to: $SCRIPTS_DIR"
echo ""
echo " To run setup, choose one:"
echo ""
echo "   Option A (single script):"
echo "   source $SCRIPTS_DIR/setup.sh"
echo ""
echo "   Option B (recommended, auto-resume):"
echo "   source $SCRIPTS_DIR/setup_part1.sh"
echo "============================================="
