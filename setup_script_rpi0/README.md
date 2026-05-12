# ePaddy — Raspberry Pi Zero Setup Guide


A step-by-step manual and automated setup script for configuring a Raspberry Pi Zero with Raspberry Pi OS (Debian), Google Voice HAT, Adafruit Blinka, and a Python virtual environment.

---

## Hardware Required

This is the hardware components required for the RPI Zero for capturing insect sounds

| Component | Details |
|-----------|---------|
| Board | Raspberry Pi Zero / Zero W / Zero 2 W |
| OS | Raspberry Pi OS Lite (Debian Bookworm or later) |
| Audio HAT | Google Voice HAT |
| Storage | MicroSD card (16GB minimum, 32GB recommended) with rw 100mb/s |
| Power | 5V micro USB power supply |
| Internet | WiFi (Zero W / Zero 2 W) or USB OTG adapter |
| Microphone | Adafruit Mems Microphone|
| Temperature Sensor | Adafruit AHT20 Temp & Humidity Sensor| 

---

## File Structure

```
~/Desktop/Epaddy/setup_script_rpi0
├── bootstrap.sh              # Run this FIRST — creates directory and downloads scripts
├── setup.sh                  # Option A — Single script (manual reboot between Blinka and config)
├── setup_part1.sh            # Option B — Part 1: Blinka setup + registers auto-resume
├── setup_part2.sh            # Option B — Part 2: Boot config + ALSA (auto or manual)
├── requirements.txt          # Python dependencies
├── raspi-blinka.py           # Downloaded automatically during setup
├── .venv/                    # Python virtual environment (created during setup)
└── scripts/                  # Your compiled .sh scripts (auto-chmod enabled)
    ├── auto_chmod.sh
    ├── edit_boot_config.sh
    ├── setup_venv.sh
    └── sound_card_setup.sh
```

---

## Before You Start

### 1. Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Select **Raspberry Pi Zero** as the device
3. Select **Raspberry Pi OS Lite (32-bit)** as the OS
   > **Note:** Use Lite if you don't need a desktop. Use the full version if you want a GUI.
4. Click the **gear icon** to pre-configure:
   - Hostname
   - Username and password
   - WiFi credentials
   - Enable SSH
5. Flash to your MicroSD card

### 2. First Boot

1. Insert MicroSD into the Pi Zero
2. Power on and wait for it to boot (first boot takes ~2 minutes)
3. SSH into the Pi or connect a keyboard and monitor

```bash
ssh pi@raspberrypi.local
# or use the hostname you set in Imager
```

### 3. Bootstrap — Create Directory and Download Scripts

Run this single command on the Pi to create the project folder and pull all setup scripts down automatically:

<!-- TODO: Replace with your actual GitHub raw URL once repo is set up -->
```bash
wget -qO- https://raw.githubusercontent.com/yourusername/epaddy/main/setup_script/bootstrap.sh | bash
```

Or if you already have `bootstrap.sh` copied to the Pi:
```bash
bash ~/bootstrap.sh
```

> **What it does:** Creates `~/Desktop/Epaddy/`, downloads `setup.sh`, `setup_part1.sh`, `setup_part2.sh`, and `requirements.txt`, then makes them all executable.

**Alternative — Git clone:**
```bash
git clone https://github.com/yourusername/epaddy.git ~/Desktop/Epaddy
```

**Alternative — SCP from your PC:**
```bash
scp -r ./setup_script pi@raspberrypi.local:~/Desktop/Epaddy
```

---

## Setup Options

There are two ways to run the setup. Choose whichever fits your preference.

---

### Option A — Single Script

Runs everything in one go. Because Adafruit Blinka requests a reboot mid-setup, **you will need to manually run Part 2 after the reboot**.

```bash
cd ~/Desktop/Epaddy
source ./setup.sh
```

After the reboot, run:

```bash
source ~/Desktop/Epaddy/setup_part2.sh
```

> **Important:** Use `source` so the virtual environment stays active in your shell.

---

### Option B — Two-Part Script (Recommended)

Run Part 1 and walk away. After the reboot, **Part 2 runs automatically** via a systemd service. No manual intervention needed.

**Step 1 — Run Part 1:**
```bash
cd ~/Desktop/Epaddy
source ./setup_part1.sh
```

The Pi will reboot. Part 2 will start automatically on the next boot.

**If auto-resume does not trigger**, run Part 2 manually:
```bash
source ~/Desktop/Epaddy/setup_part2.sh
```

> **Warning:** Both options reboot the Pi. You have 10 seconds to cancel with `CTRL+C`.

---

### What Each Script Does

**Part 1 (`setup_part1.sh` or first half of `setup.sh`):**

