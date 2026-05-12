#!/bin/bash

set -e

# =============================================================
# ePaddy Bootstrap
# Run this FIRST before anything else.
# Creates the project directory and downloads all setup scripts.
# =============================================================

TARGET_DIR="/home/$(whoami)/Desktop/Epaddy"

#Base Path of script
REPO_RAW_URL="https://raw.githubusercontent.com/cbalingbing/ePADDY/main/setup_script_rpi0"

echo "Creating project directory: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

echo "Downloading setup scripts..."


wget -q "$REPO_RAW_URL/setup.sh"          -O setup.sh
wget -q "$REPO_RAW_URL/setup_part1.sh"    -O setup_part1.sh
wget -q "$REPO_RAW_URL/setup_part2.sh"    -O setup_part2.sh
wget -q "$REPO_RAW_URL/requirements.txt"  -O requirements.txt

echo "Making scripts executable..."
chmod +x setup.sh setup_part1.sh setup_part2.sh

echo ""
echo "============================================="
echo " Bootstrap complete!"
echo " Files downloaded to: $TARGET_DIR"
echo ""
echo " To run setup, choose one:"
echo ""
echo "   Option A (single script):"
echo "   source $TARGET_DIR/setup.sh"
echo ""
echo "   Option B (recommended, auto-resume):"
echo "   source $TARGET_DIR/setup_part1.sh"
echo "============================================="
