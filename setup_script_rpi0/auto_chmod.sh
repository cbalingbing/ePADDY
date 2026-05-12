# --- Create scripts folder and make all scripts executable ---
SCRIPTS_DIR="/home/$(whoami)/Desktop/Epaddy/scripts"

mkdir -p "$SCRIPTS_DIR"

# chmod only if .sh files exist
if ls "$SCRIPTS_DIR"/*.sh &>/dev/null; then
    chmod +x "$SCRIPTS_DIR"/*.sh
    echo "Made $(ls "$SCRIPTS_DIR"/*.sh | wc -l) script(s) executable."
else
    echo "No .sh files found in $SCRIPTS_DIR yet."
fi