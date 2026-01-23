import sys
import os
import csv
import os
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path 



def lire_csv_en_listes(fichier_csv):
    with open(fichier_csv, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        lignes = list(reader)
    
    headers = lignes[1]  # Ligne 2 : noms des colonnes
    headers[0] = 'time'  # S'assurer que la première colonne s'appelle 'time'

    
    donnees = {header: [] for header in headers}
    time = []
    for row in lignes[2:] : 
        time.append(row[0])

    for row in lignes[2:]:
        for i, valeur in enumerate(row):
            if i < len(headers):
                donnees[headers[i]].append(valeur)

    return donnees, time, headers

#formaliser les données en listes de float  
p = Path(__file__).parent
file_path = (p / ".." / ".."/ "outputs").resolve()
# Lister les fichiers .csv directement dans ce dossier
fichiers_csv = [
    f for f in os.listdir(file_path)
    if os.path.isfile(os.path.join(file_path, f)) and f.lower().endswith('.csv')]

# Boucle pour traiter chaque fichier
for fichier in fichiers_csv:
    chemin_complet = os.path.join(file_path, fichier)
    print(f"Traitement du fichier : {chemin_complet}")
    donnees = lire_csv_en_listes(chemin_complet)[0]
    time = np.array(lire_csv_en_listes(chemin_complet)[1])
    headers = lire_csv_en_listes(chemin_complet)[2]
    #traiter les fichiers time et donnees
    time = list(map(float, time))
    for key, value in donnees.items() : 
        for str in donnees[key] : 
            donnees[key] = list(map(float, donnees[key]))
    #test d'affichage
    for key, value in donnees.items() : 
        test = donnees[key]
        plt.plot(time, test)
        title = os.path.basename(chemin_complet).split('/')[-1]
        plt.title(title)
    plt.show()

#pour accéder aux outputs de chaque simulation 
#acces = donnees[headers[i]]
#print(acces, headers[i])



           





