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
# Modify the initialization block to add more debugging info
try:
    if PI5_MODE:
        print("Initializing GPIO using lgpio (Pi 5 compatible)")
        
        # Check if lgpio is available
        try:
            import lgpio
            print("Successfully imported lgpio")
        except ImportError as e:
            print(f"Failed to import lgpio: {e}")
            raise
        
        # List available GPIO chips for debugging
        try:
            import subprocess
            result = subprocess.run(['ls', '-la', '/dev/gpiochip*'], capture_output=True, text=True)
            print(f"Available GPIO chips: {result.stdout}")
        except Exception as e:
            print(f"Error listing GPIO chips: {e}")
        
        # Try opening the GPIO chip with error handling
        try:
            h = lgpio.gpiochip_open(4)  # Use chip 4 for Raspberry Pi 5
            print(f"Successfully opened gpiochip4, handle: {h}")
        except Exception as e:
            print(f"Error opening gpiochip4: {e}")
            # Try alternative chip numbers
            for chip_num in [0, 1, 2, 3]:
                try:
                    print(f"Trying gpiochip{chip_num} instead...")
                    h = lgpio.gpiochip_open(chip_num)
                    print(f"Successfully opened gpiochip{chip_num}, handle: {h}")
                    break
                except Exception as sub_e:
                    print(f"Error opening gpiochip{chip_num}: {sub_e}")
            else:
                print("Could not open any GPIO chip")
                raise Exception("No accessible GPIO chips found")
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