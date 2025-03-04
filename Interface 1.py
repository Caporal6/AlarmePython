import tkinter as tk
import time
import os
import sys
import json
import threading
from pathlib import Path

print("Interface 1.py starting...")

# Flag to check if we're running in debug mode
DEBUG_MODE = os.environ.get('ALARM_DEBUG', '0') == '1'

# Flag to check if we're running in web mode
WEB_MODE = os.environ.get('WEB_MODE', '0') == '1'

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
    
    # Clear current alarms
    alarms = []
    
    # Force file sync to ensure we're reading latest version
    if hasattr(os, 'sync'):
        os.sync()
    
    # Check if the file exists
    if not os.path.exists(ALARMS_FILE):
        print(f"Warning: Alarms file {ALARMS_FILE} does not exist")
        return False
    
    # Try reading the file directly first to check content
    try:
        with open(ALARMS_FILE, 'r') as f:
            file_content = f.read()
            print(f"Alarm file raw content: {file_content}")
    except Exception as e:
        print(f"Error reading alarm file directly: {e}")
    
    # Now properly load alarms
    try:
        if os.path.exists(ALARMS_FILE):
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
                
                # Update the display if in GUI mode
                if not WEB_MODE and 'styled_update_alarm_list' in globals():
                    styled_update_alarm_list()
                    
                return True
        else:
            print(f"Alarms file {ALARMS_FILE} does not exist")
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
    global alarm_active
    
    # Check if we're running in GUI mode and if snooze_button exists
    has_snooze_button = 'snooze_button' in globals() if not WEB_MODE else False
    
    # First check the global alarm state from file (if toggled from web)
    state = get_state()
    
    # If alarm is active in the shared state but not locally, sync the local state
    if state["alarm_active"] and not alarm_active:
        alarm_active = True
        if not WEB_MODE:
            alarm_message.config(text="🔥 YOUPIII 🔥", fg="red")
            if has_snooze_button:
                snooze_button.pack(pady=10)  # Affiche le bouton Snooze
        else:
            print(f"🔔 ALARM TRIGGERED from web: {state['message']}")
        return
    
    # If alarm was snoozed from web but still active locally, sync the local state
    if not state["alarm_active"] and alarm_active:
        alarm_active = False
        if not WEB_MODE:
            alarm_message.config(text="")
            if has_snooze_button:
                snooze_button.pack_forget()
    
    # Regular alarm checking logic
    for alarm in alarms:
        if alarm["active"] and alarm["time"] == current_time and not alarm_active:
            if not WEB_MODE:
                alarm_message.config(text="🔥 YOUPIII 🔥", fg="red")
                
                # Only use snooze_button if it exists
                if has_snooze_button:
                    snooze_button.pack(pady=10)  # Affiche le bouton Snooze
            else:
                print(f"🔔 ALARM TRIGGERED: {alarm['time']}")
            
            # Set the shared state for the web interface to detect
            set_state(True, f"Alarm triggered at {current_time}")
            
            alarm_active = True
            return  # Affiche "YOUPIII" dès qu'une alarme est déclenchée
    
    if not alarm_active:
        if not WEB_MODE:
            alarm_message.config(text="")  # Efface le message si aucune alarme ne sonne
            
            # Only hide snooze_button if it exists
            if has_snooze_button:
                snooze_button.pack_forget()  # Cache le bouton Snooze

def snooze_alarm():
    """Désactive le message d'alarme."""
    global alarm_active
    if not WEB_MODE:
        alarm_message.config(text="")
        snooze_button.pack_forget()
    else:
        print("Alarm snoozed")
    
    # Clear the shared alarm state
    clear_state()
    
    alarm_active = False

def set_alarm(hour, minute, second):
    """Ajoute une alarme avec l'heure sélectionnée."""
    if WEB_MODE:
        alarm_time = f"{hour:02d}:{minute:02d}:{second:02d}"
    else:
        alarm_time = f"{hour_spinbox.get()}:{minute_spinbox.get()}:{second_spinbox.get()}"
    
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
        if not WEB_MODE:
            styled_update_alarm_list()
        return True
    else:
        print(f"Alarm for {alarm_time} already exists")
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
    alarms[index]["active"] = not alarms[index]["active"]
    status = "activated" if alarms[index]["active"] else "deactivated"
    print(f"Alarm at {alarms[index]['time']} {status}")
    save_alarms()
    
    if not WEB_MODE:
        styled_update_alarm_list()
    return status

def edit_alarm(index, hour=None, minute=None, second=None):
    """Modifie l'heure d'une alarme."""
    if WEB_MODE and hour is not None and minute is not None and second is not None:
        new_time = f"{hour:02d}:{minute:02d}:{second:02d}"
    else:
        new_time = f"{hour_spinbox.get()}:{minute_spinbox.get()}:{second_spinbox.get()}"
    
    old_time = alarms[index]["time"]
    alarms[index]["time"] = new_time
    print(f"Alarm changed from {old_time} to {new_time}")
    save_alarms()
    
    if not WEB_MODE:
        styled_update_alarm_list()
    return new_time

def delete_alarm(index):
    """Supprime une alarme."""
    deleted_time = alarms[index]["time"]
    del alarms[index]
    print(f"Alarm at {deleted_time} deleted")
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

# Move styled_update_alarm_list to global scope for use by other functions
globals()['styled_update_alarm_list'] = styled_update_alarm_list

# Initial setup of alarms - ensure we're starting with the latest data
force_refresh_alarms()
styled_update_alarm_list()

def force_refresh():
    """Force refresh alarms from file and update UI"""
    print("Forcing refresh of alarms...")
    # Use force_refresh_alarms which has more robust error handling
    success = force_refresh_alarms()
    print(f"Refresh {'successful' if success else 'failed'}")
    return success

