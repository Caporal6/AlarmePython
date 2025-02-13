import tkinter as tk
import time

def update_time():
    current_time = time.strftime('%H:%M:%S')
    label.config(text=current_time)
    root.after(1000, update_time)  # Mettre à jour toutes les secondes


def show_alarm_section():
    alarm_label.config(text="Ajouter une alarme :")
    alarm_entry.pack()
    set_alarm_button.pack()


def set_alarm():
    alarm_time = alarm_entry.get()
    alarm_label.config(text=f"Alarme réglée à {alarm_time}")


# Création de la fenêtre principale
root = tk.Tk()
root.title("Horloge en temps réel")
root.geometry("500x500")
root.configure(bg='black')


# Création du label pour afficher l'heure
label = tk.Label(root, font=('Helvetica', 48), fg='white', bg='black')
label.pack(expand=True)


# Ajout d'une section pour les alarmes
tk.Button(root, text="Ajouter une alarme", command=show_alarm_section).pack(pady=10)
alarm_label = tk.Label(root, text="", fg='white', bg='black')
alarm_label.pack()
alarm_entry = tk.Entry(root)
set_alarm_button = tk.Button(root, text="Régler l'alarme", command=set_alarm)


#Label pour acceuillir le sensore
labelSensor = tk.Label(root, text="Mettre les donner de distance ici", fg='white', bg='black')
labelSensor.pack(pady=10)

#Label pour acceuillir le sensore Thermique
labelThermique = tk.Label(root, text="Mettre les donner de thermique", fg='white', bg='black')
labelThermique.pack(pady=10)

#Label pour acceuillir le sensore photocell
labelPhotocell = tk.Label(root, text="Mettre les donner de photocell", fg='white', bg='black')
labelPhotocell.pack(pady=10)


#Label qui s'acctualise toute les 2 sec
test = 0
labelTest = tk.Label(root, text=str(test))
labelTest.pack(pady=20)


def test_sensore():
    global test
    test +=1
    labelTest.config(text=str(test))
    root.after(1000,test_sensore)


#Démarrer la fonction
test_sensore()






# Lancer la mise à jour du temps
update_time()

# Démarrer la boucle principale de l'interface
root.mainloop()




