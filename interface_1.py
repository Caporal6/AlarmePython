import tkinter as tk
import time
import os
import sys
import json
import threading
import traceback
from pathlib import Path
import random
import math

# Try to import MQTT
try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("paho-mqtt not installed, MQTT functionality will be limited")

try:
    # Hardware-specific imports, use try/except to make it work in web mode too
    from gpiozero import LED, Button, Buzzer, DistanceSensor, AngularServo
    import Freenove_DHT as DHT
    import MPU6050
    
    # Hardware definitions
    led = LED(6)
    myGPIO = 25
    SERVO_DELAY_SEC = 0.001
    myCorrection = 0.0
    maxPW = (2.5 + myCorrection) / 1000
    minPW = (0.5 - myCorrection) / 1000
    
    # Servo initialization
    servo = AngularServo(myGPIO, initial_angle=0, min_angle=0, max_angle=180, min_pulse_width=minPW, max_pulse_width=maxPW)
    
    # Buzzer initialization
    buzzer = Buzzer(18)
    
    # Ultrasonic sensor initialization
    ultrasonic = DistanceSensor(echo=19, trigger=4, max_distance=4)
    
    # DHT11 sensor for temperature and humidity
    DHTPin = 17
    
    # Accelerometer initialization
    mpu = MPU6050.MPU6050()
    accel = [0]*3  # Array to store accelerometer data
    gyro = [0]*3   # Array to store gyroscope data
    
    # Initialize MPU6050 accelerometer
    def setup():
        mpu.dmp_initialize()
        print("MPU6050 initialized")
    
    # Call setup function to initialize accelerometer
    setup()
    
    HARDWARE_AVAILABLE = True
except ImportError as e:
    print(f"Hardware modules not available: {e}")
    # Create dummy implementations for hardware functions
    class DummyComponent:
        def on(self): print("DUMMY: ON called")
        def off(self): print("DUMMY: OFF called")
        @property
        def distance(self): return 0.5  # Return a mid-range value
        @property
        def angle(self): return 0
        @angle.setter
        def angle(self, value): print(f"DUMMY: Setting angle to {value}")
    
    led = DummyComponent()
    buzzer = DummyComponent()
    ultrasonic = DummyComponent()
    servo = DummyComponent()
    
    def setup():
        print("DUMMY: Hardware setup called")
    
    HARDWARE_AVAILABLE = False

# Initialize variables for sensors
last_accel = [0, 0, 0]
last_gyro = [0, 0, 0]
movement_threshold = 1000
excessive_movement_threshold = 15000
excessive_rotation_threshold = 2000
distance_Prevue = 50  # Default expected distance in cm
correct_distance_time = 0
distance_history = []
stable_time = 0

# Function to calculate variation between two vector values
def calculate_variation(new_values, last_values):
    return [abs(new_values[i] - last_values[i]) for i in range(len(new_values))]

# Function to check movement from accelerometer
def check_movement():
    """Check for movement using accelerometer."""
    global last_accel, last_gyro
    
    if not HARDWARE_AVAILABLE:
        # For testing in web mode, generate random movement
        import random
        return random.choice([True, False])
    
    try:
        accel = mpu.get_acceleration()  # Get accelerometer data
        gyro = mpu.get_rotation()      # Get gyroscope data
        
        # Calculate variation from last readings
        accel_variation = calculate_variation(accel, last_accel)
        gyro_variation = calculate_variation(gyro, last_gyro)
        
        # Update last values
        last_accel = accel
        last_gyro = gyro
        
        # Calculate magnitudes
        accel_magnitude = math.sqrt(accel[0]**2 + accel[1]**2 + accel[2]**2)
        gyro_magnitude = math.sqrt(gyro[0]**2 + gyro[1]**2 + gyro[2]**2)
        
        # Check for excessive movement
        if any(variation > excessive_movement_threshold for variation in accel_variation) or \
           any(variation > excessive_rotation_threshold for variation in gyro_variation):
            if 'movement_warning_label' in globals() and movement_warning_label and not WEB_MODE:
                movement_warning_label.config(text="Movement detected!")
            return False  # Returns False when movement is detected (for historical reasons)
        
        # Check for regular movement
        elif accel_magnitude > movement_threshold or gyro_magnitude > movement_threshold:
            return False  # Returns False when movement is detected
            
        # No movement detected
        if 'movement_warning_label' in globals() and movement_warning_label and not WEB_MODE:
            movement_warning_label.config(text="No movement")
        return True  # Returns True when NO movement is detected
    except Exception as e:
        print(f"Error in check_movement: {e}")
        return True  # Default to "no movement" on error

# Function to check distance and handle alarm snooze
def check_distance():
    global alarm_active, correct_distance_time
    
    if not alarm_active:
        return
    
    if not HARDWARE_AVAILABLE:
        # In web mode or when hardware isn't available
        return
    
    try:
        current_distance = ultrasonic.distance * 100  # Convert to cm
        
        if not check_movement():
            if 'movement_warning_label' in globals() and not WEB_MODE:
                movement_warning_label.config(text="Mouvement détecté!")
        else:
            if 'movement_warning_label' in globals() and not WEB_MODE:
                movement_warning_label.config(text="")
                
            if current_distance < distance_Prevue - 10:
                if 'distance_label' in globals() and not WEB_MODE:
                    distance_label.config(text=f"Trop proche: {current_distance:.2f} cm")
                correct_distance_time = 0
            elif current_distance > distance_Prevue + 10:
                if 'distance_label' in globals() and not WEB_MODE:
                    distance_label.config(text=f"Trop loin: {current_distance:.2f} cm")
                correct_distance_time = 0
            else:
                if 'distance_label' in globals() and not WEB_MODE:
                    distance_label.config(text=f"Vous êtes à la bonne distance: {current_distance:.2f} cm")
                correct_distance_time += 1
                
                if correct_distance_time >= 3:
                    snooze_alarm()  # Automatically snooze when at correct distance for 3 seconds
                    if 'distance_label' in globals() and not WEB_MODE:
                        distance_label.config(text="")
                    return
        
        # Schedule next check if still active
        if not WEB_MODE and alarm_active and 'root' in globals():
            root.after(1000, check_distance)
    except Exception as e:
        print(f"Error in check_distance: {e}")

# Function to move the servo motor
def move_servo():
    global alarm_active
    
    if not HARDWARE_AVAILABLE or not alarm_active:
        return
    
    try:
        # Move servo from 0 to 180 degrees
        for angle in range(0, 181, 1):
            servo.angle = angle
            time.sleep(SERVO_DELAY_SEC)
            
        # Move servo from 180 to 0 degrees
        for angle in range(180, -1, -1):
            servo.angle = angle
            time.sleep(SERVO_DELAY_SEC)
            
        # Continue movement while alarm is active
        if alarm_active and not WEB_MODE and 'root' in globals():
            root.after(1, move_servo)
    except Exception as e:
        print(f"Error moving servo: {e}")

# Function to update temperature and humidity
def update_weather():
    """Update temperature and humidity display every minute."""
    if not HARDWARE_AVAILABLE or WEB_MODE:
        return
    
    try:
        dht = DHT.DHT(DHTPin)
        # Try multiple times to get a valid reading
        for i in range(5):  # Try up to 5 times
            chk = dht.readDHT11()
            if chk == 0:
                humidity = dht.getHumidity()
                temperature = dht.getTemperature()
                
                if 'left_label1' in globals() and 'left_label2' in globals():
                    left_label1.config(text=f"Humidity: {humidity:.1f}%")
                    left_label2.config(text=f"Temperature: {temperature:.1f}°C")
                    print(f"Updated weather: {temperature:.1f}°C, {humidity:.1f}%")
                break
            time.sleep(0.1)  # Short delay between attempts
    except Exception as e:
        print(f"Error updating weather: {e}")
        
    # Schedule the next update
    if not WEB_MODE and 'root' in globals():
        root.after(60000, update_weather)  # Update every minute


print("Interface 1.py starting...")

# Flag to check if we're running in debug mode
DEBUG_MODE = os.environ.get('ALARM_DEBUG', '0') == '1'

# Flag to check if we're running in web mode
WEB_MODE = os.environ.get('WEB_MODE', '0') == '1'

# MQTT client for receiving commands from web interface
mqtt_client = None

