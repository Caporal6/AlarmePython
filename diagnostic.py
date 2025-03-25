#!/usr/bin/env python3
import sys
import os
import time

print("Alarm Hardware Diagnostic Tool")
print("==============================")

# Add the current directory to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)
print(f"Script directory: {script_dir}")

try:
    print("\nChecking gpiozero installation...")
    import gpiozero
    print(f"✓ gpiozero version: {gpiozero.__version__}")
    
    # Check if we're running on a Pi
    print("\nChecking if we're on a Raspberry Pi...")
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read()
            print(f"✓ System model: {model.strip()}")
            
            is_pi5 = 'Raspberry Pi 5' in model
            print(f"Is Pi 5: {is_pi5}")
    except:
        print("✗ Not running on Raspberry Pi (can't access device tree)")
    
    # Try importing interface modules
    print("\nChecking interface_1.py...")
    try:
        import interface_1
        print(f"✓ interface_1 imported")
        print(f"  HARDWARE_AVAILABLE = {interface_1.HARDWARE_AVAILABLE}")
        
        if hasattr(interface_1, 'led'):
            print("  LED available")
            interface_1.led.on()
            print("  LED ON - check if it's working")
            time.sleep(2)
            interface_1.led.off()
            print("  LED OFF")
        else:
            print("  LED not available")
            
        if hasattr(interface_1, 'buzzer'):
            print("  Buzzer available")
        else:
            print("  Buzzer not available")
            
        if hasattr(interface_1, 'servo'):
            print("  Servo available")
        else:
            print("  Servo not available")
            
    except ImportError as e:
        print(f"✗ Could not import interface_1: {e}")
    
    print("\nChecking hardware_bridge.py...")
    try:
        import hardware_bridge
        print(f"✓ hardware_bridge imported")
        print(f"  HARDWARE_AVAILABLE = {hardware_bridge.HARDWARE_AVAILABLE}")
        print(f"  Hardware components: {list(hardware_bridge.HARDWARE_COMPONENTS.keys())}")
        
        # Test sensor data retrieval
        print("\nTesting sensor data...")
        sensor_data = hardware_bridge.get_sensor_data()
        print(f"  Temperature: {sensor_data.get('temperature')}")
        print(f"  Humidity: {sensor_data.get('humidity')}")
        print(f"  Distance: {sensor_data.get('distance')}")
        print(f"  Movement detected: {sensor_data.get('movement_detected')}")
        print(f"  Simulated: {sensor_data.get('simulated', 'unknown')}")
        
        # Test hardware control
        if hardware_bridge.HARDWARE_AVAILABLE:
            print("\nTesting LED control...")
            result = hardware_bridge.control_hardware('led', 'on')
            print(f"  LED ON result: {result}")
            time.sleep(1)
            result = hardware_bridge.control_hardware('led', 'off')
            print(f"  LED OFF result: {result}")
    except ImportError as e:
        print(f"✗ Could not import hardware_bridge: {e}")
    
    if os.path.exists('pi5_hardware.py'):
        print("\nChecking pi5_hardware.py...")
        try:
            import pi5_hardware
            print(f"✓ pi5_hardware imported")
            print(f"  PI5_MODE = {pi5_hardware.PI5_MODE}")
            print(f"  HARDWARE_AVAILABLE = {pi5_hardware.HARDWARE_AVAILABLE}")
        except ImportError as e:
            print(f"✗ Could not import pi5_hardware: {e}")
    
except Exception as e:
    print(f"\nError during diagnostics: {e}")
    import traceback
    traceback.print_exc()

print("\nDiagnostic complete.")