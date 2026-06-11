import json 
import csv

class Couplage:
    def __init__(self, model):
        self.model = model
    
    def read_csv_biomass(self):
        """Update biomass at a specific location"""
        """on va chercher les cartes dans la nouvelle config sans pour autant la run"""

        json_path = "configs/config.json"
        with open(json_path, 'r') as f:
            config = json.load(f)
            species_maps = config["maps"]["species_map"]
            step = config["simulation"]["step"]
        # Récupérer les cartes d'écosystème à partir de la configuration


        return species_maps, step
    
    def update_biomass(self, species_maps):
        new_fish_stocks = {}
        
        for id, path in species_maps.items(): 
            #print(f"Processing species {id} with path {path}")
            
            with open(path, mode='r') as f:
                reader = csv.reader(f, delimiter=',')
                all_row = []
                for row in reader:
                    new_row = []
                    for cell in row:
                        cell = cell.strip()
                        if cell == '':
                            new_row.append(0.0)
                        else:
                            try:
                                new_row.append(float(cell))
                            except ValueError:
                                print(f"Warning: Non-numeric value '{cell}' in file {path}, treating as 0")
                                new_row.append(0.0)
                    all_row.append(new_row)
                
                # Sauter l'en-tête et la première colonne (supposés)
                data_rows = [row[1:] for row in all_row[2:]]
                
                #if data_rows:
                    #print(f"row 1 {data_rows[0]}")
                
                for x, row in enumerate(data_rows):
                    for y, cell in enumerate(row):
                        # Option A : Si vous voulez sommer les biomasses de toutes les espèces par case
                        current_value = new_fish_stocks.get((x, y), 0.0)
                        new_fish_stocks[(x, y)] = current_value + cell
                        
                        # Option B : Si vous voulez garder les données séparées par espèce (recommandé)
                        # if (x, y) not in new_fish_stocks:
                        #     new_fish_stocks[(x, y)] = {}
                        # new_fish_stocks[(x, y)][id] = cell

                        #if x == 40 and y == 169:
                            #print(f"Read fish stock for patch ({x}, {y}) species {id}: {cell}")

        return new_fish_stocks
