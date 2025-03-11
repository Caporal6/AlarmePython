#!/bin/bash

echo "Setting up Mosquitto MQTT broker with WebSocket support..."

# Check if Mosquitto is installed
if ! command -v mosquitto &> /dev/null; then
    echo "Installing Mosquitto..."
    sudo apt-get update
    sudo apt-get install -y mosquitto mosquitto-clients
else
    echo "Mosquitto is already installed."
fi

# Stop Mosquitto before reconfiguring
echo "Stopping Mosquitto service..."
sudo systemctl stop mosquitto

# Install the WebSocket configuration
echo "Installing WebSocket configuration..."
sudo cp mosquitto-websocket.conf /etc/mosquitto/conf.d/websockets.conf

# Start Mosquitto with our configuration
echo "Starting Mosquitto service..."
sudo systemctl start mosquitto

# Check if Mosquitto is running
if systemctl is-active --quiet mosquitto; then
    echo "✅ Mosquitto is running with WebSocket support"
    echo "  • Standard MQTT on port 1883"
    echo "  • WebSockets on port 9001"
else
    echo "❌ Failed to start Mosquitto"
    echo "Checking error logs..."
    sudo journalctl -u mosquitto -n 20
fi

# Test if port 9001 is open
if command -v nc &> /dev/null; then
    echo "Testing WebSocket port 9001..."
    if nc -z localhost 9001; then
        echo "✅ Port 9001 is open and accepting connections"
    else
        echo "❌ Port 9001 is not responding"
        echo "Check Mosquitto configuration and firewall settings"
    fi
fi

echo "Setup complete!"