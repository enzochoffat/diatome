import sys
import os
import csv
import os
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path 



def export_data_outputs():
    #formaliser les données en listes de float  
    p = Path(__file__).parent
    file_path = (p / ".." / ".."/ "outputs").resolve()
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
        if GET_ALL_FISH == True : 
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

population_evolution()





