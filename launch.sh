#!/bin/bash
# Launcher script for AlarmePython

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run setup_venv.sh first."
    exit 1
fi

# Activate the virtual environment
source venv/bin/activate

# Run the application with arguments passed to this script
python app.py "$@"