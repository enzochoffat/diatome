import sys
import os
import csv
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path 
import tkinter as tk
from tkinter import filedialog

def choose_csv_file():
    """
    Ouvre une fenêtre pour sélectionner un ou plusieurs fichiers CSV.
    Retourne une liste des chemins absolus des fichiers sélectionnés.
    Retourne une liste vide si aucun fichier n’est sélectionné.
    """
    root = tk.Tk()
    root.withdraw()  # Masque la fenêtre principale

    file_paths = filedialog.askopenfilenames(
        title="Sélectionnez un ou plusieurs fichiers CSV",
        filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
    )

    # Convertit en chemins absolus et filtre les chaînes vides
    file_paths = [os.path.abspath(p) for p in file_paths] if file_paths else []

    return file_paths

def safe_float(s):
    "Retourne un float si possible, sinon la valeur initiale"
    try:
        return float(s)
    except (ValueError, TypeError):
        return s

def pop_evol_over_time_test():
    """
    Utilise choose_csv_file() pour obtenir la liste des fichiers que l'utilisateur veut étudier
    Retourne un dictionnaire de dictionnaire contenant en premier item le nom des espèces étudiées
    et en deuxième item un dictionnaire contenant en premier item les dates associées aux maps qui
    sont dans le deuxième item 
    """
    file_paths = choose_csv_file()
    dic_tot = dict(esp = [], maps = dict(dates = [], map = []))
    maps = dic_tot['maps']
    for fichier in file_paths:
        name_file = os.path.basename(fichier).split('/')[-1]
        dic_tot['esp'].append(name_file)

        with open(fichier, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=',')
            rows = [[safe_float(cell) for cell in row] for row in reader]
        
        
        for nb, row in enumerate(rows) : 
            if row : 
                if row[0] == 'MapRows' : 
                    maps_row = int(row[1])
                if row[0] == 'Year' : 
                    year = row[1] 
                    start = nb + 1
                    if len(row) > 2 : 
                        month = row[2]
                    else : 
                        month = 0
                    maps['dates'].append([year] + [month])
                    maps['map'].append(rows[start: start + maps_row])

    return dic_tot


### pour ajouter ces informations au code initial, il faut changer la fonction update_fish_stock 