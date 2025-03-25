import os
import re
import sys
import time
import json

print("Setting up hardware testing features for the AlarmePython system...")

# Make sure templates directory exists
if not os.path.exists('templates'):
    os.makedirs('templates')
    print("Created templates directory")
else:
    print("Templates directory already exists")

# Check if static directory exists
if not os.path.exists('static'):
    os.makedirs('static')
    print("Created static directory")
else:
    print("Static directory already exists")

# 1. Fix or add the test_hardware_fixed endpoint
print("\nChecking test_hardware_fixed endpoint...")
with open('app.py', 'r') as f:
    app_content = f.read()

# Check if the endpoint exists
if '/test_hardware_fixed' in app_content:
    # Make sure it has POST method
    route_pattern = r'@app\.route\([\'"]\/test_hardware_fixed[\'"](.*?)\)'
    match = re.search(route_pattern, app_content)
    
    if match:
        methods_part = match.group(1)
        if 'methods=' not in methods_part or 'POST' not in methods_part:
            # Update the route definition to include methods=['POST']
            new_route = "@app.route('/test_hardware_fixed', methods=['POST'])"
            app_content = re.sub(route_pattern, new_route, app_content)
            print("Fixed test_hardware_fixed route to explicitly accept POST")
    else:
        print("Found test_hardware_fixed but couldn't parse route definition")
else:
    # Add the test_hardware_fixed endpoint
    hw_test_route = """
@app.route('/test_hardware_fixed', methods=['POST'])
def test_hardware_fixed():
    ""Test hardware components with better error handling""
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
                    
                    threading.Thread(target=move_servo_test, daemon=True).start()
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
    main_block_match = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]:', app_content)
    if main_block_match:
        insert_pos = main_block_match.start()
        app_content = app_content[:insert_pos] + hw_test_route + app_content[insert_pos:]
        print("Added test_hardware_fixed route")
    else:
        print("Could not find if __name__ == '__main__' block")

# 2. Add the sensor_data endpoint
print("\nChecking sensor_data endpoint...")
if '/sensor_data' not in app_content:
    sensor_data_route = """
@app.route('/sensor_data')
def sensor_data():
    ""Return current sensor readings if hardware is available""
    try:
        # Try to import from the interface
        import sys
        sys.path.append(".")
        import time
        
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
"""
    
    # Find a good place to insert new route - before if __name__ block
    main_block_match = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]:', app_content)
    if main_block_match:
        insert_pos = main_block_match.start()
        app_content = app_content[:insert_pos] + sensor_data_route + app_content[insert_pos:]
        print("Added sensor_data route")
    else:
        print("Could not find if __name__ == '__main__' block")
else:
    print("sensor_data route already exists")

# 3. Add hardware_status endpoint
print("\nChecking hardware_status endpoint...")
if '/hardware_status' not in app_content:
    hw_status_route = """
@app.route('/hardware_status')
def hardware_status():
    ""Return hardware availability status""
    try:
        import sys
        sys.path.append(".")
        
        try:
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
    except Exception as e:
        print(f"Hardware status error: {e}")
        return jsonify({
            "hardware_available": False,
            "message": str(e)
        })
"""
    
    # Find a good place to insert new route - before if __name__ block
    main_block_match = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]:', app_content)
    if main_block_match:
        insert_pos = main_block_match.start()
        app_content = app_content[:insert_pos] + hw_status_route + app_content[insert_pos:]
        print("Added hardware_status route")
    else:
        print("Could not find if __name__ == '__main__' block")
else:
    print("hardware_status route already exists")

# 4. Add hardware_test_page route
print("\nChecking hardware_test_page route...")
if '/hardware_test_page' not in app_content:
    hw_test_page_route = """
@app.route('/hardware_test_page')
def hardware_test_page():
    ""Hardware test interface""
    return render_template('hardware_test.html')
