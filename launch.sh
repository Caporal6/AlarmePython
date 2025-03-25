#!/bin/bash
# Launcher script for AlarmePython

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating it now..."
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    # Activate the virtual environment
    source venv/bin/activate
fi

# Check if a specific mode is requested
if [[ "$*" == *"--web"* ]]; then
    # Web mode only
    echo "Starting in web mode only"
    python app.py --web "$@"
elif [[ "$*" == *"--gui"* ]]; then
    # GUI mode only
    echo "Starting in GUI mode only"
    python app.py --gui "$@"
else
    # Default: both modes
    echo "Starting in both web and GUI modes"
    python app.py --both "$@"
fi