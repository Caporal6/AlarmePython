// hardware.js - Enhanced hardware communication for the web client
// Add this file to your static/js folder and include it in your HTML

let hardwareAvailable = false;
let mqttHardwareClient = null;
let sensorUpdateInterval = null;
let sensorData = {
    temperature: null,
    humidity: null,
    distance: null,
    movement_detected: false,
    timestamp: 0
};

document.addEventListener('DOMContentLoaded', function() {
    // Check hardware availability on page load
    checkHardwareAvailability();
    
    // Set up hardware test buttons
    setupHardwareButtons();
    
    // Try to connect to MQTT for hardware control
    initializeHardwareMQTT();
});

function checkHardwareAvailability() {
    console.log("Checking hardware availability...");
    
    fetch('/hardware_status')
        .then(response => response.json())
        .then(data => {
            hardwareAvailable = data.hardware_available;
            updateHardwareUI(data);
            
            if (hardwareAvailable) {
                console.log("Hardware is available:", data.components);
                startSensorUpdates();
            } else {
                console.log("Hardware is not available");
                showSimulatedData();
            }
        })
        .catch(error => {
            console.error("Error checking hardware availability:", error);
            showHardwareError(error);
        });
}

function updateHardwareUI(data) {
    // Update UI elements based on hardware availability
    const sensorPanel = document.getElementById('sensorPanel');
    const hardwareTestPanel = document.getElementById('hardwareTestPanel');
    
    if (sensorPanel) {
        sensorPanel.style.display = hardwareAvailable ? 'block' : 'none';
        
        // Add a simulation notice if needed
        if (!hardwareAvailable && sensorPanel.style.display !== 'none') {
            const simNotice = document.createElement('div');
            simNotice.className = 'simulation-notice';
            simNotice.textContent = 'Running in simulation mode';
            simNotice.style.color = '#FF9800';
            simNotice.style.fontStyle = 'italic';
            simNotice.style.marginBottom = '10px';
            sensorPanel.prepend(simNotice);
        }
    }
    
    if (hardwareTestPanel) {
        hardwareTestPanel.style.display = hardwareAvailable ? 'block' : 'none';
        
        // Add available components info
        if (hardwareAvailable && data.components) {
            const componentsDiv = document.createElement('div');
            componentsDiv.className = 'available-components';
            componentsDiv.innerHTML = `<small>Available: ${data.components.join(', ')}</small>`;
            componentsDiv.style.color = '#03DAC6';
            hardwareTestPanel.appendChild(componentsDiv);
        }
    }
}

function setupHardwareButtons() {
    // LED test button
    const testLEDBtn = document.getElementById('testLED');
    if (testLEDBtn) {
        testLEDBtn.addEventListener('click', function() {
            testHardwareComponent('led', 'on');
        });
    }
    
    // Servo test button
    const testServoBtn = document.getElementById('testServo');
    if (testServoBtn) {
        testServoBtn.addEventListener('click', function() {
            testHardwareComponent('servo', 'sweep');
        });
    }
    
    // Buzzer test button
    const testBuzzerBtn = document.getElementById('testBuzzer');
    if (testBuzzerBtn) {
        testBuzzerBtn.addEventListener('click', function() {
            testHardwareComponent('buzzer', 'on');
        });
    }
}

