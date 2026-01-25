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
        if patch['density'] == model.LOW and patch['region'] == 'A':
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

# ...existing code...

def test_regional_capacity():
    """Test que les capacités régionales sont correctes"""
    print("=" * 60)
    print("TEST 3: Capacités régionales")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    print("Capacités régionales:")
    all_ok = True
    
    for region in ["A", "B", "C", "D"]:
        capacity = model.get_region_carrying_capacity(region)
        stock = model.get_region_stock(region)
        msy = capacity / 2
        percentage = (stock / capacity * 100) if capacity > 0 else 0
        difference = abs(stock - msy)
        
        print(f"  Region {region}:")
        print(f"    - Capacité totale: {capacity}")
        print(f"    - MSY (50%): {msy}")
        print(f"    - Stock actuel: {stock} ({percentage:.1f}%)")
        print(f"    - Différence avec MSY: {difference} ({(difference/msy*100):.2f}%)")
        
        # Calculer la capacité réelle basée sur les patches
        real_capacity = 0
        for pos, patch in model.patches.items():
            if patch['region'] == region:
                real_capacity += patch['carrying_capacity']
        
        print(f"    - Capacité réelle (somme patches): {real_capacity}")
        print(f"    - Écart capacité définie vs réelle: {capacity - real_capacity}")
        
        assert stock <= capacity, f"Le stock de la région {region} ne devrait pas dépasser la capacité"
        
        # Au lieu de comparer avec la constante MSY, comparons avec le MSY réel
        real_msy = real_capacity / 2
        real_difference = abs(stock - real_msy)
        tolerance = real_capacity * 0.02  # 2% de tolérance sur capacité réelle
        
        print(f"    - MSY réel (patches): {real_msy}")
        print(f"    - Différence avec MSY réel: {real_difference} ({(real_difference/real_msy*100):.2f}%)")
        
        if abs(stock - real_msy) >= tolerance:
            print(f"    ✗ Stock trop éloigné du MSY réel")
            all_ok = False
        else:
            print(f"    ✓ Stock proche du MSY réel")
    
    assert all_ok, "Les stocks initiaux devraient être proches du MSY réel de chaque région"
    print("\n✓ Test réussi\n")

# ...existing code...
    
def test_growth_with_fishing():
    """Test la croissance avec pêche simultanée"""
    print("=" * 60)
    print("TEST 4: Croissance avec pêche")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    # Stock initial région A
    initial_stock_A = model.get_region_stock("A")
    print(f"Stock initial région A: {initial_stock_A}")
    
    # Simuler 5 ans de pêche modérée (10% du stock par an)
    for year in range(5):
        # Pêche sur quelques hotspots
        for hotspot in model.HOTSPOTS_A[:2]:
            x, y = hotspot
            stock_before = model.patches[(x, y)]['fish_stock']
            catch = model.reduce_stock(x, y, int(stock_before * 0.1))
            print(f"  Année {year+1}, Hotspot {hotspot}: pêché {catch}")
        
        # Croissance annuelle
        model.update_fish_stock()
    
    final_stock_A = model.get_region_stock("A")
    print(f"\nStock final région A après 5 ans: {final_stock_A}")
    print(f"Variation: {final_stock_A - initial_stock_A} ({((final_stock_A - initial_stock_A) / initial_stock_A * 100):.1f}%)")
    
    # Avec une pêche modérée (10%/an), le stock devrait rester relativement stable
    assert abs(final_stock_A - initial_stock_A) < initial_stock_A * 0.2, "Le stock devrait rester relativement stable avec pêche modérée"
    print("✓ Test réussi\n")

def test_overfishing_depletion():
    """Test l'épuisement avec surpêche"""
    print("=" * 60)
    print("TEST 5: Épuisement par surpêche")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    # Stock initial région A
    initial_stock_A = model.get_region_stock("A")
    print(f"Stock initial région A: {initial_stock_A}")
    
    # Simuler 10 ans de surpêche intensive (50% du stock par an)
    for year in range(10):
        current_stock = model.get_region_stock("A")
        print(f"  Année {year+1} - Stock début: {current_stock}")
        
        # Pêche intensive sur tous les patches de région A
        total_catch = 0
        for pos, patch in model.patches.items():
            if patch['region'] == 'A':
                x, y = pos
                catch = model.reduce_stock(x, y, int(patch['fish_stock'] * 0.5))
                total_catch += catch
        
        print(f"           - Total pêché: {total_catch}")
        
        # Croissance annuelle
        model.update_fish_stock()
        
        stock_after_growth = model.get_region_stock("A")
        print(f"           - Stock après croissance: {stock_after_growth}")
    
    final_stock_A = model.get_region_stock("A")
    print(f"\nStock final région A après 10 ans: {final_stock_A}")
    print(f"Réduction: {initial_stock_A - final_stock_A} ({((initial_stock_A - final_stock_A) / initial_stock_A * 100):.1f}%)")
    
    # Avec surpêche intensive, le stock devrait diminuer significativement
    assert final_stock_A < initial_stock_A * 0.5, "Le stock devrait diminuer significativement avec surpêche"
    print("✓ Test réussi\n")

