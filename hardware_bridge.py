# hardware_bridge.py - Optimized for Pi 5
import os
import sys
import json
import time
import random
import subprocess
import importlib.util

# Detect if we're on a Pi 5
def is_pi5():
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            return 'Raspberry Pi 5' in model
    except:
        return False

# Flag to track hardware availability
HARDWARE_AVAILABLE = False
HARDWARE_COMPONENTS = {}
PI5_MODE = is_pi5()

print(f"Detected platform: {'Raspberry Pi 5' if PI5_MODE else 'Non-Pi 5 System'}")

# Try direct GPIO access first (works on Pi 5)
if PI5_MODE:
    try:
        import RPi.GPIO as GPIO
        print("Successfully imported RPi.GPIO")
        
        # Create GPIO-based components
        class GPIOComponent:
            def __init__(self, pin, name):
                self.pin = pin
                self.name = name
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
                print(f"Set up {name} on pin {pin}")
                
            def on(self):
                GPIO.output(self.pin, GPIO.HIGH)
                print(f"{self.name} ON")
                
            def off(self):
                GPIO.output(self.pin, GPIO.LOW)
                print(f"{self.name} OFF")
        
        # Set up GPIO mode
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Create components with direct GPIO
        # These should match the pin numbers in interface_1.py
        led_pin = 6       # GPIO6 for LED
        buzzer_pin = 18   # GPIO18 for Buzzer
        
        # Set up the components
        HARDWARE_COMPONENTS = {
            'led': GPIOComponent(led_pin, 'LED'),
            'buzzer': GPIOComponent(buzzer_pin, 'Buzzer'),
        }
        
        HARDWARE_AVAILABLE = True
        print(f"Direct GPIO access successful. Components: {list(HARDWARE_COMPONENTS.keys())}")
    except Exception as e:
        print(f"Direct GPIO access failed: {e}")

# Try to import interface_1 as fallback
if not HARDWARE_AVAILABLE:
    try:
        # Add current directory to path to ensure imports work
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Import interface_1
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
        "timestamp": time.time(),
        "pi5_mode": PI5_MODE
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
        
        # For Pi 5, generate more realistic simulated data
        if PI5_MODE:
            # Try to get real temperature from system
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp = float(f.read()) / 1000.0  # Convert from millidegrees to degrees
                    data["temperature"] = temp
            except:
                data["temperature"] = random.uniform(20.0, 25.0)
                data["simulated_temp"] = True
                
            # Simulate other sensors    
            data["humidity"] = random.uniform(40.0, 60.0)
            data["distance"] = random.uniform(30.0, 100.0)
            data["movement_detected"] = random.choice([True, False])
            data["partially_simulated"] = True
            
            return data
            
        # Fallback to original behavior
        data["temperature"] = random.uniform(20.0, 25.0)
        data["humidity"] = random.uniform(40.0, 60.0)
        data["distance"] = random.uniform(30.0, 100.0)
        data["movement_detected"] = random.choice([True, False])
        data["simulated"] = True
        
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
        "message": f"Unknown component or action: {component} / {action}",
        "pi5_mode": PI5_MODE
    }
    
    if not HARDWARE_AVAILABLE:
        return {
            "status": "error",
            "message": "Hardware not available. Running in simulation mode.",
            "pi5_mode": PI5_MODE
        }
    
    try:
        # LED control
        if component == 'led':
            led = HARDWARE_COMPONENTS.get('led')
            if not led:
                raise Exception("LED component not available")
                
            if action == 'on':
                led.on()
                result = {"status": "success", "message": "LED turned on", "pi5_mode": PI5_MODE}
            elif action == 'off':
                led.off()
                result = {"status": "success", "message": "LED turned off", "pi5_mode": PI5_MODE}
            else:
                result = {"status": "error", "message": f"Unknown LED action: {action}", "pi5_mode": PI5_MODE}
        
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
                result = {"status": "success", "message": "Buzzer beeped", "pi5_mode": PI5_MODE}
            elif action == 'off':
                buzzer.off()
                result = {"status": "success", "message": "Buzzer turned off", "pi5_mode": PI5_MODE}
            else:
                result = {"status": "error", "message": f"Unknown buzzer action: {action}", "pi5_mode": PI5_MODE}
                
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Error controlling {component}: {str(e)}",
            "pi5_mode": PI5_MODE
        }
    
    return result

# For testing
if __name__ == "__main__":
    print(f"Hardware available: {HARDWARE_AVAILABLE}")
    print(f"Components: {list(HARDWARE_COMPONENTS.keys())}")
    print("Sensor data:", get_sensor_data())
    
    # If hardware is available, test components
    if HARDWARE_AVAILABLE:
        print("\nTesting components:")
        for component_name in HARDWARE_COMPONENTS:
            print(f"Testing {component_name}...")
            result = control_hardware(component_name, 'on')
            print(f"Result: {result}")
            time.sleep(1)
            result = control_hardware(component_name, 'off')
            print(f"Result: {result}")