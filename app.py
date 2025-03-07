from flask import Flask, render_template, jsonify, request
import subprocess
import os
import signal
import sys
import time
import threading
import atexit
import json

app = Flask(__name__)

script_process = None
output_buffer = []
process_lock = threading.Lock()
ALARMS_FILE = "alarms.json"
interface_process = None  # Store the process ID of the interface window

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
        except Exception as e:
            print(f"Error reading process output: {e}")
            break

def launch_interface_fullscreen():
    """Launch the Interface 1.py script in a new process"""
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
        
        # Launch with stderr and stdout redirected to see any errors
        interface_process = subprocess.Popen(
            [sys.executable, 'Interface 1.py'],
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
                '--command', f'python3 "{os.path.join(os.getcwd(), "Interface 1.py")}"', 
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
                [sys.executable, 'Interface 1.py'],
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

@app.route('/alarm', methods=['POST'])
def add_alarm():
    try:
        data = request.json
        hour = int(data.get('hour', 0))
        minute = int(data.get('minute', 0))
        second = int(data.get('second', 0))
        
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
    print("Alarm added")
else:
    print("Alarm already exists")
'''],
            capture_output=True,
            text=True
        )
        
        return jsonify({
            "status": "success",
            "message": f"Alarm set for {hour:02d}:{minute:02d}:{second:02d}",
            "output": result.stdout.strip()
        })
    except Exception as e:
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
'''],
            capture_output=True,
            text=True
        )
        
        return jsonify({
            "status": "success",
            "message": result.stdout.strip()
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

if __name__ == '__main__':
    # Get command-line argument for mode
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface only')
    parser.add_argument('--web', action='store_true', help='Launch web interface only')
    parser.add_argument('--both', action='store_true', help='Launch both interfaces')
    args = parser.parse_args()
    
    # Determine which mode to launch
    launch_gui = args.gui or args.both or not (args.gui or args.web or args.both)
    launch_web = args.web or args.both or not (args.gui or args.web or args.both)
    
    print(f"Starting in {'GUI' if launch_gui else ''}{' and ' if launch_gui and launch_web else ''}{'Web' if launch_web else ''} mode")
    
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