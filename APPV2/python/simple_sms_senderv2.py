#!/usr/bin/env python3
"""
Simple SMS sender for ePADDY - uses classifier module
This matches your original detection.classify() pattern
Logs all predictions to predictions.csv
"""

import classifier
import time
from datetime import datetime
import serial
import csv
import os

# ============ CONFIGURATION ============
# Path to your audio folder
folder_path = '/mnt/shared_drive/insect_sounds/test'  # CHANGE THIS
output_folder = '/home/caling/Desktop/Epaddy/YOLO/output_folder'  # CHANGE THIS
#model_path = '/home/caling/Desktop/Epaddy/YOLO/Epaddy_YOLOv1medium.pt'  # CHANGE THIS
model_path = '/home/caling/Desktop/Epaddy/YOLO/Retrained_YOLOv1nano.pt'
#model_path = '/home/caling/Desktop/Epaddy/YOLO/Epaddy_YOLOv1small.pt'


# CSV log file (in same directory as this script)
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_log_file = os.path.join(script_dir, "predictions.csv")

# Serial config
serial_port = '/dev/ttyAMA0'
baud_rate = 9600

# List of recipient phone numbers
phone_numbers = ["+6XXXXXXXXXX", "+6YYYYYYYYYY"]  # Replace with actual numbers
# =======================================
ALL_KNOWN_CLASSES = ['T_Castaneum', 'S_Oryzae', 'R_Dominica']

def log_prediction_to_csv(message_text):
    """
    Log prediction to CSV file with per-class columns
    Creates file with headers if it doesn't exist
    """
    try:
        # Check if file exists to determine if we need headers
        file_exists = os.path.isfile(csv_log_file)
        
        # Parse the message to extract data
        lines = message_text.strip().split('\n')
        audio_file = "Unknown"
        total_segments = 0
        max_peaks = 0
        predictions = {}
        
        for line in lines:
            if line.startswith("Audio:"):
                audio_file = line.replace("Audio:", "").strip()
            elif line.startswith("Total:"):
                total_segments = line.replace("Total:", "").split()[0].strip()
            elif line.startswith("Max_peaks"):
                max_peaks = line.replace("Max_peaks:", "").split()[0].strip()
            elif ":" in line and "(" in line and "%" in line:
                # Parse result lines like "  healthy: 8 (80.0%)"
                parts = line.strip().split(":")
                if len(parts) == 2:
                    class_name = parts[0].strip()
                    count_part = parts[1].split("(")[0].strip()
                    percentage_part = parts[1].split("(")[1].replace(")", "").replace("%", "").strip()
                    predictions[class_name] = {
                        'count': int(count_part),
                        'percentage': float(percentage_part)
                    }
        
        # Get all unique class names (sorted for consistency)
        all_classes = sorted(ALL_KNOWN_CLASSES)
        
        # Open CSV file in append mode
        with open(csv_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            # Write header if file is new
            if not file_exists:
                header = ['Timestamp', 'Audio File', 'Total Segments', 'Max Peaks']
                # Add columns for each class (count and percentage)
                for class_name in all_classes:
                    header.append(f'{class_name}_count')
                    header.append(f'{class_name}_percentage')
                header.append('Raw Message')
                writer.writerow(header)
            
            # Prepare data row
            row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                audio_file,
                total_segments,
                max_peaks
            ]
            
            # Add count and percentage for each class
            for class_name in all_classes:
                row.append(predictions.get(class_name, {}).get('count', 0))
                row.append(predictions.get(class_name, {}).get('percentage', 0.0))
            
            # Add raw message at the end
            row.append(message_text.replace('\n', ' | '))
            
            # Write data row
            writer.writerow(row)
        
        print(f"✅ Logged to CSV: {csv_log_file}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not log to CSV: {e}")

def send_command(ser, command, delay=1):
    """Helper to send command and print the response"""
    print(f">>> {command}")
    ser.write((command + '\r').encode())
    time.sleep(delay)
    response = ser.read_all().decode(errors='ignore')
    print(response)
    return response

def send_txt_msg():
    """Send SMS with classification results"""
    try:
        # Run your classifier - just like your original code!
        message_text = classifier.classify(folder_path, output_folder, model_path)
        
        print(f"\n📧 Message to send:\n{message_text}\n")
        
        # Log to CSV
        log_prediction_to_csv(message_text)
        
        # Send to each recipient
        for phone_number in phone_numbers:
            print(f"Sending to: {phone_number}")
            
            # Open serial port each time
            ser = serial.Serial(serial_port, baud_rate, timeout=2)
            time.sleep(2)
            
            send_command(ser, 'AT')
            send_command(ser, 'AT+CMGF=1')
            send_command(ser, f'AT+CMGS="{phone_number}"')
            time.sleep(1)
            
            ser.write(message_text.encode())
            ser.write(b"\x1A")  # Ctrl+Z
            time.sleep(3)
            
            ser.close()
            print(f"✅ Sent to {phone_number}")
        
        print("Messages sent successfully.")
        
    except Exception as e:
        print(f"[{datetime.now()}] Error occurred: {e}")

# Run every hour
if __name__ == "__main__":
    print(f"CSV log file: {csv_log_file}\n")
    print(f"[{datetime.now()}] Running message sender...")
    send_txt_msg()

