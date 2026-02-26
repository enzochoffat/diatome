import sys
import os
import csv
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path 
import tkinter as tk
from tkinter import filedialog

def choisir_fichiers_csv():
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
    try:
        return float(s)
    except (ValueError, TypeError):
        return s


def pop_evol_over_time(): 
    p = Path(__file__).parent
    file_path = (p / ".." / ".."/ "Ecospace_outputs/biomass").resolve()
    # Lister les fichiers .csv directement dans ce dossier
    fichiers_csv = [f for f in os.listdir(file_path) 
                    if os.path.isfile(os.path.join(file_path, f)) 
                    and f.lower().endswith('.csv')]
    for fichier in fichiers_csv:
        chemin_complet = os.path.join(file_path, fichier)

        with open(chemin_complet, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=',')
            rows = [[safe_float(cell) for cell in row] for row in reader]

        maps = dict(dates = [], map = [])
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
                        month = '0'
                    maps['dates'] += [[year] + [month]]
                    maps['map'].append(rows[start: start + maps_row])
        
        break

def pop_evol_over_time_test():
    file_paths = choisir_fichiers_csv()
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

    print(len(dic_tot['maps']['dates']))
    print(dic_tot['esp'])

pop_evol_over_time_test()

def pop_evol_over_time_alone(f): 
        reader = csv.reader(f, delimiter=',')
        rows = list(reader)
        print(rows)
        for row in rows : 
            print(row[0])
            if row[0] == 'Year' : 
                date = row[1] 
                print(row[0])
            break

#print(pop_evol_over_time_alone('/home/agathe/Documents/CS/3A/projet/diatome/Ecospace_outputs/biomass/EcospaceMapBiomass-Bacteria.csv'))


def export_data_outputs():
    #formaliser les données en listes de float  
    p = Path(__file__).parent
    file_path = (p / ".." / ".."/ "Ecospace_outputs").resolve()
    # Lister les fichiers .csv directement dans ce dossier
    fichiers_csv = [f for f in os.listdir(file_path) 
                    if os.path.isfile(os.path.join(file_path, f)) 
                    and f.lower().endswith('.csv')]

    # Boucle pour traiter chaque fichier
    for fichier in fichiers_csv:
        chemin_complet = os.path.join(file_path, fichier)

        with open(chemin_complet, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=',')
            rows = list(reader)

        headers = rows[1]
    
        data = {header: [] for header in headers}
        time = []           

        #construire la liste contenant toutes les données 
        for row in rows[2:]:
            time.append(row[0])
            for i, valeur in enumerate(row):
                if i < len(headers):
                    data[headers[i]].append(valeur)
        data.pop(headers[0])

        #récupérer time comme liste et data comme disctionnaire
        time = list(map(float, time))
        for key, value in data.items() :
            data[key] = list(map(float, data[key]))

    return data, time, headers


end_of_sim = 120
current_step = 15
GET_ALL_FISH = True
STUDIED_SPECIES = {'OctopusVulgaris','MelicertusKerathurus', 'TrachurusTrachurus'}

def population_evolution() : 
    "Descripton of the fishes population evolution based on Ecospace's outputs."
    evol = export_data_outputs()
    data = evol[0]
    time = evol[1]
    headers = evol[2]
    if end_of_sim == len(time) :
        if GET_ALL_FISH : 
            a = []
            for key in data.keys() :
                a.append(data[key])
            all_fishes = list(map(sum, zip(*a)))
            print(all_fishes)
            current_sock = {'all' : all_fishes[current_step]}
        else : 
            studied_data = {key: data[key] for key in data.keys() & STUDIED_SPECIES}
            for species in range(len(studied_data)) :
                return(type(species))

#population_evolution()





