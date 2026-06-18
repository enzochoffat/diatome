import sys
import os
import csv
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path 
import tkinter as tk
from tkinter import filedialog

_ecospace_data_cache = None
_PROJECT_ROOT = Path(__file__).parent.parent
TOPOLOGY_MAP_PATH = str(_PROJECT_ROOT / 'Ecospace_outputs/topology/EEC_NS_Mmermaid-Depth.csv')
WINDFARM_MAP_PATH = str(_PROJECT_ROOT / 'Ecospace_outputs/topology/EEC_NS_Mmermaid-Windfarms.csv')
SPECIES_MAP_PATHS = None
SPECIES_MAP_NAMES = None


def configure_sources(topology_map_path=None, wind_farm_map_path=None, species_map_paths=None):
    """Configure the CSV sources used by the module."""
    global TOPOLOGY_MAP_PATH, WINDFARM_MAP_PATH, SPECIES_MAP_PATHS, _ecospace_data_cache

    if topology_map_path is not None:
        TOPOLOGY_MAP_PATH = str(topology_map_path)
    if wind_farm_map_path is not None:
        WINDFARM_MAP_PATH = str(wind_farm_map_path)
    if species_map_paths is not None:
        SPECIES_MAP_PATHS = species_map_paths


    _ecospace_data_cache = get_ecospace_data()  # Refresh cache when sources are configured

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
    file_paths = SPECIES_MAP_PATHS if SPECIES_MAP_PATHS is not None else choose_csv_file()
    species_names = SPECIES_MAP_NAMES if SPECIES_MAP_NAMES is not None else None
    #print(f"Selected files: {file_paths}")
    #print(f"file_paths type: {type(file_paths)}")
    if not file_paths:
        return None  # Return None if no files are selected
    
    species_names = []
    species_data = []
    
    for species_name, fichier in file_paths.items():
        #print(" ")
        #print(f"Processing species {species_name} with path {fichier}")
        species_names.append(species_name)
        maps = np.genfromtxt(fichier, delimiter=',', skip_header=1)[:, 1:]  # Skip header and first column
        species_data.append(maps)

    global_map = np.stack(species_data, axis=2)  # Stack all species data into a 3D array

    #print(f"global_map shape: {global_map.shape}")  # Should be (MapRows, width, num_species)
    #print(f"species_names: {species_names}")
    idx = {i: name for i, name in enumerate(species_names)}
    #print(f"{global_map[180, 20, 1]} is the concentration of species tkt at position (180, 20)")
    #print(f"{global_map[20, 180, 1]} is the concentration of species tkt at position (20, 180)")

    return global_map, species_names


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
        file_paths = [TOPOLOGY_MAP_PATH]
    elif windfarm : 
        file_paths = [WINDFARM_MAP_PATH]
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

def plot_masks(masks=None, title="Masks"):
    """
    Plots the given masks using matplotlib.
    
    Args:
        masks: List of 2D arrays (masks) to plot. If None, uses the default masks.
        title: Title for the plot.
    """
    if masks is None:
        masks = [np.array(m['masks'][0]) for m in masks(topology=True, windfarm=True)['masks']]
    
    num_masks = len(masks)
    fig, axes = plt.subplots(1, num_masks, figsize=(5 * num_masks, 5))
    
    if num_masks == 1:
        axes = [axes]
    
    for ax, mask in zip(axes, masks):
        im = ax.imshow(mask, cmap='viridis', interpolation='nearest')
        ax.set_title(title)
        plt.colorbar(im, ax=ax)
    
    plt.tight_layout()
    plt.show()



### pour ajouter ces informations au code initial, il faut changer la fonction update_fish_stock 
## on fais un masque grace à la vraie carte étudiée donnée par le fichier ecospace baie de seine 
# pour chaque espèce on peut alors rassembler certaines cases d'écospace pour faire correspondre avec 
# la carte du modèle, en prenant la moyenne des concentrations de poissons dans chaque case de la grille finale