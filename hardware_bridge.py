# hardware_bridge.py - Optimized for Pi 5
import os
import sys
import json
import time
import random
import subprocess
import importlib.util

# Add this at the beginning of the file to properly set the hardware availability flag

# Use simulation mode if environment variable is set
import os
SIMULATION_MODE = os.environ.get('SIMULATE_HARDWARE', '0') == '1'

# Try to detect hardware
HARDWARE_AVAILABLE = False
HARDWARE_COMPONENTS = {}

# Try the Pi 5 hardware first if it's available
try:
    from pi5_hardware import HARDWARE_AVAILABLE as PI5_HARDWARE_AVAILABLE, COMPONENTS
    if PI5_HARDWARE_AVAILABLE:
        print("Using Pi 5 hardware interface")
        HARDWARE_AVAILABLE = True
        HARDWARE_COMPONENTS = COMPONENTS
except ImportError:
    pass

# If Pi 5 hardware is not available, try the interface_1 module
if not HARDWARE_AVAILABLE:
    try:
        import interface_1
        if hasattr(interface_1, 'HARDWARE_AVAILABLE') and interface_1.HARDWARE_AVAILABLE:
            print("Using interface_1 hardware interface")
            HARDWARE_AVAILABLE = True
            
            # Map components
            HARDWARE_COMPONENTS = {}
            if hasattr(interface_1, 'led'):
                HARDWARE_COMPONENTS['led'] = 'LED pin'
            if hasattr(interface_1, 'buzzer'):
                HARDWARE_COMPONENTS['buzzer'] = 'Buzzer pin'
            if hasattr(interface_1, 'servo'):
                HARDWARE_COMPONENTS['servo'] = 'Servo pin'
    except ImportError:
        pass

# Check if we have any hardware available
if not HARDWARE_AVAILABLE:
    if SIMULATION_MODE:
        print("Hardware not detected, using simulation mode")
    else:
        print("Warning: No hardware interfaces available")

# Detect if we're on a Pi 5
def is_pi5():
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            return 'Raspberry Pi 5' in model
    except:
        return False

# Flag to track hardware availability
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

# Control hardware function
def control_hardware(component, action):
    """Control hardware components with appropriate interface"""
    # If simulation mode is forced, always use simulation
    if SIMULATION_MODE:
        return {
            "status": "success", 
            "message": f"{component} {action} (simulated)",
            "simulated": True
        }
    
    # First try Pi 5 hardware
    try:
        from pi5_hardware import control_component, HARDWARE_AVAILABLE as PI5_AVAILABLE
        if PI5_AVAILABLE:
            return control_component(component, action)
    except ImportError:
        pass
    
    # Then try interface_1
    try:
        import interface_1
        if not hasattr(interface_1, 'HARDWARE_AVAILABLE') or not interface_1.HARDWARE_AVAILABLE:
            return {
                "status": "error",
                "message": "Hardware not available in interface_1"
            }
        
        if component == 'led':
            if not hasattr(interface_1, 'led'):
                return {"status": "error", "message": "LED not available"}
            
            if action == 'on':
                interface_1.led.on()
                return {"status": "success", "message": "LED turned on"}
            elif action == 'off':
                interface_1.led.off()
                return {"status": "success", "message": "LED turned off"}
            else:
                return {"status": "error", "message": f"Unknown action for LED: {action}"}
                
        elif component == 'buzzer':
            if not hasattr(interface_1, 'buzzer'):
                return {"status": "error", "message": "Buzzer not available"}
                
            if action == 'on':
                interface_1.buzzer.on()
                import threading
                import time
                threading.Timer(1.0, lambda: interface_1.buzzer.off()).start()
                return {"status": "success", "message": "Buzzer beeped"}
            elif action == 'off':
                interface_1.buzzer.off()
                return {"status": "success", "message": "Buzzer turned off"}
            else:
                return {"status": "error", "message": f"Unknown action for buzzer: {action}"}
                
        elif component == 'servo':
            if not hasattr(interface_1, 'servo'):
                return {"status": "error", "message": "Servo not available"}
                
            if action == 'sweep':
                import threading
                def sweep_servo():
                    import time
                    for angle in range(0, 181, 10):
                        interface_1.servo.angle = angle
                        time.sleep(0.05)
                    for angle in range(180, -1, -10):
                        interface_1.servo.angle = angle
                        time.sleep(0.05)
                
                threading.Thread(target=sweep_servo, daemon=True).start()
                return {"status": "success", "message": "Servo sweeping"}
            else:
                interface_1.servo.angle = 90
                return {"status": "success", "message": "Servo centered"}
                
        return {"status": "error", "message": f"Unknown component: {component}"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error controlling hardware: {str(e)}"}
    
    # If we reach here, nothing worked
    return {
        "status": "error",
        "message": "No hardware interfaces available",
        "simulated": True
    }

# Function to get sensor data
def get_sensor_data():
    """Get sensor data from available hardware or simulate if not available"""
    # If simulation mode is forced, always use simulation
    if SIMULATION_MODE:
        return generate_simulated_sensor_data()
    
    # Try interface_1 first
    try:
        import interface_1
        if hasattr(interface_1, 'get_sensor_data'):
            return interface_1.get_sensor_data()
    except ImportError:
        pass
    
    # Try pi5_hardware
    try:
        from pi5_hardware import get_sensor_data as pi5_get_sensor_data
        return pi5_get_sensor_data()
    except ImportError:
        pass
    
    # Fall back to simulation
    return generate_simulated_sensor_data()

def generate_simulated_sensor_data():
    """Generate simulated sensor data"""
    import random
    import time
    
    return {
        "hardware_available": HARDWARE_AVAILABLE,
        "temperature": random.uniform(20.0, 25.0),
        "humidity": random.uniform(40.0, 60.0),
        "distance": random.uniform(30.0, 100.0),
        "movement_detected": random.choice([True, False]),
        "timestamp": time.time(),
        "simulated": True
    }

# For testing
if __name__ == "__main__":
    print(f"Hardware available: {HARDWARE_AVAILABLE}")
    print(f"Hardware components: {list(HARDWARE_COMPONENTS.keys())}")
    
    # Test hardware controls
    if HARDWARE_AVAILABLE:
        components = ['led', 'buzzer']
        for component in components:
            if component in HARDWARE_COMPONENTS:
                print(f"Testing {component}...")
                result = control_hardware(component, 'on')
                print(f"  Result: {result}")
                time.sleep(1)
                result = control_hardware(component, 'off')
                print(f"  Result: {result}")
            else:
                print(f"Component {component} not available")