function testHardwareComponent(component, action) {
    console.log(`Testing hardware component: ${component} (${action})`);
    
    // Update UI to show testing in progress
    const testResult = document.getElementById('testResult');
    if (testResult) {
        testResult.textContent = `Testing ${component}...`;
        testResult.className = '';
    }
    
    // Try MQTT first if available
    if (mqttHardwareClient && mqttHardwareClient.isConnected()) {
        console.log("Using MQTT for hardware test");
        
        // Set up a one-time response handler
        const responseHandler = function(message) {
            try {
                const response = JSON.parse(message.payloadString);
                
                if (testResult) {
                    testResult.textContent = response.message;
                    testResult.className = response.status === 'success' ? 'success' : 'error';
                }
                
                // Unsubscribe after receiving the response
                mqttHardwareClient.unsubscribe("alarm/hardware/response");
            } catch (e) {
                console.error("Error handling hardware response:", e);
                if (testResult) {
                    testResult.textContent = "Error processing response";
                    testResult.className = 'error';
                }
            }
        };
        
        // Subscribe to response topic
        mqttHardwareClient.subscribe("alarm/hardware/response");
        mqttHardwareClient.onMessageArrived = responseHandler;
        
        // Send the request
        const payload = JSON.stringify({
            component: component,
            action: action
        });
        const message = new Paho.MQTT.Message(payload);
        message.destinationName = 'alarm/request/hardware';
        mqttHardwareClient.send(message);
    } 
    // Fall back to HTTP API
    else {
        console.log("Using HTTP for hardware test");
        
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
            if (testResult) {
                testResult.textContent = data.message;
                testResult.className = data.status === 'success' ? 'success' : 'error';
            }
        })
        .catch(error => {
            console.error("Error testing hardware:", error);
            if (testResult) {
                testResult.textContent = `Error: ${error.message}`;
                testResult.className = 'error';
            }
            
            // Try alternative endpoint as fallback
            fetch('/test_hardware_fixed', {
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
                if (testResult) {
                    testResult.textContent = data.message + " (fallback)";
                    testResult.className = data.status === 'success' ? 'success' : 'error';
                }
            })
            .catch(fallbackError => {
                console.error("Fallback error:", fallbackError);
                if (testResult) {
                    testResult.textContent = `All attempts failed`;
                    testResult.className = 'error';
                }
            });
        });
    }
}

function initializeHardwareMQTT() {
    console.log("Initializing hardware MQTT connection...");
    
    try {
        // Create a unique client ID
        const clientId = "hw_client_" + Math.random().toString(16).substring(2, 10);
        
        // Get the current hostname
        const hostname = window.location.hostname;
        
        // Create client
        mqttHardwareClient = new Paho.MQTT.Client(hostname, 9001, clientId);
        
        // Set callbacks
        mqttHardwareClient.onConnectionLost = function(responseObject) {
            if (responseObject.errorCode !== 0) {
                console.log("Hardware MQTT connection lost:", responseObject.errorMessage);
                
                // Try to reconnect after a delay
                setTimeout(function() {
                    console.log("Attempting to reconnect hardware MQTT...");
                    initializeHardwareMQTT();
                }, 5000);
            }
        };
        
        mqttHardwareClient.onMessageArrived = function(message) {
            const topic = message.destinationName;
            
            if (topic === "alarm/sensor/data") {
                try {
                    const data = JSON.parse(message.payloadString);
                    updateSensorDisplay(data);
                    sensorData = data;
                } catch (e) {
                    console.error("Error processing sensor data:", e);
                }
            }
        };
        
        // Connect
        mqttHardwareClient.connect({
            onSuccess: function() {
                console.log("Connected to hardware MQTT broker");
                
                // Subscribe to sensor data topic
                mqttHardwareClient.subscribe("alarm/sensor/data");
                
                // Request initial sensor data
                requestSensorDataMQTT();
            },
            onFailure: function(responseObject) {
                console.error("Failed to connect to hardware MQTT broker:", responseObject.errorMessage);
                
                // Fall back to HTTP polling
                startSensorUpdates();
            },
            useSSL: window.location.protocol === 'https:',
            timeout: 10  // 10 seconds
        });
        
    } catch (error) {
        console.error("Error setting up hardware MQTT client:", error);
        
        // Fall back to HTTP polling
        startSensorUpdates();
    }
}

function requestSensorDataMQTT() {
    if (mqttHardwareClient && mqttHardwareClient.isConnected()) {
        const message = new Paho.MQTT.Message('{}');
        message.destinationName = 'alarm/request/sensor';
        mqttHardwareClient.send(message);
    }
}

function startSensorUpdates() {
    // Clear any existing interval
    if (sensorUpdateInterval) {
        clearInterval(sensorUpdateInterval);
    }
    
    // Initial update
    updateSensorData();
    
    // Set up regular updates
    sensorUpdateInterval = setInterval(updateSensorData, 2000);
}

