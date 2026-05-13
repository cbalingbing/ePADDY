#!/usr/bin/python3
import os
import sys
import subprocess
from datetime import datetime
import logging
import board
import adafruit_ahtx0


# ==============================
# Load config
# ==============================
def load_config(file_path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, file_path)
    config = {}
    with open(full_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip()
    return config

config = load_config("config.txt")

path = config["path"]
log_path = config["log_path"]
csv_path = config["csv_path"]
node_counter = int(config["node_counter"])
duration = int(config["duration"])
device_name = config["device_name"]
channel_count = config["channel_count"]

MOUNTPOINT = config["mountpoint"]
SERVER = config["server"]
CREDS = config["credentials"]


# ==============================
# Mount functions
# ==============================
def is_mounted():
    return os.path.ismount(MOUNTPOINT)


def mount_share():
    cmd = f"sudo mount -t cifs {SERVER} {MOUNTPOINT} -o credentials={CREDS},uid=1000,gid=1000,iocharset=utf8,vers=3.0,noperm,file_mode=0660,dir_mode=0770,_netdev"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stderr

# ==============================
# STEP 1: Ensure mount exists
# ==============================
if not is_mounted():
    print("Shared drive not mounted. Attempting mount...")
    success, error = mount_share()

    if success:
        print("Mount successful.")
    else:
        print(f"Mount failed: {error}")
        print("Cannot proceed without Samba connection. Exiting.")
        sys.exit(1)
else:
    print("Shared drive already mounted.")


# ==============================
# STEP 2: Check and create directories
# ==============================
try:
    # Check if log directory exists, create if not
    log_dir = os.path.dirname(log_path)
    if not os.path.exists(log_dir):
        print(f"Log directory does not exist. Creating: {log_dir}")
        os.makedirs(log_dir, exist_ok=True)
    
    # Check if CSV directory exists, create if not
    csv_dir = os.path.dirname(csv_path)
    if not os.path.exists(csv_dir):
        print(f"CSV directory does not exist. Creating: {csv_dir}")
        os.makedirs(csv_dir, exist_ok=True)
    
    # Check if recording path exists, create if not
    if not os.path.exists(path):
        print(f"Recording directory does not exist. Creating: {path}")
        os.makedirs(path, exist_ok=True)
    
    print("All directories verified/created successfully.")
    
except Exception as e:
    print(f"Error creating directories on Samba share: {e}")
    print("Cannot proceed without proper directory structure. Exiting.")
    sys.exit(1)


# ==============================
# STEP 3: Test write access
# ==============================
try:
    # Try to write a test file to verify write permissions
    test_file = os.path.join(log_dir, ".test_write")
    with open(test_file, 'w') as f:
        f.write("test")
    os.remove(test_file)
    print("Write access verified.")
except Exception as e:
    print(f"Cannot write to Samba share: {e}")
    print("Check permissions and credentials. Exiting.")
    sys.exit(1)


# ==============================
# STEP 4: Configure logging
# ==============================
logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("="*50)
logging.info("Script started successfully")
logging.info(f"Mount point: {MOUNTPOINT}")
logging.info(f"Log path: {log_path}")
logging.info(f"CSV path: {csv_path}")


# ==============================
# STEP 5: Initialize sensors
# ==============================
try:
    i2c = board.I2C()
    sensor = adafruit_ahtx0.AHTx0(i2c)
    logging.info("Sensor initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize sensor: {e}")
    print(f"Sensor initialization failed: {e}")
    sys.exit(1)


# ==============================
# STEP 6: Prepare recording
# ==============================
timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
filename = f"{path}{node_counter}_{timestamp}-iSound.wav"

command = f"arecord -d {duration} -D {device_name} -c {channel_count} -f S32_LE -t wav {filename}"


# ==============================
# STEP 7: Start recording
# ==============================
logging.info(f"Device {node_counter} Record Start: {datetime.now()}")
logging.info(f"Command: {command}")
print(f"Starting recording: {filename}")

try:
    result = os.system(command)
    if result != 0:
        logging.error(f"Recording command failed with exit code: {result}")
        print(f"Recording failed with exit code: {result}")
        sys.exit(1)
except Exception as e:
    logging.error(f"Recording error: {e}")
    print(f"Recording error: {e}")
    sys.exit(1)


# ==============================
# STEP 8: Read sensors
# ==============================
try:
    temp = sensor.temperature
    hum = sensor.relative_humidity
    logging.info(f"Sensor readings - Temp: {temp:.2f}°C, Humidity: {hum:.2f}%")
except Exception as e:
    logging.error(f"Failed to read sensor data: {e}")
    temp = None
    hum = None


# ==============================
# STEP 9: Log completion
# ==============================
logging.info(f"Device {node_counter} Record End: {datetime.now()}")
logging.info(f"File: {filename}, Temp: {temp:.2f}, Humidity: {hum:.2f}")
logging.info("Script completed successfully")
logging.info("="*50)

print(f"Recording completed: {filename}")
print(f"Temperature: {temp:.2f}°C, Humidity: {hum:.2f}%")


# ==============================
# STEP 10: Optionally write to CSV
# ==============================
try:
    # Check if CSV exists, create with headers if not
    csv_exists = os.path.exists(csv_path)

    with open(csv_path, 'a') as csv_file:
        if not csv_exists:
            # Write header
            csv_file.write("timestamp,node_id,filename,temperature,humidity\n")

        # Write data
        csv_file.write(f"{timestamp},{node_counter},{filename},{temp:.2f},{hum:.2f}\n")

    logging.info(f"Data written to CSV: {csv_path}")
    print("Data logged to CSV successfully")

except Exception as e:
    logging.error(f"Failed to write to CSV: {e}")
    print(f"CSV write failed: {e}")
