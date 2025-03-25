import re
import os
import time

# Read the app.py file
try:
    with open('app.py', 'r') as file:
        content = file.read()
except Exception as e:
    print(f"Error reading app.py: {e}")
    exit(1)

# Define the routes to add
routes_to_add = """
# Hardware API routes
@app.route('/hardware_status')
def hardware_status():
    \"\"\"Return hardware availability status\"\"\"
    try:
        import sys
        sys.path.append(".")
        from interface_1 import HARDWARE_AVAILABLE
        
        return jsonify({
            "hardware_available": HARDWARE_AVAILABLE,
            "sensors": {
                "temperature": True,
                "humidity": True,
                "distance": True,
                "movement": True
            } if HARDWARE_AVAILABLE else {}
        })
    except ImportError as e:
        print(f"Error importing interface_1 module: {e}")
        return jsonify({
            "hardware_available": False,
            "message": "Hardware interface not accessible"
        })

@app.route('/sensor_data')
def sensor_data():
    \"\"\"Return current sensor readings if hardware is available\"\"\"
    try:
        # Try to import from the interface
        import sys
        sys.path.append(".")
        
        try:
            # First check if the interface_1 module has a get_sensor_data function
            from interface_1 import get_sensor_data
            data = get_sensor_data()
            return jsonify(data)
        except (ImportError, AttributeError) as e:
            print(f"Error accessing sensor data: {e}")
            
            # Create a dummy response with error message
            return jsonify({
                "hardware_available": False,
                "error": "Cannot access sensor data function",
                "message": str(e),
                "timestamp": time.time()
            })
    except Exception as e:
        print(f"Sensor data error: {e}")
        return jsonify({
            "hardware_available": False,
            "error": str(e),
            "timestamp": time.time()
        })

@app.route('/test_hardware_fixed', methods=['POST'])
def test_hardware_fixed():
    \"\"\"Test hardware components with better error handling\"\"\"
    try:
        if not request.is_json:
            return jsonify({
                "status": "error", 
                "message": "Request must be JSON"
            }), 400
            
        data = request.json
        component = data.get('component', '')
        action = data.get('action', '')
        
        if not component or not action:
            return jsonify({
                "status": "error", 
                "message": "Missing component or action parameter"
            }), 400
            
        # Check for hardware availability
        try:
            import sys
            sys.path.append(".")
            import interface_1
            
            # Check if hardware is available at all
            if not getattr(interface_1, 'HARDWARE_AVAILABLE', False):
                return jsonify({
                    "status": "error", 
                    "message": "Hardware is not available in this environment"
                }), 200
                
            # Process by component type
            if component == 'led':
                led = getattr(interface_1, 'led', None)
                if not led:
                    return jsonify({"status": "error", "message": "LED component not found"}), 200
                    
                if action == 'on':
                    led.on()
                    return jsonify({"status": "success", "message": "LED turned on"}), 200
                elif action == 'off':
                    led.off()
                    return jsonify({"status": "success", "message": "LED turned off"}), 200
                else:
                    return jsonify({"status": "error", "message": f"Unknown LED action: {action}"}), 200
                    
            elif component == 'servo':
                servo = getattr(interface_1, 'servo', None)
                if not servo:
                    return jsonify({"status": "error", "message": "Servo component not found"}), 200
                    
                if action == 'sweep':
                    # Use a thread to avoid blocking
                    import threading
                    import time
                    
                    def move_servo_test():
                        try:
                            for angle in range(0, 181, 5):
                                servo.angle = angle
                                time.sleep(0.01)
                            for angle in range(180, -1, -5):
                                servo.angle = angle
                                time.sleep(0.01)
                        except Exception as e:
                            print(f"Error in servo sweep thread: {e}")
                    
                    threading.Thread(target=move_servo_test).start()
                    return jsonify({"status": "success", "message": "Servo moving back and forth"}), 200
                    
                elif action == 'center':
                    servo.angle = 90
                    return jsonify({"status": "success", "message": "Servo centered at 90°"}), 200
                else:
                    return jsonify({"status": "error", "message": f"Unknown servo action: {action}"}), 200
                    
            elif component == 'buzzer':
                buzzer = getattr(interface_1, 'buzzer', None)
                if not buzzer:
                    return jsonify({"status": "error", "message": "Buzzer component not found"}), 200
                    
                if action == 'on':
                    buzzer.on()
                    # Turn off after 1 second
                    import threading
                    import time
                    threading.Timer(1.0, lambda: buzzer.off()).start()
                    return jsonify({"status": "success", "message": "Buzzer beeped"}), 200
                elif action == 'off':
                    buzzer.off()
                    return jsonify({"status": "success", "message": "Buzzer turned off"}), 200
                else:
                    return jsonify({"status": "error", "message": f"Unknown buzzer action: {action}"}), 200
            else:
                return jsonify({"status": "error", "message": f"Unknown component: {component}"}), 200
                
        except ImportError as e:
            return jsonify({
                "status": "error", 
                "message": f"Failed to import hardware module: {str(e)}"
            }), 200
        except Exception as e:
            return jsonify({
                "status": "error", 
                "message": f"Hardware control error: {str(e)}"
            }), 200
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/debug/sensor')
def debug_sensor():
    \"\"\"Debug endpoint for sensor data\"\"\"
    import time
    info = {
        "timestamp": time.time(),
        "routes": [rule.rule for rule in app.url_map.iter_rules()],
        "modules": []
    }
    
    # Try to import interface modules
    try:
        import sys
        sys.path.append(".")
        info["sys_path"] = sys.path
        
        # Check interface_1
        try:
            import interface_1
            info["interface_1_imported"] = True
            info["hardware_available"] = getattr(interface_1, 'HARDWARE_AVAILABLE', False)
            info["has_get_sensor_data"] = hasattr(interface_1, 'get_sensor_data')
            
            # If get_sensor_data exists, try calling it
            if info["has_get_sensor_data"]:
                try:
                    sensor_data = interface_1.get_sensor_data()
                    info["sensor_data_call_success"] = True
                    info["sensor_data_result"] = sensor_data
                except Exception as e:
                    info["sensor_data_call_success"] = False
                    info["sensor_data_error"] = str(e)
            
            # Check for specific components
            if info["hardware_available"]:
                components = ["led", "buzzer", "servo", "ultrasonic"]
                for comp in components:
                    info[f"has_{comp}"] = hasattr(interface_1, comp)
            
        except ImportError as e:
            info["interface_1_imported"] = False
            info["interface_1_error"] = str(e)
        
        # List all available Python files
        import os
        info["python_files"] = [f for f in os.listdir(".") if f.endswith(".py")]
        
    except Exception as e:
        info["error"] = str(e)
    
    return jsonify(info)
"""

# Find where to insert the new routes (before if __name__ == '__main__':)
main_block = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]:', content)
if main_block:
    insert_point = main_block.start()
    # Add the routes to the content
    new_content = content[:insert_point] + routes_to_add + content[insert_point:]
    
    # Write back to app.py
    try:
        with open('app.py', 'w') as file:
            file.write(new_content)
        print("Successfully added hardware API endpoints to app.py")
    except Exception as e:
        print(f"Error writing to app.py: {e}")
        exit(1)
else:
    print("Could not find if __name__ == '__main__': block in app.py")
    exit(1)

print("API endpoints have been added. Please restart your Flask application.")