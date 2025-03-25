// MQTT client
let mqttClient = null;
let alarmNotificationShown = false;
let hardwareAvailable = false;
let sensorUpdateInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const statusSpan = document.getElementById('status');
    const outputElement = document.getElementById('output');
    const hourSelect = document.getElementById('hourSelect');
    const minuteSelect = document.getElementById('minuteSelect');
    const secondSelect = document.getElementById('secondSelect');
    const addAlarmBtn = document.getElementById('addAlarmBtn');
    const alarmList = document.getElementById('alarmList');
    
    // Initialize time selectors
    initTimeSelectors();
    
    // Try to connect to MQTT
    initializeMQTT();
    
    // Add alarm button handler
    addAlarmBtn.addEventListener('click', function() {
        const hour = hourSelect.value;
        const minute = minuteSelect.value;
        const second = secondSelect.value;
        
        if (mqttClient && mqttClient.isConnected()) {
            console.log(`Adding alarm via MQTT: ${hour}:${minute}:${second}`);
            
            // Create and send the MQTT message
            const payload = JSON.stringify({
                hour: hour,
                minute: minute,
                second: second
            });
            const message = new Paho.MQTT.Message(payload);
            message.destinationName = 'alarm/request/add';
            mqttClient.send(message);
            
            appendOutput(`Requesting to add alarm at ${hour}:${minute}:${second}`);
        } else {
            console.log("MQTT client not connected, using HTTP fallback");
            // Fallback to HTTP
            fetch('/alarm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    hour: hour,
                    minute: minute,
                    second: second
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    appendOutput(`Alarm set for ${hour}:${minute}:${second}`);
                    loadAlarms(); // Refresh alarm list
                } else {
                    appendOutput(`Error: ${data.message}`);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                appendOutput(`Error adding alarm: ${error.message}`);
            });
        }
    });
    
    // Add refresh button functionality
    const refreshAlarmsBtn = document.getElementById('refreshAlarmsBtn');
    if (refreshAlarmsBtn) {
        refreshAlarmsBtn.addEventListener('click', function() {
            refreshAlarmsBtn.classList.add('refreshing');
            
            if (mqttClient && mqttClient.isConnected()) {
                // Create and send MQTT message
                const message = new Paho.MQTT.Message('{}');
                message.destinationName = 'alarm/request/list';
                mqttClient.send(message);
                
                appendOutput("Requesting updated alarm list via MQTT");
            } else {
                loadAlarms(); // Use HTTP fallback
                appendOutput("Requesting updated alarm list via HTTP");
            }
            
            setTimeout(() => {
                refreshAlarmsBtn.classList.remove('refreshing');
            }, 1000);
        });
    }
    
    // Initialize hardware availability check
    checkHardwareAvailability();

    // Add event listeners for hardware test buttons
    document.getElementById('testLED').addEventListener('click', function() {
        testHardware('led', 'on');
    });

    document.getElementById('testServo').addEventListener('click', function() {
        testHardware('servo', 'sweep');
    });

    document.getElementById('testBuzzer').addEventListener('click', function() {
        testHardware('buzzer', 'on');
    });
});