def run_gui_mode():
    global root, label, alarm_message, snooze_button, hour_spinbox, minute_spinbox
    global second_spinbox, alarm_canvas, alarm_list_frame
    
    # Set up file watching
    event_handler = AlarmFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    
    # Custom colors
    BG_COLOR = "#121212"  # Dark background
    TEXT_COLOR = "#FFFFFF"  # White text
    ACCENT_COLOR = "#BB86FC"  # Purple accent
    DANGER_COLOR = "#CF6679"  # Red for alarms/delete
    SUCCESS_COLOR = "#03DAC6"  # Teal for active states
    CARD_BG = "#1E1E1E"  # Slightly lighter than background for cards
    
    # Création de la fenêtre principale
    root = tk.Tk()
    root.title("Horloge et Alarme")
    
    # Account for taskbar by making the window slightly smaller than 800x450
    root.geometry("800x450")  # 30 pixels for taskbar
    
    # Set the window to fullscreen but account for taskbar
    # Uncomment one of these approaches:
    # 1. No decorations but not true fullscreen (keeps taskbar visible)
    root.attributes('-type', 'dock')  # For Linux/X11
    
    # 2. Alternative method for Raspberry Pi
    # root.overrideredirect(True)  # Remove window decorations
    # root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight() - 30))
    
    root.configure(bg=BG_COLOR)
    
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

    # Section pour sélectionner une heure
    time_frame = tk.Frame(add_alarm_frame, bg=CARD_BG)
    time_frame.pack(pady=5)  # Reduced padding from 10 to 5

    # Style for spinboxes with integrated up/down buttons
    spinbox_style = {
        'width': 3,
        'format': "%02.0f", 
        'wrap': True,
        'bg': BG_COLOR,
        'fg': TEXT_COLOR,
        'buttonbackground': ACCENT_COLOR,
        'font': ('Helvetica', 24, 'bold'),
        'justify': 'center',
        'bd': 2,
        'relief': tk.RIDGE,
    }

    # Sélecteurs pour les heures, minutes et secondes
    hour_spinbox = tk.Spinbox(time_frame, from_=0, to=23, **spinbox_style)
    minute_spinbox = tk.Spinbox(time_frame, from_=0, to=59, **spinbox_style)
    second_spinbox = tk.Spinbox(time_frame, from_=0, to=59, **spinbox_style)

    # Add more padding and larger separators between spinboxes
    hour_spinbox.pack(side="left", padx=8)
    separator1 = tk.Label(time_frame, text=":", font=('Helvetica', 32, 'bold'), bg=CARD_BG, fg=TEXT_COLOR)
    separator1.pack(side="left")
    minute_spinbox.pack(side="left", padx=8)
    separator2 = tk.Label(time_frame, text=":", font=('Helvetica', 32, 'bold'), bg=CARD_BG, fg=TEXT_COLOR)
    separator2.pack(side="left")
    second_spinbox.pack(side="left", padx=8)

    # Remove the separate control buttons frame and use the spinbox built-in buttons
    # Make sure the spinbox buttons are visible and large enough
    for spinbox in [hour_spinbox, minute_spinbox, second_spinbox]:
        spinbox.config(buttondownrelief=tk.RAISED, buttonuprelief=tk.RAISED)
        # Make the spinbox buttons more visible by highlighting them
        spinbox.config(highlightbackground=ACCENT_COLOR, highlightthickness=2)

    # Define increment/decrement functions for keyboard or external button access
    def increment_spinbox(spinbox):
        current = int(spinbox.get())
        max_val = int(spinbox.cget('to'))
        spinbox.delete(0, 'end')
        spinbox.insert(0, f"{(current + 1) % (max_val + 1):02d}")
    
    def decrement_spinbox(spinbox):
        current = int(spinbox.get())
        max_val = int(spinbox.cget('to'))
        spinbox.delete(0, 'end')
        spinbox.insert(0, f"{(current - 1) % (max_val + 1):02d}")
    
    # Add keyboard bindings for easier control
    hour_spinbox.bind('<Up>', lambda e: increment_spinbox(hour_spinbox))
    hour_spinbox.bind('<Down>', lambda e: decrement_spinbox(hour_spinbox))
    minute_spinbox.bind('<Up>', lambda e: increment_spinbox(minute_spinbox))
    minute_spinbox.bind('<Down>', lambda e: decrement_spinbox(minute_spinbox))
    second_spinbox.bind('<Up>', lambda e: increment_spinbox(second_spinbox))
    second_spinbox.bind('<Down>', lambda e: decrement_spinbox(second_spinbox))

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
    
    # Initial setup of alarms
    styled_update_alarm_list()
    
    # Initialize GUI with periodic checks
    initialize_gui()
    
    try:
        # Lancer l'application
        root.mainloop()
    finally:
        observer.stop()
        observer.join()

def initialize_gui():
    """Additional initialization for GUI mode"""
    # Force refresh of alarms when starting up
    force_refresh_alarms()
    
    # Schedule regular checks for changes in alarms file
    def periodic_alarm_check():
        force_refresh_alarms()
        root.after(5000, periodic_alarm_check)  # Check every 5 seconds
    
    # Start the periodic check
    root.after(5000, periodic_alarm_check)
    update_time()
    monitor_file_changes()

    try:
        # Lancer l'application
        root.mainloop()
    finally:
        observer.stop()
        observer.join()

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

if __name__ == "__main__":
    print(f"Starting in {'web' if WEB_MODE else 'GUI'} mode")
    if WEB_MODE:
        run_web_mode()
    else:
        run_gui_mode()