| Step | Task | Description |
|------|------|-------------|
| 1/6 | Auto-Chmod | Creates `scripts/`, makes `.sh` files executable, sets up auto-chmod service |
| 2/6 | System Update | Runs `apt update`, `apt upgrade`, installs `python3-venv` and `python3-pip` |
| 3/6 | Project Directory | Creates `~/Desktop/Epaddy/`, sets correct ownership |
| 4/6 | Virtual Environment | Creates and activates Python venv at `~/Desktop/Epaddy/.venv` |
| 5/6 | Python Packages | Installs from `requirements.txt`, upgrades `adafruit-python-shell` |
| 6/6 | Adafruit Blinka | Downloads and runs `raspi-blinka.py`, registers auto-resume service |

**Part 2 (`setup_part2.sh`):**

| Step | Task | Description |
|------|------|-------------|
| 1/2 | Boot Config | Enables I2C, SPI, and Google Voice HAT overlay in `/boot/firmware/config.txt` |
| 2/2 | ALSA Sound | Writes audio config to `/etc/asound.conf` for the Voice HAT microphone |

---

## Manual Setup (If You Prefer Not to Use the Script)

### Step 1 — Update the System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip inotify-tools
```

### Step 2 — Create Project Directory

```bash
mkdir -p ~/Desktop/Epaddy
cd ~/Desktop/Epaddy
```

### Step 3 — Set Up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 4 — Install Python Packages

```bash
pip install -r requirements.txt
pip3 install --upgrade adafruit-python-shell
```

### Step 5 — Install Adafruit Blinka

```bash
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
sudo .venv/bin/python3 raspi-blinka.py
```

### Step 6 — Edit Boot Config

```bash
sudo nano /boot/firmware/config.txt
```

Add or uncomment the following lines:

```
dtparam=i2c_arm=on
dtparam=spi=on
dtoverlay=googlevoicehat-soundcard
```

> **Note:** On older Raspberry Pi OS the file may be at `/boot/config.txt` instead.

### Step 7 — Configure ALSA Sound

```bash
sudo nano /etc/asound.conf
```

Paste the following:

```
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
```

### Step 8 — Reboot

```bash
sudo reboot
```

---

## After Final Reboot

### Reactivate the virtual environment

```bash
source ~/Desktop/Epaddy/.venv/bin/activate
```

### Verify I2C is working

```bash
sudo i2cdetect -y 1
```

### Verify sound card is detected

```bash
arecord -l
```

### Check auto-chmod service is running

```bash
sudo systemctl status auto-chmod
```

### Connect Tailscale

Tailscale is installed during setup but must be connected manually:

```bash
sudo tailscale up
```

Follow the link it provides to authenticate in your browser.

### Check auto-resume service (Option B only)

The `epaddy-resume` service is automatically removed after Part 2 completes. If you want to confirm it's gone:

```bash
sudo systemctl status epaddy-resume
# Should return: Unit epaddy-resume.service could not be found
```

---

## Boot Config Reference

| Parameter | Purpose |
|-----------|---------|
| `dtparam=i2c_arm=on` | Enables I2C communication |
| `dtparam=spi=on` | Enables SPI communication |
| `dtoverlay=googlevoicehat-soundcard` | Enables Google Voice HAT audio driver |

---

## Python Packages (requirements.txt)

<!-- TODO: Add or remove packages as your project grows -->

```
adafruit-circuitpython-ahtx0
adafruit-circuitpython-busdevice
```

---

## Troubleshooting

<!-- TODO: Add issues you encounter during setup -->

| Issue | Fix |
|-------|-----|
| `apt update` fails | Check WiFi connection: `ping google.com` |
| Venv not active after reboot | Run `source ~/Desktop/Epaddy/.venv/bin/activate` |
| `raspi-blinka.py` fails | Make sure I2C and SPI are enabled in boot config |
| Sound not working | Run `arecord -l` and check `dtoverlay` in `/boot/firmware/config.txt` |
| I2C not detected | Run `sudo i2cdetect -y 1` and verify `dtparam=i2c_arm=on` is set |
| Boot config not found | Try `/boot/config.txt` instead of `/boot/firmware/config.txt` |
| Script permission denied | Run `chmod +x setup.sh` then `source ./setup.sh` |
| auto-chmod service not running | Run `sudo systemctl restart auto-chmod` |
| Part 2 did not auto-run after reboot | Run manually: `source ~/Desktop/Epaddy/setup_part2.sh` |
| epaddy-resume service still active | Run `sudo systemctl disable epaddy-resume && sudo rm /etc/systemd/system/epaddy-resume.service` |

---

## Notes

<!-- TODO: Add any project-specific notes here -->

- The Pi Zero is slower than other Pi models — `apt upgrade` may take 10–20 minutes
- Always use `source ./setup.sh` not `bash ./setup.sh` so the venv activation persists
- Drop any `.sh` file into `~/Desktop/Epaddy/scripts/` and it will be auto-chmod'd
- Option B (two-part) is recommended — it handles Blinka's reboot automatically
- The `epaddy-resume` service is self-cleaning — it removes itself after Part 2 completes

---

## License

<!-- TODO: Choose a license or remove this section -->
MIT License