function initializeMQTT() {
    console.log("Initializing MQTT connection...");
    appendOutput("Connecting to MQTT broker...");
    
    try {
        // Create a client ID with a random suffix
        const clientId = "web_client_" + Math.random().toString(16).substring(2, 10);
        
        // Get the current hostname for the broker (same as web server)
        const hostname = window.location.hostname;
        
        // For WebSockets, we use port 9001
        console.log(`Connecting to ${hostname}:9001 via WebSockets`);
        
        // Create the client instance
        mqttClient = new Paho.MQTT.Client(hostname, 9001, clientId);
        
        // Set up the callbacks
        mqttClient.onConnectionLost = function(responseObject) {
            if (responseObject.errorCode !== 0) {
                console.log("Connection lost: " + responseObject.errorMessage);
                appendOutput(`MQTT connection lost: ${responseObject.errorMessage}`);
                
                // Get status element safely
                const statusSpan = document.getElementById('status');
                if (statusSpan) {
                    statusSpan.textContent = "Disconnected";
                    statusSpan.className = "stopped";
                }
                
                // Try to reconnect after a delay
                setTimeout(function() {
                    appendOutput("Attempting to reconnect...");
                    initializeMQTT();
                }, 5000);
            }
        };
        
        mqttClient.onMessageArrived = function(message) {
            const topic = message.destinationName;
            console.log(`Message received on topic ${topic}: ${message.payloadString}`);
            
            let payload;
            try {
                payload = JSON.parse(message.payloadString);
            } catch (e) {
                console.error("Failed to parse message as JSON:", e);
                payload = message.payloadString;
            }
            
            // Process different message types
            switch(topic) {
                case "alarm/list":
                    console.log("Received alarm list:", payload);
                    if (Array.isArray(payload)) {
                        updateAlarmList(payload);
                        appendOutput(`Updated alarm list: ${payload.length} alarms`);
                    } else {
                        console.error("Received invalid alarm list:", payload);
                    }
                    break;
                    
                case "alarm/added":
                    appendOutput(payload.message || "Alarm added");
                    // Request updated list
                    const listRequestMsg = new Paho.MQTT.Message("{}");
                    listRequestMsg.destinationName = "alarm/request/list";
                    mqttClient.send(listRequestMsg);
                    break;
                    
                case "alarm/deleted":
                    appendOutput(payload.message || "Alarm deleted");
                    // Request updated list
                    const deleteListMsg = new Paho.MQTT.Message("{}");
                    deleteListMsg.destinationName = "alarm/request/list";
                    mqttClient.send(deleteListMsg);
                    break;
                    
                case "alarm/toggled":
                    appendOutput(payload.message || "Alarm toggled");
                    // Request updated list
                    const toggleListMsg = new Paho.MQTT.Message("{}");
                    toggleListMsg.destinationName = "alarm/request/list";
                    mqttClient.send(toggleListMsg);
                    break;
                    
                case "alarm/state":
                    handleAlarmState(payload);
                    break;
                    
                case "alarm/output":
                    appendOutput(typeof payload === "string" ? payload : payload.message || "Output received");
                    break;
                    
                case "alarm/error":
                    appendOutput(`Error: ${typeof payload === "string" ? payload : payload.message || "Unknown error"}`);
                    break;
                    
                default:
                    console.log(`Unhandled topic: ${topic}`, payload);
            }
        };
        
        // Connect
        appendOutput(`Connecting to MQTT broker at ${hostname}:9001...`);
        mqttClient.connect({
            onSuccess: function() {
                console.log("Connected to MQTT broker!");
                appendOutput("Successfully connected to MQTT broker");
                
                // Get status element safely
                const statusSpan = document.getElementById('status');
                if (statusSpan) {
                    statusSpan.textContent = "Connected";
                    statusSpan.className = "running";
                }
                
                // Subscribe to topics
                mqttClient.subscribe("alarm/list");
                mqttClient.subscribe("alarm/added");
                mqttClient.subscribe("alarm/deleted");
                mqttClient.subscribe("alarm/toggled");
                mqttClient.subscribe("alarm/state");
                mqttClient.subscribe("alarm/output");
                mqttClient.subscribe("alarm/error");
                
                // Request current alarm list
                const listMsg = new Paho.MQTT.Message("{}");
                listMsg.destinationName = "alarm/request/list";
                mqttClient.send(listMsg);
            },
            onFailure: function(responseObject) {
                console.error("Failed to connect to MQTT broker:", responseObject.errorMessage);
                appendOutput(`Failed to connect to MQTT broker: ${responseObject.errorMessage}`);
                
                // Get status element safely
                const statusSpan = document.getElementById('status');
                if (statusSpan) {
                    statusSpan.textContent = "Disconnected";
                    statusSpan.className = "stopped";
                }
                
                // Fall back to HTTP polling
                startHttpPolling();
            },
            useSSL: window.location.protocol === 'https:',
            timeout: 10  // 10 seconds
        });
        
    } catch (error) {
        console.error("Error setting up MQTT client:", error);
        appendOutput(`Error setting up MQTT client: ${error.message}`);
        
        // Fall back to HTTP polling
        startHttpPolling();
    }
}

