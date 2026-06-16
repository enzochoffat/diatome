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


def configure_sources(topology_map_path=None, wind_farm_map_path=None, species_map_paths=None):
    """Configure the CSV sources used by the module."""
    global TOPOLOGY_MAP_PATH, WINDFARM_MAP_PATH, SPECIES_MAP_PATHS, _ecospace_data_cache

    if topology_map_path is not None:
        TOPOLOGY_MAP_PATH = str(topology_map_path)
    if wind_farm_map_path is not None:
        WINDFARM_MAP_PATH = str(wind_farm_map_path)
    if species_map_paths is not None:
        SPECIES_MAP_PATHS = [str(path) for path in species_map_paths]

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
    file_paths = SPECIES_MAP_PATHS if SPECIES_MAP_PATHS is not None else choose_csv_file()

    dic_tot = {
        'species': [],
        'maps': {
            'dates': [],
            'map': []
        },
        'maps_per_species': {}
    }

    if not file_paths:
        return dic_tot
    
    all_species_data = []
    
    for fichier in file_paths:
        name_file = os.path.basename(fichier).split('/')[-1]
        species_maps = []
        dates_list = []
        maps_list = []

        current_map_rows = 0
        reading_map = False
        current_map_data = []
        rows_read_count = 0

        try:
            with open(fichier, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=',')

                for row in reader:
                    if not row:
                        continue

                    cell_0 = row[0].strip()

                    if cell_0 == 'MapRows':
                        current_map_rows = int(row[1])
                        continue

                    if cell_0 == 'Year':
                        if reading_map and current_map_data:
                            map_array = np.array(current_map_data, dtype=np.float64)
                            maps_list.append(map_array)
                            current_map_data = []
                            rows_read_count = 0
                        
                        year = safe_float(row[1])
                        month = safe_float(row[2]) if len(row) > 2 else 0
                        dates_list.append([year, month])

                        reading_map = True
                        continue

                    if reading_map:
                        if rows_read_count < current_map_rows:
                            try:
                                line_data = [safe_float(cell) for cell in row]
                                current_map_data.append(line_data)
                                rows_read_count += 1
                            except Exception as e:
                                print(f"Error processing row in file {fichier}: {e}")
                                continue
                        
                        elif rows_read_count == current_map_rows:
                            continue

                if reading_map and current_map_data:
                    map_array = np.array(current_map_data, dtype=np.float64)
                    maps_list.append(map_array)

        except Exception as e:
            print(f"Error reading file {fichier}: {e}")
            continue

        if maps_list and dates_list:
            all_species_data.append({
                'name': name_file,
                'dates': dates_list,
                'maps': maps_list
            })
        
    if not all_species_data:
        return dic_tot
    
    ref_dates = all_species_data[0]['dates']
    ref_shape = all_species_data[0]['maps'][0].shape
    num_dates = len(ref_dates)

    valid_species = []
    for data in all_species_data:
        if len(data['dates']) == num_dates:
            if data['maps'][0].shape == ref_shape:
                valid_species.append(data)

    if not valid_species:
        valid_species = [all_species_data[0]]

    stack_maps = np.array([sp['maps'] for sp in valid_species])

    summed_maps_array = np.sum(stack_maps, axis=0)

    summed_maps_formatted = [[[m]] for m in summed_maps_array]
    summed_dates = ref_dates

    per_species_maps = {}
    for sp in valid_species:
            formatted_maps_sp = [[m] for m in sp['maps']]
            per_species_maps[sp['name']] = {
                'dates': sp['dates'],
                'map': formatted_maps_sp
            }

    dic_tot = {
        'species': [sp['name'] for sp in valid_species],
        'maps': {
            'dates': summed_dates,
            'map': summed_maps_formatted
        },
        'maps_per_species': per_species_maps
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