def setup_mqtt_client():
    """Set up MQTT client to listen for commands from web interface"""
    global mqtt_client
    try:
        import paho.mqtt.client as mqtt
        
        # Create MQTT client with a clean session
        client_id = f'alarm-gui-{os.getpid()}'
        mqtt_client = mqtt.Client(client_id, clean_session=True)
        
        # Define callbacks
        def on_connect(client, userdata, flags, rc):
            print(f"MQTT Connected with result code {rc}")
            # Subscribe to all command topics with QoS 1 to ensure reliability
            client.subscribe("alarm/request/#", qos=1)
            # Also subscribe to the alarm/list topic to stay in sync with the web
            client.subscribe("alarm/list", qos=1)
            client.subscribe("alarm/added", qos=1)
            client.subscribe("alarm/deleted", qos=1)
            client.subscribe("alarm/toggled", qos=1)
            
            # Publish the current list of alarms so the web gets the latest state
            try:
                client.publish("alarm/list", json.dumps(alarms), qos=1, retain=True)
                print(f"Published {len(alarms)} alarms to MQTT on connect")
            except Exception as e:
                print(f"Error publishing alarm list on connect: {e}")
        
        def on_message(client, userdata, msg):
            """Process incoming MQTT messages"""
            global alarms  # Must be at the beginning of the function
        
            try:
                topic = msg.topic
                payload_text = msg.payload.decode()
                
                # Skip empty messages
                if not payload_text.strip():
                    return
                    
                try:
                    payload = json.loads(payload_text)
                    print(f"Received MQTT message on {topic}: {payload}")
                except json.JSONDecodeError:
                    print(f"Received non-JSON MQTT message on {topic}: {payload_text}")
                    payload = {"message": payload_text}
                
                # Process messages differently based on topic
                if topic == "alarm/list" and isinstance(payload, list):
                    print(f"Received alarm list from MQTT with {len(payload)} alarms")
                    # Only update if the received list is different
                    current_list_json = json.dumps(sorted(alarms, key=lambda x: x["time"]), sort_keys=True)
                    received_list_json = json.dumps(sorted(payload, key=lambda x: x["time"]), sort_keys=True)
                    
                    if current_list_json != received_list_json:
                        print("Alarm list is different, updating")
                        # Create a new list instead of modifying the existing one
                        alarms = list(payload)
                        
                        # Save to disk first
                        save_alarms()
                        
                        # Schedule UI update in main thread if in GUI mode
                        if not WEB_MODE and root is not None:
                            # Use root.after to schedule UI update on the main thread
                            root.after(100, safe_ui_update)
                
                # Process commands from web interface
                elif topic == "alarm/request/add":
                    try:
                        hour = int(payload.get('hour', 0))
                        minute = int(payload.get('minute', 0))
                        second = int(payload.get('second', 0))
                        print(f"Adding alarm from MQTT: {hour:02d}:{minute:02d}:{second:02d}")
                        success = set_alarm(hour, minute, second)
                        if success:
                            print(f"Alarm added for {hour:02d}:{minute:02d}:{second:02d}")
                            # Schedule UI update on main thread
                            if not WEB_MODE and root is not None:
                                root.after(100, safe_ui_update)
                        else:
                            print(f"Failed to add alarm for {hour:02d}:{minute:02d}:{second:02d}")
                    except Exception as e:
                        print(f"Error handling add alarm request: {e}")
                
                elif topic == "alarm/request/delete":
                    try:
                        index = int(payload.get('index', -1))
                        print(f"Deleting alarm at index {index} from MQTT")
                        if index >= 0 and index < len(alarms):
                            success = delete_alarm(index)
                            print(f"Alarm at index {index} deleted: {success}")
                            # Schedule UI update on main thread
                            if not WEB_MODE and root is not None:
                                root.after(100, safe_ui_update)
                        else:
                            print(f"Invalid alarm index: {index}")
                    except Exception as e:
                        print(f"Error handling delete alarm request: {e}")
                
                elif topic == "alarm/request/toggle":
                    try:
                        index = int(payload.get('index', -1))
                        print(f"Toggling alarm at index {index} from MQTT")
                        if index >= 0 and index < len(alarms):
                            status = toggle_alarm(index)
                            print(f"Alarm at index {index} toggled: {status}")
                            # Schedule UI update on main thread
                            if not WEB_MODE and root is not None:
                                root.after(100, safe_ui_update)
                        else:
                            print(f"Invalid alarm index: {index}")
                    except Exception as e:
                        print(f"Error handling toggle alarm request: {e}")
                
                elif topic == "alarm/request/snooze":
                    try:
                        print("Snoozing alarm from MQTT")
                        snooze_alarm()
                        print("Alarm snoozed from web interface")
                    except Exception as e:
                        print(f"Error handling snooze request: {e}")
                
                elif topic == "alarm/request/list":
                    try:
                        # Publish current alarm list
                        if mqtt_client and mqtt_client.is_connected():
                            mqtt_client.publish("alarm/list", json.dumps(alarms), qos=1)
                            print(f"Published {len(alarms)} alarms to MQTT")
                    except Exception as e:
                        print(f"Error handling list request: {e}")
                        
            except Exception as e:
                print(f"Error handling MQTT message: {e}")

        def on_disconnect(client, userdata, rc):
            print(f"MQTT disconnected with result code {rc}")
            # Try to reconnect if it wasn't a clean disconnect
            if rc != 0:
                print("Attempting to reconnect...")
                try:
                    client.reconnect()
                except Exception as e:
                    print(f"Error reconnecting: {e}")
        
        # Set callbacks
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.on_disconnect = on_disconnect
        
        # Configure reliable QoS and session persistence
        mqtt_client.max_inflight_messages_set(20)
        mqtt_client.max_queued_messages_set(100)
        
        # Connect to broker
        print("Connecting to MQTT broker...")
        mqtt_client.connect("localhost", 1883, 60)
        
        # Start MQTT client in a background thread
        mqtt_client.loop_start()
        
        print("MQTT client started for receiving web commands")
        return True
    except ImportError:
        print("paho-mqtt not installed, MQTT bidirectional control disabled")
        return False
    except Exception as e:
        print(f"Failed to set up MQTT client: {e}")
        return False

def reset_alarm_state():
    """Reset the alarm state if it gets out of sync"""
    global alarm_active
    
    # Clear the shared state
    clear_state()
    
    # Reset local state
    alarm_active = False
    
    if not WEB_MODE:
        if 'alarm_message' in globals():
            alarm_message.config(text="")
        # Fix this line - remove the 'vars()' check
        if 'snooze_button' in globals():
            try:
                snooze_button.pack_forget()
            except Exception as e:
                # Silently catch any errors to prevent them from propagating
                if DEBUG_MODE:
                    print(f"Non-critical error hiding snooze button: {e}")
    
    print("Alarm state has been reset")
    return True

if DEBUG_MODE:
    print("Debug mode enabled")

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    print("Watchdog imported successfully")
except ImportError as e:
    print(f"Error importing watchdog: {e}")
    print("Please install watchdog with: pip install watchdog")
    # Fall back to a simpler implementation without file watching
    Observer = None
    FileSystemEventHandler = object

# Import the alarm state module
try:
    # First import the module itself without functions
    import alarm_state
    print("Alarm state module imported successfully")
    
    # We'll access functions through the module to avoid circular imports
    def get_state():
        try:
            return alarm_state.get_state()
        except Exception as e:
            if DEBUG_MODE:
                print(f"Error getting alarm state: {e}")
            return {"alarm_active": False, "timestamp": 0, "message": ""}
    
    def set_state(alarm_active, message=""):
        try:
            return alarm_state.set_state(alarm_active, message)
        except Exception as e:
            if DEBUG_MODE:
                print(f"Error setting alarm state: {e}")
            return False
    
    def clear_state():
        try:
            return alarm_state.clear_state()
        except Exception as e:
            if DEBUG_MODE:
                print(f"Error clearing alarm state: {e}")
            return False
            
except ImportError as e:
    print(f"Error importing alarm_state module: {e}")
    # Fallback implementation if the module isn't available
    def get_state():
        print("Using fallback get_state implementation")
        return {"alarm_active": False, "timestamp": 0, "message": ""}
    
    def set_state(alarm_active, message=""):
        print(f"Setting alarm state (fallback): {alarm_active}, {message}")
        return True
    
    def clear_state():
        print("Clearing alarm state (fallback)")
        return True

def publish_alarm_added(time, success):
    """Publish alarm added event to MQTT"""
    if mqtt_client:
        try:
            mqtt_client.publish("alarm/added", json.dumps({
                "time": time,
                "success": success,
                "message": f"Alarm {'added' if success else 'already exists'} for {time}"
            }))
        except Exception as e:
            print(f"Error publishing alarm added event: {e}")

def publish_alarm_toggled(index, active):
    """Publish alarm toggled event to MQTT"""
    if mqtt_client:
        try:
            mqtt_client.publish("alarm/toggled", json.dumps({
                "index": index,
                "active": active,
                "time": alarms[index]["time"] if index < len(alarms) else "",
                "message": f"Alarm {'activated' if active else 'deactivated'}"
            }))
        except Exception as e:
            print(f"Error publishing alarm toggled event: {e}")

def publish_alarm_deleted(index, time):
    """Publish alarm deleted event to MQTT"""
    if mqtt_client:
        try:
            mqtt_client.publish("alarm/deleted", json.dumps({
                "index": index,
                "time": time,
                "message": f"Alarm at {time} deleted"
            }))
        except Exception as e:
            print(f"Error publishing alarm deleted event: {e}")

def publish_alarm_list():
    """Publish current alarm list to MQTT"""
    if mqtt_client:
        try:
            mqtt_client.publish("alarm/list", json.dumps(alarms))
        except Exception as e:
            print(f"Error publishing alarm list: {e}")

# File to store alarms data
ALARMS_FILE = "alarms.json"