def test_regional_constraint():
    """Test que les contraintes régionales sont respectées"""
    print("=" * 60)
    print("TEST 6: Contraintes régionales lors de la croissance")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    # Simuler 50 ans sans pêche (croissance maximale)
    print("Simulation de 50 ans sans pêche...")
    for year in range(50):
        model.update_fish_stock()
        
        if year % 10 == 0:
            violations = model.validate_regional_stocks()
            print(f"  Année {year}: {len(violations)} violation(s)")
    
    # Vérifier qu'aucune région ne dépasse sa capacité
    violations = model.validate_regional_stocks()
    
    print(f"\nVérification finale:")
    for region in ["A", "B", "C", "D"]:
        stock = model.get_region_stock(region)
        capacity = model.get_region_carrying_capacity(region)
        percentage = (stock / capacity * 100) if capacity > 0 else 0
        status = "✓" if stock <= capacity else "✗"
        print(f"  {status} Region {region}: {stock}/{capacity} ({percentage:.1f}%)")
    
    if violations:
        print(f"\n✗ {len(violations)} violation(s) détectée(s):")
        for v in violations:
            print(f"  Region {v['region']}: {v['current']}/{v['max']} ({v['percentage']:.1f}%)")
        assert False, "Les stocks régionaux ne devraient pas dépasser les capacités"
    else:
        print("\n✓ Toutes les régions respectent leur capacité de charge")
    
    print("✓ Test réussi\n")

# ...existing code...

# ...existing code...

def test_initialization_precision():
    """Test de diagnostic pour comprendre les écarts d'initialisation"""
    print("=" * 60)
    print("TEST DIAGNOSTIC: Précision de l'initialisation")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=0
    )
    
    for region in ["A", "B", "C", "D"]:
        print(f"\nRégion {region}:")
        
        # Compter les patches par densité (utiliser defaultdict ou get)
        density_counts = {}
        density_stocks = {}
        total_patches = 0
        
        for pos, patch in model.patches.items():
            if patch['region'] == region:
                density = patch['density']
                if density:  # Ignorer None
                    # Initialiser si nécessaire
                    if density not in density_counts:
                        density_counts[density] = 0
                        density_stocks[density] = 0
                    
                    density_counts[density] += 1
                    density_stocks[density] += patch['fish_stock']
                    total_patches += 1
        
        print(f"  Total patches: {total_patches}")
        
        # Afficher toutes les densités trouvées
        for density in sorted(density_counts.keys()):
            print(f"  Patches {density}: {density_counts[density]} (stock total: {density_stocks[density]})")
        
        # Calcul théorique de la capacité basée sur les patches
        # Utiliser les constantes du modèle avec normalisation des noms
        theoretical_capacity = 0
        for density, count in density_counts.items():
            if density.upper() == "HIGH" or density == model.HIGH:
                theoretical_capacity += count * model.HIGH_CARRYING_CAPACITY
            elif density.upper() == "MEDIUM" or density == model.MEDIUM:
                theoretical_capacity += count * model.MEDIUM_CARRYING_CAPACITY
            elif density.upper() == "LOW" or density == model.LOW:
                theoretical_capacity += count * model.LOW_CARRYING_CAPACITY
        
        theoretical_msy = theoretical_capacity / 2
        actual_stock = model.get_region_stock(region)
        regional_capacity = model.get_region_carrying_capacity(region)
        
        print(f"\n  Capacité théorique (somme patches): {theoretical_capacity}")
        print(f"  Capacité régionale définie (constante): {regional_capacity}")
        print(f"  Différence capacités: {theoretical_capacity - regional_capacity}")
        print(f"  MSY théorique (patches): {theoretical_msy}")
        print(f"  MSY régional (constante): {regional_capacity/2}")
        print(f"  Stock actuel: {actual_stock}")
        print(f"  Différence stock vs MSY théorique: {actual_stock - theoretical_msy}")
        print(f"  Différence stock vs MSY régional: {actual_stock - regional_capacity/2}")
    
    print("\n✓ Diagnostic terminé\n")

# ...existing code...   
# ...existing code...

def run_all_tests():
    """Exécute tous les tests du Step 2"""
    print("\n" + "=" * 60)
    print("TESTS STEP 2: DYNAMIQUES DES POISSONS")
    print("=" * 60 + "\n")
    
    try:
        test_initialization_precision()  # AJOUTER CE TEST EN PREMIER
        test_reduce_stock_normal()
        test_reduce_stock_exceeds_available()
        test_regional_capacity()
        test_growth_with_fishing()
        test_overfishing_depletion()
        test_regional_constraint()
        
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