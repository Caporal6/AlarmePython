#!/bin/bash
# Setup script for AlarmePython virtual environment

echo "Creating Python virtual environment for AlarmePython..."

# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install --upgrade pip
pip install flask flask-mqtt paho-mqtt watchdog

# If using Raspberry Pi, install additional packages for GUI
if [ -f /etc/os-release ] && grep -q "Raspberry Pi" /etc/os-release; then
    echo "Raspberry Pi detected, installing additional packages..."
    pip install RPi.GPIO
fi

echo "Done! Virtual environment is set up."
echo "To activate the virtual environment, run: source venv/bin/activate"