# Liste pour stocker les alarmes
alarms = []

# Load alarms from file
def load_alarms():
    global alarms
    try:
        if os.path.exists(ALARMS_FILE):
            # Force sync to ensure we're reading the latest version
            if hasattr(os, 'sync'):
                os.sync()
                
            # Get file stats before reading
            file_size = os.path.getsize(ALARMS_FILE)
            if file_size == 0:
                print("Warning: Alarms file is empty (zero bytes)")
                alarms = []
                return False
                
            with open(ALARMS_FILE, 'r') as f:
                file_content = f.read()
                if not file_content.strip():
                    print("Warning: Alarms file is empty (no content)")
                    alarms = []
                    return False
                    
                loaded_alarms = json.loads(file_content)
                print(f"Loaded raw alarms from file: {loaded_alarms}")
                
                # Validate the structure before replacing
                valid_alarms = []
                for alarm in loaded_alarms:
                    if "time" not in alarm or "active" not in alarm:
                        print(f"Warning: Invalid alarm format: {alarm}")
                        continue
                    valid_alarms.append(alarm)
                
                # Only update if we found any valid alarms
                if valid_alarms:
                    # Update the global alarms list
                    alarms = valid_alarms
                    print(f"Loaded {len(alarms)} alarms from file")
                    return True
                else:
                    print("No valid alarms found in file")
                    return False
        else:
            print(f"Alarms file {ALARMS_FILE} does not exist")
            return False
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in alarms file: {e}")
        print(f"File content: {open(ALARMS_FILE, 'r').read() if os.path.exists(ALARMS_FILE) else 'File does not exist'}")
        return False
    except Exception as e:
        print(f"Error loading alarms: {e}")
        return False


def force_refresh_alarms():
    """Force reload alarms from file and update the display"""
    global alarms
    print("Forcing refresh of alarms from file...")
    
    # Force file sync to ensure we're reading latest version
    if hasattr(os, 'sync'):
        os.sync()
    
    # Check if the file exists
    if not os.path.exists(ALARMS_FILE):
        print(f"Warning: Alarms file {ALARMS_FILE} does not exist")
        return False
    
    # Now properly load alarms
    try:
        with open(ALARMS_FILE, 'r') as f:
            loaded_alarms = json.load(f)
            print(f"Loaded alarms content: {loaded_alarms}")
            
            # Validate the structure before replacing
            valid_alarms = []
            for alarm in loaded_alarms:
                if "time" not in alarm or "active" not in alarm:
                    print(f"Warning: Invalid alarm format: {alarm}")
                    continue
                valid_alarms.append(alarm)
            
            # Update the global alarms list
            alarms = valid_alarms
            print(f"Successfully loaded {len(alarms)} alarms from file")
            
            # Only update the display if we're in GUI mode
            if not WEB_MODE and 'root' in globals() and root is not None:
                # Schedule a safe UI update
                root.after(100, safe_ui_update)
            
            return True
    except json.JSONDecodeError as e:
        print(f"JSON parsing error in alarms file: {e}")
        # Try to fix the file with a default empty list
        try:
            with open(ALARMS_FILE, 'w') as f:
                json.dump([], f)
            print("Reset alarms file to empty list due to JSON error")
        except Exception as write_err:
            print(f"Error fixing alarms file: {write_err}")
    except Exception as e:
        print(f"Error loading alarms: {e}")
    
    return False


# Save alarms to file
def save_alarms():
    """Save alarms to file with proper flushing to ensure file modification is detected"""
    try:
        # Create a temporary file and then rename it to ensure atomic write
        temp_file = ALARMS_FILE + ".tmp"
        with open(temp_file, 'w') as f:
            json.dump(alarms, f)
            f.flush()  # Flush internal Python buffers
            os.fsync(f.fileno())  # Flush OS buffers to disk
        
        # Rename is atomic on POSIX systems
        os.rename(temp_file, ALARMS_FILE)
        
        # Force sync the directory to ensure rename is committed
        dir_fd = os.open(os.path.dirname(ALARMS_FILE) or '.', os.O_DIRECTORY)
        os.fsync(dir_fd)
        os.close(dir_fd)
        
        # Publish to MQTT after saving to file
        if mqtt_client and mqtt_client.is_connected():
            mqtt_client.publish("alarm/list", json.dumps(alarms), qos=1)
            print(f"Published {len(alarms)} alarms to MQTT after save")
        
        print(f"Saved {len(alarms)} alarms to file")
    except Exception as e:
        print(f"Error saving alarms: {e}")

# Immediate load attempt with retry
for _ in range(3):  # Try up to 3 times
    if load_alarms():
        break
    print("Retry loading alarms...")
    time.sleep(0.5)

alarm_active = False

def update_time():
    """Met à jour l'heure en temps réel."""
    current_time = time.strftime('%H:%M:%S')
    if not WEB_MODE:
        label.config(text=current_time)
    else:
        print(f"Current time: {current_time}")
    
    check_alarm(current_time)
    
    if not WEB_MODE:
        root.after(1000, update_time)  # Rafraîchit toutes les secondes

def check_alarm(current_time):
    """Vérifie si une alarme doit sonner."""
    global alarm_active, distance_Prevue
    
    # Check if we're running in GUI mode and if snooze_button exists
    has_snooze_button = 'snooze_button' in globals() if not WEB_MODE else False
    
    try:
        # First check the global alarm state from file (if toggled from web)
        state = get_state()
        
        # If alarm is active in the shared state but not locally, sync the local state
        if state["alarm_active"] and not alarm_active:
            alarm_active = True
            if not WEB_MODE:
                if 'alarm_message' in globals():
                    alarm_message.config(text="🔥 YOUPIII 🔥", fg="red")
                if has_snooze_button:
                    snooze_button.pack(pady=10)  # Show the snooze button
                
                # Start the hardware actions for the alarm
                if HARDWARE_AVAILABLE:
                    led.on()
                    buzzer.on()
                    distance_Prevue = random.uniform(0.2, 1.2) * 100  # Random expected distance
                    print(f"Distance prévue: {distance_Prevue:.2f} cm")
                    check_distance()  # Start distance checking
                    move_servo()      # Start servo movement
            else:
                print(f"🔔 ALARM TRIGGERED from web: {state['message']}")
            return
        
        # If alarm was snoozed from web but still active locally, sync the local state
        if not state["alarm_active"] and alarm_active:
            alarm_active = False
            if not WEB_MODE:
                if 'alarm_message' in globals():
                    alarm_message.config(text="")
                if has_snooze_button:
                    snooze_button.pack_forget()  # Hide the snooze button
                
                # Stop hardware actions
                if HARDWARE_AVAILABLE:
                    led.off()
                    buzzer.off()
        
        # Regular alarm checking logic
        for alarm in alarms:
            if alarm["active"] and alarm["time"] == current_time and not alarm_active:
                if not WEB_MODE:
                    if 'alarm_message' in globals():
                        alarm_message.config(text="🔥 YOUPIII 🔥", fg="red")
                    
                    if has_snooze_button:
                        snooze_button.pack(pady=10)  # Show the snooze button
                    
                    # Start hardware actions for the alarm
                    if HARDWARE_AVAILABLE:
                        led.on()
                        buzzer.on()
                        distance_Prevue = random.uniform(0.2, 1.2) * 100  # Random expected distance
                        print(f"Distance prévue: {distance_Prevue:.2f} cm")
                        check_distance()  # Start distance checking
                        move_servo()      # Start servo movement
                else:
                    print(f"🔔 ALARM TRIGGERED: {alarm['time']}")
                
                # Set the shared state for the web interface to detect
                set_state(True, f"Alarm triggered at {current_time}")
                
                alarm_active = True
                return
        
        if not alarm_active:
            if not WEB_MODE:
                if 'alarm_message' in globals():
                    alarm_message.config(text="")  # Clear message if no alarm is sounding
                
                # Only hide snooze_button if it exists
                if has_snooze_button:
                    snooze_button.pack_forget()  # Hide the snooze button
    except Exception as e:
        print(f"Error in check_alarm: {e}")
        # If an error occurs, try to recover by resetting the alarm state
        if alarm_active:
            reset_alarm_state()

def snooze_alarm():
    """Désactive le message d'alarme."""
    global alarm_active
    if not WEB_MODE:
        if 'alarm_message' in globals():
            alarm_message.config(text="")
        if 'snooze_button' in globals():
            snooze_button.pack_forget()
        
        # Turn off hardware components
        if HARDWARE_AVAILABLE:
            led.off()
            buzzer.off()
        
        # Clear any warning messages
        if 'movement_warning_label' in globals():
            movement_warning_label.config(text="")
        if 'distance_label' in globals():
            distance_label.config(text="")
    else:
        print("Alarm snoozed")
    
    # Clear the shared alarm state
    clear_state()
    
    # MQTT publish
    if mqtt_client and hasattr(mqtt_client, 'publish'):
        try:
            mqtt_client.publish("alarm/state", json.dumps({
                "alarm_active": False,
                "timestamp": time.time(),
                "message": "Alarm snoozed"
            }))
        except Exception as e:
            print(f"Error publishing alarm state: {e}")
    
    alarm_active = False

