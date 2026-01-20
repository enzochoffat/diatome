"""
Tests pour Step 3: Système de mémoire
"""

import sys
import os

# Add parent directory to path to import model
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model import FisheryModel
from agent import FisherAgent

def test_temporal_memory_fifo():
    """Test la mémoire temporelle FIFO"""
    print("=" * 60)
    print("TEST 1: Mémoire temporelle FIFO")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    # Créer un agent test
    agent = FisherAgent(1, model, "archipelago")
    
    print(f"Taille de mémoire: {agent.memory_size}")
    print(f"Mémoire initiale: {len(agent.memory)} trips")
    
    # Ajouter 15 sorties (plus que la taille mémoire)
    for i in range(15):
        trip_info = {
            'location': (i, i),
            'catch': 100 + i * 10,
            'cost': 50,
            'profit': 50 + i * 10,
            'days': 1,
            'tick': i
        }
        agent.update_memory(trip_info)
    
    print(f"Mémoire après 15 trips: {len(agent.memory)} trips")
    print(f"Premier trip en mémoire: tick {agent.memory[0]['tick']}")
    print(f"Dernier trip en mémoire: tick {agent.memory[-1]['tick']}")
    
    # Vérifier FIFO
    assert len(agent.memory) == agent.memory_size, "La mémoire devrait être limitée à memory_size"
    assert agent.memory[0]['tick'] == 5, "Le plus ancien trip devrait être le tick 5"
    assert agent.memory[-1]['tick'] == 14, "Le plus récent trip devrait être le tick 14"
    
    print("✓ Test réussi\n")

def test_spatial_memory_good_spots():
    """Test la mémoire spatiale des bons spots"""
    print("=" * 60)
    print("TEST 2: Mémoire spatiale - Bons spots")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = FisherAgent(1, model, "archipelago")
    
    # Simuler des visites à différents spots
    locations = [(7, 3), (16, 3), (10, 5), (5, 2)]
    catches = [500, 450, 200, 550]  # Certains bons, d'autres moins
    expected_catch = 400
    
    for loc, catch in zip(locations, catches):
        agent.update_memory_good_spots(loc, catch, expected_catch)
    
    print(f"Nombre de spots en mémoire: {len(agent.good_spots_memory)}")
    
    # Afficher les spots
    for loc, memory in agent.good_spots_memory.items():
        print(f"  Spot {loc}: catch={memory['avg_catch']:.0f}, "
              f"efficiency={memory['efficiency']:.2f}, "
              f"good={memory.get('is_good', False)}")
    
    # Récupérer les bons spots
    good_spots = agent.get_good_spots()
    print(f"\nBons spots (efficiency > {agent.good_spots_threshold}):")
    for loc, memory in good_spots:
        print(f"  {loc}: avg_catch={memory['avg_catch']:.0f}")
    
    # Vérifications
    assert len(agent.good_spots_memory) == 4, "Devrait avoir 4 spots en mémoire"
    assert len(good_spots) == 3, "Devrait avoir 3 bons spots (catch > 70% expected)"
    assert good_spots[0][0] == (5, 2), "Le meilleur spot devrait être (5,2)"
    
    print("✓ Test réussi\n")

def test_spatial_memory_rolling_average():
    """Test la moyenne glissante dans la mémoire spatiale"""
    print("=" * 60)
    print("TEST 3: Mémoire spatiale - Moyenne glissante")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = FisherAgent(1, model, "archipelago")
    
    location = (7, 3)
    expected_catch = 100
    
    # Première visite
    agent.update_memory_good_spots(location, 100, expected_catch)
    print(f"Visite 1: catch=100, avg={agent.good_spots_memory[location]['avg_catch']:.1f}")
    
    # Deuxième visite avec catch différent
    agent.update_memory_good_spots(location, 200, expected_catch)
    print(f"Visite 2: catch=200, avg={agent.good_spots_memory[location]['avg_catch']:.1f}")
    
    # Troisième visite
    agent.update_memory_good_spots(location, 150, expected_catch)
    print(f"Visite 3: catch=150, avg={agent.good_spots_memory[location]['avg_catch']:.1f}")
    
    expected_avg = (100 + 200 + 150) / 3
    actual_avg = agent.good_spots_memory[location]['avg_catch']
    
    assert agent.good_spots_memory[location]['visits'] == 3, "Devrait avoir 3 visites"
    assert abs(actual_avg - expected_avg) < 0.1, f"Moyenne devrait être {expected_avg:.1f}"
    
    print("✓ Test réussi\n")

