import tkinter as tk
import time
import os
import sys
import json
import threading
from pathlib import Path

print("Interface 1.py starting...")

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
    from alarm_state import set_state, clear_state
except ImportError:
    # Fallback implementation if the module isn't available
    def set_state(alarm_active, message=""):
        print(f"Setting alarm state: {alarm_active}, {message}")
        return True
    
    def clear_state():
        print("Clearing alarm state")
        return True

# File to store alarms data
ALARMS_FILE = "alarms.json"

# Liste pour stocker les alarmes
alarms = []

# Flag to check if we're running in web mode
WEB_MODE = os.environ.get('WEB_MODE', '0') == '1'

# Load alarms from file
def load_alarms():
    global alarms
    try:
        if os.path.exists(ALARMS_FILE):
            with open(ALARMS_FILE, 'r') as f:
                alarms = json.load(f)
                print(f"Loaded {len(alarms)} alarms from file")
    except Exception as e:
        print(f"Error loading alarms: {e}")

# Save alarms to file
def save_alarms():
    try:
        with open(ALARMS_FILE, 'w') as f:
            json.dump(alarms, f)
            print(f"Saved {len(alarms)} alarms to file")
    except Exception as e:
        print(f"Error saving alarms: {e}")

# Load alarms at startup
load_alarms()

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
    for alarm in alarms:
        if alarm["active"] and alarm["time"] == current_time and not alarm_active:
            if not WEB_MODE:
                alarm_message.config(text="🔥 YOUPIII 🔥", fg="red")
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
            update_alarm_list()
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
        update_alarm_list()
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
        update_alarm_list()
    return new_time

def delete_alarm(index):
    """Supprime une alarme."""
    deleted_time = alarms[index]["time"]
    del alarms[index]
    print(f"Alarm at {deleted_time} deleted")
    save_alarms()
    
    if not WEB_MODE:
        update_alarm_list()
    return True

class AlarmFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(ALARMS_FILE):
            print(f"Detected changes to {ALARMS_FILE}")
            load_alarms()
            if not WEB_MODE:
                update_alarm_list()

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
    root.geometry("800x480")
    root.configure(bg=BG_COLOR)
    
    # Custom font styles
    title_font = ('Helvetica', 48, 'bold')
    subtitle_font = ('Helvetica', 24)
    button_font = ('Helvetica', 10, 'bold')
    text_font = ('Helvetica', 12)
    
    # Main layout with two columns
    left_frame = tk.Frame(root, bg=BG_COLOR)
    left_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)
    
    right_frame = tk.Frame(root, bg=BG_COLOR)
    right_frame.pack(side="right", fill="both", padx=20, pady=20)
    
    # Clock frame with gradient-like effect
    clock_frame = tk.Frame(left_frame, bg=CARD_BG, padx=15, pady=15, 
                          highlightbackground=ACCENT_COLOR, highlightthickness=2)
    clock_frame.pack(fill="x", pady=(0, 20))
    
    # Title for clock section
    clock_title = tk.Label(clock_frame, text="Current Time", font=subtitle_font, 
                          fg=ACCENT_COLOR, bg=CARD_BG)
    clock_title.pack(pady=(0, 10))

    # Affichage de l'heure
    label = tk.Label(clock_frame, font=title_font, fg=TEXT_COLOR, bg=CARD_BG)
    label.pack(pady=10)

    # Message d'alarme container
    alarm_frame = tk.Frame(left_frame, bg=BG_COLOR)
    alarm_frame.pack(fill="x", pady=10)
    
    # Message d'alarme
    alarm_message = tk.Label(alarm_frame, text="", font=subtitle_font, fg=DANGER_COLOR, bg=BG_COLOR)
    alarm_message.pack(pady=5)

    # Bouton Snooze with custom style
    snooze_button = tk.Button(
        alarm_frame, 
        text="SNOOZE", 
        command=snooze_alarm,
        font=button_font,
        bg=DANGER_COLOR,
        fg=TEXT_COLOR,
        activebackground="#A03A45",  # Darker shade for pressed state
        activeforeground=TEXT_COLOR,
        relief=tk.FLAT,
        padx=20,
        pady=10,
        borderwidth=0
    )
    # Not packed initially - will be shown when alarm triggers
    
    # Add new alarm section
    add_alarm_frame = tk.Frame(left_frame, bg=CARD_BG, padx=15, pady=15)
    add_alarm_frame.pack(fill="x", pady=10)
    
    # Title for add alarm section
    add_title = tk.Label(add_alarm_frame, text="Set New Alarm", font=subtitle_font, 
                        fg=ACCENT_COLOR, bg=CARD_BG)
    add_title.pack(pady=(0, 15))

    # Section pour sélectionner une heure
    time_frame = tk.Frame(add_alarm_frame, bg=CARD_BG)
    time_frame.pack(pady=5)

    # Style for spinboxes
    spinbox_style = {
        'width': 3, 
        'format': "%02.0f", 
        'wrap': True,
        'bg': BG_COLOR,
        'fg': TEXT_COLOR,
        'buttonbackground': ACCENT_COLOR,
        'font': text_font
    }

    # Sélecteurs pour les heures, minutes et secondes
    hour_spinbox = tk.Spinbox(time_frame, from_=0, to=23, **spinbox_style)
    minute_spinbox = tk.Spinbox(time_frame, from_=0, to=59, **spinbox_style)
    second_spinbox = tk.Spinbox(time_frame, from_=0, to=59, **spinbox_style)

    # Add more padding and style between spinboxes
    hour_spinbox.pack(side="left", padx=5)
    separator1 = tk.Label(time_frame, text=":", font=title_font, bg=CARD_BG, fg=TEXT_COLOR)
    separator1.pack(side="left")
    minute_spinbox.pack(side="left", padx=5)
    separator2 = tk.Label(time_frame, text=":", font=title_font, bg=CARD_BG, fg=TEXT_COLOR)
    separator2.pack(side="left")
    second_spinbox.pack(side="left", padx=5)

    # Bouton pour ajouter une alarme
    set_alarm_button = tk.Button(
        add_alarm_frame, 
        text="ADD ALARM", 
        command=lambda: set_alarm(None, None, None),
        font=button_font,
        bg=ACCENT_COLOR,
        fg=TEXT_COLOR,
        activebackground="#9065CC",  # Darker shade for pressed state
        activeforeground=TEXT_COLOR,
        relief=tk.FLAT,
        padx=20,
        pady=10,
        borderwidth=0
    )
    set_alarm_button.pack(pady=15)

    # Title for alarm list section
    list_title = tk.Label(right_frame, text="Your Alarms", font=subtitle_font, 
                         fg=ACCENT_COLOR, bg=BG_COLOR)
    list_title.pack(pady=(0, 15), anchor="w")

    # --- ScrollView pour les alarmes ---
    alarm_container = tk.Frame(right_frame, bg=CARD_BG, padx=10, pady=10)
    alarm_container.pack(fill="both", expand=True)

    # Création du Canvas pour le scroll
    alarm_canvas = tk.Canvas(alarm_container, bg=CARD_BG, width=320, height=300, 
                            borderwidth=0, highlightthickness=0)
    alarm_canvas.pack(side="left", fill="both", expand=True, padx=(0, 10))

    # Scrollbar verticale
    scrollbar = tk.Scrollbar(alarm_container, orient="vertical", command=alarm_canvas.yview)
    scrollbar.pack(side="right", fill="y")

    # Associer la scrollbar au Canvas
    alarm_canvas.configure(yscrollcommand=scrollbar.set)

    # Frame contenant la liste des alarmes
    alarm_list_frame = tk.Frame(alarm_canvas, bg=CARD_BG)
    alarm_canvas.create_window((0, 0), window=alarm_list_frame, anchor="nw")
    
    # Override the update_alarm_list function for better styling
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
            # Create a card-like frame for each alarm
            card = tk.Frame(alarm_list_frame, bg=BG_COLOR, padx=10, pady=10)
            card.pack(fill="x", pady=5, padx=5)
            
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
        alarm_canvas.config(scrollregion=alarm_canvas.bbox("all"))
    
    # Replace the original update_alarm_list
    global update_alarm_list
    update_alarm_list = styled_update_alarm_list
    
    # Update the alarm list
    update_alarm_list()
    
    # Démarrer la mise à jour de l'horloge
    update_time()

    try:
        # Lancer l'application
        root.mainloop()
    finally:
        observer.stop()
        observer.join()

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