def set_alarm(hour, minute, second):
    """Ajoute une alarme avec l'heure sélectionnée."""
    if WEB_MODE and hour is not None and minute is not None and second is not None:
        alarm_time = f"{hour:02d}:{minute:02d}:{second:02d}"
    else:
        alarm_time = get_wheel_time()
    
    new_alarm = {"time": alarm_time, "active": True}
    actif = False

    # Regarder si l'alarme est déjà dans la liste 
    # Si oui, on ne l'ajoute pas
    for alarm in alarms:
        if alarm["time"] == new_alarm["time"]:
            actif = True
            break
        
    if not actif:
        alarms.append(new_alarm)
        print(f"New alarm set for {alarm_time}")
        save_alarms()
        # MQTT publish
        publish_alarm_added(alarm_time, True)
        publish_alarm_list()
        if not WEB_MODE:
            # Use the safe UI update function
            root.after(100, safe_ui_update)
        return True
    else:
        print(f"Alarm for {alarm_time} already exists")
        # MQTT publish event for duplicate alarm
        publish_alarm_added(alarm_time, False)
        return False

def update_alarm_list():
    """Met à jour l'affichage des alarmes avec une ScrollView."""
    if WEB_MODE:
        return
        
    alarms.sort(key=lambda x: x["time"])
    for widget in alarm_list_frame.winfo_children():
        widget.destroy()  # Efface les anciennes alarmes avant de les recréer

    for i, alarm in enumerate(alarms):
        frame = tk.Frame(alarm_list_frame, bg="black")
        frame.pack(fill="x", pady=2)

        # Affichage de l'heure de l'alarme
        label = tk.Label(frame, text=alarm["time"], fg="white", bg="black", width=10)
        label.pack(side="left")

        # Bouton pour activer/désactiver l'alarme
        state_btn = tk.Button(frame, text="On" if alarm["active"] else "Off", 
                              command=lambda i=i: toggle_alarm(i), width=5)
        state_btn.pack(side="left", padx=5)

        # Bouton pour modifier l'alarme
        edit_btn = tk.Button(frame, text="✏", command=lambda i=i: edit_alarm(i), width=3)
        edit_btn.pack(side="left", padx=5)

        # Bouton pour supprimer l'alarme
        delete_btn = tk.Button(frame, text="🗑", command=lambda i=i: delete_alarm(i), width=3)
        delete_btn.pack(side="left", padx=5)
    
    # Trier les alarmes par heure
    alarms.sort(key=lambda x: x["time"])
    alarm_canvas.update_idletasks()  # Met à jour la ScrollView
    alarm_canvas.config(scrollregion=alarm_canvas.bbox("all"))  # Ajuste la zone de défilement

def toggle_alarm(index):
    """Active ou désactive une alarme."""
    global alarm_active
    # Add bounds checking to avoid index errors
    if index < 0 or index >= len(alarms):
        print(f"Error: Invalid alarm index {index}")
        return "error"
        
    try:
        alarms[index]["active"] = not alarms[index]["active"]
        status = "activated" if alarms[index]["active"] else "deactivated"
        print(f"Alarm at {alarms[index]['time']} {status}")
        
        # MQTT publish
        publish_alarm_toggled(index, alarms[index]["active"])
        publish_alarm_list()
        
        # If we're deactivating an alarm that is currently triggered, also clear the alarm state
        if not alarms[index]["active"] and alarm_active:
            current_time = time.strftime('%H:%M:%S')
            if alarms[index]["time"] == current_time:
                print("Clearing active alarm state because matching alarm was deactivated")
                # Use try/except to handle the case when we're in web mode
                try:
                    # Use reset_alarm_state which has better error handling
                    reset_alarm_state()
                except Exception as e:
                    print(f"Non-critical error resetting alarm state: {e}")
                    # Still clear the state
                    clear_state()
                    alarm_active = False
        
        save_alarms()
        
        # Only try to update the UI if we're in GUI mode and the UI has been initialized
        if not WEB_MODE:
            # Check if styled_update_alarm_list is available and alarm_list_frame is defined
            if 'styled_update_alarm_list' in globals() and 'alarm_list_frame' in globals():
                try:
                    styled_update_alarm_list()
                except Exception as e:
                    print(f"Non-critical error updating alarm list: {e}")
        
        return status
    except Exception as e:
        print(f"Error toggling alarm: {e}")
        return "error"

def edit_alarm(index, hour=None, minute=None, second=None):
    """Modifie l'heure d'une alarme."""
    if WEB_MODE and hour is not None and minute is not None and second is not None:
        new_time = f"{hour:02d}:{minute:02d}:{second:02d}"
    else:
        new_time = get_wheel_time()
    
    old_time = alarms[index]["time"]
    alarms[index]["time"] = new_time
    print(f"Alarm changed from {old_time} to {new_time}")
    save_alarms()
    
    if not WEB_MODE:
        styled_update_alarm_list()
    return new_time

def delete_alarm(index):
    """Supprime une alarme."""
    if index < 0 or index >= len(alarms):
        print(f"Error: Invalid alarm index {index}")
        return False
        
    deleted_time = alarms[index]["time"]
    del alarms[index]
    print(f"Alarm at {deleted_time} deleted")
    
    # MQTT publish
    publish_alarm_deleted(index, deleted_time)
    publish_alarm_list()
    
    save_alarms()
    
    if not WEB_MODE:
        styled_update_alarm_list()
    return True

class AlarmFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(ALARMS_FILE):
            print(f"Detected changes to {ALARMS_FILE}")
            # Use a slight delay to ensure the file is completely written
            time.sleep(0.1)
            # Use the more robust force_refresh_alarms function
            force_refresh_alarms()

def styled_update_alarm_list():
    """Met à jour l'affichage des alarmes avec une ScrollView."""
    if WEB_MODE:
        return
        
    alarms.sort(key=lambda x: x["time"])
    for widget in alarm_list_frame.winfo_children():
        widget.destroy()  # Efface les anciennes alarmes avant de les recréer

    if not alarms:
        # Show a message when no alarms are set
        no_alarms = tk.Label(alarm_list_frame, text="No alarms set", 
                           font=text_font, fg="#888888", bg=CARD_BG)
        no_alarms.pack(pady=20)
        return

    for i, alarm in enumerate(alarms):
        # Create a more compact card-like frame for each alarm
        card = tk.Frame(alarm_list_frame, bg=BG_COLOR, padx=5, pady=5)  # Reduced padding
        card.pack(fill="x", pady=3, padx=3)  # Reduced padding
        
        # Top row with time and toggle
        top_row = tk.Frame(card, bg=BG_COLOR)
        top_row.pack(fill="x", expand=True)

        # Affichage de l'heure de l'alarme
        label = tk.Label(top_row, text=alarm["time"], font=text_font, 
                       fg=TEXT_COLOR, bg=BG_COLOR)
        label.pack(side="left")

        # Spacer to push toggle button to the right
        tk.Frame(top_row, bg=BG_COLOR).pack(side="left", fill="x", expand=True)

        # Toggle button with custom style
        toggle_color = SUCCESS_COLOR if alarm["active"] else "#555555"
        state_text = "ON" if alarm["active"] else "OFF"
        state_btn = tk.Button(
            top_row, 
            text=state_text, 
            command=lambda i=i: toggle_alarm(i),
            font=button_font,
            bg=toggle_color,
            fg=TEXT_COLOR,
            width=6,
            relief=tk.FLAT,
            borderwidth=0
        )
        state_btn.pack(side="right", padx=5)

        # Bottom row with edit and delete buttons
        bottom_row = tk.Frame(card, bg=BG_COLOR)
        bottom_row.pack(fill="x", pady=(10, 0))
        
        # Spacer to push buttons to the right
        tk.Frame(bottom_row, bg=BG_COLOR).pack(side="left", fill="x", expand=True)

        # Action buttons with better styling
        edit_btn = tk.Button(
            bottom_row, 
            text="✏️ Edit", 
            command=lambda i=i: edit_alarm(i),
            font=button_font,
            bg=ACCENT_COLOR,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            borderwidth=0,
            padx=10
        )
        edit_btn.pack(side="left", padx=5)

        # Bouton pour supprimer l'alarme
        delete_btn = tk.Button(
            bottom_row, 
            text="🗑️ Delete", 
            command=lambda i=i: delete_alarm(i),
            font=button_font,
            bg=DANGER_COLOR,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            borderwidth=0,
            padx=10
        )
        delete_btn.pack(side="left", padx=5)
    
    # Ajuste la zone de défilement
    alarm_canvas.update_idletasks()

