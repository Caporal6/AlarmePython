import tkinter as tk
import time 
from gpiozero import LED, Button, Buzzer, DistanceSensor, AngularServo
import random
import Freenove_DHT as DHT
import MPU6050 
import math


# Déclaration LED
led = LED(6)

myGPIO = 25
SERVO_DELAY_SEC = 0.001
myCorrection = 0.0
maxPW = (2.5 + myCorrection) / 1000
minPW = (0.5 - myCorrection) / 1000

# Initialisation du servo avec un angle initial défini
servo = AngularServo(myGPIO, initial_angle=0, min_angle=0, max_angle=180, min_pulse_width=minPW, max_pulse_width=maxPW)

# ...existing code...
# Liste pour stocker les alarmes
alarms = []

# Liste pour stocker les dernières distances mesurées
distance_history = []
stable_time = 0  # Timer pour la stabilité de l'alarme

# Configuration de l'accéléromètre
mpu = MPU6050.MPU6050()     # instancier un objet MPU6050
accel = [0]*3               # tableau pour stocker les données de l'accéléromètre
gyro = [0]*3                # tableau pour stocker les données du gyroscope

# Initialisation de l'accéléromètre
def setup():
    mpu.dmp_initialize()    # initialiser le MPU6050

#Declaration Buzzer 
buzzer = Buzzer(18)


#Declaration Sensor
ultrasonic = DistanceSensor(echo=19,trigger=4, max_distance=4)

#Declaration boucle buzzer
alarm_active = False

#Declaration meteo et humidite
DHTPin = 17







def update_time():
    """Met à jour l'heure en temps réel."""
    current_time = time.strftime('%H:%M:%S')
    label.config(text=current_time)
    check_alarm(current_time)
    root.after(1000, update_time)  # Rafraîchit toutes les secondes



def check_alarm(current_time):
    """Vérifie si une alarme doit sonner."""
    global alarm_active, distance_Prevue
    for alarm in alarms:
        if alarm["active"] and alarm["time"] == current_time and not alarm_active:
            alarm_message.config(text="🔥 YOUPIII 🔥", fg="red")
            led.on()
            buzzer.on()
            alarm_active = True
            distance_Prevue = random.uniform(0.2, 1.2) * 100  # Initialiser distance_Prevue en cm
            print(f"Distance prévue: {distance_Prevue:.2f} cm")
            distance()  # Démarre la mise à jour de la distance
            snooze_button.pack(pady=10)  # Affiche le bouton Snooze
            move_servo()  # Démarre le mouvement du servo
            return  # Affiche "YOUPIII" dès qu'une alarme est déclenchée
    if not alarm_active:
        alarm_message.config(text="")  # Efface le message si aucune alarme ne sonne
        snooze_button.pack_forget()  # Cache le bouton Snooze

def move_servo():
    """Fait faire des allers-retours au servo sans pause."""
    for angle in range(0, 181, 1):
        servo.angle = angle
        time.sleep(SERVO_DELAY_SEC)
    for angle in range(180, -1, -1):
        servo.angle = angle
        time.sleep(SERVO_DELAY_SEC)
    if alarm_active:
        root.after(1, move_servo)  # Continue le mouvement tant que l'alarme est active

def snooze_alarm():
    """Désactive le message d'alarme."""
    global alarm_active
    alarm_message.config(text="")
    snooze_button.pack_forget()
    buzzer.off()
    led.off()
    alarm_active = False
    movement_warning_label.config(text="")  # Efface le message de mouvement excessif

def set_alarm():
    """Ajoute une alarme avec l'heure sélectionnée."""
    alarm_time = f"{hour_spinbox.get()}:{minute_spinbox.get()}:{second_spinbox.get()}"
    
    new_alarm = {"time": alarm_time, "active": True}
    actif = False

    # Regarder si l'alarme est déjà dans la liste 
    # Si oui, on ne l'ajoute pas
    for alarm in alarms:
        if new_alarm == alarm:
            actif = True
        
    if not actif:
        alarms.append(new_alarm)
        update_alarm_list()

def update_alarm_list():
    alarms.sort(key=lambda x: x["time"])
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
    # Trier les alarmes par heure
    alarms.sort(key=lambda x: x["time"])
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


# Variables globales pour la dernière accélération et gyroscope
last_accel = [0, 0, 0]
last_gyro = [0, 0, 0]
movement_threshold = 1000  # seuil de détection du mouvement normal
excessive_movement_threshold = 15000  # seuil pour un mouvement excessif
excessive_rotation_threshold = 2000  # seuil pour une rotation excessive
movement_warning_label = None  # Assurez-vous que cette variable est bien initialisée

# Fonction pour calculer la variation (changement) d'un vecteur entre deux points
def calculate_variation(new_values, last_values):
    return [abs(new_values[i] - last_values[i]) for i in range(len(new_values))]

