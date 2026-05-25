import smtplib
import classifier
import time
from datetime import datetime
import csv
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# List of recipient emails
emails = ["i.perilla@cgiar.org","carlbalingbing@gmail.com"]

# folder_path = '/mnt/shared_drive/insect_sounds/test'  # CHANGE THIS
# output_folder = '/home/caling/Desktop/Epaddy/YOLO/output_folder'
# model_path = '/home/caling/Desktop/Epaddy/YOLO/Retrained_YOLOv1nano.pt'
folder_path =  r"C:\Users\i.perilla\Desktop\ePaddy\test - Copy"
output_folder = r"C:\Users\i.perilla\Desktop\ePaddy\output_folder"
model_path = r"C:\Users\i.perilla\Desktop\ePaddy\Models\Epaddy_YOLOv2nano.pt"


# CSV log file (in same directory as this script)
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_log_file = os.path.join(script_dir, "predictions.csv")

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

        print(f" Logged to CSV: {csv_log_file}")

    except Exception as e:
        print(f" Warning: Could not log to CSV: {e}")


def sending_emails():
    try:
        message_text = classifier.classify(folder_path, output_folder, model_path)
        log_prediction_to_csv(message_text)
        print("Email sent successfully")

        for email in emails:
            s = smtplib.SMTP('smtp.gmail.com', 587)
            s.starttls()
            s.login("perillaiancarlo@gmail.com", "jijz zpmc ktjv ihpg")

            # Build email with subject
            msg = MIMEMultipart()
            msg['From'] = "perillaiancarlo@gmail.com"
            msg['To'] = email
            msg['Subject'] = "[Test] ePADDY Classification Results"
            msg.attach(MIMEText(message_text, 'plain'))

            s.sendmail("your_email@gmail.com", email, msg.as_string())
            s.quit()
            print(f"Email sent to {email}")

    except Exception as e:
        print(f"[{datetime.now()}] Error occurred: {e}")

if __name__ == "__main__":
    print(f"CSV log file: {csv_log_file}\n")
    print(f"[{datetime.now()}] Running message sender...")
    sending_emails()
    print(f"[{datetime.now()}] Message sent successfully")