def safe_ui_update():
    """Safely update UI elements from the main thread"""
    try:
        if WEB_MODE:
            return
            
        # Check if critical elements exist before attempting update
        if 'alarm_list_frame' not in globals() or 'alarm_canvas' not in globals():
            print("UI elements not ready for update")
            return
            
        # Check if root is still valid (not destroyed)
        if not root or not root.winfo_exists():
            print("Root window no longer exists")
            return
        
        # Use local copy of alarms to avoid race conditions
        local_alarms = list(alarms)
        
        # Now safely update the UI
        print("Performing safe UI update")
        
        # Clear existing alarm list
        for widget in alarm_list_frame.winfo_children():
            widget.destroy()

        # Check if alarms is empty
        if not local_alarms:
            # Show a message when no alarms are set
            try:
                no_alarms = tk.Label(alarm_list_frame, text="No alarms set", 
                                  font=text_font, fg="#888888", bg=CARD_BG)
                no_alarms.pack(pady=20)
            except Exception as e:
                print(f"Error showing empty alarms message: {e}")
            return

        # Create UI elements for each alarm
        try:
            for i, alarm in enumerate(local_alarms):
                # Create a card-like frame for each alarm
                card = tk.Frame(alarm_list_frame, bg=BG_COLOR, padx=5, pady=5)
                card.pack(fill="x", pady=3, padx=3)
                
                # Top row with time and toggle
                top_row = tk.Frame(card, bg=BG_COLOR)
                top_row.pack(fill="x", expand=True)

                # Display alarm time
                label = tk.Label(top_row, text=alarm["time"], font=text_font, 
                               fg=TEXT_COLOR, bg=BG_COLOR)
                label.pack(side="left")

                # Spacer to push toggle button to the right
                tk.Frame(top_row, bg=BG_COLOR).pack(side="left", fill="x", expand=True)

                # Toggle button with custom style
                toggle_color = SUCCESS_COLOR if alarm["active"] else "#555555"
                state_text = "ON" if alarm["active"] else "OFF"
                state_btn = tk.Button(
                    top_row, 
                    text=state_text, 
                    command=lambda i=i: toggle_alarm(i),
                    font=button_font,
                    bg=toggle_color,
                    fg=TEXT_COLOR,
                    width=6,
                    relief=tk.FLAT,
                    borderwidth=0
                )
                state_btn.pack(side="right", padx=5)

                # Bottom row with edit and delete buttons
                bottom_row = tk.Frame(card, bg=BG_COLOR)
                bottom_row.pack(fill="x", pady=(10, 0))
                
                # Spacer to push buttons to the right
                tk.Frame(bottom_row, bg=BG_COLOR).pack(side="left", fill="x", expand=True)

                # Action buttons with better styling
                edit_btn = tk.Button(
                    bottom_row, 
                    text="✏️ Edit", 
                    command=lambda i=i: edit_alarm(i),
                    font=button_font,
                    bg=ACCENT_COLOR,
                    fg=TEXT_COLOR,
                    relief=tk.FLAT,
                    borderwidth=0,
                    padx=10
                )
                edit_btn.pack(side="left", padx=5)

                # Delete button
                delete_btn = tk.Button(
                    bottom_row, 
                    text="🗑️ Delete", 
                    command=lambda i=i: delete_alarm(i),
                    font=button_font,
                    bg=DANGER_COLOR,
                    fg=TEXT_COLOR,
                    relief=tk.FLAT,
                    borderwidth=0,
                    padx=10
                )
                delete_btn.pack(side="left", padx=5)
            
            # Update the scroll region for the canvas
            alarm_canvas.update_idletasks()
            alarm_canvas.config(scrollregion=alarm_canvas.bbox("all"))
            
        except Exception as ui_error:
            print(f"Error updating alarm UI: {ui_error}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"Error in safe_ui_update: {e}")
        import traceback
        traceback.print_exc()

def force_refresh():
    """Force refresh alarms from file and update UI"""
    print("Forcing refresh of alarms...")
    # Use force_refresh_alarms which has more robust error handling
    success = force_refresh_alarms()
    print(f"Refresh {'successful' if success else 'failed'}")
    return success

def run_gui_mode():
    print("Starting GUI mode...")
    global root, label, alarm_message, snooze_button, hour_spinbox, minute_spinbox
    global second_spinbox, alarm_canvas, alarm_list_frame
    global BG_COLOR, TEXT_COLOR, ACCENT_COLOR, DANGER_COLOR, SUCCESS_COLOR, CARD_BG
    global title_font, subtitle_font, button_font, text_font
    
    # Set up file watching if Observer is available
    if Observer is not None:
        try:
            event_handler = AlarmFileHandler()
            observer = Observer()
            observer.schedule(event_handler, path='.', recursive=False)
            observer.start()
            print("File watcher started")
        except Exception as e:
            print(f"Error starting file watcher: {e}")
            observer = None
    else:
        observer = None
        print("File watching not available (watchdog not installed)")
    
    # Custom colors
    BG_COLOR = "#121212"  # Dark background
    TEXT_COLOR = "#FFFFFF"  # White text
    ACCENT_COLOR = "#BB86FC"  # Purple accent
    DANGER_COLOR = "#CF6679"  # Red for alarms/delete
    SUCCESS_COLOR = "#03DAC6"  # Teal for active states
    CARD_BG = "#1E1E1E"  # Slightly lighter than background for cards
    
    # Create the main window
    root = tk.Tk()
    print("Tk root window created")
    root.title("Horloge et Alarme")
    
    # IMPORTANT: Set window attributes in a safer way
    try:
        # Skip the problematic -type attribute entirely
        # Just set reasonable window size
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight() - 30  # Account for taskbar
        root.geometry(f"{screen_width}x{screen_height}+0+0")
        print(f"Window size set to {screen_width}x{screen_height}")
    except Exception as e:
        # Fallback to basic size if needed
        print(f"Error setting window size: {e}")
        root.geometry("800x450")
    
    # Configure the window to look nice
    root.configure(bg=BG_COLOR)
    
    # Add fullscreen toggle with F11 key
    def toggle_fullscreen(event=None):
        try:
            is_fullscreen = bool(root.attributes('-fullscreen'))
            root.attributes('-fullscreen', not is_fullscreen)
        except Exception as e:
            print(f"Error toggling fullscreen: {e}")
    
    root.bind('<F11>', toggle_fullscreen)
    root.bind('<Escape>', lambda event: root.attributes('-fullscreen', False))
    
    # Make more compact layout
    # Custom font styles - slightly smaller
    title_font = ('Helvetica', 42, 'bold')  # Reduced from 48
    subtitle_font = ('Helvetica', 20)       # Reduced from 24
    button_font = ('Helvetica', 10, 'bold')
    text_font = ('Helvetica', 12)
    
    # Main layout with two columns - adjust padding
    left_frame = tk.Frame(root, bg=BG_COLOR)
    left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)  # Reduced padding
    
    right_frame = tk.Frame(root, bg=BG_COLOR)
    right_frame.pack(side="right", fill="both", padx=10, pady=10)  # Reduced padding
    
    # Clock frame with gradient-like effect
    clock_frame = tk.Frame(left_frame, bg=CARD_BG, padx=15, pady=10,  # Reduced padding
                          highlightbackground=ACCENT_COLOR, highlightthickness=2)
    clock_frame.pack(fill="x", pady=(0, 10))  # Reduced bottom padding from 20 to 10
    
    # Title for clock section
    clock_title = tk.Label(clock_frame, text="Current Time", font=subtitle_font, 
                          fg=ACCENT_COLOR, bg=CARD_BG)
    clock_title.pack(pady=(0, 5))  # Reduced padding from 10 to 5

    # Affichage de l'heure
    label = tk.Label(clock_frame, font=title_font, fg=TEXT_COLOR, bg=CARD_BG)
    label.pack(pady=5)  # Reduced padding from 10 to 5

    # Message d'alarme container
    alarm_frame = tk.Frame(left_frame, bg=BG_COLOR)
    alarm_frame.pack(fill="x", pady=5)  # Reduced padding from 10 to 5
    
    # Message d'alarme
    alarm_message = tk.Label(alarm_frame, text="", font=subtitle_font, fg=DANGER_COLOR, bg=BG_COLOR)
    alarm_message.pack(pady=2)  # Reduced padding from 5 to 2
    
    # Create the snooze button early so it's available to check_alarm
    snooze_button = tk.Button(
        alarm_frame,
        text="SNOOZE",
        command=snooze_alarm,
        font=button_font,
        bg=DANGER_COLOR,
        fg=TEXT_COLOR,
        padx=20,
        pady=5
    )
    # Don't pack it initially - it will be shown when an alarm triggers

    # Add new alarm section
    add_alarm_frame = tk.Frame(left_frame, bg=CARD_BG, padx=15, pady=10)  # Reduced vertical padding
    add_alarm_frame.pack(fill="x", pady=5)  # Reduced padding from 10 to 5
    
    # Title for add alarm section
    add_title = tk.Label(add_alarm_frame, text="Set New Alarm", font=subtitle_font, 
                        fg=ACCENT_COLOR, bg=CARD_BG)
    add_title.pack(pady=(0, 10))  # Reduced padding from 15 to 10

    # Time selection section with scroll wheels
    time_frame = tk.Frame(add_alarm_frame, bg=CARD_BG)
    time_frame.pack(pady=5, fill="x")  # Reduced padding from 10 to 5

    # Create scrollable time wheel frames
    hour_wheel = tk.Frame(time_frame, bg=CARD_BG, highlightbackground=ACCENT_COLOR, highlightthickness=2)
    minute_wheel = tk.Frame(time_frame, bg=CARD_BG, highlightbackground=ACCENT_COLOR, highlightthickness=2)
    second_wheel = tk.Frame(time_frame, bg=CARD_BG, highlightbackground=ACCENT_COLOR, highlightthickness=2)

    # Pack the wheels side by side with separators
    hour_wheel.pack(side="left", fill="y", expand=True, padx=5)
    separator1 = tk.Label(time_frame, text=":", font=('Helvetica', 32, 'bold'), bg=CARD_BG, fg=TEXT_COLOR)
    separator1.pack(side="left")
    minute_wheel.pack(side="left", fill="y", expand=True, padx=5)
    separator2 = tk.Label(time_frame, text=":", font=('Helvetica', 32, 'bold'), bg=CARD_BG, fg=TEXT_COLOR)
    separator2.pack(side="left")
    second_wheel.pack(side="left", fill="y", expand=True, padx=5)

    # Create canvases for the scrolling effect
    hour_canvas = tk.Canvas(hour_wheel, width=60, height=150, bg=CARD_BG, 
                        highlightthickness=0, bd=0)
    minute_canvas = tk.Canvas(minute_wheel, width=60, height=150, bg=CARD_BG, 
                            highlightthickness=0, bd=0)
    second_canvas = tk.Canvas(second_wheel, width=60, height=150, bg=CARD_BG, 
                            highlightthickness=0, bd=0)

    hour_canvas.pack(fill="both", expand=True)
    minute_canvas.pack(fill="both", expand=True)
    second_canvas.pack(fill="both", expand=True)

    # Create frames that will hold the time values
    hour_frame = tk.Frame(hour_canvas, bg=CARD_BG)
    minute_frame = tk.Frame(minute_canvas, bg=CARD_BG)
    second_frame = tk.Frame(second_canvas, bg=CARD_BG)

    # Add windows to canvases
    hour_window = hour_canvas.create_window((30, 75), window=hour_frame, anchor="center")
    minute_window = minute_canvas.create_window((30, 75), window=minute_frame, anchor="center")
    second_window = second_canvas.create_window((30, 75), window=second_frame, anchor="center")

    # Create highlight area in the middle to show selected time
    for canvas in [hour_canvas, minute_canvas, second_canvas]:
        # Create highlight rectangle for the selected value
        canvas.create_rectangle(0, 60, 60, 90, fill=BG_COLOR, outline=ACCENT_COLOR)

    # Functions to create and manage time wheels
    def create_time_wheel(frame, canvas, values):
        # Clear existing widgets
        for widget in frame.winfo_children():
            widget.destroy()
            
        # Create each time value as a label
        for i, val in enumerate(values):
            label = tk.Label(frame, text=f"{val:02d}", font=('Helvetica', 20), 
                            fg=TEXT_COLOR, bg=CARD_BG, width=2)
            label.pack(pady=5)
            # Add click/touch event to select this value
            label.bind("<Button-1>", lambda e, v=val, c=canvas, f=frame: select_time_value(v, c, f))
        
        # Configure scroll region
        frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    # Function to handle scrolling
    def on_wheel_scroll(event, canvas, frame, max_val):
        # Get current scroll position
        current_y = canvas.canvasy(0)
        # Convert to item index (each item is about 40px high)
        item_height = 40
        current_index = int(current_y / item_height)
        
        # Calculate new index based on scroll direction
        if event.delta > 0:  # Scroll up
            new_index = max(current_index - 1, 0)
        else:  # Scroll down
            new_index = min(current_index + 1, max_val)
        
        # Scroll to the new position
        canvas.yview_moveto(new_index * item_height / frame.winfo_height())
        
        # Get the selected value
        selected_val = new_index % (max_val + 1)
        return selected_val

    # Function to select a time value when clicked
    def select_time_value(value, canvas, frame):
        # Calculate position to center the selected value
        item_height = 40
        canvas.yview_moveto((value * item_height) / frame.winfo_height() - 0.3)

    # Create hours, minutes, and seconds wheels
    create_time_wheel(hour_frame, hour_canvas, list(range(24)))
    create_time_wheel(minute_frame, minute_canvas, list(range(60)))
    create_time_wheel(second_frame, second_canvas, list(range(60)))

    # Add mouse wheel binding
    hour_canvas.bind("<MouseWheel>", lambda e: on_wheel_scroll(e, hour_canvas, hour_frame, 23))
    minute_canvas.bind("<MouseWheel>", lambda e: on_wheel_scroll(e, minute_canvas, minute_frame, 59))
    second_canvas.bind("<MouseWheel>", lambda e: on_wheel_scroll(e, second_canvas, second_frame, 59))

    # Add touch scrolling for touchscreens
    def start_scroll(event, canvas):
        canvas.scan_mark(event.x, event.y)
        
    def do_scroll(event, canvas):
        canvas.scan_dragto(event.x, event.y, gain=1)

    for canvas in [hour_canvas, minute_canvas, second_canvas]:
        canvas.bind("<ButtonPress-1>", lambda e, c=canvas: start_scroll(e, c))
        canvas.bind("<B1-Motion>", lambda e, c=canvas: do_scroll(e, c))
        canvas.bind("<ButtonRelease-1>", lambda e, c=canvas: snap_to_closest(e, c))

    # Define how to get the time from the wheels
    def get_wheel_time():
        # Get center position of each wheel to determine selected values
        hour_pos = hour_canvas.canvasy(0) + 75
        minute_pos = minute_canvas.canvasy(0) + 75
        second_pos = second_canvas.canvasy(0) + 75
        
        # Convert to indices (each item is about 40px high)
        item_height = 40
        hour = int((hour_pos // item_height) % 24)
        minute = int((minute_pos // item_height) % 60)
        second = int((second_pos // item_height) % 60)
        
        return f"{hour:02d}:{minute:02d}:{second:02d}"

    # Function to snap to closest value after scrolling
    def snap_to_closest(event, canvas):
        # Get current scroll position
        current_y = canvas.canvasy(0)
        # Calculate closest item position (each item is about 40px high)
        item_height = 40
        closest_item = round(current_y / item_height)
        # Snap to that position
        canvas.yview_moveto(closest_item * item_height / canvas.winfo_height())

    # Larger "Add Alarm" button for touch screens with reduced padding
    set_alarm_button = tk.Button(
        add_alarm_frame, 
        text="ADD ALARM", 
        command=lambda: set_alarm(None, None, None),
        font=('Helvetica', 14, 'bold'),
        bg=ACCENT_COLOR,
        fg=TEXT_COLOR,
        activebackground="#9065CC",
        activeforeground=TEXT_COLOR,
        relief=tk.RAISED,
        padx=20,
        pady=8,
        borderwidth=3,
        height=1,
    )
    set_alarm_button.pack(pady=10, fill="x")  # Reduced from 15 to 10

    # Title for alarm list section
    list_title = tk.Label(right_frame, text="Your Alarms", font=subtitle_font, 
                         fg=ACCENT_COLOR, bg=BG_COLOR)
    list_title.pack(pady=(0, 15), anchor="w")

    # --- ScrollView pour les alarmes - more compact ---
    alarm_container = tk.Frame(right_frame, bg=CARD_BG, padx=5, pady=5)  # Reduced padding
    alarm_container.pack(fill="both", expand=True)

    # Création du Canvas pour le scroll - adjust size for smaller screen
    alarm_canvas = tk.Canvas(alarm_container, bg=CARD_BG, width=300, height=280, 
                            borderwidth=0, highlightthickness=0)
    alarm_canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))  # Reduced padding

    # Scrollbar verticale
    scrollbar = tk.Scrollbar(alarm_container, orient="vertical", command=alarm_canvas.yview)
    scrollbar.pack(side="right", fill="y")

    # Associer la scrollbar au Canvas
    alarm_canvas.configure(yscrollcommand=scrollbar.set)

    # Frame contenant la liste des alarmes
    alarm_list_frame = tk.Frame(alarm_canvas, bg=CARD_BG)
    alarm_canvas.create_window((0, 0), window=alarm_list_frame, anchor="nw")
    
    # Inside the styled_update_alarm_list function, make cards more compact:
    def styled_update_alarm_list():
        """Met à jour l'affichage des alarmes avec une ScrollView."""
        if WEB_MODE:
            return
            
        alarms.sort(key=lambda x: x["time"])
        for widget in alarm_list_frame.winfo_children():
            widget.destroy()  # Efface les anciennes alarmes avant de les recréer

        if not alarms:
            # Show a message when no alarms are set
            no_alarms = tk.Label(alarm_list_frame, text="No alarms set", 
                               font=text_font, fg="#888888", bg=CARD_BG)
            no_alarms.pack(pady=20)
            return

        for i, alarm in enumerate(alarms):
            # Create a more compact card-like frame for each alarm
            card = tk.Frame(alarm_list_frame, bg=BG_COLOR, padx=5, pady=5)  # Reduced padding
            card.pack(fill="x", pady=3, padx=3)  # Reduced padding
            
            # Top row with time and toggle
            top_row = tk.Frame(card, bg=BG_COLOR)
            top_row.pack(fill="x", expand=True)

            # Affichage de l'heure de l'alarme
            label = tk.Label(top_row, text=alarm["time"], font=text_font, 
                           fg=TEXT_COLOR, bg=BG_COLOR)
            label.pack(side="left")

            # Spacer to push toggle button to the right
            tk.Frame(top_row, bg=BG_COLOR).pack(side="left", fill="x", expand=True)

            # Toggle button with custom style
            toggle_color = SUCCESS_COLOR if alarm["active"] else "#555555"
            state_text = "ON" if alarm["active"] else "OFF"
            state_btn = tk.Button(
                top_row, 
                text=state_text, 
                command=lambda i=i: toggle_alarm(i),
                font=button_font,
                bg=toggle_color,
                fg=TEXT_COLOR,
                width=6,
                relief=tk.FLAT,
                borderwidth=0
            )
            state_btn.pack(side="right", padx=5)

            # Bottom row with edit and delete buttons
            bottom_row = tk.Frame(card, bg=BG_COLOR)
            bottom_row.pack(fill="x", pady=(10, 0))
            
            # Spacer to push buttons to the right
            tk.Frame(bottom_row, bg=BG_COLOR).pack(side="left", fill="x", expand=True)

            # Action buttons with better styling
            edit_btn = tk.Button(
                bottom_row, 
                text="✏️ Edit", 
                command=lambda i=i: edit_alarm(i),
                font=button_font,
                bg=ACCENT_COLOR,
                fg=TEXT_COLOR,
                relief=tk.FLAT,
                borderwidth=0,
                padx=10
            )
            edit_btn.pack(side="left", padx=5)

            # Bouton pour supprimer l'alarme
            delete_btn = tk.Button(
                bottom_row, 
                text="🗑️ Delete", 
                command=lambda i=i: delete_alarm(i),
                font=button_font,
                bg=DANGER_COLOR,
                fg=TEXT_COLOR,
                relief=tk.FLAT,
                borderwidth=0,
                padx=10
            )
            delete_btn.pack(side="left", padx=5)
        
        # Ajuste la zone de défilement
        alarm_canvas.update_idletasks()

    monitor_file_changes()
    
    # Make styled_update_alarm_list accessible globally AFTER it's defined
    globals()['styled_update_alarm_list'] = styled_update_alarm_list
    
    # Initial setup of alarms - NOW it's safe to do this
    force_refresh_alarms()
    
    # Add sensor information section if hardware is available
    if HARDWARE_AVAILABLE:
        # Create sensor frame with more prominent styling
        sensor_frame = tk.Frame(left_frame, bg=CARD_BG, padx=15, pady=10,
                              highlightbackground=ACCENT_COLOR, highlightthickness=1)
        sensor_frame.pack(fill="x", pady=10)
        
        # Title for sensor section
        sensor_title = tk.Label(sensor_frame, text="Sensor Information", font=subtitle_font,
                               fg=ACCENT_COLOR, bg=CARD_BG)
        sensor_title.pack(pady=(0, 5))
        
        # Create temperature and humidity labels with initial values
        left_label1 = tk.Label(sensor_frame, text="Humidity: ---%", font=text_font,
                             fg=TEXT_COLOR, bg=CARD_BG)
        left_label1.pack(pady=2, anchor="w")
        
        left_label2 = tk.Label(sensor_frame, text="Temperature: ---°C", font=text_font,
                             fg=TEXT_COLOR, bg=CARD_BG)
        left_label2.pack(pady=2, anchor="w")
        
        # Create distance label with more info
        distance_label = tk.Label(sensor_frame, text="Distance: ---", font=text_font,
                                fg=TEXT_COLOR, bg=CARD_BG)
        distance_label.pack(pady=2, anchor="w")
        
        # Create movement warning label
        movement_warning_label = tk.Label(sensor_frame, text="", font=text_font,
                                        fg=DANGER_COLOR, bg=CARD_BG)
        movement_warning_label.pack(pady=2, anchor="w")
        
        # Start sensor updates immediately
        update_weather()
        
        # Also check acceleration immediately
        if check_movement():
            movement_warning_label.config(text="No movement detected")
        else:
            movement_warning_label.config(text="Movement detected!")
        
        update_distance_display()  # Start regular distance updates

    # Now start the main event loop with proper error handling
    print("Starting main event loop...")
    try:
        update_time()  # Start the time updates which will also check alarms
        monitor_file_changes()  # Start monitoring for file changes
        root.mainloop()
    except KeyboardInterrupt:
        print("Keyboard interrupt received, shutting down...")
    except Exception as e:
        print(f"Error in main event loop: {e}")
    finally:
        # Clean up
        print("GUI shutting down, cleaning up...")
        if observer is not None:
            try:
                observer.stop()
                observer.join(timeout=1.0)  # Wait up to 1 second
                print("File watcher stopped")
            except Exception as e:
                print(f"Error stopping file watcher: {e}")

def monitor_file_changes():
    """Monitor file changes to help with debugging"""
    if not os.path.exists(ALARMS_FILE):
        print("File does not exist yet")
        return
        
    last_modified = os.path.getmtime(ALARMS_FILE)
    file_size = os.path.getsize(ALARMS_FILE)
    print(f"File monitor: size={file_size}, last_modified={last_modified}")
    
    # Schedule next check
    if not WEB_MODE:
        root.after(5000, monitor_file_changes)

def run_web_mode():
    print("Starting alarm system in web mode")
    
    # Main loop for web mode
    while True:
        update_time()
        time.sleep(1)

def get_sensor_data():
    """Get current sensor data for web interface"""
    import time
    import random
    
    data = {
        "hardware_available": HARDWARE_AVAILABLE,
        "timestamp": time.time()
    }
    
    if not HARDWARE_AVAILABLE:
        # Return simulated data for testing
        data["temperature"] = random.uniform(20.0, 25.0)
        data["humidity"] = random.uniform(40.0, 60.0)
        data["distance"] = random.uniform(30.0, 100.0)
        data["movement_detected"] = random.choice([True, False])
        return data
    
    try:
        # Try to get temperature and humidity
        try:
            import Freenove_DHT as DHT
            dht = DHT.DHT(17)  # Using pin 17
            chk = dht.readDHT11()
            if chk == 0:
                data["temperature"] = dht.temperature
                data["humidity"] = dht.humidity
            else:
                # Fall back to simulated data
                data["temperature"] = random.uniform(20.0, 25.0)
                data["humidity"] = random.uniform(40.0, 60.0)
        except Exception as e:
            print(f"Temperature/humidity sensor error: {e}")
            data["temperature"] = random.uniform(20.0, 25.0)
            data["humidity"] = random.uniform(40.0, 60.0)
        
        # Try to get distance
        try:
            data["distance"] = ultrasonic.distance * 100  # Convert to cm
        except Exception as e:
            print(f"Ultrasonic sensor error: {e}")
            data["distance"] = random.uniform(30.0, 100.0)
        
        # Check for movement
        try:
            data["movement_detected"] = not check_movement()  # Inverted for consistency
        except Exception as e:
            print(f"Movement detection error: {e}")
            data["movement_detected"] = random.choice([True, False])
        
    except Exception as e:
        print(f"Error getting sensor data: {e}")
    
    return data

if __name__ == "__main__":
    print(f"Starting in {'web' if WEB_MODE else 'GUI'} mode")
    
    # Set up MQTT client to receive commands from web interface
    setup_mqtt_client()
    
    if WEB_MODE:
        run_web_mode()
    else:
        try:
            run_gui_mode()
        except tk.TclError as e:
            print(f"Error initializing GUI: {e}")
            print("Trying fallback GUI mode...")
            try:
                # Try without any special window attributes
                # This approach correctly redefines the run_gui_mode function
                def simplified_run_gui_mode():
                    """Simplified GUI mode with fewer features but more reliability."""
                    global root, label, alarm_message, snooze_button, alarm_canvas, alarm_list_frame
                    global BG_COLOR, TEXT_COLOR, ACCENT_COLOR, DANGER_COLOR, SUCCESS_COLOR, CARD_BG
                    global title_font, subtitle_font, button_font, text_font
                    global left_label1, left_label2, distance_label, movement_warning_label
                    
                    # Custom colors (same as original)
                    BG_COLOR = "#121212"  # Dark background
                    TEXT_COLOR = "#FFFFFF"  # White text
                    ACCENT_COLOR = "#BB86FC"  # Purple accent
                    DANGER_COLOR = "#CF6679"  # Red for alarms/delete
                    SUCCESS_COLOR = "#03DAC6"  # Teal for active states
                    CARD_BG = "#1E1E1E"  # Slightly lighter than background for cards
                    
                    # Create the main window with NO special attributes
                    root = tk.Tk()
                    root.title("Alarm System")
                    root.geometry("800x480")  # Good size for RPi screens
                    root.configure(bg=BG_COLOR)
                    
                    # Font definitions for this simplified mode
                    title_font = ('Helvetica', 36, 'bold')
                    subtitle_font = ('Helvetica', 18)
                    button_font = ('Helvetica', 10, 'bold')
                    text_font = ('Helvetica', 12)
                    
                    # Main layout with two columns
                    left_frame = tk.Frame(root, bg=BG_COLOR)
                    left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
                    
                    right_frame = tk.Frame(root, bg=BG_COLOR)
                    right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
                    
                    # Clock frame
                    clock_frame = tk.Frame(left_frame, bg=CARD_BG, padx=15, pady=10)
                    clock_frame.pack(fill="x", pady=10)
                    
                    # Clock label
                    label = tk.Label(clock_frame, font=title_font, fg=TEXT_COLOR, bg=CARD_BG)
                    label.pack(pady=5)
                    
                    # Alarm message
                    alarm_message = tk.Label(left_frame, text="", font=subtitle_font, fg=DANGER_COLOR, bg=BG_COLOR)
                    alarm_message.pack(pady=10)
                    
                    # Snooze button (hidden by default)
                    snooze_button = tk.Button(
                        left_frame,
                        text="SNOOZE",
                        command=snooze_alarm,
                        font=button_font,
                        bg=DANGER_COLOR,
                        fg=TEXT_COLOR,
                        padx=20,
                        pady=5
                    )
                    
                    # Manual time entry (simpler than wheels)
                    time_frame = tk.Frame(left_frame, bg=CARD_BG, padx=15, pady=10)
                    time_frame.pack(fill="x", pady=10)
                    
                    # Title for alarm section
                    add_title = tk.Label(time_frame, text="Add New Alarm", font=subtitle_font, 
                                       fg=ACCENT_COLOR, bg=CARD_BG)
                    add_title.pack(pady=5)
                    
                    # Simple spinbox selectors for time
                    hour_spinbox = tk.Spinbox(time_frame, from_=0, to=23, width=3, format="%02.0f")
                    minute_spinbox = tk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f")
                    second_spinbox = tk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f")
                    
                    # Layout the spinboxes
                    time_selectors = tk.Frame(time_frame, bg=CARD_BG)
                    time_selectors.pack(pady=5)
                    
                    hour_spinbox.pack(side="left", padx=2)
                    tk.Label(time_selectors, text=":", bg=CARD_BG, fg=TEXT_COLOR).pack(side="left")
                    minute_spinbox.pack(side="left", padx=2)
                    tk.Label(time_selectors, text=":", bg=CARD_BG, fg=TEXT_COLOR).pack(side="left")
                    second_spinbox.pack(side="left", padx=2)
                    
                    # Add alarm button
                    set_alarm_button = tk.Button(
                        time_frame, 
                        text="ADD ALARM", 
                        command=lambda: set_alarm(int(hour_spinbox.get()), 
                                                 int(minute_spinbox.get()), 
                                                 int(second_spinbox.get())),
                        font=button_font,
                        bg=ACCENT_COLOR,
                        fg=TEXT_COLOR,
                        padx=20,
                        pady=5
                    )
                    set_alarm_button.pack(pady=10)
                    
                    # Add sensor section for hardware if available
                    if HARDWARE_AVAILABLE:
                        sensor_frame = tk.Frame(left_frame, bg=CARD_BG, padx=15, pady=10)
                        sensor_frame.pack(fill="x", pady=10)
                        
                        sensor_title = tk.Label(sensor_frame, text="Sensor Information", font=subtitle_font,
                                              fg=ACCENT_COLOR, bg=CARD_BG)
                        sensor_title.pack(pady=5)
                        
                        left_label1 = tk.Label(sensor_frame, text="Humidity: ---%", font=text_font,
                                             fg=TEXT_COLOR, bg=CARD_BG)
                        left_label1.pack(pady=2, anchor="w")
                        
                        left_label2 = tk.Label(sensor_frame, text="Temperature: ---°C", font=text_font,
                                             fg=TEXT_COLOR, bg=CARD_BG)
                        left_label2.pack(pady=2, anchor="w")
                        
                        distance_label = tk.Label(sensor_frame, text="Distance: ---", font=text_font,
                                                fg=TEXT_COLOR, bg=CARD_BG)
                        distance_label.pack(pady=2, anchor="w")
                        
                        movement_warning_label = tk.Label(sensor_frame, text="", font=text_font,
                                                        fg=DANGER_COLOR, bg=CARD_BG)
                        movement_warning_label.pack(pady=2, anchor="w")
                    
                    # Alarm list section
                    list_title = tk.Label(right_frame, text="Your Alarms", font=subtitle_font, 
                                        fg=ACCENT_COLOR, bg=BG_COLOR)
                    list_title.pack(pady=5, anchor="w")
                    
                    # Simple alarm container
                    alarm_container = tk.Frame(right_frame, bg=CARD_BG)
                    alarm_container.pack(fill="both", expand=True)
                    
                    # Scrollable canvas
                    alarm_canvas = tk.Canvas(alarm_container, bg=CARD_BG, highlightthickness=0)
                    alarm_canvas.pack(side="left", fill="both", expand=True)
                    
                    # Scrollbar
                    scrollbar = tk.Scrollbar(alarm_container, orient="vertical", command=alarm_canvas.yview)
                    scrollbar.pack(side="right", fill="y")
                    
                    # Connect scrollbar to canvas
                    alarm_canvas.configure(yscrollcommand=scrollbar.set)
                    
                    # Frame for alarm list
                    alarm_list_frame = tk.Frame(alarm_canvas, bg=CARD_BG)
                    alarm_canvas.create_window((0, 0), window=alarm_list_frame, anchor="nw")
                    
                    # Define get_wheel_time function for compatibility
                    def get_wheel_time():
                        h = int(hour_spinbox.get())
                        m = int(minute_spinbox.get())
                        s = int(second_spinbox.get())
                        return f"{h:02d}:{m:02d}:{s:02d}"
                    
                    # Override global function
                    globals()['get_wheel_time'] = get_wheel_time
                    
                    # Create an update_alarm_list function that works with this UI
                    def simple_update_alarm_list():
                        """Simplified alarm list update function."""
                        try:
                            if WEB_MODE:
                                return
                                
                            # Sort alarms by time
                            alarms.sort(key=lambda x: x["time"])
                            
                            # Clear existing list
                            for widget in alarm_list_frame.winfo_children():
                                widget.destroy()
                            
                            # Show message if no alarms
                            if not alarms:
                                no_alarms = tk.Label(alarm_list_frame, text="No alarms set", 
                                                   font=text_font, fg="#888888", bg=CARD_BG)
                                no_alarms.pack(pady=20)
                                return
                            
                            # Create simple alarm list
                            for i, alarm in enumerate(alarms):
                                # Main frame for each alarm
                                alarm_frame = tk.Frame(alarm_list_frame, bg=CARD_BG, padx=5, pady=5)
                                alarm_frame.pack(fill="x", pady=5)
                                
                                # Time display
                                time_label = tk.Label(alarm_frame, text=alarm["time"], font=text_font, 
                                                    fg=TEXT_COLOR, bg=CARD_BG)
                                time_label.pack(side="left", padx=5)
                                
                                # Status label
                                status_color = SUCCESS_COLOR if alarm["active"] else "#555555"
                                status_label = tk.Label(alarm_frame, text="ON" if alarm["active"] else "OFF", 
                                                       font=text_font, fg=status_color, bg=CARD_BG)
                                status_label.pack(side="left", padx=10)
                                
                                # Button frame for controls
                                btn_frame = tk.Frame(alarm_frame, bg=CARD_BG)
                                btn_frame.pack(side="right")
                                
                                # Toggle button
                                toggle_btn = tk.Button(
                                    btn_frame,
                                    text="Toggle",
                                    command=lambda i=i: toggle_alarm(i),
                                    font=button_font,
                                    bg=ACCENT_COLOR,
                                    fg=TEXT_COLOR
                                )
                                toggle_btn.pack(side="left", padx=2)
                                
                                # Delete button
                                delete_btn = tk.Button(
                                    btn_frame,
                                    text="Delete",
                                    command=lambda i=i: delete_alarm(i),
                                    font=button_font,
                                    bg=DANGER_COLOR,
                                    fg=TEXT_COLOR
                                )
                                delete_btn.pack(side="left", padx=2)
                            
                            # Update canvas scroll region
                            alarm_canvas.update_idletasks()
                            alarm_canvas.config(scrollregion=alarm_canvas.bbox("all"))
                            
                        except Exception as e:
                            print(f"Error updating alarm list: {e}")
                    
                    # Override global functions
                    globals()['styled_update_alarm_list'] = simple_update_alarm_list
                    
                    # Init alarm list and start updates
                    force_refresh_alarms()
                    update_time()
                    
                    # Start sensor updates if hardware is available
                    if HARDWARE_AVAILABLE:
                        update_weather()
                        update_distance_display()
                    
                    # Start the main loop
                    root.mainloop()
                
                # Run the simplified version instead
                simplified_run_gui_mode()
                
            except Exception as e2:
                print(f"Fallback GUI mode also failed: {e2}")
                print("Starting web mode instead")
                run_web_mode()