def test_memory_statistics():
    """Test les statistiques calculées depuis la mémoire"""
    print("=" * 60)
    print("TEST 4: Statistiques de mémoire")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = FisherAgent(1, model, "archipelago")
    
    # Ajouter quelques trips
    trips_data = [
        {'location': (7, 3), 'catch': 500, 'cost': 100, 'profit': 400, 'days': 1, 'tick': 0},
        {'location': (16, 3), 'catch': 300, 'cost': 100, 'profit': 200, 'days': 1, 'tick': 1},
        {'location': (10, 5), 'catch': 200, 'cost': 100, 'profit': 100, 'days': 1, 'tick': 2},
        {'location': (5, 2), 'catch': 100, 'cost': 150, 'profit': -50, 'days': 1, 'tick': 3},
    ]
    
    for trip in trips_data:
        agent.update_memory(trip)
    
    stats = agent.get_memory_statistics()
    
    print("Statistiques de mémoire:")
    print(f"  Total trips: {stats['total_trips']}")
    print(f"  Average catch: {stats['avg_catch']:.1f}")
    print(f"  Average profit: {stats['avg_profit']:.1f}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Best location: {stats['best_location']}")
    
    assert stats['total_trips'] == 4, "Devrait avoir 4 trips"
    assert stats['avg_catch'] == 275, "Moyenne catch devrait être 275"
    assert stats['avg_profit'] == 162.5, "Moyenne profit devrait être 162.5"
    assert stats['success_rate'] == 0.75, "Success rate devrait être 75%"
    assert stats['best_location'] == (7, 3), "Meilleur spot devrait être (7, 3)"
    
    print("✓ Test réussi\n")

def test_forgetting_mechanism():
    """Test le mécanisme d'oubli des vieux spots"""
    print("=" * 60)
    print("TEST 5: Mécanisme d'oubli")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = FisherAgent(1, model, "archipelago")
    
    # Ajouter des spots à différents moments
    model.steps = 0
    agent.update_memory_good_spots((7, 3), 500, 400)
    
    model.steps = 160
    agent.update_memory_good_spots((16, 3), 450, 400)
    
    model.steps = 200
    agent.update_memory_good_spots((10, 5), 400, 400)
    
    print(f"Spots en mémoire: {len(agent.good_spots_memory)}")
    
    # Avancer dans le temps et oublier les vieux spots
    model.steps = 300
    max_age = 150  # Oublier spots non visités depuis 150 ticks
    
    agent.forget_old_spots(max_age)
    
    print(f"Spots après oubli (max_age={max_age}): {len(agent.good_spots_memory)}")
    
    # Vérifier que seuls les spots récents restent
    assert len(agent.good_spots_memory) == 2, "Devrait rester 2 spots (visités après tick 150)"
    assert (7, 3) not in agent.good_spots_memory, "Spot (7,3) devrait être oublié"
    assert (16, 3) in agent.good_spots_memory, "Spot (16,3) devrait être retenu"
    assert (10, 5) in agent.good_spots_memory, "Spot (10,5) devrait être retenu"
    
    print("✓ Test réussi\n")

def test_region_filtering():
    """Test le filtrage des spots par région"""
    print("=" * 60)
    print("TEST 6: Filtrage par région")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=0,
        num_coastal=1,
        num_trawler=0
    )
    
    agent = FisherAgent(1, model, "coastal")
    
    # Ajouter des spots dans différentes régions
    # Région A: y < 8
    agent.update_memory_good_spots((7, 3), 500, 400)
    agent.update_memory_good_spots((16, 3), 450, 400)
    
    # Région B: 8 <= y < 24
    agent.update_memory_good_spots((3, 19), 550, 400)
    agent.update_memory_good_spots((8, 11), 500, 400)
    
    print(f"Total spots: {len(agent.good_spots_memory)}")
    
    # Filtrer par région A
    spots_A = agent.get_good_spots(region="A")
    print(f"Spots en région A: {len(spots_A)}")
    for loc, mem in spots_A:
        print(f"  {loc}")
    
    # Filtrer par région B
    spots_B = agent.get_good_spots(region="B")
    print(f"Spots en région B: {len(spots_B)}")
    for loc, mem in spots_B:
        print(f"  {loc}")
    
    assert len(spots_A) == 2, "Devrait avoir 2 spots en région A"
    assert len(spots_B) == 2, "Devrait avoir 2 spots en région B"
    
    print("✓ Test réussi\n")

def run_all_tests():
    """Exécute tous les tests du Step 3"""
    print("\n" + "=" * 60)
    print("TESTS STEP 3: SYSTÈME DE MÉMOIRE")
    print("=" * 60 + "\n")
    
    try:
        test_temporal_memory_fifo()
        test_spatial_memory_good_spots()
        test_spatial_memory_rolling_average()
        test_memory_statistics()
        test_forgetting_mechanism()
        test_region_filtering()
        
        print("=" * 60)
        print("RÉSUMÉ")
        print("=" * 60)
        print("✓ Tous les tests du Step 3 ont été exécutés avec succès")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()