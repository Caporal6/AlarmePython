import re

# Read the app.py file
with open('app.py', 'r') as f:
    content = f.read()

# Check if the route definition exists
route_pattern = r'@app\.route\([\'"]\/test_hardware_fixed[\'"](.*?)\)'
match = re.search(route_pattern, content)

if match:
    methods_part = match.group(1)
    # Check if methods=['POST'] is in the route definition
    if 'methods=' not in methods_part or 'POST' not in methods_part:
        # Update the route definition to include methods=['POST']
        new_route = "@app.route('/test_hardware_fixed', methods=['POST'])"
        content = re.sub(route_pattern, new_route, content)
        print("Fixed test_hardware_fixed route to explicitly accept POST")
    else:
        print("Route already correctly configured with POST method")
else:
    # Route doesn't exist, let's add the complete implementation
    new_route = """
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
"""
    
    # Find a good place to insert new route - before if __name__ block
    main_block_match = re.search(r'if __name__ == [\'"]__main__[\'"]:.*$', content, re.DOTALL)
    if main_block_match:
        insert_pos = main_block_match.start()
        content = content[:insert_pos] + new_route + content[insert_pos:]
        print("Added test_hardware_fixed route")
    else:
        print("Could not find if __name__ == '__main__' block")
        exit(1)

# Ensure the necessary imports are at the top
needed_imports = [
    "from flask import Flask, render_template, jsonify, request",
    "import time",
    "import threading",
    "import json"
]

for imp in needed_imports:
    if imp not in content[:500]:  # Check only the top of the file
        content = imp + "\n" + content
        print(f"Added missing import: {imp}")

# Write back to app.py
with open('app.py', 'w') as f:
    f.write(content)

print("Successfully updated test_hardware_fixed in app.py")