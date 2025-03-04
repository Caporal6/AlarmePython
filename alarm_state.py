import json
import os
import time

STATE_FILE = "alarm_state.json"

def get_state():
    """Get the current alarm state"""
    try:
        if os.path.exists(STATE_FILE):
            # Force sync to ensure we're reading the latest version
            os.sync()
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                return state
        else:
            return {"alarm_active": False, "timestamp": 0, "message": ""}
    except Exception as e:
        print(f"Error reading state: {e}")
        return {"alarm_active": False, "timestamp": 0, "message": ""}

def set_state(alarm_active, message=""):
    """Set the current alarm state"""
    try:
        state = {
            "alarm_active": alarm_active,
            "timestamp": time.time(),
            "message": message
        }
        
        # Create a temporary file and then rename it to ensure atomic write
        temp_file = STATE_FILE + ".tmp"
        with open(temp_file, 'w') as f:
            json.dump(state, f)
            f.flush()  # Flush internal Python buffers
            os.fsync(f.fileno())  # Flush OS buffers to disk
        
        # Rename is atomic on POSIX systems
        os.rename(temp_file, STATE_FILE)
        
        # Force sync the directory to ensure rename is committed
        dir_fd = os.open(os.path.dirname(STATE_FILE) or '.', os.O_DIRECTORY)
        os.fsync(dir_fd)
        os.close(dir_fd)
        
        return True
    except Exception as e:
        print(f"Error writing state: {e}")
        return False

def clear_state():
    """Clear the alarm state"""
    return set_state(False, "")