"""
    
    # Find a good place to insert new route - before if __name__ block
    main_block_match = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]:', app_content)
    if main_block_match:
        insert_pos = main_block_match.start()
        app_content = app_content[:insert_pos] + hw_test_page_route + app_content[insert_pos:]
        print("Added hardware_test_page route")
    else:
        print("Could not find if __name__ == '__main__' block")
else:
    print("hardware_test_page route already exists")

# 5. Add debug_sensor route
print("\nChecking debug_sensor route...")
if '/debug/sensor' not in app_content:
    debug_sensor_route = """
@app.route('/debug/sensor')
def debug_sensor():
    ""Debug endpoint for sensor data""
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
    
    # Find a good place to insert new route - before if __name__ block
    main_block_match = re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]:', app_content)
    if main_block_match:
        insert_pos = main_block_match.start()
        app_content = app_content[:insert_pos] + debug_sensor_route + app_content[insert_pos:]
        print("Added debug_sensor route")
    else:
        print("Could not find if __name__ == '__main__' block")
else:
    print("debug_sensor route already exists")

# Write the modified content back to app.py
with open('app.py', 'w') as f:
    f.write(app_content)
print("Updated app.py with all necessary routes")

# 6. Update or create hardware_test.html
print("\nUpdating hardware_test.html...")
hardware_test_html = """<!DOCTYPE html>
<html>
<head>
    <title>Hardware Test Interface</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #121212;
            color: #FFFFFF;
        }
        
        h1, h2 {
            color: #BB86FC;
        }
        
        .panel {
            background-color: #1E1E1E;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
        
        .component-row {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #333;
        }
        
        .component-name {
            width: 150px;
            font-weight: bold;
        }
        
        .component-controls {
            display: flex;
            gap: 10px;
        }
        
        button {
            padding: 8px 15px;
            background-color: #BB86FC;
            color: #121212;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        
        button:hover {
            background-color: #9965CC;
        }
        
        .status-box {
            margin-top: 10px;
            padding: 10px;
            background-color: #272727;
            border-radius: 4px;
            min-height: 40px;
            white-space: pre-line;
        }
        
        .success {
            color: #03DAC6;
        }
        
        .error {
            color: #CF6679;
        }
        
        .nav-links {
            margin: 20px 0;
        }
        
        .nav-links a {
            color: #BB86FC;
            margin-right: 15px;
            text-decoration: none;
        }
        
        .nav-links a:hover {
            text-decoration: underline;
        }
        
        #sensorData {
            margin-top: 10px;
        }
        
        .sensor-row {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
        }
        
        .sensor-label {
            font-weight: bold;
        }
        
        .sensor-value {
            color: #03DAC6;
        }
    </style>
</head>
<body>
    <div class="nav-links">
        <a href="/">Home</a>
        <a href="/hardware_test_page">Hardware Test</a>
        <a href="/debug/sensor">Debug Sensor</a>
    </div>

    <h1>Hardware Test Interface</h1>
    
    <div class="panel">
        <h2>Component Control</h2>
        
        <div class="component-row">
            <div class="component-name">LED</div>
            <div class="component-controls">
                <button onclick="testComponent('led', 'on')">Turn On</button>
                <button onclick="testComponent('led', 'off')">Turn Off</button>
            </div>
        </div>
        
        <div class="component-row">
            <div class="component-name">Servo</div>
            <div class="component-controls">
                <button onclick="testComponent('servo', 'sweep')">Sweep</button>
                <button onclick="testComponent('servo', 'center')">Center</button>
            </div>
        </div>
        
        <div class="component-row">
            <div class="component-name">Buzzer</div>
            <div class="component-controls">
                <button onclick="testComponent('buzzer', 'on')">Beep</button>
                <button onclick="testComponent('buzzer', 'off')">Stop</button>
            </div>
        </div>
        
        <div class="status-box" id="testResult">
            Test results will appear here...
        </div>
        
        <div style="margin-top: 15px;">
            <button onclick="checkEndpoints()">Check API Endpoints</button>
            <button onclick="testPostMethod()" style="margin-left: 10px;">Test POST Method</button>
        </div>
    </div>
    
    <div class="panel">
        <h2>Sensor Readings</h2>
        <button onclick="refreshSensorData()">Refresh Sensor Data</button>
        
        <div id="sensorData">
            <div class="sensor-row">
                <span class="sensor-label">Hardware Available:</span>
                <span class="sensor-value" id="hardware-status">Unknown</span>
            </div>
            <div class="sensor-row">
                <span class="sensor-label">Temperature:</span>
                <span class="sensor-value" id="temperature">--°C</span>
            </div>
            <div class="sensor-row">
                <span class="sensor-label">Humidity:</span>
                <span class="sensor-value" id="humidity">--%</span>
            </div>
            <div class="sensor-row">
                <span class="sensor-label">Distance:</span>
                <span class="sensor-value" id="distance">-- cm</span>
            </div>
            <div class="sensor-row">
                <span class="sensor-label">Movement:</span>
                <span class="sensor-value" id="movement">Unknown</span>
            </div>
        </div>
    </div>
    
    <script>
        // More robust component testing with retries
        function testComponent(component, action) {
            const resultElement = document.getElementById('testResult');
            resultElement.textContent = `Testing ${component} (${action})...`;
            resultElement.className = '';
            
            // Use fetch with timeout and retry
            const fetchWithTimeout = (url, options, timeout = 5000) => {
                return Promise.race([
                    fetch(url, options),
                    new Promise((_, reject) =>
                        setTimeout(() => reject(new Error('Request timed out')), timeout)
                    )
                ]);
            };
            
            const fetchWithRetry = (url, options, retries = 3, timeout = 5000) => {
                return fetchWithTimeout(url, options, timeout)
                    .catch(error => {
                        if (retries === 0) throw error;
                        return fetchWithRetry(url, options, retries - 1, timeout);
                    });
            };
            
            fetchWithRetry('/test_hardware_fixed', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    component: component,
                    action: action
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP Error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                resultElement.textContent = data.message;
                resultElement.className = data.status === 'success' ? 'success' : 'error';
            })
            .catch(error => {
                resultElement.textContent = `Error: ${error.message}`;
                resultElement.className = 'error';
                console.error("Hardware test error:", error);
                
                // Fallback to test_hardware endpoint if test_hardware_fixed fails
                if (error.message.includes('404') || error.message.includes('405')) {
                    resultElement.textContent = `Trying alternative endpoint...`;
                    
                    fetch('/test_hardware', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            component: component,
                            action: action
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        resultElement.textContent = data.message;
                        resultElement.className = data.status === 'success' ? 'success' : 'error';
                    })
                    .catch(fallbackError => {
                        resultElement.textContent = `All attempts failed: ${error.message}, Fallback: ${fallbackError.message}`;
                        resultElement.className = 'error';
                    });
                }
            });
        }
        
        function refreshSensorData() {
            // Show loading state
            document.getElementById('hardware-status').textContent = "Loading...";
            
            fetch('/sensor_data')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP Error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log("Sensor data:", data);
                    document.getElementById('hardware-status').textContent = 
                        data.hardware_available ? "Available" : "Not Available";
                        
                    if (data.hardware_available) {
                        if ('temperature' in data) {
                            document.getElementById('temperature').textContent = 
                                `${data.temperature.toFixed(1)}°C`;
                        }
                        
                        if ('humidity' in data) {
                            document.getElementById('humidity').textContent = 
                                `${data.humidity.toFixed(1)}%`;
                        }
                        
                        if ('distance' in data) {
                            document.getElementById('distance').textContent = 
                                `${data.distance.toFixed(1)} cm`;
                        }
                        
                        if ('movement_detected' in data) {
                            document.getElementById('movement').textContent = 
                                data.movement_detected ? "Movement Detected" : "No Movement";
                        }
                    } else {
                        // Show simulated data if hardware is not available
                        document.getElementById('temperature').textContent = "22.5°C (simulated)";
                        document.getElementById('humidity').textContent = "45.0% (simulated)";
                        document.getElementById('distance').textContent = "50.0 cm (simulated)";
                        document.getElementById('movement').textContent = "No Movement (simulated)";
                    }
                })
                .catch(error => {
                    console.error("Error fetching sensor data:", error);
                    document.getElementById('hardware-status').textContent = "Error: " + error.message;
                    
                    // Show fallback interface
                    document.getElementById('temperature').textContent = "Error loading data";
                    document.getElementById('humidity').textContent = "Error loading data";
                    document.getElementById('distance').textContent = "Error loading data";
                    document.getElementById('movement').textContent = "Error loading data";
                });
        }
        
        // Add a utility function to check if routes are accessible
        function checkEndpoints() {
            const endpoints = [
                '/hardware_status',
                '/sensor_data',
                '/test_hardware_fixed'
            ];
            
            const resultElement = document.getElementById('testResult');
            resultElement.textContent = 'Checking API endpoints...';
            
            // Check each endpoint
            const checkPromises = endpoints.map(endpoint => 
                fetch(endpoint)
                    .then(response => ({
                        endpoint,
                        status: response.status,
                        ok: response.ok
                    }))
                    .catch(error => ({
                        endpoint,
                        error: error.message,
                        ok: false
                    }))
            );
            
            // Display the results when all checks are done
            Promise.all(checkPromises)
                .then(results => {
                    let message = 'API Endpoint Status:\\n';
                    let allOk = true;
                    
                    results.forEach(result => {
                        message += `${result.endpoint}: ${result.ok ? '✓' : '✗'} ${result.status || result.error}\\n`;
                        if (!result.ok) allOk = false;
                    });
                    
                    resultElement.textContent = message;
                    resultElement.className = allOk ? 'success' : 'error';
                });
        }
        
        // Test that POST requests work correctly
        function testPostMethod() {
            const resultElement = document.getElementById('testResult');
            resultElement.textContent = 'Testing POST method...';
            resultElement.className = '';
            
            fetch('/test_hardware_fixed', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ test: 'post-method' })
            })
            .then(response => {
                resultElement.textContent = `POST test: ${response.status} ${response.statusText}`;
                resultElement.className = response.ok ? 'success' : 'error';
                return response.text();
            })
            .then(text => {
                console.log("POST test response:", text);
            })
            .catch(error => {
                resultElement.textContent = `POST test error: ${error.message}`;
                resultElement.className = 'error';
            });
        }
        
        // Refresh sensor data when page loads
        refreshSensorData();
        
        // Auto refresh every 5 seconds
        setInterval(refreshSensorData, 5000);
    </script>
</body>
</html>
"""

