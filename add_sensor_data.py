import re

# Read the interface_1.py file
with open('interface_1.py', 'r') as file:
    content = file.read()

# Check if function already exists
if 'def get_sensor_data():' in content:
    print("get_sensor_data function already exists in interface_1.py")
    exit(0)

# Find a good place to insert the function
# Looking for global variable declarations
global_section = re.search(r'# Initialize variables for sensors[^\n]*', content)
if not global_section:
    print("Could not find sensors initialization section")
    exit(1)

# Position right after it
insert_point = global_section.end()

# Prepare the function to insert
function_to_add = '''

# Function to get sensor data for web interface
def get_sensor_data():
    """Get current sensor data for web interface"""
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

'''

# Add the function at the insert point
content = content[:insert_point] + function_to_add + content[insert_point:]

# Write the modified content back
with open('interface_1.py', 'w') as file:
    file.write(content)

print("Successfully added get_sensor_data function to interface_1.py")