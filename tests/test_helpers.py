"""
Tests pour Step 7: Utilités et helpers
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model import FisheryModel
import random

def test_financial_methods():
    """Test méthodes financières"""
    print("=" * 60)
    print("TEST 1: Méthodes financières")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    # Test estimate_trip_cost
    print("\nTest estimate_trip_cost:")
    location = (7, 3)
    cost = agent.estimate_trip_cost(location)
    print(f"  Coût estimé pour {location}: {cost:.2f}")
    assert cost > 0, "Le coût devrait être positif"
    assert cost >= agent.cost_existence, "Devrait inclure coût existence"
    
    # Test can_afford_trip
    print("\nTest can_afford_trip:")
    agent.capital = 100
    print(f"  Capital: {agent.capital}")
    print(f"  Peut payer {cost:.2f}? {agent.can_afford_trip(cost)}")
    
    agent.capital = 0
    print(f"  Capital: {agent.capital}")
    print(f"  Peut payer {cost:.2f}? {agent.can_afford_trip(cost)}")
    
    # Test update_finances
    print("\nTest update_finances:")
    agent.capital = 100
    initial_capital = agent.capital
    
    # Trip profitable
    agent.update_finances(profit=50, cost=30, revenue=80)
    print(f"  Après trip profitable:")
    print(f"    Capital: {initial_capital} → {agent.capital}")
    print(f"    Profitable trips: {agent.profitable_trip}")
    assert agent.capital == initial_capital + 50, "Capital devrait augmenter"
    
    # Trip non profitable
    initial_capital = agent.capital
    agent.update_finances(profit=-20, cost=30, revenue=10)
    print(f"  Après trip non profitable:")
    print(f"    Capital: {initial_capital} → {agent.capital}")
    print(f"    Unprofitable trips: {agent.unprofitable_trip}")
    assert agent.capital == initial_capital - 20, "Capital devrait diminuer"
    
    print("✓ Test réussi\n")

def test_bankruptcy():
    """Test gestion de la faillite"""
    print("=" * 60)
    print("TEST 2: Gestion faillite")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    # Agent avec capital positif
    print("\nScénario 1: Capital positif")
    agent.capital = 1000
    agent.check_bankruptcy()
    print(f"  Capital: {agent.capital}")
    print(f"  Bankrupt: {agent.bankrupt}")
    assert not agent.bankrupt, "Ne devrait pas être en faillite"
    
    # Agent avec dette modérée
    print("\nScénario 2: Dette modérée")
    agent.capital = -50
    agent.check_bankruptcy()
    print(f"  Capital: {agent.capital}")
    print(f"  Bankrupt: {agent.bankrupt}")
    print(f"  LayLow: {agent.lay_low}")
    
    # Agent en faillite
    print("\nScénario 3: Faillite")
    bankruptcy_threshold = -(agent.cost_existence * 365)
    agent.capital = bankruptcy_threshold - 100
    agent.check_bankruptcy()
    print(f"  Capital: {agent.capital}")
    print(f"  Threshold: {bankruptcy_threshold:.2f}")
    print(f"  Bankrupt: {agent.bankrupt}")
    print(f"  LayLow: {agent.lay_low}")
    print(f"  LayLow counter: {agent.lay_low_counter}")
    assert agent.bankrupt, "Devrait être en faillite"
    assert agent.lay_low, "Devrait être en layLow"
    
    print("✓ Test réussi\n")

def test_navigation_state():
    """Test méthodes de navigation et états"""
    print("=" * 60)
    print("TEST 3: Navigation et états")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=0,
        num_coastal=1,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    # Test return_home
    print("\nTest return_home:")
    agent.at_sea = True
    agent.gone_fishing = True
    agent.at_home = False
    agent.accumulated_catch = 100
    agent.trip_cost = 50
    
    print(f"  Avant retour:")
    print(f"    At sea: {agent.at_sea}")
    print(f"    Gone fishing: {agent.gone_fishing}")
    print(f"    At home: {agent.at_home}")
    
    agent.return_home()
    
    print(f"  Après retour:")
    print(f"    At sea: {agent.at_sea}")
    print(f"    Gone fishing: {agent.gone_fishing}")
    print(f"    At home: {agent.at_home}")
    print(f"    Accumulated catch reset: {agent.accumulated_catch}")
    
    assert agent.at_home, "Devrait être à la maison"
    assert not agent.at_sea, "Ne devrait pas être en mer"
    assert not agent.gone_fishing, "Ne devrait pas être en train de pêcher"
    assert agent.accumulated_catch == 0, "Capture accumulée devrait être reset"
    
    # Test stay_home
    print("\nTest stay_home:")
    initial_capital = agent.capital
    initial_memory_size = len(agent.memory)
    
    agent.stay_home()
    
    print(f"  Capital: {initial_capital} → {agent.capital}")
    print(f"  Mémoire: {initial_memory_size} → {len(agent.memory)}")
    print(f"  At home: {agent.at_home}")
    print(f"  Will fish: {agent.will_fish}")
    
    assert agent.at_home, "Devrait être à la maison"
    assert not agent.will_fish, "Ne devrait pas vouloir pêcher"
    assert len(agent.memory) == initial_memory_size + 1, "Devrait ajouter entrée mémoire"
    
    print("✓ Test réussi\n")

def test_satisfaction_update():
    """Test mise à jour satisfaction"""
    print("=" * 60)
    print("TEST 4: Mise à jour satisfaction")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=0,
        num_coastal=1,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    agent.memory.clear()
    
    # Ajouter historique mixte
    print("\nAjout historique (7 trips pêche, 7 jours maison):")
    for i in range(14):
        if i < 7:
            # Trips de pêche
            trip_info = {
                'location': (7, 3),
                'catch': 100,
                'cost': 30,
                'profit': 70,
                'days': 1,
                'tick': i,
                'went_fishing': True
            }
        else:
            # Jours à la maison
            trip_info = {
                'location': None,
                'catch': 0,
                'cost': 5,
                'profit': -5,
                'days': 1,
                'tick': i,
                'went_fishing': False
            }
        agent.update_memory(trip_info)
    
    agent.update_satisfaction()
    
    print(f"  Satisfaction home: {agent.satisfaction_home:.2f}")
    print(f"  Satisfaction growth: {agent.satisfaction_growth:.2f}")
    
    assert 0 <= agent.satisfaction_home <= 1, "Satisfaction home doit être entre 0 et 1"
    assert 0 <= agent.satisfaction_growth <= 1, "Satisfaction growth doit être entre 0 et 1"
    
    # Avec peu de données
    print("\nAvec peu de données (< 7):")
    agent.memory.clear()
    for i in range(3):
        trip_info = {
            'location': (7, 3),
            'catch': 50,
            'cost': 30,
            'profit': 20,
            'days': 1,
            'tick': i,
            'went_fishing': True
        }
        agent.update_memory(trip_info)
    
    agent.update_satisfaction()
    print(f"  Satisfaction home: {agent.satisfaction_home:.2f}")
    print(f"  Satisfaction growth: {agent.satisfaction_growth:.2f}")
    
    print("✓ Test réussi\n")

def test_perception_scarcity():
    """Test perception de rareté"""
    print("=" * 60)
    print("TEST 5: Perception rareté")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    agent.memory.clear()
    
    # Bonnes captures
    print("\nScénario 1: Bonnes captures")
    for i in range(10):
        trip_info = {
            'location': (7, 3),
            'catch': agent.catchability * 0.9,  # 90% de catchability
            'cost': 30,
            'profit': 50,
            'days': 1,
            'tick': i,
            'went_fishing': True
        }
        agent.update_memory(trip_info)
    
    agent.update_perception_scarcity()
    print(f"  Perceive scarcity: {agent.perceive_scarcity}")
    assert not agent.perceive_scarcity, "Ne devrait pas percevoir rareté"
    
    # Mauvaises captures
    print("\nScénario 2: Mauvaises captures")
    agent.memory.clear()
    for i in range(10):
        trip_info = {
            'location': (7, 3),
            'catch': agent.catchability * 0.3,  # 30% de catchability
            'cost': 30,
            'profit': -10,
            'days': 1,
            'tick': i,
            'went_fishing': True
        }
        agent.update_memory(trip_info)
    
    agent.update_perception_scarcity()
    print(f"  Perceive scarcity: {agent.perceive_scarcity}")
    assert agent.perceive_scarcity, "Devrait percevoir rareté"
    
    print("✓ Test réussi\n")

def test_agent_summary():
    """Test génération résumé agent"""
    print("=" * 60)
    print("TEST 6: Résumé agent")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=1,
        num_coastal=1,
        num_trawler=1
    )
    
    for agent in model.agents:
        print(f"\n{agent.fisher_type.upper()}:")
        summary = agent.get_agent_summary()
        
        print(f"  ID: {summary['id']}")
        print(f"  Capital: {summary['capital']:.2f}")
        print(f"  Total catch: {summary['total_catch']}")
        print(f"  Days at sea: {summary['days_at_sea']}")
        print(f"  Memory size: {summary['memory_size']}")
        print(f"  Good spots: {summary['good_spots_count']}")
        
        # Vérifier clés essentielles
        assert 'id' in summary
        assert 'type' in summary
        assert 'capital' in summary
        assert 'total_catch' in summary
        assert 'at_home' in summary
    
    print("\n✓ Test réussi\n")

def test_memory_statistics():
    """Test statistiques mémoire"""
    print("=" * 60)
    print("TEST 7: Statistiques mémoire")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    agent.memory.clear()
    
    agent.memory_size = 30
    
    # Ajouter historique
    print("\nAjout 20 trips:")
    for i in range(20):
        profit = random.uniform(-10, 100)
        trip_info = {
            'location': (7, 3),
            'catch': max(0, profit + 30),
            'cost': 30,
            'profit': profit,
            'days': 1,
            'tick': i,
            'went_fishing': True
        }
        agent.update_memory(trip_info)
    
    stats = agent.get_memory_statistics()
    
    print(f"  Statistiques:")
    print(f"    Total trips: {stats['total_trips']}")
    print(f"    Avg catch: {stats['avg_catch']:.2f}")
    print(f"    Median catch: {stats['median_catch']:.2f}")
    print(f"    Avg profit: {stats['avg_profit']:.2f}")
    print(f"    Success rate: {stats['success_rate']:.1%}")
    print(f"    Recent trend: {stats['recent_trend']:+.2%}")
    
    assert stats['total_trips'] == 20
    assert 0 <= stats['success_rate'] <= 1
    
    print("✓ Test réussi\n")

def test_integrated_utilities():
    """Test intégration utilities dans simulation"""
    print("=" * 60)
    print("TEST 8: Intégration utilities (30 jours)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=2,
        num_coastal=1,
        num_trawler=1
    )
    
    print("\nSimulation 30 jours...")
    
    for day in range(30):
        model.step()
        
        if (day + 1) % 10 == 0:
            print(f"\nJour {day + 1}:")
            for agent in model.agents:
                summary = agent.get_agent_summary()
                status = "🎣" if summary['gone_fishing'] else "🏠"
                print(f"  {status} {agent.fisher_type}: "
                      f"Capital={summary['capital']:.0f}, "
                      f"Catch={summary['total_catch']}, "
                      f"Trips={summary['profitable_trips']}✓/"
                      f"{summary['unprofitable_trips']}✗")
    
    # Vérifications finales
    print("\n\nRésumé final:")
    for agent in model.agents:
        summary = agent.get_agent_summary()
        print(f"\n{agent.fisher_type.upper()}:")
        print(f"  Capital: {summary['capital']:.2f}")
        print(f"  Total catch: {summary['total_catch']}")
        print(f"  Success rate: {summary.get('success_rate', 0):.1%}")
        print(f"  Bankrupt: {summary['bankrupt']}")
        
        # Vérifier cohérence
        assert summary['profitable_trips'] + summary['unprofitable_trips'] >= 0
        assert summary['days_at_sea'] >= 0
    
    print("\n✓ Test réussi\n")

def run_all_tests():
    """Exécute tous les tests du Step 7"""
    print("\n" + "=" * 60)
    print("TESTS STEP 7: UTILITÉS ET HELPERS")
    print("=" * 60 + "\n")
    
    try:
        test_financial_methods()
        test_bankruptcy()
        test_navigation_state()
        test_satisfaction_update()
        test_perception_scarcity()
        test_agent_summary()
        test_memory_statistics()
        test_integrated_utilities()
        
        print("=" * 60)
        print("RÉSUMÉ")
        print("=" * 60)
        print("✓ Tous les tests du Step 7 ont été exécutés avec succès")
        print("\n🎉 Step 7 COMPLÉTÉ!")
        print("\nProchaines étapes:")
        print("  - Step 8: Outputs et collecte données")
        print("  - Step 9: Validation et calibration")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()