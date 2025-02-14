import tkinter as tk
import tkSnack
import time
from playsound import playsound

# Path to the sound file
sound_file = 't-rex-roar.mp3'

# Play the sound file
playsound(sound_file)

# Liste pour stocker les alarmes
alarms = []

def update_time():
    """Met à jour l'heure en temps réel."""
    current_time = time.strftime('%H:%M:%S')
    label.config(text=current_time)
    check_alarm(current_time)
    root.after(1000, update_time)  # Rafraîchit toutes les secondes

def check_alarm(current_time):
    """Vérifie si une alarme doit sonner."""
    for alarm in alarms:
        if alarm["active"] and alarm["time"] == current_time:
            alarm_message.config(text="🔥 YOUPIII 🔥", fg="red")
            return  # Affiche "YOUPIII" dès qu'une alarme est déclenchée
    alarm_message.config(text="")  # Efface le message si aucune alarme ne sonne

def set_alarm():
    """Ajoute une alarme avec l'heure sélectionnée."""
    alarm_time = f"{hour_spinbox.get()}:{minute_spinbox.get()}:{second_spinbox.get()}"
    
    alarm = {"time": alarm_time, "active": True}
    alarms.append(alarm)
    update_alarm_list()

def update_alarm_list():
    """Met à jour l'affichage des alarmes avec une ScrollView."""
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

    alarm_canvas.update_idletasks()  # Met à jour la ScrollView
    alarm_canvas.config(scrollregion=alarm_canvas.bbox("all"))  # Ajuste la zone de défilement

def toggle_alarm(index):
    """Active ou désactive une alarme."""
    alarms[index]["active"] = not alarms[index]["active"]
    update_alarm_list()

def edit_alarm(index):
    """Modifie l'heure d'une alarme."""
    new_time = f"{hour_spinbox.get()}:{minute_spinbox.get()}:{second_spinbox.get()}"
    alarms[index]["time"] = new_time
    update_alarm_list()

def delete_alarm(index):
    """Supprime une alarme."""
    del alarms[index]
    update_alarm_list()

# Création de la fenêtre principale
root = tk.Tk()
root.title("Horloge et Alarme")
root.geometry("1000x800")
root.configure(bg='black')

# Affichage de l'heure
label = tk.Label(root, font=('Helvetica', 48), fg='white', bg='black')
label.pack(expand=True)

# Message d'alarme
alarm_message = tk.Label(root, text="", font=('Helvetica', 20), fg='red', bg='black')
alarm_message.pack(pady=10)

# Section pour sélectionner une heure
time_frame = tk.Frame(root, bg="black")
time_frame.pack(pady=5)

# Sélecteurs pour les heures, minutes et secondes
hour_spinbox = tk.Spinbox(time_frame, from_=0, to=23, width=3, format="%02.0f", wrap=True)
minute_spinbox = tk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f", wrap=True)
second_spinbox = tk.Spinbox(time_frame, from_=0, to=59, width=3, format="%02.0f", wrap=True)

hour_spinbox.pack(side="left", padx=2)
tk.Label(time_frame, text=":", bg="black", fg="white").pack(side="left")
minute_spinbox.pack(side="left", padx=2)
tk.Label(time_frame, text=":", bg="black", fg="white").pack(side="left")
second_spinbox.pack(side="left", padx=2)

# Bouton pour ajouter une alarme
set_alarm_button = tk.Button(root, text="Ajouter une alarme", command=set_alarm)
set_alarm_button.pack(pady=5)

# --- ScrollView pour les alarmes ---
alarm_container = tk.Frame(root, bg="black")
alarm_container.pack(side="right", fill="y", padx=10, pady=10)

# Création du Canvas pour le scroll
alarm_canvas = tk.Canvas(alarm_container, bg="black", width=300, height=200)
alarm_canvas.pack(side="left", fill="both", expand=True)

# Scrollbar verticale
scrollbar = tk.Scrollbar(alarm_container, orient="vertical", command=alarm_canvas.yview)
scrollbar.pack(side="right", fill="y")

# Associer la scrollbar au Canvas
alarm_canvas.configure(yscrollcommand=scrollbar.set)

# Frame contenant la liste des alarmes
alarm_list_frame = tk.Frame(alarm_canvas, bg="black")
alarm_canvas.create_window((0, 0), window=alarm_list_frame, anchor="nw")

# Démarrer la mise à jour de l'horloge
update_time()

# Lancer l'application
root.mainloop()
