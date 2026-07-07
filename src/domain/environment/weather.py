
import random


def determine_weather(model) -> bool:
    model.bad_weather = (
        random.random() < model.bad_weather_probability
    )
    return model.bad_weather

# On aura un vecteur journalier d'hauteur de vagues moyennes dans la zone d'études. Pour chaque flottille un seuil d'hauteur de vagues.

# Dans chaque flottille un paramètre d'hauteur de vagues

# Créer un fichier pour les courants marins, load d'une carte jounalière.

# Faut que chaque agent puisse lire la carte des profondeur et espèces

# Ajouter dans la config des cartes de zones interdites, et un chemin vers le vecteur d'ouverture de ces zones

# A voir plus tard l'ouverture des parcs éolien (fermés, navigation, pêches)

# Récupérer dans ecopath le tableau "off vessel price" 

# Faire une carte de distance à la côte.

# Regarder comment avoir les agents aux alentours du patch

# Calculer la distance du port à la zone de pêche, A* (pour éviter les zones interdites)