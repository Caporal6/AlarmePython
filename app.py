from flask import Flask, render_template, jsonify, request
import subprocess
import os
import signal
import sys
import time
import threading
import atexit
import json
import paho.mqtt.client as mqtt
from flask_mqtt import Mqtt

app = Flask(__name__)

# MQTT Configuration
app.config['MQTT_BROKER_URL'] = 'localhost'  # Use your MQTT broker IP
app.config['MQTT_BROKER_PORT'] = 1883  # Default port for MQTT
app.config['MQTT_USERNAME'] = ''  # Set if your broker requires authentication
app.config['MQTT_PASSWORD'] = ''  # Set if your broker requires authentication
app.config['MQTT_KEEPALIVE'] = 60  # Increased keepalive for better reliability
app.config['MQTT_TLS_ENABLED'] = False
app.config['MQTT_CLEAN_SESSION'] = False  # Maintain persistent session

# Initialize Flask-MQTT extension with improved error handling
try:
    mqtt_client = Mqtt(app)
    print("MQTT client initialized successfully")
except Exception as e:
    print(f"Error initializing MQTT client: {e}")
    # Create a fallback MQTT client that does nothing
    class FallbackMqtt:
        def publish(self, *args, **kwargs):
            print(f"MQTT publish attempted but MQTT is not available: {args}")
    mqtt_client = FallbackMqtt()

script_process = None
output_buffer = []
process_lock = threading.Lock()
ALARMS_FILE = "alarms.json"
interface_process = None  # Store the process ID of the interface window

# Set up MQTT topics
TOPIC_ALARMS = "alarm/list"
TOPIC_ALARM_ADDED = "alarm/added"
TOPIC_ALARM_DELETED = "alarm/deleted"
TOPIC_ALARM_TOGGLED = "alarm/toggled"
TOPIC_ALARM_STATE = "alarm/state"
TOPIC_OUTPUT = "alarm/output"

@mqtt_client.on_connect()
def handle_connect(client, userdata, flags, rc):
    """Called when the MQTT client connects to the broker"""
    print(f"Connected to MQTT broker with result code {rc}")
    # Subscribe to client requests
    mqtt_client.subscribe("alarm/request/#")

@mqtt_client.on_message()
def handle_mqtt_message(client, userdata, message):
    """Process incoming MQTT messages"""
    topic = message.topic
    payload = message.payload.decode()
    
    print(f"Received message on topic {topic}: {payload}")
    
    try:
        # Parse JSON payload
        data = json.loads(payload)
        
        # Process different request types
        if topic == "alarm/request/list":
            # Client is requesting alarm list
            publish_alarms()
        elif topic == "alarm/request/add":
            # Client is adding an alarm
            try:
                hour = int(data.get('hour', 0))
                minute = int(data.get('minute', 0))
                second = int(data.get('second', 0))
                add_alarm_mqtt(hour, minute, second)
            except Exception as e:
                print(f"Error processing add alarm request: {e}")
                mqtt_client.publish("alarm/error", f"Failed to add alarm: {str(e)}")
        elif topic == "alarm/request/delete":
            # Client is deleting an alarm
            try:
                index = int(data.get('index', -1))
                if index >= 0:
                    delete_alarm_mqtt(index)
            except Exception as e:
                print(f"Error processing delete alarm request: {e}")
                mqtt_client.publish("alarm/error", f"Failed to delete alarm: {str(e)}")
        elif topic == "alarm/request/toggle":
            # Client is toggling an alarm
            try:
                index = int(data.get('index', -1))
                if index >= 0:
                    toggle_alarm_mqtt(index)
            except Exception as e:
                print(f"Error processing toggle alarm request: {e}")
                mqtt_client.publish("alarm/error", f"Failed to toggle alarm: {str(e)}")
        elif topic == "alarm/request/snooze":
            # Client is snoozing an alarm
            try:
                snooze_alarm_mqtt()
            except Exception as e:
                print(f"Error processing snooze request: {e}")
                mqtt_client.publish("alarm/error", f"Failed to snooze alarm: {str(e)}")
        elif topic == "alarm/list" and isinstance(data, list):
            # Got an alarm list from another client (likely the GUI)
            # Update our local copy without republishing to avoid loops
            try:
                # Load current alarms for comparison
                current_alarms = []
                if os.path.exists(ALARMS_FILE):
                    with open(ALARMS_FILE, 'r') as f:
                        current_alarms = json.load(f)
                
                # Only update if different
                if json.dumps(current_alarms, sort_keys=True) != json.dumps(data, sort_keys=True):
                    with open(ALARMS_FILE, 'w') as f:
                        json.dump(data, f)
                    print(f"Updated alarms from MQTT message: {len(data)} alarms")
            except Exception as e:
                print(f"Error updating alarms from MQTT: {e}")
                
    except json.JSONDecodeError:
        print(f"Received non-JSON payload: {payload}")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")
