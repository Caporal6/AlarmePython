#!/usr/bin/env python3
"""
Test MQTT broker functionality
"""
import paho.mqtt.client as mqtt
import time
import sys

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected successfully to MQTT broker")
    else:
        print(f"❌ Failed to connect to MQTT broker with result code {rc}")
    
def on_message(client, userdata, msg):
    print(f"Message received on {msg.topic}: {msg.payload.decode()}")

def on_disconnect(client, userdata, rc):
    if rc == 0:
        print("Disconnected successfully")
    else:
        print(f"Unexpected disconnection with code {rc}")

def run_test():
    print("Testing MQTT broker...")
    
    # Create client
    client = mqtt.Client("python_test_client")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # Connect to broker
        print("Connecting to localhost:1883...")
        client.connect("localhost", 1883, 60)
        
        # Start network loop in background
        client.loop_start()
        
        # Wait for connection
        time.sleep(1)
        
        # Subscribe to test topic
        test_topic = "mqtt/test"
        print(f"Subscribing to {test_topic}...")
        client.subscribe(test_topic)
        
        # Publish a test message
        print(f"Publishing test message to {test_topic}...")
        client.publish(test_topic, "Hello from Python test")
        
        # Wait for the message to be received
        time.sleep(2)
        
        # Clean up
        client.loop_stop()
        client.disconnect()
        print("Test complete!")
        return True
    
    except Exception as e:
        print(f"❌ Error during MQTT test: {e}")
        return False

if __name__ == "__main__":
    success = run_test()
    if not success:
        print("\nTroubleshooting tips:")
        print("1. Ensure Mosquitto is installed: sudo apt-get install mosquitto")
        print("2. Ensure Mosquitto is running: sudo systemctl status mosquitto")
        print("3. Check if port 1883 is open: netstat -an | grep 1883")
        print("4. Run setup_mosquitto.sh to configure WebSockets")
        sys.exit(1)