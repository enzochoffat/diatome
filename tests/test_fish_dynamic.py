"""
Tests pour Step 2: Dynamiques des poissons
"""

import sys
import os

# Add parent directory to path to import model
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model import FisheryModel

def test_reduce_stock_normal():
    """Test la réduction de stock avec capture normale"""
    print("=" * 60)
    print("TEST 1: Réduction de stock - Cas normal")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    # Trouver un patch avec du stock
    test_patch = (7, 3)  # Hotspot en région A
    initial_stock = model.patches[test_patch]['fish_stock']
    
    print(f"Stock initial au patch {test_patch}: {initial_stock}")
    
    # Tenter de capturer 100 poissons
    catch_request = 100
    actual_catch = model.reduce_stock(test_patch[0], test_patch[1], catch_request)
    
    final_stock = model.patches[test_patch]['fish_stock']
    
    print(f"Capture demandée: {catch_request}")
    print(f"Capture réelle: {actual_catch}")
    print(f"Stock final: {final_stock}")
    print(f"Différence: {initial_stock - final_stock}")
    
    assert actual_catch == catch_request, "La capture devrait être égale à la demande"
    assert final_stock == initial_stock - catch_request, "Le stock devrait diminuer correctement"
    print("✓ Test réussi\n")

def test_reduce_stock_exceeds_available():
    """Test la réduction de stock quand la demande dépasse le stock disponible"""
    print("=" * 60)
    print("TEST 2: Réduction de stock - Demande > Stock disponible")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    # Trouver un patch avec peu de stock
    test_patch = None
    for pos, patch in model.patches.items():
        if patch['density'] == model.LOW:
            test_patch = pos
            break
    
    initial_stock = model.patches[test_patch]['fish_stock']
    
    print(f"Stock initial au patch {test_patch}: {initial_stock}")
    
    # Tenter de capturer plus que disponible
    catch_request = initial_stock + 500
    actual_catch = model.reduce_stock(test_patch[0], test_patch[1], catch_request)
    
    final_stock = model.patches[test_patch]['fish_stock']
    
    print(f"Capture demandée: {catch_request}")
    print(f"Capture réelle: {actual_catch}")
    print(f"Stock final: {final_stock}")
    
    assert actual_catch == initial_stock, "La capture devrait être limitée au stock disponible"
    assert final_stock == 0, "Le stock devrait être épuisé (0)"
    print("✓ Test réussi\n")

def test_growth_with_fishing():
    """Test la croissance avec pêche simultanée"""
    print("=" * 60)
    print("TEST 3: Croissance avec pêche")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    # Stock total initial
    initial_stock = model.get_total_stock()
    print(f"Stock total initial: {initial_stock}")
    
    # Simuler 5 ans de pêche modérée (10% du stock par an)
    for year in range(5):
        # Pêche sur quelques hotspots
        for hotspot in list(model.HOTSPOTS)[:2]:
            x, y = hotspot
            stock_before = model.patches[(x, y)]['fish_stock']
            catch = model.reduce_stock(x, y, int(stock_before * 0.1))
            print(f"  Année {year+1}, Hotspot {hotspot}: pêché {catch}")
        
        # Croissance annuelle
        model.update_fish_stock()
    
    final_stock = model.get_total_stock()
    print(f"\nStock total final après 5 ans: {final_stock}")
    print(f"Variation: {final_stock - initial_stock} ({((final_stock - initial_stock) / initial_stock * 100):.1f}%)")
    
    # Avec une pêche modérée (10%/an), le stock devrait rester relativement stable
    assert abs(final_stock - initial_stock) < initial_stock * 0.2, "Le stock devrait rester relativement stable avec pêche modérée"
    print("✓ Test réussi\n")

def test_overfishing_depletion():
    """Test l'épuisement avec surpêche"""
    print("=" * 60)
    print("TEST 4: Épuisement par surpêche")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    # Stock total initial
    initial_stock = model.get_total_stock()
    print(f"Stock total initial: {initial_stock}")
    
    # Simuler 10 ans de surpêche intensive (50% du stock par an)
    for year in range(10):
        current_stock = model.get_total_stock()
        print(f"  Année {year+1} - Stock début: {current_stock}")
        
        # Pêche intensive sur tous les patches
        total_catch = 0
        for pos, patch in model.patches.items():
            x, y = pos
            catch = model.reduce_stock(x, y, int(patch['fish_stock'] * 0.5))
            total_catch += catch
        
        print(f"           - Total pêché: {total_catch}")
        
        # Croissance annuelle
        model.update_fish_stock()
        
        stock_after_growth = model.get_total_stock()
        print(f"           - Stock après croissance: {stock_after_growth}")
    
    final_stock = model.get_total_stock()
    print(f"\nStock total final après 10 ans: {final_stock}")
    print(f"Réduction: {initial_stock - final_stock} ({((initial_stock - final_stock) / initial_stock * 100):.1f}%)")
    
    # Avec surpêche intensive, le stock devrait diminuer significativement
    assert final_stock < initial_stock * 0.5, "Le stock devrait diminuer significativement avec surpêche"
    print("✓ Test réussi\n")

def test_growth_no_fishing():
    """Test la croissance des stocks sans pêche"""
    print("=" * 60)
    print("TEST 5: Croissance sans pêche")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    initial_stock = model.get_total_stock()
    print(f"Stock initial: {initial_stock}")
    
    # Simuler 50 ans sans pêche
    for year in range(50):
        model.update_fish_stock()
    
    final_stock = model.get_total_stock()
    print(f"Stock après 50 ans: {final_stock}")
    print(f"Variation: {(final_stock - initial_stock) / initial_stock * 100:+.1f}%")
    
    assert final_stock >= initial_stock, "Le stock devrait au moins se maintenir sans pêche"
    print("✓ Test réussi\n")

def run_all_tests():
    """Exécute tous les tests du Step 2"""
    print("\n" + "=" * 60)
    print("TESTS STEP 2: DYNAMIQUES DES POISSONS")
    print("=" * 60 + "\n")
    
    try:
        test_reduce_stock_normal()
        test_reduce_stock_exceeds_available()
        test_growth_with_fishing()
        test_overfishing_depletion()
        test_growth_no_fishing()
        
        print("=" * 60)
        print("RÉSUMÉ")
        print("=" * 60)
        print("✓ Tous les tests du Step 2 ont été exécutés avec succès")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()
if __name__ == "__main__":
    run_all_tests()
# ...existing code...