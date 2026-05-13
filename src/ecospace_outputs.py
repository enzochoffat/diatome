import sys
import os
import csv
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path 
import tkinter as tk
from tkinter import filedialog

_ecospace_data_cache = None

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
    


def get_ecospace_data():
    """Charge les données Ecospace une seule fois et les met en cache"""
    global _ecospace_data_cache
    if _ecospace_data_cache is None:
        _ecospace_data_cache = pop_evol_over_time()
    return _ecospace_data_cache

def pop_evol_over_time(): #modifié pour renvoyer une carte par date qui est la somme des cartes de toutes les espèces (avoir la concentration totale de poissons)
    """
    Selects CSV files from user and extracts population evolution data over time.
    
    Returns:
        dict: Dictionary with structure:
        {
            'species': [list of species filenames],
            'maps': {
                'dates': [[year, month], ...] for each species,
                'map': [[[matrix for each date]], ...] for each species
            }
        }
        
        Each matrix has dimensions [MapRows][width] and contains concentration values in g/L
    """
    file_paths = choose_csv_file()
    esp = []
    date = []
    maps = []
    
    for fichier in file_paths:
        name_file = os.path.basename(fichier).split('/')[-1]
        species_maps = []
        species_dates = []

        with open(fichier, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=',')
            rows = [[safe_float(cell) for cell in row] for row in reader]
        for row in rows : 
            if row : 
                if row[0] == 'MapRows' : 
                    maps_row = int(row[1])
        
        for nb, row in enumerate(rows) : 
            if row : 
                if row[0] == 'Year' : 
                    year = row[1] 
                    start = nb + 1
                    if len(row) > 2 : 
                        month = row[2]
                    else : 
                        month = 0
                    species_dates.append([year, month])
                    species_maps.append([rows[start: start + maps_row]])

        date.append(species_dates)
        maps.append(species_maps)
        esp.append(name_file)

    # Sommer les concentrations par date (somme toutes espèces)
    if maps:  # Vérifier qu'on a des données
        num_dates = len(maps[0])  # Nombre de dates (supposé identique pour toutes espèces)
        summed_maps = []
        summed_dates = maps[0][:num_dates]  # Utiliser les dates de la première espèce
        
        for date_idx in range(num_dates):
            summed_map = None
            for species_idx in range(len(maps)):
                current_map = np.array(maps[species_idx][date_idx][0])
                if summed_map is None:
                    summed_map = current_map.copy()
                else:
                    summed_map = summed_map + current_map
            summed_maps.append([summed_map])
        per_species_maps = {}
        for species_idx, species_name in enumerate(esp):
            per_species_maps[species_name] = {
                'dates' : maps[0][:num_dates],
                'map' : [maps[species_idx][date_idx][0] for date_idx in range(num_dates)]
            }
        dic_tot = {
            'species': esp,
            'maps': {
                'dates': summed_dates,
                'map': summed_maps
            },
            'maps_per_species' : per_species_maps
        }

    return dic_tot

def masks(topology = False, windfarm = False):
    """
    Lit un fichier CSV et retourne une matrice (liste de listes) servant de masque.
    - Ignore la première ligne (en-tête).
    - Ignore la première colonne de chaque ligne.
    - Si la valeur est 0, le masque contient 0.
    - Si la valeur est non nulle, le masque contient cette valeur.
    Renvoie un dictionnaire contenant une matrice et le fichier étudié  

    This is used for topology maps
    """
    masks = []
    names = []
    if topology : 
        file_paths = [str(Path(__file__).parent.parent / 'Ecospace_outputs/topology/EEC_NS_Mmermaid-Depth.csv')]
    elif windfarm : 
        file_paths = [str(Path(__file__).parent.parent / 'Ecospace_outputs/topology/EEC_NS_Mmermaid-Windfarms.csv')]
    else:
        file_paths = choose_csv_file()
    for fichier in file_paths : 
        name_file = os.path.basename(fichier).split('/')[-1]
        names.append(name_file)
        mask_file = []
        
        with open(fichier, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=',')
            # Ignorer la première ligne (en-tête)
            next(reader, None)
        
            for row in reader:
                # Ignorer la première colonne 
                ligne_masque = []
                for cell in row[1:]:
                    if cell : 
                        val = safe_float(cell)
                        ligne_masque.append(val)
                
                mask_file.append(ligne_masque)
        
        masks.append(mask_file)
    
    named_masks = {
        'name of the masks' : names ,
        'masks' : masks
    }
    

    return named_masks

def plot_masks():
    """
    Affiche les masques en tant qu'heatmaps (images).
    Chaque masque est affiché dans un subplot séparé.
    """
    result = masks()
    mask_list = result['masks']
    names = result['name of the masks']
    
    # Convertir les listes de listes en arrays numpy pour le plotting
    mask_arrays = [np.array(mask) for mask in mask_list]
    
    # Créer un subplot pour chaque masque
    num_masks = len(mask_arrays)
    fig, axes = plt.subplots(1, num_masks, figsize=(5*num_masks, 5))
    
    # Si un seul masque, axes n'est pas un array
    if num_masks == 1:
        axes = [axes]
    
    for idx, (mask_array, name) in enumerate(zip(mask_arrays, names)):
        im = axes[idx].imshow(mask_array, cmap='viridis', aspect='auto')
        axes[idx].set_title(name)
        axes[idx].set_xlabel('Longitude')
        axes[idx].set_ylabel('Latitude')
        plt.colorbar(im, ax=axes[idx])
    
    plt.tight_layout()
    plt.show()



### pour ajouter ces informations au code initial, il faut changer la fonction update_fish_stock 
## on fais un masque grace à la vraie carte étudiée donnée par le fichier ecospace baie de seine 
# pour chaque espèce on peut alors rassembler certaines cases d'écospace pour faire correspondre avec 
# la carte du modèle, en prenant la moyenne des concentrations de poissons dans chaque case de la grille finale