with open('templates/hardware_test.html', 'w') as f:
    f.write(hardware_test_html)
print("Updated hardware_test.html template")

# 7. Make sure get_sensor_data exists in interface_1.py
print("\nChecking get_sensor_data function in interface_1.py...")
with open('interface_1.py', 'r') as f:
    interface_content = f.read()

if 'def get_sensor_data():' not in interface_content:
    print("Adding get_sensor_data function to interface_1.py...")
    
    # Define the function to add
    sensor_data_func = """
# Function to get sensor data for web interface
def get_sensor_data():
    ""Get current sensor data for web interface""
    import time
    import random
    
    data = {
        "hardware_available": HARDWARE_AVAILABLE,
        "timestamp": time.time()
    }
    
    if not HARDWARE_AVAILABLE:
        # Return dummy data for testing
        data["temperature"] = random.uniform(20.0, 25.0)
        data["humidity"] = random.uniform(40.0, 60.0)
        data["distance"] = random.uniform(30.0, 100.0)
        data["movement_detected"] = random.choice([True, False])
        return data
    
    try:
        # Get temperature and humidity if available
        try:
            import Freenove_DHT as DHT
            dht = DHT.DHT(17)  # Assuming pin 17
            chk = dht.readDHT11()
            if chk == 0:
                data["temperature"] = dht.temperature
                data["humidity"] = dht.humidity
            else:
                # Use placeholder values if reading fails
                data["temperature"] = 22.5
                data["humidity"] = 45.0
        except Exception as e:
            print(f"Error reading temperature/humidity: {e}")
            data["temperature"] = 22.5
            data["humidity"] = 45.0
        
        # Get distance if available
        try:
            data["distance"] = ultrasonic.distance * 100  # Convert to cm
        except Exception as e:
            print(f"Error reading distance: {e}")
            data["distance"] = 50.0  # Default value
        
        # Get movement status
        try:
            data["movement_detected"] = not check_movement()  # Inverted for consistency
        except Exception as e:
            print(f"Error checking movement: {e}")
            data["movement_detected"] = False
        
        # Add alarm state if available
        if "alarm_active" in globals():
            data["alarm_active"] = alarm_active
            data["distance_expected"] = distance_Prevue
        
    except Exception as e:
        print(f"Error getting sensor data: {e}")
    
    return data
"""
    
    # Find a good place to insert (after the hardware initialization)
    hardware_init_pattern = r'# Initialize hardware components.*?HARDWARE_AVAILABLE = (True|False)'
    hw_init_match = re.search(hardware_init_pattern, interface_content, re.DOTALL)
    
    if hw_init_match:
        # Insert after the hardware initialization
        insert_pos = hw_init_match.end()
        interface_content = interface_content[:insert_pos] + "\n" + sensor_data_func + interface_content[insert_pos:]
    else:
        # If can't find the pattern, insert before if __name__ == '__main__':
        main_match = re.search(r'if __name__ == [\'"]__main__[\'"]:', interface_content)
        if main_match:
            insert_pos = main_match.start()
            interface_content = interface_content[:insert_pos] + sensor_data_func + "\n\n" + interface_content[insert_pos:]
        else:
            # Fallback: append to the end
            interface_content += "\n\n" + sensor_data_func
    
    with open('interface_1.py', 'w') as f:
        f.write(interface_content)
    print("Added get_sensor_data function to interface_1.py")
