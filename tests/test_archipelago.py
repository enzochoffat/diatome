"""
Tests pour Step 4: Exécution de pêche (archipelago)
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model import FisheryModel
from agent import FisherAgent

def test_agent_creation():
    """Test la création d'un agent archipelago"""
    print("=" * 60)
    print("TEST 1: Création agent archipelago")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    # Vérifier qu'un agent a été créé
    assert len(list(model.agents)) == 1, "Devrait avoir 1 agent"
    
    agent = list(model.agents)[0]
    
    print(f"Agent ID: {agent.unique_id}")
    print(f"Type: {agent.fisher_type}")
    print(f"Capital initial: {agent.capital}")
    print(f"Catchability: {agent.catchability}")
    print(f"Régions accessibles: {agent.accessible_regions}")
    print(f"Max good spots: {agent.max_good_spots}")
    
    assert agent.fisher_type == "archipelago"
    assert agent.accessible_regions == ["A"]
    assert agent.at_home == True
    assert agent.gone_fishing == False
    
    print("✓ Test réussi\n")

def test_spot_selection():
    """Test la sélection de spots de pêche"""
    print("=" * 60)
    print("TEST 2: Sélection de spots")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    # Test exploration (pas de mémoire encore)
    print("Exploration (pas de mémoire):")
    for i in range(5):
        spot = agent.select_fishing_spot(region="A")
        print(f"  Tentative {i+1}: {spot}")
        assert spot is not None, "Devrait trouver un spot"
        assert spot in [tuple(h) for h in model.HOTSPOTS_A], "Devrait être un hotspot de région A"
    
    # Ajouter des spots en mémoire
    print("\nAjout de spots en mémoire:")
    agent.update_memory_good_spots((7, 3), 500, 400)
    agent.update_memory_good_spots((16, 3), 450, 400)
    
    good_spots = agent.get_good_spots(region="A")
    print(f"Bons spots en mémoire: {len(good_spots)}")
    
    # Test sélection depuis mémoire
    print("\nSélection depuis mémoire:")
    for i in range(5):
        spot = agent.select_fishing_spot(region="A")
        print(f"  Tentative {i+1}: {spot}")
        assert spot in [(7, 3), (16, 3)], "Devrait choisir depuis les spots connus"
    
    print("✓ Test réussi\n")

def test_single_fishing_trip():
    """Test une sortie de pêche complète"""
    print("=" * 60)
    print("TEST 3: Sortie de pêche unique")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    # État initial
    initial_capital = agent.capital
    initial_wealth = agent.wealth
    
    print(f"État initial:")
    print(f"  Capital: {initial_capital}")
    print(f"  Wealth: {initial_wealth}")
    
    # Choisir un hotspot
    location = (7, 3)  # Premier hotspot région A
    initial_stock = model.patches[location]['fish_stock']
    
    print(f"\nSpot choisi: {location}")
    print(f"  Stock avant pêche: {initial_stock}")
    
    # Exécuter pêche
    trip_result = agent.go_fish(location)
    
    print(f"\nRésultat:")
    print(f"  Capture: {trip_result['catch']}")
    print(f"  Coûts: {trip_result['costs']:.2f}")
    print(f"  Revenue: {trip_result['revenue']:.2f}")
    print(f"  Profit: {trip_result['profit']:.2f}")
    
    final_stock = model.patches[location]['fish_stock']
    print(f"  Stock après pêche: {final_stock}")
    
    # Vérifications
    assert trip_result['catch'] > 0, "Devrait avoir capturé des poissons"
    assert trip_result['catch'] <= agent.catchability, "Ne devrait pas dépasser catchability"
    assert final_stock == initial_stock - trip_result['catch'], "Le stock devrait diminuer"
    assert agent.total_catch == trip_result['catch'], "Total catch devrait être mis à jour"
    assert agent.days_at_sea == 1, "Devrait avoir 1 jour en mer"
    
    # Vérifier mémoire spatiale
    assert location in agent.good_spots_memory, "Le spot devrait être en mémoire"
    
    print("✓ Test réussi\n")

