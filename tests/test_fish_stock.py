"""
Script de test pour vérifier l'environnement spatial du modèle
"""

import sys
sys.path.append('.')

from model import FisheryModel

def test_grid_creation():
    """Test la création de la grille"""
    print("=" * 50)
    print("TEST 1: Création de la grille")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    print(f"✓ Grille créée: {model.grid.width}x{model.grid.height}")
    print(f"✓ Nombre total de patches: {len(model.patches)}")
    print()

def test_regions():
    """Test la répartition des régions"""
    print("=" * 50)
    print("TEST 2: Répartition des régions")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    region_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "LAND": 0, "NULL": 0}
    
    for patch in model.patches.values():
        region = patch['region']
        if region in region_counts:
            region_counts[region] += 1
    
    print("Nombre de patches par région:")
    for region, count in region_counts.items():
        print(f"  - {region}: {count} patches")
    
    print()

def test_hotspots():
    """Test la génération des hotspots"""
    print("=" * 50)
    print("TEST 3: Génération des hotspots")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    density_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, None: 0}
    
    for patch in model.patches.values():
        density = patch['density']
        if density in density_counts:
            density_counts[density] += 1
    
    print("Répartition des densités:")
    for density, count in density_counts.items():
        if density:
            print(f"  - {density}: {count} patches")
    
    print("\nVérification des hotspots définis:")
    print(f"  - Region A: {len(model.HOTSPOTS_A)} hotspots")
    print(f"  - Region B: {len(model.HOTSPOTS_B)} hotspots")
    print(f"  - Region C: {len(model.HOTSPOTS_C)} hotspots")
    print(f"  - Region D: {len(model.HOTSPOTS_D)} hotspots")
    
    print()

def test_fish_stocks():
    """Test l'initialisation des stocks de poissons"""
    print("=" * 50)
    print("TEST 4: Stocks de poissons initiaux")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    print("Stocks initiaux par région:")
    print(f"  - Region A: {model.get_region_stock('A')} (MSY: {model.MSY_STOCK_A})")
    print(f"  - Region B: {model.get_region_stock('B')} (MSY: {model.MSY_STOCK_B})")
    print(f"  - Region C: {model.get_region_stock('C')} (MSY: {model.MSY_STOCK_C})")
    print(f"  - Region D: {model.get_region_stock('D')} (MSY: {model.MSY_STOCK_D})")
    print(f"  - Total: {model.get_total_stock()}")
    
    print()

def test_patch_access():
    """Test l'accès aux informations d'un patch spécifique"""
    print("=" * 50)
    print("TEST 5: Accès aux informations des patches")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    # Test quelques patches spécifiques
    test_coords = [
        (7, 3),   # Hotspot en région A
        (3, 19),  # Hotspot en région B
        (4, 51),  # Hotspot en région C
        (30, 51), # Hotspot en région D
        (30, 10), # LAND
    ]
    
    print("Informations sur quelques patches:")
    for x, y in test_coords:
        patch_info = model.get_patch_info(x, y)
        if patch_info:
            print(f"\n  Patch ({x}, {y}):")
            print(f"    - Region: {patch_info['region']}")
            print(f"    - Density: {patch_info['density']}")
            print(f"    - Fish stock: {patch_info['fish_stock']}")
            print(f"    - Carrying capacity: {patch_info['carrying_capacity']}")
    
    print()

def test_stock_update():
    """Test la mise à jour des stocks de poissons"""
    print("=" * 50)
    print("TEST 6: Mise à jour des stocks (croissance)")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    initial_stock = model.get_total_stock()
    print(f"Stock initial total: {initial_stock}")
    
    # Simuler une année de croissance
    model.update_fish_stock()
    
    updated_stock = model.get_total_stock()
    print(f"Stock après croissance: {updated_stock}")
    print(f"Augmentation: {updated_stock - initial_stock} (+{((updated_stock - initial_stock) / initial_stock * 100):.2f}%)")
    
    print()

def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "=" * 50)
    print("TESTS DE L'ENVIRONNEMENT SPATIAL")
    print("=" * 50 + "\n")
    
    try:
        test_grid_creation()
        test_regions()
        test_hotspots()
        test_fish_stocks()
        test_patch_access()
        test_stock_update()
        
        print("=" * 50)
        print("RÉSUMÉ")
        print("=" * 50)
        print("✓ Tous les tests ont été exécutés avec succès")
        print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()