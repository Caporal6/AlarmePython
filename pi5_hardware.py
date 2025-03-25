# pi5_hardware.py - Raspberry Pi 5 hardware control using lgpio
import time
import sys
import os
import json
import random
import threading

# Flag to track hardware availability
HARDWARE_AVAILABLE = False
PI5_MODE = False

# Check if we're on a Pi 5
try:
    with open('/proc/device-tree/model', 'r') as f:
        model = f.read()
        PI5_MODE = 'Raspberry Pi 5' in model
        print(f"System model: {model.strip()}")
except:
    print("Could not determine if running on Pi 5")

# Pin definitions - adjust to match your connections
LED_PIN = 6        # GPIO pin for LED
BUZZER_PIN = 18    # GPIO pin for buzzer

# Define components with their pins
COMPONENTS = {
    'led': LED_PIN,
    'buzzer': BUZZER_PIN
}

# Try to initialize GPIO
try:
    if PI5_MODE:
        print("Initializing GPIO using lgpio (Pi 5 compatible)")
        import lgpio
        
        # Open the GPIO chip
        h = lgpio.gpiochip_open(4)  # Use chip 4 for Raspberry Pi 5
        
        # Configure pins as outputs
        lgpio.gpio_claim_output(h, LED_PIN)
        lgpio.gpio_claim_output(h, BUZZER_PIN)
        
        # Set all outputs to LOW initially
        lgpio.gpio_write(h, LED_PIN, 0)
        lgpio.gpio_write(h, BUZZER_PIN, 0)
        
        # Flag that hardware is available
        HARDWARE_AVAILABLE = True
        print("GPIO initialization successful")
    else:
        print("Not running on Pi 5, hardware control disabled")
except Exception as e:
    print(f"Error initializing GPIO: {e}")
    HARDWARE_AVAILABLE = False

def control_component(component, action):
    """Control a hardware component using lgpio"""
    result = {
        "status": "error",
        "message": f"Unknown component or action: {component} / {action}"
    }
    
    if not HARDWARE_AVAILABLE or not PI5_MODE:
        return {
            "status": "error",
            "message": "Hardware control not available"
        }
    
    try:
        if component not in COMPONENTS:
            return {
                "status": "error",
                "message": f"Unknown component: {component}"
            }
        
        pin_number = COMPONENTS[component]
        
        if action == "on":
            lgpio.gpio_write(h, pin_number, 1)
            result = {"status": "success", "message": f"{component} turned on"}
            
            # For buzzer, turn off after a short time
            if component == "buzzer":
                def turn_off_buzzer():
                    time.sleep(0.5)
                    lgpio.gpio_write(h, pin_number, 0)
                
                threading.Thread(target=turn_off_buzzer).start()
                
        elif action == "off":
            lgpio.gpio_write(h, pin_number, 0)
            result = {"status": "success", "message": f"{component} turned off"}
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}
        
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Error controlling {component}: {str(e)}"
        }
    
    return result

def get_sensor_data():
    """Get simulated sensor data"""
    data = {
        "hardware_available": HARDWARE_AVAILABLE,
        "pi5_mode": PI5_MODE,
        "timestamp": time.time()
    }
    
    # Generate simulated data
    data["temperature"] = random.uniform(20.0, 25.0)
    data["humidity"] = random.uniform(40.0, 60.0)
    data["distance"] = random.uniform(30.0, 100.0)
    data["movement_detected"] = random.choice([True, False])
    data["simulated"] = True
    
    return data

# Test functionality if run directly
if __name__ == "__main__":
    print(f"Running on Pi 5: {PI5_MODE}")
    print(f"Hardware available: {HARDWARE_AVAILABLE}")
    
    if HARDWARE_AVAILABLE:
        print("\nTesting LED...")
        print(control_component("led", "on"))
        time.sleep(1)
        print(control_component("led", "off"))
        
        print("\nTesting Buzzer...")
        print(control_component("buzzer", "on"))
        time.sleep(1)
        
        print("\nSensor data sample:")
        print(json.dumps(get_sensor_data(), indent=2))