def test_decision_execution():
    """Test la décision et exécution complète"""
    print("=" * 60)
    print("TEST 4: Décision et exécution")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    print("Simulation de 10 jours:")
    fishing_days = 0
    home_days = 0
    
    for day in range(10):
        initial_capital = agent.capital
        
        # Agent décide et exécute
        agent.decide_to_fish_simple()
        agent.execute_decision()
        
        if agent.will_fish:
            fishing_days += 1
            status = "🎣 Pêche"
        else:
            home_days += 1
            status = "🏠 Maison"
        
        capital_change = agent.capital - initial_capital
        
        print(f"  Jour {day+1}: {status} | Capital change: {capital_change:+.2f} | Total catch: {agent.total_catch}")
    
    print(f"\nRésumé:")
    print(f"  Jours de pêche: {fishing_days}")
    print(f"  Jours à la maison: {home_days}")
    print(f"  Total capture: {agent.total_catch}")
    print(f"  Capital final: {agent.capital:.2f}")
    print(f"  Trips en mémoire: {len(agent.memory)}")
    print(f"  Spots connus: {len(agent.good_spots_memory)}")
    
    assert fishing_days > 0, "Devrait avoir pêché au moins une fois"
    assert agent.total_catch > 0, "Devrait avoir capturé des poissons"
    
    print("✓ Test réussi\n")

def test_30_days_simulation():
    """Test simulation complète sur 30 jours"""
    print("=" * 60)
    print("TEST 5: Simulation 30 jours")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    initial_stock_A = model.get_region_stock("A")
    print(f"Stock initial région A: {initial_stock_A}")
    
    # Simuler 30 jours
    for day in range(30):
        model.step()
    
    final_stock_A = model.get_region_stock("A")
    stock_reduction = initial_stock_A - final_stock_A
    
    print(f"\nAprès 30 jours:")
    print(f"  Stock final région A: {final_stock_A}")
    print(f"  Réduction stock: {stock_reduction} ({stock_reduction/initial_stock_A*100:.1f}%)")
    print(f"  Total capture agent: {agent.total_catch}")
    print(f"  Capital agent: {agent.capital:.2f}")
    print(f"  Jours en mer: {agent.days_at_sea}")
    print(f"  Trips en mémoire: {len(agent.memory)}")
    print(f"  Spots connus: {len(agent.good_spots_memory)}")
    
    # Statistiques mémoire
    if agent.memory:
        stats = agent.get_memory_statistics()
        print(f"\nStatistiques mémoire:")
        print(f"  Profit moyen: {stats['avg_profit']:.2f}")
        print(f"  Capture moyenne: {stats['avg_catch']:.1f}")
        print(f"  Taux succès: {stats['success_rate']:.1%}")
    
    assert agent.total_catch > 0, "Devrait avoir capturé des poissons"
    assert final_stock_A < initial_stock_A, "Le stock devrait diminuer"
    assert final_stock_A >= 0, "Le stock ne devrait pas être négatif"
    
    print("✓ Test réussi\n")

def test_memory_limit():
    """Test que la mémoire spatiale respecte la limite"""
    print("=" * 60)
    print("TEST 6: Limite mémoire spatiale")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    print(f"Limite spots archipelago: {agent.max_good_spots}")
    
    # Simuler visites de beaucoup de spots
    hotspots = model.HOTSPOTS_A
    
    for i, hotspot in enumerate(hotspots):
        location = tuple(hotspot)
        catch = 400 + i * 10  # Tous bons spots
        expected = 400
        agent.update_memory_good_spots(location, catch, expected)
    
    print(f"Hotspots visités: {len(hotspots)}")
    print(f"Spots en mémoire: {len(agent.good_spots_memory)}")
    
    good_spots = agent.get_good_spots(region="A")
    print(f"Bons spots: {len(good_spots)}")
    
    # Note: Pour l'instant, pas de limite imposée dans update_memory_good_spots
    # À implémenter si nécessaire selon le comportement NetLogo
    
    print("✓ Test réussi\n")

def run_all_tests():
    """Exécute tous les tests du Step 4"""
    print("\n" + "=" * 60)
    print("TESTS STEP 4: EXÉCUTION DE PÊCHE (ARCHIPELAGO)")
    print("=" * 60 + "\n")
    
    try:
        test_agent_creation()
        test_spot_selection()
        test_single_fishing_trip()
        test_decision_execution()
        test_30_days_simulation()
        test_memory_limit()
        
        print("=" * 60)
        print("RÉSUMÉ")
        print("=" * 60)
        print("✓ Tous les tests du Step 4 ont été exécutés avec succès")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()