def read_output(process):
    """Read output from the process and store it in buffer"""
    global output_buffer
    while True:
        try:
            if process.poll() is not None:
                break
                
            line = process.stdout.readline()
            if not line:
                break
                
            line_str = line.decode('utf-8').strip()
            output_buffer.append(line_str)
            print(f"Process output: {line_str}")  # Log to console for debugging
            
            # Publish output to MQTT
            mqtt_client.publish(TOPIC_OUTPUT, line_str)
        except Exception as e:
            print(f"Error reading process output: {e}")
            break

def launch_interface_fullscreen():
    """Launch the interface_1.py script in a new process"""
    global interface_process
    
    # Check if a process is already running
    if interface_process is not None:
        print("Interface is already running")
        return True
    
    try:
        # First try with direct launch (most reliable)
        print("Launching interface directly...")
        
        # Set environment variables to help with troubleshooting
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'  # Disable output buffering
        env['ALARM_DEBUG'] = '1'  # Add debug flag for our code
        env['DISPLAY'] = os.environ.get('DISPLAY', ':0')  # Ensure X display is set
        env['XAUTHORITY'] = os.environ.get('XAUTHORITY', os.path.expanduser('~/.Xauthority'))
        
        # Launch with stderr and stdout redirected to see any errors
        interface_process = subprocess.Popen(
            [sys.executable, 'interface_1.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=env
        )
        
        # Start a thread to read error output
        def read_stderr(proc):
            for line in proc.stderr:
                print(f"Interface Error: {line.strip()}")
        
        stderr_thread = threading.Thread(target=read_stderr, args=(interface_process,))
        stderr_thread.daemon = True
        stderr_thread.start()
        
        # Give it a moment to start and check for immediate errors
        time.sleep(1)
        
        # Check if process started successfully
        if interface_process.poll() is None:
            print("Interface launched successfully")
            return True
        else:
            print("Failed to launch interface directly. Exit code:", interface_process.poll())
            # Try to read any error output
            stderr_output = interface_process.stderr.read()
            if stderr_output:
                print(f"Error output: {stderr_output}")
            return False
    except Exception as e:
        print(f"Error launching Interface directly: {e}")
    
    # Try with terminal as fallback (for Raspberry Pi)
    try:
        if os.path.exists('/usr/bin/lxterminal'):
            # Raspberry Pi with LXDE desktop environment
            print("Trying to launch interface in lxterminal...")
            interface_process = subprocess.Popen([
                'lxterminal', 
                '--command', f'python3 "{os.path.join(os.getcwd(), "interface_1.py")}"', 
                '--title=Alarm Interface',
                '--geometry=maximized'
            ])
            
            # Give it a moment to start
            time.sleep(1)
            
            # Check if process is still running
            if interface_process.poll() is None:
                print("Launched Interface in terminal window")
                return True
    except Exception as e:
        print(f"Error launching Interface in terminal: {e}")
    
    print("All methods to launch interface failed")
    return False


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_script():
    global script_process, output_buffer, interface_process
    
    with process_lock:
        # Check if script is already running (either from web or from GUI)
        if script_process is not None:
            return jsonify({"status": "error", "message": "Script is already running"})
            
        # Check if interface GUI is running
        if interface_process is not None:
            return jsonify({"status": "error", "message": "Interface GUI is already running"})
        
        output_buffer = []
        try:
            # Set environment variable for web mode
            env = os.environ.copy()
            env['WEB_MODE'] = '1'
            
            # Start the alarm script with stdout and stderr redirected
            script_process = subprocess.Popen(
                [sys.executable, 'interface_1.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                env=env
            )
            
            # Start a thread to read the output
            thread = threading.Thread(target=read_output, args=(script_process,))
            thread.daemon = True
            thread.start()
            
            return jsonify({"status": "success", "message": "Script started"})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to start script: {str(e)}"})

@app.route('/stop', methods=['POST'])
def stop_script():
    global script_process
    
    with process_lock:
        if script_process is None:
            return jsonify({"status": "error", "message": "No script is running"})
        
        try:
            # Send SIGTERM to the process group
            if sys.platform != 'win32':
                os.killpg(os.getpgid(script_process.pid), signal.SIGTERM)
            else:
                script_process.terminate()
            
            script_process.wait(timeout=5)  # Wait for process to terminate
            script_process = None
            return jsonify({"status": "success", "message": "Script stopped"})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to stop script: {str(e)}"})

@app.route('/output')
def get_output():
    global script_process
    
    with process_lock:
        status = "stopped"
        if script_process is not None:
            if script_process.poll() is not None:
                status = "finished" 
                script_process = None
            else:
                status = "running"
        
        output = output_buffer.copy()
        output_buffer.clear()  # Using clear() instead of assignment
        
        return jsonify({
            "status": status,
            "output": output
        })

@app.route('/alarms', methods=['GET'])
def get_alarms():
    try:
        # Force reading from disk, bypass any OS caching
        os.sync()
        if os.path.exists(ALARMS_FILE):
            last_modified = os.path.getmtime(ALARMS_FILE)
            with open(ALARMS_FILE, 'r') as f:
                alarms = json.load(f)
                # Read the current file content for hash comparison
                f.seek(0)
                content = f.read()
                content_hash = hash(content)
                return jsonify({
                    "status": "success", 
                    "alarms": alarms,
                    "timestamp": last_modified,
                    "content_hash": content_hash
                })
        else:
            return jsonify({"status": "success", "alarms": [], "timestamp": 0, "content_hash": 0})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/mqtt_test')
def mqtt_test():
    """Test page for MQTT WebSocket connection"""
    return render_template('test.html')

@app.route('/alarm', methods=['POST'])
def add_alarm():
    try:
        data = request.json
        hour = int(data.get('hour', 0))
        minute = int(data.get('minute', 0))
        second = int(data.get('second', 0))
        
        # Format the time properly with leading zeros
        alarm_time = f"{hour:02d}:{minute:02d}:{second:02d}"
        print(f"Attempting to add alarm for {alarm_time}")
        
        # Execute a Python script to add the alarm
        result = subprocess.run(
            [sys.executable, '-c', f'''
import json, os
alarms_file = "{ALARMS_FILE}"
alarm_time = "{hour:02d}:{minute:02d}:{second:02d}"
alarms = []

if os.path.exists(alarms_file):
    with open(alarms_file, 'r') as f:
        alarms = json.load(f)

# Check if alarm already exists
exists = False
for alarm in alarms:
    if alarm["time"] == alarm_time:
        exists = True
        break

if not exists:
    alarms.append({{"time": alarm_time, "active": True}})
    with open(alarms_file, 'w') as f:
        json.dump(alarms, f)
        f.flush()
        os.fsync(f.fileno())
    print("Alarm added")
else:
    print("Alarm already exists")

# Ensure file is properly flushed to disk
os.sync()
'''],
            capture_output=True,
            text=True
        )
        
        print(f"Command output: {result.stdout.strip()}")
        print(f"Command error: {result.stderr.strip()}" if result.stderr else "No errors")
        
        return jsonify({
            "status": "success",
            "message": f"Alarm set for {hour:02d}:{minute:02d}:{second:02d}",
            "output": result.stdout.strip()
        })
    except Exception as e:
        print(f"Error adding alarm: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})

@app.route('/alarm/<int:index>', methods=['DELETE'])
def delete_alarm(index):
    try:
        # Execute a Python script to delete the alarm
        result = subprocess.run(
            [sys.executable, '-c', f'''
import json, os
alarms_file = "{ALARMS_FILE}"
index = {index}
alarms = []

if os.path.exists(alarms_file):
    with open(alarms_file, 'r') as f:
        alarms = json.load(f)

if 0 <= index < len(alarms):
    deleted = alarms.pop(index)
    with open(alarms_file, 'w') as f:
        json.dump(alarms, f)
    print(f"Deleted alarm at {{deleted['time']}}")
else:
    print("Invalid alarm index")
'''],
            capture_output=True,
            text=True
        )
        
        return jsonify({
            "status": "success",
            "message": "Alarm deleted",
            "output": result.stdout.strip()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/alarm/<int:index>/toggle', methods=['POST'])
def toggle_alarm(index):
    try:
        # Execute a Python script to toggle the alarm
        result = subprocess.run(
            [sys.executable, '-c', f'''
import json, os, time
from alarm_state import clear_state, set_state, get_state
alarms_file = "{ALARMS_FILE}"
index = {index}
alarms = []

try:
    if os.path.exists(alarms_file):
        with open(alarms_file, 'r') as f:
            alarms = json.load(f)

    if 0 <= index < len(alarms):
        # Toggle the alarm
        alarms[index]["active"] = not alarms[index]["active"]
        status = "activated" if alarms[index]["active"] else "deactivated"
        message = f"Alarm at {{alarms[index]['time']}} {{status}}"
        
        # If deactivating an alarm that matches the current time, also clear alarm state
        if not alarms[index]["active"]:
            current_state = get_state()
            current_time = time.strftime('%H:%M:%S')
            
            if current_state["alarm_active"] and alarms[index]["time"] == current_time:
                clear_state()
                print("Cleared alarm state because matching alarm was deactivated")
        
        # Save changes
        with open(alarms_file, 'w') as f:
            json.dump(alarms, f)
            f.flush()
            os.fsync(f.fileno())
        print(message)
        
        # Also ensure file is properly flushed to disk
        os.sync()
    else:
        message = "Invalid alarm index"
        print(message)
except Exception as e:
    print(f"Error: {{e}}")
    message = f"Error: {{e}}"
'''],
            capture_output=True,
            text=True
        )
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        
        # Check if there was an error in the Python script
        if "Error:" in stdout or stderr:
            return jsonify({
                "status": "error",
                "message": stdout if "Error:" in stdout else stderr
            })
        
        return jsonify({
            "status": "success",
            "message": stdout
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/alarm_state')
def get_alarm_state():
    """Check if any alarm is currently active"""
    try:
        from alarm_state import get_state
        state = get_state()
        return jsonify(state)
    except ImportError:
        # If the module isn't available
        return jsonify({"alarm_active": False, "timestamp": 0, "message": "State module not available"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/snooze', methods=['POST'])
def snooze():
    """Snooze the currently active alarm"""
    try:
        from alarm_state import clear_state
        clear_state()
        return jsonify({"status": "success", "message": "Alarm snoozed"})
    except ImportError:
        return jsonify({"status": "error", "message": "State module not available"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/check_alarms_updated')
def check_alarms_updated():
    """Check if the alarms file has been modified"""
    try:
        if os.path.exists(ALARMS_FILE):
            # Get the actual content modification time
            last_modified = os.path.getmtime(ALARMS_FILE)
            # Read the current file content for hash comparison
            with open(ALARMS_FILE, 'rb') as f:
                content = f.read()
                content_hash = hash(content)
            
            return jsonify({
                "timestamp": last_modified,
                "content_hash": content_hash
            })
        else:
            return jsonify({"timestamp": 0, "content_hash": 0})
    except Exception as e:
        return jsonify({"timestamp": 0, "content_hash": 0, "error": str(e)})

@app.route('/status')
def get_status():
    """Return the status of the local application"""
    global script_process, interface_process
    
    return jsonify({
        "script_running": script_process is not None and script_process.poll() is None,
        "interface_running": interface_process is not None and interface_process.poll() is None,
        "web_mode": True,
        "server_time": time.strftime('%H:%M:%S')
    })

def cleanup():
    global script_process, interface_process
    print("Running cleanup...")
    
    if script_process is not None:
        try:
            print("Terminating script process...")
            if sys.platform != 'win32':
                os.killpg(os.getpgid(script_process.pid), signal.SIGTERM)
            else:
                script_process.terminate()
            print("Script process terminated")
        except Exception as e:
            print(f"Error terminating script process: {e}")
    
    if interface_process is not None:
        try:
            print("Terminating interface process...")
            interface_process.terminate()
            print("Interface process terminated")
        except Exception as e:
            print(f"Error terminating interface process: {e}")

# Register cleanup function to be called on exit
atexit.register(cleanup)

# MQTT message broker for WebSockets
@app.route('/mqtt')
def mqtt_status():
    """Return MQTT WebSocket connection details"""
    # Get the server's hostname
    host = request.host.split(':')[0]  # Remove port if present
    
    return jsonify({
        "broker_url": host,  # Use the same host as the web server
        "broker_websocket_port": 9001,  # WebSocket port (must match Mosquitto config)
        "use_ssl": request.is_secure  # Match the security of the current connection
    })

# Additional MQTT functions to publish alarm updates to topics
def publish_alarms():
    """Publish the current list of alarms to MQTT"""
    try:
        if os.path.exists(ALARMS_FILE):
            with open(ALARMS_FILE, 'r') as f:
                alarms = json.load(f)
                mqtt_client.publish(TOPIC_ALARMS, json.dumps(alarms))
                print(f"Published {len(alarms)} alarms to MQTT")
                return True
        else:
            mqtt_client.publish(TOPIC_ALARMS, "[]")
            return True
    except Exception as e:
        print(f"Error publishing alarms to MQTT: {e}")
        return False

def add_alarm_mqtt(hour, minute, second):
    """Add alarm via MQTT request"""
    try:
        # Format the time properly with leading zeros
        alarm_time = f"{hour:02d}:{minute:02d}:{second:02d}"
        print(f"MQTT: Adding alarm for {alarm_time}")
        
        # Load existing alarms
        alarms = []
        if os.path.exists(ALARMS_FILE):
            with open(ALARMS_FILE, 'r') as f:
                alarms = json.load(f)
        
        # Check if alarm already exists
        exists = False
        for alarm in alarms:
            if alarm["time"] == alarm_time:
                exists = True
                break
        
        # Add new alarm if it doesn't exist
        if not exists:
            alarms.append({"time": alarm_time, "active": True})
            with open(ALARMS_FILE, 'w') as f:
                json.dump(alarms, f)
                f.flush()
                os.fsync(f.fileno())
            
            # Publish events
            mqtt_client.publish(TOPIC_ALARM_ADDED, json.dumps({
                "time": alarm_time,
                "message": f"Alarm added for {alarm_time}"
            }))
            
            # Also publish updated list with retain flag to keep it persistent
            mqtt_client.publish(TOPIC_ALARMS, json.dumps(alarms), qos=1, retain=True)
            
            return True
        else:
            mqtt_client.publish(TOPIC_ALARM_ADDED, json.dumps({
                "message": f"Alarm for {alarm_time} already exists"
            }))
            return False
    except Exception as e:
        print(f"Error adding alarm via MQTT: {e}")
        mqtt_client.publish("alarm/error", json.dumps({
            "message": f"Failed to add alarm: {str(e)}"
        }))
        return False
    
def toggle_alarm_mqtt(index):
    """Toggle alarm via MQTT request"""
    try:
        # Load alarms
        if not os.path.exists(ALARMS_FILE):
            mqtt_client.publish("alarm/error", json.dumps({
                "message": "Alarm file does not exist"
            }))
            return False
        
        with open(ALARMS_FILE, 'r') as f:
            alarms = json.load(f)
        
        if index < 0 or index >= len(alarms):
            mqtt_client.publish("alarm/error", json.dumps({
                "message": f"Invalid alarm index: {index}"
            }))
            return False
        
        # Toggle the alarm
        alarms[index]["active"] = not alarms[index]["active"]
        status = "activated" if alarms[index]["active"] else "deactivated"
        message = f"Alarm at {alarms[index]['time']} {status}"
        
        # Save changes
        with open(ALARMS_FILE, 'w') as f:
            json.dump(alarms, f)
            f.flush()
            os.fsync(f.fileno())
        
        # Publish event
        mqtt_client.publish(TOPIC_ALARM_TOGGLED, json.dumps({
            "index": index,
            "active": alarms[index]["active"],
            "time": alarms[index]["time"],
            "message": message
        }))
        
        # Also publish updated list
        publish_alarms()
        return True
    except Exception as e:
        print(f"Error toggling alarm via MQTT: {e}")
        mqtt_client.publish("alarm/error", json.dumps({
            "message": f"Failed to toggle alarm: {str(e)}"
        }))
        return False

def delete_alarm_mqtt(index):
    """Delete alarm via MQTT request"""
    try:
        # Load alarms
        if not os.path.exists(ALARMS_FILE):
            mqtt_client.publish("alarm/error", json.dumps({
                "message": "Alarm file does not exist"
            }))
            return False
        
        with open(ALARMS_FILE, 'r') as f:
            alarms = json.load(f)
        
        if index < 0 or index >= len(alarms):
            mqtt_client.publish("alarm/error", json.dumps({
                "message": f"Invalid alarm index: {index}"
            }))
            return False
        
        # Store the time before deleting
        deleted_time = alarms[index]["time"]
        
        # Delete the alarm
        del alarms[index]
        
        # Save changes
        with open(ALARMS_FILE, 'w') as f:
            json.dump(alarms, f)
            f.flush()
            os.fsync(f.fileno())
        
        # Publish event
        mqtt_client.publish(TOPIC_ALARM_DELETED, json.dumps({
            "index": index,
            "time": deleted_time,
            "message": f"Deleted alarm at {deleted_time}"
        }))
        
        # Also publish updated list
        publish_alarms()
        return True
    except Exception as e:
        print(f"Error deleting alarm via MQTT: {e}")
        mqtt_client.publish("alarm/error", json.dumps({
            "message": f"Failed to delete alarm: {str(e)}"
        }))
        return False

def snooze_alarm_mqtt():
    """Snooze the currently active alarm via MQTT"""
    try:
        from alarm_state import clear_state
        clear_state()
        mqtt_client.publish("alarm/state", json.dumps({
            "alarm_active": False,
            "timestamp": time.time(),
            "message": "Alarm snoozed"
        }))
        return True
    except Exception as e:
        print(f"Error snoozing alarm via MQTT: {e}")
        mqtt_client.publish("alarm/error", json.dumps({
            "message": f"Failed to snooze alarm: {str(e)}"
        }))
        return False

# Add a more robust publish function
def safe_mqtt_publish(topic, payload, qos=1, retain=False):
    """Safely publish a message to MQTT with error handling"""
    try:
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload)
        mqtt_client.publish(topic, payload, qos=qos, retain=retain)
        return True
    except Exception as e:
        print(f"Error publishing to MQTT topic {topic}: {e}")
        return False

# Start a thread to periodically publish alarm state
def publish_alarm_state_loop():
    """Periodically publish alarm state to MQTT"""
    try:
        from alarm_state import get_state
        state = get_state()
        mqtt_client.publish("alarm/state", json.dumps(state))
    except Exception as e:
        print(f"Error publishing alarm state: {e}")
    
    # Schedule next update
    threading.Timer(1.0, publish_alarm_state_loop).start()

    

    

# Start the alarm state publishing thread when the app starts

@app.route('/websocket_test')
def websocket_test():
    """Test page for WebSocket connections"""
    return render_template('test.html')

@app.route('/hardware_test_page')
def hardware_test_page():
    """Dedicated page for testing hardware components"""
    return render_template('hardware_test.html')

if __name__ == '__main__':
    # Start publishing alarm state
    threading.Timer(2.0, publish_alarm_state_loop).start()
    
    # Rest of your main code...

if __name__ == '__main__':
    # Check if running in virtual environment
    import sys
    import os
    
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv and not os.environ.get('SKIP_VENV_CHECK'):
        print("Warning: Not running in a virtual environment.")
        print("For best results, run this application using the run_alarm.sh script.")
        print("If you want to bypass this check, set SKIP_VENV_CHECK=1 in your environment.")
        print("Continuing anyway in 3 seconds...")
        time.sleep(3)
    
    # Get command-line argument for mode
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface only')
    parser.add_argument('--web', action='store_true', help='Launch web interface only')
    parser.add_argument('--both', action='store_true', help='Launch both interfaces')
    parser.add_argument('--mqtt-broker', default='localhost', help='MQTT broker host')
    args = parser.parse_args()
    
    # Update MQTT configuration from command line if provided
    if args.mqtt_broker:
        app.config['MQTT_BROKER_URL'] = args.mqtt_broker
    
    # Determine which mode to launch
    launch_gui = args.gui or args.both or not (args.gui or args.web or args.both)
    launch_web = args.web or args.both or not (args.gui or args.web or args.both)
    
    print(f"Starting in {'GUI' if launch_gui else ''}{' and ' if launch_gui and launch_web else ''}{'Web' if launch_web else ''} mode")
    print(f"Using MQTT broker: {app.config['MQTT_BROKER_URL']}")
    
    # Start publishing alarm state
    threading.Timer(2.0, publish_alarm_state_loop).start()
    
    # Launch the interfaces in the correct order
    if launch_gui:
        # Launch the interface in fullscreen
        if launch_interface_fullscreen():
            print("GUI interface launched successfully")
        else:
            print("Failed to launch GUI interface")
    
    if launch_web:
        # Start Flask server
        print("Starting web server...")
        app.run(debug=False, host='0.0.0.0')  # Set debug to False in production

# Add this route to app.py
@app.route('/hardware_status')
def hardware_status():
    """Return hardware availability status"""
    try:
        # Check if interface_1.py is running with hardware
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
    except ImportError:
        # If we can't import directly, check if we can find the process
        return jsonify({
            "hardware_available": False,
            "message": "Hardware interface not accessible"
        })

# Add this route to app.py
@app.route('/sensor_data')
def sensor_data():
    """Return current sensor readings if hardware is available"""
    try:
        # Try to import from the interface
        import sys
        sys.path.append(".")
        
        try:
            from interface_1 import get_sensor_data
            data = get_sensor_data()
            return jsonify(data)
        except (ImportError, AttributeError):
            # If the function doesn't exist, create a dummy implementation
            if interface_process and interface_process.poll() is None:
                # Interface is running, but we can't directly access its data
                return jsonify({
                    "status": "running",
                    "message": "Interface running but data not accessible"
                })
            else:
                # Interface is not running
                return jsonify({
                    "status": "offline",
                    "message": "Hardware interface not running"
                })
    except Exception as e:
        return jsonify({
            "error": str(e)
        })

@app.route('/test_hardware', methods=['POST'])
def test_hardware():
    """Test hardware components"""
    try:
        component = request.json.get('component', '')
        action = request.json.get('action', '')
        
        if component == 'led':
            # Try to control LED
            try:
                from interface_1 import led
                if action == 'on':
                    led.on()
                    return jsonify({"status": "success", "message": "LED turned on"})
                else:
                    led.off()
                    return jsonify({"status": "success", "message": "LED turned off"})
            except Exception as e:
                return jsonify({"status": "error", "message": f"LED control failed: {str(e)}"})
        
        elif component == 'servo':
            # Try to move servo
            try:
                from interface_1 import servo
                if action == 'sweep':
                    # Start a thread to move the servo since it blocks
                    def move_servo_test():
                        for angle in range(0, 181, 5):  # Faster movement
                            servo.angle = angle
                            time.sleep(0.01)
                        for angle in range(180, -1, -5):
                            servo.angle = angle
                            time.sleep(0.01)
                    
                    threading.Thread(target=move_servo_test).start()
                    return jsonify({"status": "success", "message": "Servo moving back and forth"})
                    
                elif action == 'center':
                    # Move servo to center position (90 degrees)
                    servo.angle = 90
                    return jsonify({"status": "success", "message": "Servo centered at 90°"})
                    
            except Exception as e:
                return jsonify({"status": "error", "message": f"Servo control failed: {str(e)}"})
        
        elif component == 'buzzer':
            # Try to control buzzer
            try:
                from interface_1 import buzzer
                if action == 'on':
                    buzzer.on()
                    # Turn off after 1 second
                    threading.Timer(1.0, lambda: buzzer.off()).start()
                    return jsonify({"status": "success", "message": "Buzzer beeped"})
                else:
                    buzzer.off()
                    return jsonify({"status": "success", "message": "Buzzer turned off"})
            except Exception as e:
                return jsonify({"status": "error", "message": f"Buzzer control failed: {str(e)}"})
                
        return jsonify({"status": "error", "message": "Invalid component or action"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/test_hardware_fixed', methods=['POST'])
def test_hardware_fixed():
    """Test hardware components with better error handling"""
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

@app.route('/websocket_test')
def websocket_test():
    """Test page for WebSocket connections"""
    return render_template('test.html')

@app.route('/hardware_test_page')
def hardware_test_page():
    """Dedicated page for testing hardware components"""
    return render_template('hardware_test.html')