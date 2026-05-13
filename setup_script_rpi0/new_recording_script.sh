#!/bin/bash

# Configuration
PYTHON_SCRIPT="/path/to/recordv2.py"
PYTHON_CMD="python3"
LOG_FILE="//path/to/recordv2.log"

# Activate virtual environment if needed
source /path/to/venv/bin/activate

# Run the Python script with logging
echo "Starting script at $(date)" >> "$LOG_FILE"
$PYTHON_CMD "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1

# Check exit status
if [ $? -eq 0 ]; then
    echo "Script completed successfully at $(date)" >> "$LOG_FILE"
else
    echo "Script failed at $(date)" >> "$LOG_FILE"
    exit 1
fi