else:
    print("get_sensor_data function already exists in interface_1.py")

# 8. Add a hardware test link to index.html if it exists
print("\nChecking for hardware test link in index.html...")
if os.path.exists('templates/index.html'):
    with open('templates/index.html', 'r') as f:
        index_content = f.read()
    
    # Check if the link already exists
    if '/hardware_test_page' not in index_content:
        # Try to find a good place to add the link
        if '<div class="nav-links">' in index_content:
            # Add to existing nav links
            index_content = index_content.replace(
                '<div class="nav-links">',
                '<div class="nav-links">\n        <a href="/hardware_test_page">Hardware Test</a>'
            )
            with open('templates/index.html', 'w') as f:
                f.write(index_content)
            print("Added hardware test link to index.html nav links")
        elif '<header>' in index_content:
            # Add after header
            index_content = index_content.replace(
                '</header>',
                '</header>\n    <div class="nav-links">\n        <a href="/hardware_test_page">Hardware Test</a>\n    </div>'
            )
            with open('templates/index.html', 'w') as f:
                f.write(index_content)
            print("Added hardware test link to index.html after header")
        else:
            print("Couldn't find a suitable place to add hardware test link in index.html")
    else:
        print("Hardware test link already exists in index.html")
else:
    print("index.html doesn't exist, creating a basic one with hardware test link")
    
    # Create a simple index.html
    index_html = """<!DOCTYPE html>
<html>
<head>
    <title>Alarm System</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #121212;
            color: #FFFFFF;
        }
        
        h1, h2 {
            color: #BB86FC;
        }
        
        .nav-links {
            margin: 20px 0;
        }
        
        .nav-links a {
            color: #BB86FC;
            margin-right: 15px;
            text-decoration: none;
        }
        
        .nav-links a:hover {
            text-decoration: underline;
        }
        
        .panel {
            background-color: #1E1E1E;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <header>
        <h1>Alarm System</h1>
    </header>
    
    <div class="nav-links">
        <a href="/">Home</a>
        <a href="/hardware_test_page">Hardware Test</a>
    </div>
    
    <div class="panel">
        <h2>Alarm System Controls</h2>
        <p>Use the navigation links above to access different parts of the system.</p>
    </div>
</body>
</html>
"""
    with open('templates/index.html', 'w') as f:
        f.write(index_html)
    print("Created basic index.html with hardware test link")

print("\nSetup complete! Now run the application with ./launch.sh")