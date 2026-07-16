
import random

from typing import Dict, Any
from datetime import datetime, timedelta


def determine_weather(model) -> bool:
    model.bad_weather = (
        random.random() < model.bad_weather_probability
    )
    return model.bad_weather

# v On aura un vecteur journalier d'hauteur de vagues moyennes dans la zone d'études. Pour chaque flottille un seuil d'hauteur de vagues.

# v Dans chaque flottille un paramètre d'hauteur de vagues

# v Créer un fichier pour les courants marins, load d'une carte jounalière.

# Faut que chaque agent puisse lire la carte des profondeur et espèces

# Ajouter dans la config des cartes de zones interdites, et un chemin vers le vecteur d'ouverture de ces zones

# A voir plus tard l'ouverture des parcs éolien (fermés, navigation, pêches)

# Récupérer dans ecopath le tableau "off vessel price" 

# Faire une carte de distance à la côte.

# Regarder comment avoir les agents aux alentours du patch

# Calculer la distance du port à la zone de pêche, A* (pour éviter les zones interdites)

# faire une liste de comment ajouter une nouvelle flottille


def read_wave_height_vector(wave_height_vector_path: str) -> Dict[datetime, float]:
    """Reads the wave height vector from a CSV file specified in the model's configuration.

    Args:
        wave_height_vector_path: The path to the wave height vector CSV file.

    Returns:
        Dict[datetime, float]: A dictionary mapping dates to wave height values.
    """
    global VECTOR_WAVE_HEIGHT
    
    wave_height_vector = {}

    with open(wave_height_vector_path, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                date_str, wave_height_str = line.strip().split(';')
                date = datetime.strptime(date_str, '%d/%m/%Y').date()
                #print(f"Read wave height for date {date}: {wave_height_str}")
                wave_height = float(wave_height_str)
                wave_height_vector[date] = wave_height
            except ValueError:
                # Handle the case where conversion to float fails
                #print(f"Warning: Could not convert wave height to float for line: {line.strip()}")
                continue

    VECTOR_WAVE_HEIGHT = wave_height_vector
    print(f"Loaded wave height vector with {len(VECTOR_WAVE_HEIGHT)} entries.")

    return VECTOR_WAVE_HEIGHT

def get_wave_height(model) -> float:
    """Retrieve the current wave height from the model.

    Args:
        model: The model containing the current wave height information.
    
    Returns:
        float: The current wave height value.
    """
    step = model.current_step
    date = model.current_date

    if date not in VECTOR_WAVE_HEIGHT:
        print(f"Warning: Date {date} not found in wave height vector. Returning default value of 0.0.")
        return date, 0.0  # Default to 0.0 if the date is not found in the vector
    return date, VECTOR_WAVE_HEIGHT[date]


def wave_height_check(agent, model) -> bool:
    """Check if the wave height is below the threshold for the agent's fleet.

    Args:
        agent: The agent whose fleet's wave height threshold is to be checked.
        model: The model containing the current wave height information.
        wave_height: The current wave height value to compare against the threshold.
    Returns:
        bool: True if the wave height is below the threshold, False otherwise.
    """
    date, wave_height = get_wave_height(model)
    return wave_height < agent.fleet_wave_height_threshold