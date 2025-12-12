"""
Script de test pour créer plusieurs agents et vérifier leur intégration avec le modèle
"""

import sys
sys.path.append('.')

from model import FisheryModel
from agent import FisherAgent

def test_create_multiple_agents():
    """Test la création de plusieurs agents de chaque type"""
    print("=" * 50)
    print("TEST: Création de plusieurs agents")
    print("=" * 50)
    
    # Créer un modèle
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=5,
        num_coastal=5,
        num_trawler=5
    )
    
    print(f"✓ Modèle créé")
    
    # Créer plusieurs agents de chaque type
    archipelago_agents = []
    coastal_agents = []
    trawler_agents = []
    
    # Créer 5 archipelago fishers
    for i in range(5):
        agent = FisherAgent(model=model, style="archipelago")
        archipelago_agents.append(agent)
    
    # Créer 5 coastal fishers
    for i in range(5):
        agent = FisherAgent(model=model, style="coastal")
        coastal_agents.append(agent)
    
    # Créer 5 trawler fishers
    for i in range(5):
        agent = FisherAgent(model=model, style="trawler")
        trawler_agents.append(agent)
    
    total_agents = len(archipelago_agents) + len(coastal_agents) + len(trawler_agents)
    
    print(f"\n✓ {total_agents} agents créés:")
    print(f"  - {len(archipelago_agents)} archipelago fishers")
    print(f"  - {len(coastal_agents)} coastal fishers")
    print(f"  - {len(trawler_agents)} trawler fishers")
    
    # Vérifier que tous les agents ont des IDs uniques
    all_agents = archipelago_agents + coastal_agents + trawler_agents
    unique_ids = set([agent.unique_id for agent in all_agents])
    
    if len(unique_ids) == total_agents:
        print(f"\n✓ Tous les agents ont des IDs uniques")
        print(f"  IDs: {sorted(unique_ids)}")
    else:
        print(f"\n✗ PROBLÈME: IDs dupliqués détectés")
        print(f"  Total agents: {total_agents}")
        print(f"  IDs uniques: {len(unique_ids)}")
    
    return model, all_agents


def test_agent_attributes():
    """Test que tous les agents ont les bons attributs initiaux"""
    print("\n" + "=" * 50)
    print("TEST: Vérification des attributs des agents")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=10,
        num_coastal=10,
        num_trawler=10
    )
    
    # Créer un échantillon d'agents
    test_agents = [
        FisherAgent(model=model, style="archipelago"),
        FisherAgent(model=model, style="coastal"),
        FisherAgent(model=model, style="trawler")
    ]
    
    required_attributes = [
        'style', 'willFish', 'layLow', 'atHome', 'currentCapital',
        'previousCapital', 'satisfaction', 'catch', 'accumulatedCatch',
        'accumulatedCatchThisYear', 'profit', 'accumulatedProfit',
        'accumulatedProfitThisYear', 'lowCatchCounter', 'notAtSeaCounter',
        'atSea', 'goneFishing', 'jumped', 'thinkFishIsScarce',
        'fishOnboard', 'memoryCatchTicks', 'memoryCatch', 'memoryCatchA',
        'memoryCatchB', 'memoryCatchC', 'memoryCatchD', 'memoryProfit',
        'growthPerception', 'goodSpotToday', 'counterWentFishing',
        'counterFishingPeriod'
    ]
    
    all_ok = True
    for agent in test_agents:
        print(f"\nAgent {agent.style} (ID: {agent.unique_id}):")
        missing = []
        for attr in required_attributes:
            if not hasattr(agent, attr):
                missing.append(attr)
                all_ok = False
        
        if missing:
            print(f"  ✗ Attributs manquants: {', '.join(missing)}")
        else:
            print(f"  ✓ Tous les attributs requis sont présents ({len(required_attributes)} attributs)")
    
    if all_ok:
        print(f"\n✓ Tous les agents ont les attributs requis")
    else:
        print(f"\n✗ Certains attributs sont manquants")
    
    return all_ok


def test_model_registration():
    """Test que les agents sont bien enregistrés dans le modèle"""
    print("\n" + "=" * 50)
    print("TEST: Enregistrement des agents dans le modèle")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=10,
        num_coastal=10,
        num_trawler=10
    )
    
    print(f"Nombre initial d'agents dans le modèle: {len(model.agents)}")
    
    # Créer des agents
    agents_created = []
    for i in range(3):
        agents_created.append(FisherAgent(model=model, style="archipelago"))
    for i in range(3):
        agents_created.append(FisherAgent(model=model, style="coastal"))
    for i in range(3):
        agents_created.append(FisherAgent(model=model, style="trawler"))
    
    print(f"Nombre d'agents créés: {len(agents_created)}")
    print(f"Nombre d'agents dans le modèle: {len(model.agents)}")
    
    if len(model.agents) == len(agents_created):
        print(f"\n✓ Tous les agents sont enregistrés dans le modèle")
    else:
        print(f"\n✗ Problème d'enregistrement des agents")
    
    # Vérifier que chaque agent créé est dans le modèle
    all_in_model = all(agent in model.agents for agent in agents_created)
    if all_in_model:
        print(f"✓ Tous les agents créés sont bien dans model.agents")
    else:
        print(f"✗ Certains agents créés ne sont pas dans model.agents")


def test_agent_initial_values():
    """Test les valeurs initiales des agents"""
    print("\n" + "=" * 50)
    print("TEST: Valeurs initiales des agents")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=10,
        num_coastal=10,
        num_trawler=10
    )
    
    agent = FisherAgent(model=model, style="archipelago")
    
    print(f"\nAgent {agent.style} (ID: {agent.unique_id}):")
    print(f"  willFish: {agent.willFish} (attendu: True)")
    print(f"  atHome: {agent.atHome} (attendu: True)")
    print(f"  currentCapital: {agent.currentCapital} (attendu: 0)")
    print(f"  catch: {agent.catch} (attendu: 0)")
    print(f"  satisfaction: {agent.satisfaction:.3f} (attendu: entre 0 et 1)")
    print(f"  fishOnboard: {agent.fishOnboard} (attendu: 0)")
    
    # Vérifications
    checks = [
        (agent.willFish == True, "willFish = True"),
        (agent.atHome == True, "atHome = True"),
        (agent.currentCapital == 0, "currentCapital = 0"),
        (agent.catch == 0, "catch = 0"),
        (0 <= agent.satisfaction <= 1, "satisfaction entre 0 et 1"),
        (agent.fishOnboard == 0, "fishOnboard = 0"),
    ]
    
    print("\nVérifications:")
    all_ok = True
    for check, desc in checks:
        if check:
            print(f"  ✓ {desc}")
        else:
            print(f"  ✗ {desc}")
            all_ok = False
    
    if all_ok:
        print("\n✓ Toutes les valeurs initiales sont correctes")
    else:
        print("\n✗ Certaines valeurs initiales sont incorrectes")


def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "#" * 50)
    print("# TESTS DE CRÉATION DE PLUSIEURS AGENTS")
    print("#" * 50 + "\n")
    
    try:
        # Test 1: Création multiple
        test_create_multiple_agents()
        
        # Test 2: Attributs
        test_agent_attributes()
        
        # Test 3: Enregistrement
        test_model_registration()
        
        # Test 4: Valeurs initiales
        test_agent_initial_values()
        
        print("\n" + "=" * 50)
        print("RÉSUMÉ FINAL")
        print("=" * 50)
        print("✓ Tous les tests ont été exécutés")
        print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