# Fonction améliorée pour vérifier les mouvements
def check_movement():
    global last_accel, last_gyro

    accel = mpu.get_acceleration()  # récupérer les données de l'accéléromètre
    gyro = mpu.get_rotation()  # récupérer les données du gyroscope
    print(f"Accélération: {accel} Gyroscope: {gyro}")


    # Calculer la variation de l'accélération et de la rotation par rapport aux dernières valeurs
    accel_variation = calculate_variation(accel, last_accel)
    gyro_variation = calculate_variation(gyro, last_gyro)

    # Mettre à jour les dernières valeurs d'accélération et de rotation
    last_accel = accel
    last_gyro = gyro

    # Calculer la magnitude de l'accélération et de la rotation pour déterminer l'intensité
    accel_magnitude = math.sqrt(accel[0]**2 + accel[1]**2 + accel[2]**2)
    gyro_magnitude = math.sqrt(gyro[0]**2 + gyro[1]**2 + gyro[2]**2)

    # Si la variation d'accélération ou de rotation dépasse les seuils, c'est un mouvement excessif
    if any(variation > excessive_movement_threshold for variation in accel_variation) or any(variation > excessive_rotation_threshold for variation in gyro_variation):
        movement_warning_label.config(text="Mouvement excessif détecté!")
        return False  # Mouvement excessif détecté
    # Sinon, si l'intensité de l'accélération ou de la rotation est suffisante, il y a un mouvement
    elif accel_magnitude > movement_threshold or gyro_magnitude > movement_threshold:
        return True  # Mouvement détecté
    return False  # Aucun mouvement détecté

# Fonction pour vérifier la distance et activer les alertes
def distance():
    global alarm_active, correct_distance_time

    if alarm_active:

        current_distance = ultrasonic.distance * 100  # Convertir en cm
        if not check_movement():
            movement_warning_label.config(text="Mouvement détecté!")
        else:
            movement_warning_label.config(text="")
            if current_distance < distance_Prevue - 10:
                distance_label.config(text=f"Trop proche: {current_distance:.2f} cm")
                correct_distance_time = 0  # Réinitialiser le timer si la distance est incorrecte
            elif current_distance > distance_Prevue + 10:
                distance_label.config(text=f"Trop loin: {current_distance:.2f} cm")
                correct_distance_time = 0  # Réinitialiser le timer si la distance est incorrecte
            else:
                distance_label.config(text=f"Vous êtes à la bonne distance: {current_distance:.2f} cm")
                correct_distance_time += 1  # Incrémenter le timer si la distance est correcte
                if correct_distance_time >= 3:  # Vérifier si l'utilisateur est à la bonne distance pendant 3 secondes
                    snooze_alarm()  # Mettre l'alarme en veille
                    distance_label.config(text="")  # Afficher un message
                    return
        root.after(1000, distance)  # Planifie la prochaine vérification





# Initialize the correct distance timer
correct_distance_time = 0




def loop():
	dht = DHT.DHT(DHTPin)
	#create a DHT class object
	counts = 0 # Measurement counts

	while(True):
		counts += 1
		print("Measurement counts: ", counts)
		for i in range(0,15):
			chk = dht.readDHT11()
	#read DHT11 and get a return value. Then determine
			if (chk == 0):
	#read DHT11 and get a return value. Then determine
				print("DHT11,OK!")
				break
			time.sleep(0.1)

		print("Humidity : %.2f, \t Temperature : %.2f \n"%( dht.getHumidity(),
dht.getTemperature()))

def update_weather():
    """Met à jour l'humidité et la température toutes les minutes."""
    dht = DHT.DHT(DHTPin)
    chk = dht.readDHT11()
    if chk == 0:
        humidity = dht.getHumidity()
        temperature = dht.getTemperature()
        left_label1.config(text=f"Humidité: {humidity:.2f}%")
        left_label2.config(text=f"Température: {temperature:.2f}°C")
    root.after(60000, update_weather)  # Rafraîchit toutes les minutes

# Création de la fenêtre principale
root = tk.Tk()
root.title("SmartAlarm")
root.geometry("1000x800")
root.configure(bg='black')

# Frame principale pour l'affichage de l'heure et les labels
main_frame = tk.Frame(root, bg='black')
main_frame.pack(expand=True, fill='both')

# Frame pour les labels de gauche
left_frame = tk.Frame(main_frame, bg='black')
left_frame.pack(side='left', padx=10, pady=10)

# Frame pour l'affichage de l'heure
time_frame = tk.Frame(main_frame, bg='black')
time_frame.pack(side='left', padx=10, pady=10)

# Frame pour les labels de droite
right_frame = tk.Frame(main_frame, bg='black')
right_frame.pack(side='left', padx=10, pady=10)



# Message d'alarme
alarm_message = tk.Label(root, text="", font=('Helvetica', 20), fg='red', bg='black')
alarm_message.pack(pady=10)

# Bouton Snooze
snooze_button = tk.Button(root, text="Arret", command=snooze_alarm)

# Labels à gauche de l'heure
left_label1 = tk.Label(left_frame, text="Humidité: ", font=('Helvetica', 20), fg='white', bg='black')
left_label1.pack(pady=5)

left_label2 = tk.Label(left_frame, text="Température: ", font=('Helvetica', 20), fg='white', bg='black')
left_label2.pack(pady=5)



#label pour la distance
distance_label = tk.Label(right_frame, text="Distance: ", font=('Helvetica', 20), fg='white', bg='black')
distance_label.pack(pady=5)

# Ajout du label pour avertir de trop grands déplacements
movement_warning_label = tk.Label(right_frame, text="", font=('Helvetica', 16), fg='yellow', bg='black')
movement_warning_label.pack(pady=5)

# Affichage de l'heure
label = tk.Label(time_frame, font=('Helvetica', 48), fg='white', bg='black')
label.pack(expand=True)

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

# Démarrer la mise à jour de l'horloge et de la météo
update_time()
update_weather()

# Lancer l'application
root.mainloop()