function startHttpPolling() {
    console.log("Starting HTTP polling as fallback");
    appendOutput("Starting HTTP polling as fallback");
    
    // Update alarm list every 5 seconds
    setInterval(loadAlarms, 5000);
    
    // Check alarm state every second
    setInterval(checkAlarmState, 1000);
    
    // Get output every 500ms
    setInterval(pollOutput, 500);
}

// Load alarms via HTTP
function loadAlarms() {
    fetch('/alarms')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateAlarmList(data.alarms);
            } else {
                console.error("Error loading alarms:", data.message);
                appendOutput(`Error loading alarms: ${data.message}`);
            }
        })
        .catch(error => {
            console.error("Error loading alarms:", error);
            appendOutput(`Error loading alarms: ${error.message}`);
        });
}

// Check alarm state via HTTP
function checkAlarmState() {
    fetch('/alarm_state')
        .then(response => response.json())
        .then(data => {
            handleAlarmState(data);
        })
        .catch(error => {
            console.error("Error checking alarm state:", error);
        });
}

// Poll for script output via HTTP
function pollOutput() {
    fetch('/output')
        .then(response => response.json())
        .then(data => {
            if (data.output && data.output.length > 0) {
                data.output.forEach(line => {
                    appendOutput(line);
                });
            }
        })
        .catch(error => {
            console.error("Error polling output:", error);
        });
}

// Handle alarm state changes
function handleAlarmState(state) {
    if (state.alarm_active) {
        if (!alarmNotificationShown) {
            showAlarmNotification(state.message || "Alarm activated");
        }
    } else {
        if (alarmNotificationShown) {
            hideAlarmNotification();
        }
    }
}

