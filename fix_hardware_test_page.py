import os

# Check if the hardware_test_page route exists in app.py
with open('app.py', 'r') as f:
    content = f.read()

if '/hardware_test_page' not in content:
    # Route is missing, add it
    new_route = """
@app.route('/hardware_test_page')
def hardware_test_page():
    \"\"\"Hardware test interface\"\"\"
    return render_template('hardware_test.html')
"""
    
    # Find where to insert - before if __name__ block
    import re
    main_block_match = re.search(r'if __name__ == [\'"]__main__[\'"]:.*$', content, re.DOTALL)
    if main_block_match:
        insert_pos = main_block_match.start()
        content = content[:insert_pos] + new_route + content[insert_pos:]
        
        # Write back to app.py
        with open('app.py', 'w') as f:
            f.write(content)
        print("Added hardware_test_page route")
    else:
        print("Could not find if __name__ == '__main__' block")
else:
    print("hardware_test_page route already exists")

# Ensure the templates directory exists
if not os.path.exists('templates'):
    os.makedirs('templates')
    print("Created templates directory")

# Fix the hardware_test.html file to support the API correctly
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
        <a href="/mqtt_test">MQTT Test</a>
        <a href="/websocket_test">WebSocket Test</a>
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
        
        // Add check endpoints button when page loads
        document.addEventListener('DOMContentLoaded', function() {
            const panel = document.querySelector('.panel');
            const button = document.createElement('button');
            button.textContent = 'Check API Endpoints';
            button.onclick = checkEndpoints;
            button.style.marginTop = '10px';
            panel.appendChild(button);
            
            // Show POST test button - helpful for debugging 405 errors
            const postTestButton = document.createElement('button');
            postTestButton.textContent = 'Test POST Method';
            postTestButton.onclick = testPostMethod;
            postTestButton.style.marginTop = '10px';
            postTestButton.style.marginLeft = '10px';
            panel.appendChild(postTestButton);
        });
        
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

# Write hardware_test.html to the templates directory
with open('templates/hardware_test.html', 'w') as f:
    f.write(hardware_test_html)
print("Updated hardware_test.html template")

# Update index.html to include a link to the hardware test page
if os.path.exists('templates/index.html'):
    with open('templates/index.html', 'r') as f:
        index_content = f.read()
    
    # Check if the hardware test link already exists
    if '/hardware_test_page' not in index_content:
        # Try to find a good place to add the link
        if '<div class="hardware-links">' in index_content:
            index_content = index_content.replace(
                '<div class="hardware-links">',
                '<div class="hardware-links">\n                <a href="/hardware_test_page">Hardware Test</a>'
            )
            
            with open('templates/index.html', 'w') as f:
                f.write(index_content)
            print("Added hardware test link to index.html")
        else:
            print("Couldn't find a place to add the hardware test link in index.html")
    else:
        print("Hardware test link already exists in index.html")
else:
    print("index.html doesn't exist, skipping link addition")

print("Hardware test page setup completed")