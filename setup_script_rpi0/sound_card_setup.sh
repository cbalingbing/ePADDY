#!/bin/bash

set -e

# --- Configure ALSA sound ---
echo "Writing /etc/asound.conf..."

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

echo "Sound config written successfully."

# --- Reboot ---
arecord -l
echo "See the list of soundcards available below"

echo "Reboot is needed for changes to take effect..."
echo "Rebooting in 10 seconds... Press CTRL+C to cancel."
arecord -l
sleep 10
sudo reboot