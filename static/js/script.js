document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusSpan = document.getElementById('status');
    const outputElement = document.getElementById('output');
    const hourSelect = document.getElementById('hourSelect');
    const minuteSelect = document.getElementById('minuteSelect');
    const secondSelect = document.getElementById('secondSelect');
    const addAlarmBtn = document.getElementById('addAlarmBtn');
    const alarmList = document.getElementById('alarmList');
    
    let outputPollInterval = null;
    let alarmPollInterval = null;
    let alarmStateInterval = null;
    let statusPollInterval = null;
    
    // Initialize time selectors
    initTimeSelectors();
    
    // Load alarms on page load
    loadAlarms();
    
    // Start the script
    startBtn.addEventListener('click', function() {
        fetch('/start', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                    statusSpan.textContent = 'En cours d\'exécution';
                    statusSpan.className = 'running';
                    
                    // Start polling for output
                    if (!outputPollInterval) {
                        outputPollInterval = setInterval(pollOutput, 500);
                    }
                    
                    // Start polling for alarms
                    if (!alarmPollInterval) {
                        alarmPollInterval = setInterval(loadAlarms, 5000);
                    }
                } else {
                    alert('Erreur: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Une erreur est survenue lors du démarrage du script');
            });
    });
    
    // Stop the script
    stopBtn.addEventListener('click', function() {
        fetch('/stop', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    statusSpan.textContent = 'Arrêté';
                    statusSpan.className = '';
                    
                    // Stop polling
                    if (outputPollInterval) {
                        clearInterval(outputPollInterval);
                        outputPollInterval = null;
                    }
                    
                    if (alarmPollInterval) {
                        clearInterval(alarmPollInterval);
                        alarmPollInterval = null;
                    }
                } else {
                    alert('Erreur: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Une erreur est survenue lors de l\'arrêt du script');
            });
    });
    
    // Add alarm
    addAlarmBtn.addEventListener('click', function() {
        const hour = hourSelect.value;
        const minute = minuteSelect.value;
        const second = secondSelect.value;
        
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
                loadAlarms(); // Refresh alarm list
                appendOutput(`Alarm set for ${hour}:${minute}:${second}`);
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while setting the alarm');
        });
    });
    
    // Delete alarm
    function deleteAlarm(index) {
        fetch(`/alarm/${index}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                loadAlarms(); // Refresh alarm list
                appendOutput(data.output);
            } else {
                alert('Error: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while deleting the alarm');
        });
    }
    
    // Initialize time selectors
    function initTimeSelectors() {
        // Hours
        for (let i = 0; i < 24; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = i.toString().padStart(2, '0');
            hourSelect.appendChild(option);
        }
        
        // Minutes
        for (let i = 0; i < 60; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = i.toString().padStart(2, '0');
            minuteSelect.appendChild(option);
        }
        
        // Seconds
        for (let i = 0; i < 60; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = i.toString().padStart(2, '0');
            secondSelect.appendChild(option);
        }
    }
    
    // Load alarms
    function loadAlarms() {
        fetch('/alarms')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Clear the current alarm list
                    alarmList.innerHTML = '';
                    
                    // Add each alarm to the table
                    data.alarms.forEach((alarm, index) => {
                        const row = document.createElement('tr');
                        
                        // Time
                        const timeCell = document.createElement('td');
                        timeCell.textContent = alarm.time;
                        row.appendChild(timeCell);
                        
                        // Status
                        const statusCell = document.createElement('td');
                        statusCell.textContent = alarm.active ? 'Active' : 'Inactive';
                        statusCell.className = alarm.active ? 'status-active' : 'status-inactive';
                        row.appendChild(statusCell);
                        
                        // Actions
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
                    
                    // Update timestamps and hashes
                    if (data.timestamp) {
                        lastAlarmTimestamp = data.timestamp;
                    }
                    if (data.content_hash) {
                        lastAlarmContentHash = data.content_hash;
                    }
                    
                    console.log(`Updated alarm list: ${data.alarms.length} alarms found`);
                } else {
                    console.error('Error loading alarms:', data.message);
                }
            })
            .catch(error => {
                console.error('Error loading alarms:', error);
            });
    }
    
    // Poll for script output
    function pollOutput() {
        fetch('/output')
            .then(response => response.json())
            .then(data => {
                // Update output display
                if (data.output && data.output.length > 0) {
                    data.output.forEach(line => {
                        appendOutput(line);
                    });
                }
                
                // Update status if script has finished
                if (data.status === 'finished') {
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    statusSpan.textContent = 'Terminé';
                    statusSpan.className = '';
                    
                    // Stop polling
                    if (outputPollInterval) {
                        clearInterval(outputPollInterval);
                        outputPollInterval = null;
                    }
                    
                    if (alarmPollInterval) {
                        clearInterval(alarmPollInterval);
                        alarmPollInterval = null;
                    }
                }
            })
            .catch(error => {
                console.error('Error polling output:', error);
            });
    }
    
    // Start all polling functions
    startStatusPolling();
    startAlarmFileWatcher();
    startAlarmStatePolling();

    // Add refresh button functionality
    const refreshAlarmsBtn = document.getElementById('refreshAlarmsBtn');
    if (refreshAlarmsBtn) {
        refreshAlarmsBtn.addEventListener('click', function() {
            refreshAlarmsBtn.classList.add('refreshing');
            loadAlarms();
            setTimeout(() => {
                refreshAlarmsBtn.classList.remove('refreshing');
            }, 1000);
        });
    }
});

// Add these variables at the top of the file (outside any functions)
let lastAlarmTimestamp = 0;
let lastAlarmContentHash = 0;
let alarmWatcherInterval = null;

function startAlarmFileWatcher() {
    // Check more frequently - every 1 second
    alarmWatcherInterval = setInterval(checkAlarmsUpdated, 1000);
    // Initial check to get the current timestamp
    checkAlarmsUpdated();
}

function checkAlarmsUpdated() {
    fetch('/check_alarms_updated')
        .then(response => response.json())
        .then(data => {
            // Debug logging
            console.log(`Checking alarms: last timestamp=${lastAlarmTimestamp}, current=${data.timestamp}`);
            console.log(`Last content hash=${lastAlarmContentHash}, current=${data.content_hash}`);
            
            // Check if either the timestamp or content hash has changed
            if (
                (data.timestamp > 0 && data.timestamp != lastAlarmTimestamp) || 
                (data.content_hash > 0 && data.content_hash != lastAlarmContentHash)
            ) {
                console.log('Alarms file has been modified, refreshing');
                loadAlarms(); // Refresh the alarm list
            }
            
            // Always update both values
            lastAlarmTimestamp = data.timestamp;
            lastAlarmContentHash = data.content_hash;
        })
        .catch(error => {
            console.error('Error checking alarms file:', error);
        });
}

// Add toggle alarm functionality
function toggleAlarm(index) {
    fetch(`/alarm/${index}/toggle`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            loadAlarms(); // Refresh alarm list
            appendOutput(data.message);
            
            // Also check the alarm state after toggling
            checkAlarmState();
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while toggling the alarm');
    });
}
function startAlarmStatePolling() {
    // Poll every second to check if an alarm is active
    alarmStateInterval = setInterval(checkAlarmState, 1000);
}

function stopAlarmStatePolling() {
    if (alarmStateInterval) {
        clearInterval(alarmStateInterval);
        alarmStateInterval = null;
    }
}

function checkAlarmState() {
    fetch('/alarm_state')
        .then(response => response.json())
        .then(data => {
            if (data.alarm_active) {
                if (!alarmNotificationShown) {
                    showAlarmNotification(data.message);
                }
            } else {
                // If the alarm is not active but notification is shown, hide it
                if (alarmNotificationShown) {
                    hideAlarmNotification();
                }
            }
        })
        .catch(error => {
            console.error('Error checking alarm state:', error);
        });
}

function hideAlarmNotification() {
    const overlay = document.querySelector('.alarm-notification-overlay');
    if (overlay) {
        document.body.removeChild(overlay);
    }
    alarmNotificationShown = false;
}

let alarmNotificationShown = false;

function showAlarmNotification(message) {
    // Only show the notification once
    if (alarmNotificationShown) return;
    
    alarmNotificationShown = true;
    
    // Create notification overlay
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
    
    // Message
    const messageEl = document.createElement('h1');
    messageEl.textContent = '🔔 ALARM! 🔔';
    messageEl.style.color = 'white';
    messageEl.style.fontSize = '3rem';
    overlay.appendChild(messageEl);
    
    // Details
    const detailsEl = document.createElement('p');
    detailsEl.textContent = message;
    detailsEl.style.color = 'white';
    detailsEl.style.fontSize = '1.5rem';
    overlay.appendChild(detailsEl);
    
    // Snooze button
    const snoozeBtn = document.createElement('button');
    snoozeBtn.textContent = 'Snooze';
    snoozeBtn.className = 'btn btn-primary';
    snoozeBtn.style.marginTop = '20px';
    snoozeBtn.style.padding = '10px 20px';
    snoozeBtn.style.fontSize = '1.2rem';
    snoozeBtn.onclick = function() {
        // Send request to snooze the alarm
        fetch('/snooze', { method: 'POST' })
            .then(response => response.json())
            .then(() => {
                // Remove the overlay
                document.body.removeChild(overlay);
                alarmNotificationShown = false;
                
                // Also refresh alarm list to ensure UI is in sync
                loadAlarms();
            })
            .catch(error => {
                console.error('Error snoozing alarm:', error);
            });
    };
    overlay.appendChild(snoozeBtn);
    
    document.body.appendChild(overlay);
}

function startStatusPolling() {
    // Check every 5 seconds
    statusPollInterval = setInterval(checkApplicationStatus, 5000);
    // Initial check
    checkApplicationStatus();
}

function checkApplicationStatus() {
    fetch('/status')
        .then(response => response.json())
        .then(data => {
            // Update UI based on status
            updateUIFromStatus(data);
        })
        .catch(error => {
            console.error('Error checking application status:', error);
        });
}

function snoozeAlarm() {
    fetch('/snooze', { method: 'POST' })
        .then(response => response.json())
        .then(() => {
            // Remove the overlay
            hideAlarmNotification();
            
            // Also refresh alarm list to ensure UI is in sync
            loadAlarms();
        })
        .catch(error => {
            console.error('Error snoozing alarm:', error);
        });
}

function updateUIFromStatus(data) {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusSpan = document.getElementById('status');
    
    if (data.script_running) {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        statusSpan.textContent = 'En cours d\'exécution';
        statusSpan.className = 'running';
        
        // Start polling if not already
        if (!outputPollInterval) {
            outputPollInterval = setInterval(pollOutput, 500);
        }
        
        // Start polling for alarms
        if (!alarmPollInterval) {
            alarmPollInterval = setInterval(loadAlarms, 5000);
        }
    } else {
        startBtn.disabled = false;
        stopBtn.disabled = true;
        statusSpan.textContent = 'Arrêté';
        statusSpan.className = '';
    }
}

// Move this to global scope or handle correctly in the code
function appendOutput(text) {
    const outputElement = document.getElementById('output');
    outputElement.textContent += text + '\n';
    
    // Auto-scroll to bottom
    const outputContainer = outputElement.parentElement;
    outputContainer.scrollTop = outputContainer.scrollHeight;
}