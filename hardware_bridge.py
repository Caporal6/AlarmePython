# hardware_bridge.py
# Bridge module to safely interface between web app and hardware components

import os
import sys
import json
import time
import random
import importlib.util

# Flag to track hardware availability
HARDWARE_AVAILABLE = False
HARDWARE_COMPONENTS = {}

# Try to import hardware interface module
try:
    # Add current directory to path to ensure imports work
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # First try direct import
    import interface_1
    
    # Check if hardware is available in the imported module
    if hasattr(interface_1, 'HARDWARE_AVAILABLE'):
        HARDWARE_AVAILABLE = interface_1.HARDWARE_AVAILABLE
        
        # If hardware is available, import the components
        if HARDWARE_AVAILABLE:
            HARDWARE_COMPONENTS = {
                'led': getattr(interface_1, 'led', None),
                'servo': getattr(interface_1, 'servo', None),
                'buzzer': getattr(interface_1, 'buzzer', None),
                'ultrasonic': getattr(interface_1, 'ultrasonic', None),
            }
            print(f"Hardware components imported: {list(HARDWARE_COMPONENTS.keys())}")
    
    print(f"Interface module imported successfully. Hardware available: {HARDWARE_AVAILABLE}")
    
except ImportError as e:
    print(f"Error importing interface_1 module: {e}")
    print("Hardware functionality will be limited")

# Function to get sensor data with robust error handling
def get_sensor_data():
    """Get current sensor data safely with fallbacks for testing"""
    data = {
        "hardware_available": HARDWARE_AVAILABLE,
        "timestamp": time.time()
    }
    
    if not HARDWARE_AVAILABLE:
        # Return simulated data for testing
        data["temperature"] = random.uniform(20.0, 25.0)
        data["humidity"] = random.uniform(40.0, 60.0)
        data["distance"] = random.uniform(30.0, 100.0)
        data["movement_detected"] = random.choice([True, False])
        data["simulated"] = True
        return data
    
    try:
        # Try to use the interface's get_sensor_data function first
        if hasattr(interface_1, 'get_sensor_data'):
            return interface_1.get_sensor_data()
        
        # Fallback: Try to get temperature and humidity directly
        try:
            if hasattr(interface_1, 'DHT') and hasattr(interface_1, 'DHTPin'):
                dht = interface_1.DHT.DHT(interface_1.DHTPin)
                chk = dht.readDHT11()
                if chk == 0:
                    data["temperature"] = dht.temperature
                    data["humidity"] = dht.humidity
            else:
                # Fall back to simulated data
                data["temperature"] = random.uniform(20.0, 25.0)
                data["humidity"] = random.uniform(40.0, 60.0)
                data["simulated_temp_humidity"] = True
        except Exception as e:
            print(f"Temperature/humidity sensor error: {e}")
            data["temperature"] = random.uniform(20.0, 25.0)
            data["humidity"] = random.uniform(40.0, 60.0)
            data["simulated_temp_humidity"] = True
        
        # Try to get distance
        if 'ultrasonic' in HARDWARE_COMPONENTS and HARDWARE_COMPONENTS['ultrasonic']:
            data["distance"] = HARDWARE_COMPONENTS['ultrasonic'].distance * 100  # Convert to cm
        else:
            data["distance"] = random.uniform(30.0, 100.0)
            data["simulated_distance"] = True
        
        # Try to check for movement
        if hasattr(interface_1, 'check_movement'):
            data["movement_detected"] = not interface_1.check_movement()  # Inverted for consistency
        else:
            data["movement_detected"] = random.choice([True, False])
            data["simulated_movement"] = True
        
    except Exception as e:
        print(f"Error getting sensor data: {e}")
        # Return fallback data on error
        data["error"] = str(e)
        data["temperature"] = random.uniform(20.0, 25.0)
        data["humidity"] = random.uniform(40.0, 60.0)
        data["distance"] = random.uniform(30.0, 100.0)
        data["movement_detected"] = random.choice([True, False])
        data["simulated"] = True
    
    return data

# Function to safely control hardware components
def control_hardware(component, action):
    """Safely control hardware components with error handling"""
    result = {
        "status": "error",
        "message": f"Unknown component or action: {component} / {action}"
    }
    
    if not HARDWARE_AVAILABLE:
        return {
            "status": "error",
            "message": "Hardware not available. Running in simulation mode."
        }
    
    try:
        # LED control
        if component == 'led':
            led = HARDWARE_COMPONENTS.get('led')
            if not led:
                raise Exception("LED component not available")
                
            if action == 'on':
                led.on()
                result = {"status": "success", "message": "LED turned on"}
            elif action == 'off':
                led.off()
                result = {"status": "success", "message": "LED turned off"}
            else:
                result = {"status": "error", "message": f"Unknown LED action: {action}"}
        
        # Servo control
        elif component == 'servo':
            servo = HARDWARE_COMPONENTS.get('servo')
            if not servo:
                raise Exception("Servo component not available")
                
            if action == 'sweep':
                # Start a thread to move the servo in interface_1
                if hasattr(interface_1, 'move_servo'):
                    interface_1.move_servo()
                    result = {"status": "success", "message": "Servo sweep initiated"}
                else:
                    # Manual servo sweep if move_servo not available
                    for angle in range(0, 181, 10):
                        servo.angle = angle
                        time.sleep(0.05)
                    for angle in range(180, -1, -10):
                        servo.angle = angle
                        time.sleep(0.05)
                    result = {"status": "success", "message": "Servo sweep completed"}
            elif action == 'center':
                servo.angle = 90
                result = {"status": "success", "message": "Servo centered"}
            else:
                result = {"status": "error", "message": f"Unknown servo action: {action}"}
        
        # Buzzer control
        elif component == 'buzzer':
            buzzer = HARDWARE_COMPONENTS.get('buzzer')
            if not buzzer:
                raise Exception("Buzzer component not available")
                
            if action == 'on':
                buzzer.on()
                # Schedule buzzer to turn off after a second
                import threading
                threading.Timer(1.0, lambda: buzzer.off()).start()
                result = {"status": "success", "message": "Buzzer beeped"}
            elif action == 'off':
                buzzer.off()
                result = {"status": "success", "message": "Buzzer turned off"}
            else:
                result = {"status": "error", "message": f"Unknown buzzer action: {action}"}
                
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Error controlling {component}: {str(e)}"
        }
    
    return result

# For testing
if __name__ == "__main__":
    print(f"Hardware available: {HARDWARE_AVAILABLE}")
    print(f"Components: {list(HARDWARE_COMPONENTS.keys())}")
    print("Sensor data:", get_sensor_data())