function updateSensorData() {
    // If we have MQTT connection, use that instead
    if (mqttHardwareClient && mqttHardwareClient.isConnected()) {
        requestSensorDataMQTT();
        return;
    }
    
    // Fallback to HTTP
    fetch('/sensor_data')
        .then(response => response.json())
        .then(data => {
            updateSensorDisplay(data);
            sensorData = data;
        })
        .catch(error => {
            console.error("Error fetching sensor data:", error);
            showSensorError(error);
        });
}

function updateSensorDisplay(data) {
    // Update temperature
    const tempElement = document.getElementById('temperature');
    if (tempElement && 'temperature' in data) {
        tempElement.textContent = `${data.temperature.toFixed(1)}°C`;
        if (data.simulated || data.simulated_temp_humidity) {
            tempElement.textContent += ' (sim)';
        }
    }
    
    // Update humidity
    const humidityElement = document.getElementById('humidity');
    if (humidityElement && 'humidity' in data) {
        humidityElement.textContent = `${data.humidity.toFixed(1)}%`;
        if (data.simulated || data.simulated_temp_humidity) {
            humidityElement.textContent += ' (sim)';
        }
    }
    
    // Update distance
    const distanceElement = document.getElementById('distance');
    if (distanceElement && 'distance' in data) {
        distanceElement.textContent = `${data.distance.toFixed(1)} cm`;
        if (data.simulated || data.simulated_distance) {
            distanceElement.textContent += ' (sim)';
        }
    }
    
    // Update movement status
    const movementElement = document.getElementById('movement');
    if (movementElement && 'movement_detected' in data) {
        if (data.movement_detected) {
            movementElement.textContent = "Movement detected!";
            movementElement.className = "sensor-value warning";
        } else {
            movementElement.textContent = "No movement";
            movementElement.className = "sensor-value";
        }
        
        if (data.simulated || data.simulated_movement) {
            movementElement.textContent += ' (sim)';
        }
    }
    
    // Update distance container visibility based on alarm state
    const distanceContainer = document.getElementById('distanceContainer');
    if (distanceContainer) {
        distanceContainer.style.display = data.alarm_active ? 'block' : 'none';
    }
}

function showSimulatedData() {
    const simData = {
        hardware_available: false,
        temperature: 22.5,
        humidity: 45.0,
        distance: 50.0,
        movement_detected: false,
        simulated: true,
        timestamp: Date.now() / 1000
    };
    
    updateSensorDisplay(simData);
    
    // Show simulation message
    const sensorPanel = document.getElementById('sensorPanel');
    if (sensorPanel) {
        sensorPanel.style.display = 'block';  // Show it anyway in simulation mode
        
        // Add simulation notice if it doesn't exist
        if (!document.querySelector('.simulation-notice')) {
            const simNotice = document.createElement('div');
            simNotice.className = 'simulation-notice';
            simNotice.textContent = 'Running in simulation mode (hardware not detected)';
            simNotice.style.color = '#FF9800';
            simNotice.style.fontStyle = 'italic';
            simNotice.style.marginBottom = '10px';
            sensorPanel.prepend(simNotice);
        }
    }
}

function showHardwareError(error) {
    console.error("Hardware error:", error);
    
    // Show error in sensor panel
    const sensorPanel = document.getElementById('sensorPanel');
    if (sensorPanel) {
        sensorPanel.style.display = 'block';
        
        // Add error notice
        const errorNotice = document.createElement('div');
        errorNotice.className = 'error-notice';
        errorNotice.textContent = `Hardware Error: ${error.message}`;
        errorNotice.style.color = '#CF6679';
        errorNotice.style.fontWeight = 'bold';
        errorNotice.style.marginBottom = '10px';
        sensorPanel.prepend(errorNotice);
    }
    
    // Disable hardware test buttons
    const hardwareTestPanel = document.getElementById('hardwareTestPanel');
    if (hardwareTestPanel) {
        hardwareTestPanel.style.display = 'none';
    }
}

function showSensorError(error) {
    // Show error in sensor values
    const elements = ['temperature', 'humidity', 'distance', 'movement'];
    elements.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = 'Error';
            element.className = 'sensor-value error';
        }
    });
}
