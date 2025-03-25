import re

# Read the app.py file
with open('app.py', 'r') as file:
    content = file.read()

# Find the problematic route definitions
websocket_route = re.search(r'@app\.route\(\'/websocket_test\'\)\s*def websocket_test\(\):[^}]*?return render_template\(\'test.html\'\)', content, re.DOTALL)
hardware_route = re.search(r'@app\.route\(\'/hardware_test_page\'\)\s*def hardware_test_page\(\):[^}]*?return render_template\(\'hardware_test.html\'\)', content, re.DOTALL)

if websocket_route and hardware_route:
    # Remove these routes from their current locations
    content = content.replace(websocket_route.group(0), '')
    content = content.replace(hardware_route.group(0), '')
    
    # Find a good place to put them (before the if __name__ block)
    main_block = re.search(r'if __name__ == \'__main__\':', content)
    if main_block:
        insert_point = main_block.start()
        
        # Add the routes at the insert point
        content = (content[:insert_point] + 
                  "\n@app.route('/websocket_test')\n" +
                  "def websocket_test():\n" +
                  '    """Test page for WebSocket connections"""\n' +
                  "    return render_template('test.html')\n\n" +
                  "@app.route('/hardware_test_page')\n" +
                  "def hardware_test_page():\n" +
                  '    """Dedicated page for testing hardware components"""\n' +
                  "    return render_template('hardware_test.html')\n\n" +
                  content[insert_point:])
        
        # Write the fixed content back
        with open('app.py', 'w') as file:
            file.write(content)
        
        print("Routes fixed successfully.")
    else:
        print("Could not find if __name__ == '__main__' block.")
else:
    print("Could not find the route definitions.")

@app.route('/simple_test', methods=['GET', 'POST'])
def simple_test():
    """Simple hardware test endpoint that's maximally compatible"""
    try:
        print("simple_test endpoint called")
        if request.method == 'GET':
            return jsonify({"status": "ok", "message": "Simple test endpoint is working"}), 200
            
        # For POST requests
        if not request.is_json:
            print("Request is not JSON")
            return jsonify({
                "status": "error", 
                "message": "Request must be JSON"
            }), 400
            
        data = request.json
        print(f"Received test data: {data}")
        
        component = data.get('component', '')
        action = data.get('action', '')
        
        if not component or not action:
            return jsonify({
                "status": "error", 
                "message": "Missing component or action parameter"
            }), 400
            
        # Try different hardware control methods
        
        # First, try hardware_bridge
        try:
            from hardware_bridge import control_hardware, HARDWARE_AVAILABLE
            if HARDWARE_AVAILABLE:
                print(f"Using hardware_bridge for {component} {action}")
                result = control_hardware(component, action)
                return jsonify(result), 200
        except ImportError:
            print("hardware_bridge not available")
            pass
            
        # Next, try pi5_hardware
        try:
            from pi5_hardware import control_component, HARDWARE_AVAILABLE as PI5_HARDWARE_AVAILABLE
            if PI5_HARDWARE_AVAILABLE:
                print(f"Using pi5_hardware for {component} {action}")
                result = control_component(component, action)
                return jsonify(result), 200
        except ImportError:
            print("pi5_hardware not available")
            pass
            
        # Finally, try interface_1 directly
        try:
            import interface_1
            hardware_available = getattr(interface_1, 'HARDWARE_AVAILABLE', False)
            
            print(f"Using interface_1 (hardware available: {hardware_available})")
            
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
                
            elif component == 'buzzer':
                buzzer = getattr(interface_1, 'buzzer', None)
                if not buzzer:
                    return jsonify({"status": "error", "message": "Buzzer component not found"}), 200
                
                if action == 'on':
                    buzzer.on()
                    import threading
                    import time
                    threading.Timer(1.0, lambda: buzzer.off()).start()
                    return jsonify({"status": "success", "message": "Buzzer beeped"}), 200
                elif action == 'off':
                    buzzer.off()
                    return jsonify({"status": "success", "message": "Buzzer turned off"}), 200
            
            # Fallback for unknown components
            return jsonify({
                "status": "error",
                "message": f"Unknown component/action: {component}/{action}"
            }), 200
            
        except ImportError as e:
            print(f"interface_1 not available: {e}")
            # Fallback to simulated response
            return jsonify({
                "status": "success", 
                "message": f"{component} {action} (simulated)",
                "simulated": True
            }), 200
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "message": f"Error: {str(e)}"
        }), 500