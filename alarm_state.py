import json
import os
import time

STATE_FILE = "alarm_state.json"

def get_state():
    """Get the current alarm state"""
    try:
        if os.path.exists(STATE_FILE):
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
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
        return True
    except Exception as e:
        print(f"Error writing state: {e}")
        return False

def clear_state():
    """Clear the alarm state"""
    return set_state(False, "")