// Delete alarm
function deleteAlarm(index) {
    if (mqttClient && mqttClient.isConnected()) {
        // Use MQTT
        const payload = JSON.stringify({
            index: index
        });
        const message = new Paho.MQTT.Message(payload);
        message.destinationName = 'alarm/request/delete';
        mqttClient.send(message);
        
        appendOutput(`Requesting to delete alarm at index ${index}`);
    } else {
        // Use HTTP fallback
        fetch(`/alarm/${index}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                appendOutput(data.message || `Deleted alarm at index ${index}`);
                loadAlarms();
            } else {
                appendOutput(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            appendOutput(`Error deleting alarm: ${error.message}`);
        });
    }
}

// Toggle alarm
function toggleAlarm(index) {
    // Visual feedback immediately
    const row = document.querySelector(`#alarmList tr:nth-child(${index + 1})`);
    if (row) {
        row.classList.add('refreshing');
    }
    
    if (mqttClient && mqttClient.isConnected()) {
        // Use MQTT
        const payload = JSON.stringify({
            index: index
        });
        const message = new Paho.MQTT.Message(payload);
        message.destinationName = 'alarm/request/toggle';
        mqttClient.send(message);
        
        appendOutput(`Requesting to toggle alarm at index ${index}`);
    } else {
        // Use HTTP fallback
        fetch(`/alarm/${index}/toggle`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                appendOutput(data.message || `Toggled alarm at index ${index}`);
                loadAlarms();
            } else {
                appendOutput(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            appendOutput(`Error toggling alarm: ${error.message}`);
        });
    }
    
    // Remove visual feedback after a delay
    setTimeout(() => {
        if (row) {
            row.classList.remove('refreshing');
        }
    }, 1000);
}

// Initialize time selectors
function initTimeSelectors() {
    const hourSelect = document.getElementById('hourSelect');
    const minuteSelect = document.getElementById('minuteSelect');
    const secondSelect = document.getElementById('secondSelect');
    
    if (!hourSelect || !minuteSelect || !secondSelect) return;
    
    // Clear existing options
    hourSelect.innerHTML = '';
    minuteSelect.innerHTML = '';
    secondSelect.innerHTML = '';
    
    // Hours
    for (let i = 0; i < 24; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.textContent = i.toString().padStart(2, '0');
        hourSelect.appendChild(option);
    }
    
    // Minutes and seconds
    for (let i = 0; i < 60; i++) {
        const minuteOption = document.createElement('option');
        minuteOption.value = i;
        minuteOption.textContent = i.toString().padStart(2, '0');
        minuteSelect.appendChild(minuteOption);
        
        const secondOption = document.createElement('option');
        secondOption.value = i;
        secondOption.textContent = i.toString().padStart(2, '0');
        secondSelect.appendChild(secondOption);
    }
}

// Update the alarm list in the UI
function updateAlarmList(alarms) {
    const alarmList = document.getElementById('alarmList');
    if (!alarmList) return;
    
    // Clear the current list
    alarmList.innerHTML = '';
    
    // Add each alarm
    alarms.forEach((alarm, index) => {
        const row = document.createElement('tr');
        
        // Time column
        const timeCell = document.createElement('td');
        timeCell.textContent = alarm.time;
        row.appendChild(timeCell);
        
        // Status column
        const statusCell = document.createElement('td');
        statusCell.textContent = alarm.active ? 'Active' : 'Inactive';
        statusCell.className = alarm.active ? 'status-active' : 'status-inactive';
        row.appendChild(statusCell);
        
        // Actions column
        const actionsCell = document.createElement('td');
        
        // Toggle button
        const toggleBtn = document.createElement('button');
        toggleBtn.textContent = alarm.active ? '🔕' : '🔔';
        toggleBtn.title = alarm.active ? 'Disable' : 'Enable';
        toggleBtn.className = 'btn btn-sm ' + (alarm.active ? 'btn-success' : 'btn-secondary');
        toggleBtn.onclick = function() { toggleAlarm(index); };
        actionsCell.appendChild(toggleBtn);
        
        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = '🗑️';
        deleteBtn.title = 'Delete';
        deleteBtn.className = 'btn btn-danger btn-sm';
        deleteBtn.style.marginLeft = '5px';
        deleteBtn.onclick = function() { deleteAlarm(index); };
        actionsCell.appendChild(deleteBtn);
        
        row.appendChild(actionsCell);
        alarmList.appendChild(row);
    });
}

// Show alarm notification
function showAlarmNotification(message) {
    if (alarmNotificationShown) return;
    
    alarmNotificationShown = true;
    
    const overlay = document.createElement('div');
    overlay.className = 'alarm-notification-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.backgroundColor = 'rgba(255, 0, 0, 0.8)';
    overlay.style.display = 'flex';
    overlay.style.flexDirection = 'column';
    overlay.style.justifyContent = 'center';
    overlay.style.alignItems = 'center';
    overlay.style.zIndex = '9999';
    
    const messageEl = document.createElement('h1');
    messageEl.textContent = '🔔 ALARM! 🔔';
    messageEl.style.color = 'white';
    messageEl.style.fontSize = '3rem';
    overlay.appendChild(messageEl);
    
    const detailsEl = document.createElement('p');
    detailsEl.textContent = message;
    detailsEl.style.color = 'white';
    detailsEl.style.fontSize = '1.5rem';
    overlay.appendChild(detailsEl);
    
    const snoozeBtn = document.createElement('button');
    snoozeBtn.textContent = 'Snooze';
    snoozeBtn.className = 'btn btn-primary';
    snoozeBtn.style.marginTop = '20px';
    snoozeBtn.style.padding = '10px 20px';
    snoozeBtn.style.fontSize = '1.2rem';
    snoozeBtn.onclick = snoozeAlarm;
    overlay.appendChild(snoozeBtn);
    
    document.body.appendChild(overlay);
}

function hideAlarmNotification() {
    const overlay = document.querySelector('.alarm-notification-overlay');
    if (overlay) {
        document.body.removeChild(overlay);
    }
    alarmNotificationShown = false;
}

// Snooze the alarm
function snoozeAlarm() {
    if (mqttClient && mqttClient.isConnected()) {
        // Use MQTT
        const message = new Paho.MQTT.Message('{}');
        message.destinationName = 'alarm/request/snooze';
        mqttClient.send(message);
        
        appendOutput('Requesting to snooze alarm via MQTT');
    } else {
        // Use HTTP fallback
        fetch('/snooze', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                appendOutput('Alarm snoozed');
            } else {
                appendOutput(`Error: ${data.message}`);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            appendOutput(`Error snoozing alarm: ${error.message}`);
        });
    }
    
    // Hide the notification immediately for better UX
    hideAlarmNotification();
}

// Add to output log
function appendOutput(text) {
    const outputElement = document.getElementById('output');
    if (!outputElement) return;
    
    const timestamp = new Date().toLocaleTimeString();
    outputElement.textContent += `[${timestamp}] ${text}\n`;
    
    // Auto-scroll to bottom
    const outputContainer = outputElement.parentElement;
    outputContainer.scrollTop = outputContainer.scrollHeight;
}

// Check if hardware is available when page loads
function checkHardwareAvailability() {
    fetch('/hardware_status')
        .then(response => response.json())
        .then(data => {
            hardwareAvailable = data.hardware_available;
            if (hardwareAvailable) {
                console.log("Hardware interface available, enabling sensor display");
                document.getElementById('sensorPanel').style.display = 'block';
                document.getElementById('hardwareTestPanel').style.display = 'block';
                // Start polling sensor data
                updateSensorData();
                sensorUpdateInterval = setInterval(updateSensorData, 2000);
            } else {
                console.log("Hardware interface not available");
                document.getElementById('sensorPanel').style.display = 'none';
                document.getElementById('hardwareTestPanel').style.display = 'none';
            }
        })
        .catch(error => {
            console.error("Error checking hardware availability:", error);
        });
}

// Poll sensor data from the backend
function updateSensorData() {
    fetch('/sensor_data')
        .then(response => response.json())
        .then(data => {
            if (data.hardware_available) {
                // Update temperature and humidity
                if ('temperature' in data) {
                    document.getElementById('temperature').textContent = `${data.temperature.toFixed(1)}°C`;
                }
                if ('humidity' in data) {
                    document.getElementById('humidity').textContent = `${data.humidity.toFixed(1)}%`;
                }
                
                // Update distance if alarm is active
                if (data.alarm_active && 'distance' in data) {
                    const distanceElement = document.getElementById('distance');
                    const distanceStatus = document.getElementById('distanceStatus');
                    
                    distanceElement.textContent = `${data.distance.toFixed(1)} cm`;
                    
                    if (data.distance_expected) {
                        const diff = Math.abs(data.distance - data.distance_expected);
                        if (diff <= 10) {
                            distanceStatus.textContent = "Good distance!";
                            distanceStatus.className = "status-good";
                        } else if (data.distance < data.distance_expected) {
                            distanceStatus.textContent = "Too close!";
                            distanceStatus.className = "status-warning";
                        } else {
                            distanceStatus.textContent = "Too far!";
                            distanceStatus.className = "status-warning";
                        }
                    }
                    
                    document.getElementById('distanceContainer').style.display = 'block';
                } else {
                    document.getElementById('distanceContainer').style.display = 'none';
                }
                
                // Update movement status
                if ('movement_detected' in data) {
                    const movementElement = document.getElementById('movement');
                    if (data.movement_detected) {
                        movementElement.textContent = "Movement detected!";
                        movementElement.className = "status-warning";
                    } else {
                        movementElement.textContent = "No movement";
                        movementElement.className = "status-good";
                    }
                }
            }
        })
        .catch(error => {
            console.error("Error updating sensor data:", error);
        });
}

// Function to test hardware components with proper error handling
function testHardware(component, action) {
    const resultElement = document.getElementById('testResult');
    if (resultElement) {
        resultElement.textContent = `Testing ${component}...`;
        resultElement.className = '';
    }
    
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
    .then(response => {
        // First check if the response is OK
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (!resultElement) return;
        
        if (data.status === 'success') {
            resultElement.textContent = data.message;
            resultElement.className = 'text-success';
        } else {
            resultElement.textContent = data.message;
            resultElement.className = 'text-danger';
        }
    })
    .catch(error => {
        if (!resultElement) return;
        
        resultElement.textContent = `Error: ${error.message}`;
        resultElement.className = 'text-danger';
        console.error("Hardware test error:", error);
    });
}

fetch('/test_hardware_fixed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ component: 'led', action: 'on' })
});