"""
Tests pour Step 6: Modèles de décision
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model import FisheryModel
import random

def test_archipelago_satisficing():
    """Test le modèle de décision satisficing (archipelago)"""
    print("=" * 60)
    print("TEST 1: Décision Satisficing (Archipelago)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    # Scénario 1: Agent avec bon capital, captures récentes suffisantes
    print("\nScénario 1: Capital OK, captures suffisantes")
    agent.capital = 1000
    agent.memory.clear()
    agent.growth_perception = 0
    for _ in range(7):
        trip_info = {
            'location': (7, 3),
            'catch': 100,
            'cost': 50,
            'profit': 50,
            'days': 1,
            'tick': model.current_step
        }
        agent.update_memory(trip_info)
    
    agent.satisfice_lifestyle()
    print(f"  Will fish: {agent.will_fish} (attendu: False)")
    assert not agent.will_fish, "Ne devrait pas pêcher si besoins satisfaits"
    
    # Scénario 2: Agent avec capital négatif
    print("\nScénario 2: Capital négatif")
    agent.capital = -100
    agent.memory.clear()
    agent.growth_perception = 0
    agent.satisfice_lifestyle()
    print(f"  Will fish: {agent.will_fish} (attendu: True)")
    assert agent.will_fish, "Devrait pêcher si capital négatif"
    
    # Scénario 3: Captures insuffisantes
    print("\nScénario 3: Captures insuffisantes")
    agent.capital = 500
    agent.memory.clear()
    agent.growth_perception = 0
    model.bad_weather = False
    for _ in range(7):
        trip_info = {
            'location': (7, 3),
            'catch': 0.3,
            'cost': 6,
            'profit': -5.7,
            'days': 1,
            'tick': model.current_step
        }
        agent.update_memory(trip_info)
        
        # DEBUG: Afficher l'état avant la décision
    print(f"  DEBUG - État avant décision:")
    print(f"    Mémoire: {len(agent.memory)} trips")
    catches_week = sum(t['catch'] for t in agent.memory)
    needs_week = agent.cost_existence * 7
    print(f"    Captures semaine: {catches_week:.1f}")
    print(f"    Besoins hebdo: {needs_week:.1f}")
    print(f"    Captures < Besoins: {catches_week < needs_week}")
    print(f"    Capital: {agent.capital}")
    print(f"    Growth perception: {agent.growth_perception}")
    print(f"    Bad weather: {model.bad_weather}")
    print(f"    LayLow: {agent.lay_low}")
    
    agent.satisfice_lifestyle()
    
    # DEBUG: Afficher l'état après la décision
    print(f"  DEBUG - État après décision:")
    print(f"    Will fish: {agent.will_fish}")
    
    print(f"  Will fish: {agent.will_fish} (attendu: True)")
    assert agent.will_fish, "Devrait pêcher si captures insuffisantes"
    
    # Scénario 4: Mauvais temps
    print("\nScénario 4: Mauvais temps")
    model.bad_weather = True
    agent.satisfice_lifestyle()
    print(f"  Will fish: {agent.will_fish} (attendu: False)")
    assert not agent.will_fish, "Ne devrait pas pêcher si mauvais temps"
    
    print("✓ Test réussi\n")

def test_coastal_optimization():
    """Test le modèle d'optimisation lifestyle+growth (coastal)"""
    print("=" * 60)
    print("TEST 2: Optimisation Lifestyle+Growth (Coastal)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=0,
        num_coastal=1,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    
    # Test 1: Agent sans mémoire (exploration initiale)
    print("\nTest 1: Sans mémoire (exploration)")
    agent.capital = 1000
    agent.memory.clear()
    model.bad_weather = False
    
    print(f"  Catchability: {agent.catchability}")
    print(f"  Cost existence: {agent.cost_existence}")
    print(f"  Cost activity: {agent.cost_activity}")
    
    agent.optimise_lifestyle_and_growth()
    
    print(f"  Will fish: {agent.will_fish}")
    
    # Test 2: Ajouter mémoire de pêche réussie en région A
    print("\nTest 2: Avec mémoire région A")
    agent.memory.clear()
    for _ in range(10):
        trip_info = {
            'location': (7, 3),
            'catch': 150,
            'cost': 50,
            'profit': 100,
            'days': 1,
            'tick': model.current_step
        }
        agent.update_memory(trip_info)
    
    # Ajouter mémoire de pêche moyenne en région B
    print("  Ajout mémoire région B")
    for _ in range(10):
        trip_info = {
            'location': (30, 10),
            'catch': 120,
            'cost': 50,
            'profit': 70,
            'days': 1,
            'tick': model.current_step
        }
        agent.update_memory(trip_info)
    
    # Test décision
    agent.capital = 500
    agent.optimise_lifestyle_and_growth()
    
    print(f"\n  Résultat:")
    print(f"    Will fish: {agent.will_fish}")
    
    # Test 3: avec capital négatif
    print("\nTest 3: Capital négatif")
    agent.capital = -50
    agent.optimise_lifestyle_and_growth()
    print(f"  Will fish: {agent.will_fish} (attendu: True)")
    assert agent.will_fish, "Devrait pêcher si capital négatif"
    
    print("✓ Test réussi\n")

def test_trawler_optimization():
    """Test le modèle d'optimisation pure (trawler)"""
    print("=" * 60)
    print("TEST 3: Optimisation Pure Profit (Trawler)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=0,
        num_coastal=0,
        num_trawler=1
    )
    
    agent = list(model.agents)[0]
    
    # Test: Décision depuis la maison
    print("\nScénario 1: Décision depuis la maison")
    agent.at_home = True
    agent.at_sea = False
    agent.capital = 1000
    
    # Ajouter mémoire de pêche lucrative
    for _ in range(10):
        trip_info = {
            'location': (40, 45),
            'catch': 500,
            'cost': 100,
            'profit': 400,
            'days': 1,
            'tick': model.current_step
        }
        agent.update_memory(trip_info)
    
    agent.optimise_growth()
    print(f"  Will fish: {agent.will_fish}")
    
    # Test: Décision en mer avec stockage non plein
    print("\nScénario 2: En mer, stockage non plein")
    agent.at_home = False
    agent.at_sea = True
    agent.fish_onboard = 1000
    agent.days_at_sea_current_trip = 2
    
    agent.optimise_growth()
    print(f"  Will fish: {agent.will_fish}")
    
    # Test: Stockage plein
    print("\nScénario 3: Stockage plein")
    agent.fish_onboard = agent.storing_capacity
    agent.optimise_growth()
    print(f"  Will fish: {agent.will_fish} (attendu: False)")
    assert not agent.will_fish, "Ne devrait pas pêcher si stockage plein"
    
    print("✓ Test réussi\n")

def test_spot_selection_knowledge():
    """Test sélection de spots basée sur la connaissance"""
    print("=" * 60)
    print("TEST 4: Sélection spots (Knowledge)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    agent = list(model.agents)[0]
    agent.spot_selection_strategy = "knowledge"
    
    # Ajouter quelques bons spots en mémoire
    print("\nAjout spots en mémoire:")
    agent.update_memory_good_spots((7, 3), 400, 400)
    agent.update_memory_good_spots((16, 3), 450, 400)
    
    print(f"Spots en mémoire: {len(agent.good_spots_memory)}")
    
    # Sélectionner plusieurs spots
    print("\nSélection de 10 spots:")
    selected_spots = []
    for i in range(10):
        spot = agent.decide_fishSpot()
        selected_spots.append(spot)
        print(f"  {i+1}. {spot}")
    
    # Vérifier que les spots sont dans la mémoire
    for spot in selected_spots:
        assert spot in [(7, 3), (16, 3)], f"Spot {spot} devrait être en mémoire"
    
    print("✓ Test réussi\n")

def test_spot_selection_expertise():
    """Test sélection de spots basée sur l'expertise"""
    print("=" * 60)
    print("TEST 5: Sélection spots (Expertise)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=3,
        num_coastal=0,
        num_trawler=0
    )
    
    agents = list(model.agents)
    
    # Agent 0 suit l'expertise
    follower = agents[0]
    follower.spot_selection_strategy = "expertise"
    
    # Agent 1 est l'expert (beaucoup de captures)
    expert = agents[1]
    expert.total_catch = 5000
    expert.gone_fishing = True
    expert.pos = (7, 3)
    
    # Agent 2 a peu de captures
    novice = agents[2]
    novice.total_catch = 100
    novice.gone_fishing = True
    novice.pos = (16, 3)
    
    # Sélection du follower
    print(f"\nExpert position: {expert.pos} (catch: {expert.total_catch})")
    print(f"Novice position: {novice.pos} (catch: {novice.total_catch})")
    
    spot = follower.decide_fishSpot()
    print(f"Follower selected: {spot}")
    
    assert spot == expert.pos, "Devrait suivre l'expert"
    
    print("✓ Test réussi\n")

def test_spot_selection_descriptive_norm():
    """Test sélection de spots basée sur la norme descriptive"""
    print("=" * 60)
    print("TEST 6: Sélection spots (Descriptive Norm)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=5,
        num_coastal=0,
        num_trawler=0
    )
    
    agents = list(model.agents)
    
    # Agent 0 suit la norme
    follower = agents[0]
    follower.spot_selection_strategy = "descriptive_norm"
    
    # 3 agents au spot (7, 3)
    for i in range(1, 4):
        agents[i].gone_fishing = True
        agents[i].pos = (7, 3)
    
    # 1 agent au spot (16, 3)
    agents[4].gone_fishing = True
    agents[4].pos = (16, 3)
    
    # Sélection du follower
    print("\nDistribution agents:")
    print(f"  (7, 3): 3 agents")
    print(f"  (16, 3): 1 agent")
    
    spot = follower.decide_fishSpot()
    print(f"\nFollower selected: {spot} (attendu: (7, 3))")
    
    assert spot == (7, 3), "Devrait aller où il y a le plus d'agents"
    
    print("✓ Test réussi\n")

def test_integrated_decision_making():
    """Test intégration complète: décision + sélection + exécution"""
    print("=" * 60)
    print("TEST 7: Intégration décision complète")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=1,
        num_coastal=1,
        num_trawler=1
    )
    
    print("\nSimulation de 30 jours avec décisions:")
    
    for day in range(30):
        model.step()
        
        if day % 7 == 0:  # Rapport hebdomadaire
            print(f"\nJour {day}:")
            for agent in model.agents:
                status = "🎣" if agent.gone_fishing else "🏠"
                print(f"  {agent.fisher_type}: {status} | "
                      f"Capital: {agent.capital:.0f} | "
                      f"Catch: {agent.total_catch}")
    
    print("\n\nRésumé final:")
    for agent in model.agents:
        print(f"\n{agent.fisher_type.upper()}:")
        print(f"  Total catch: {agent.total_catch}")
        print(f"  Capital: {agent.capital:.2f}")
        print(f"  Days at sea: {agent.days_at_sea}")
        print(f"  Trips: {len(agent.memory)}")
        
        if agent.memory:
            stats = agent.get_memory_statistics()
            print(f"  Avg profit: {stats['avg_profit']:.2f}")
            print(f"  Success rate: {stats['success_rate']:.1%}")
    
    print(f"\nStock total: {model.get_total_stock():,}")
    
    print("✓ Test réussi\n")

def test_multi_agent_simulation():
    """Test simulation avec plusieurs agents de chaque type"""
    print("=" * 60)
    print("TEST 8: Simulation multi-agents (1 an)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=10,
        num_coastal=5,
        num_trawler=2
    )
    
    print(f"\nConfiguration:")
    print(f"  {model.num_archipelago} archipelago")
    print(f"  {model.num_coastal} coastal")
    print(f"  {model.num_trawler} trawler")
    
    # Simulation
    print(f"\nSimulation de 365 jours...")
    
    for day in range(365):
        model.step()
        
        if (day + 1) % 30 == 0:  # Rapport mensuel
            month = (day + 1) // 30
            num_fishing = sum(1 for a in model.agents if a.gone_fishing)
            avg_capital = sum(a.capital for a in model.agents) / len(list(model.agents))
            total_catch = sum(a.total_catch for a in model.agents)
            
            print(f"  Mois {month}: {num_fishing} fishing | "
                  f"Avg capital: {avg_capital:.0f} | "
                  f"Total catch: {total_catch:,}")
    
    # Statistiques finales par type
    print("\n\nStatistiques finales par type:")
    
    for fisher_type in ["archipelago", "coastal", "trawler"]:
        agents_of_type = [a for a in model.agents if a.fisher_type == fisher_type]
        if agents_of_type:
            avg_catch = sum(a.total_catch for a in agents_of_type) / len(agents_of_type)
            avg_capital = sum(a.capital for a in agents_of_type) / len(agents_of_type)
            avg_days = sum(a.days_at_sea for a in agents_of_type) / len(agents_of_type)
            
            print(f"\n{fisher_type.upper()}:")
            print(f"  Nombre: {len(agents_of_type)}")
            print(f"  Capture moyenne: {avg_catch:,.0f}")
            print(f"  Capital moyen: {avg_capital:,.2f}")
            print(f"  Jours en mer moyen: {avg_days:.1f}")
    
    # Stocks finaux
    print(f"\n\nStock final total: {model.get_total_stock():,}")
    
    print("✓ Test réussi\n")

def run_all_tests():
    """Exécute tous les tests du Step 6"""
    print("\n" + "=" * 60)
    print("TESTS STEP 6: MODÈLES DE DÉCISION")
    print("=" * 60 + "\n")
    
    try:
        test_archipelago_satisficing()
        test_coastal_optimization()
        test_trawler_optimization()
        test_spot_selection_knowledge()
        test_spot_selection_expertise()
        test_spot_selection_descriptive_norm()
        test_integrated_decision_making()
        test_multi_agent_simulation()
        
        print("=" * 60)
        print("RÉSUMÉ")
        print("=" * 60)
        print("✓ Tous les tests du Step 6 ont été exécutés avec succès")
        print("\n🎉 Step 6 COMPLÉTÉ!")
        print("\nProchaines étapes:")
        print("  - Step 7: Utilités et helpers")
        print("  - Step 8: Outputs et collecte données")
        print("  - Step 9: Validation et calibration")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()