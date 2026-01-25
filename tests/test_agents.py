"""
Script de test pour vérifier la création et les propriétés des agents
"""

import sys
sys.path.append('.')

from model import FisheryModel
from agent import FisherAgent

def test_model_creation():
    """Test la création du modèle"""
    print("=" * 50)
    print("TEST 1: Création du modèle")
    print("=" * 50)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=30,
        num_coastal=30,
        num_trawler=30
    )
    
    print(f"✓ Modèle créé avec succès")
    print(f"  - Nombre archipelago: {model.num_archipelago}")
    print(f"  - Nombre coastal: {model.num_coastal}")
    print(f"  - Nombre trawler: {model.num_trawler}")
    print(f"  - Durée simulation: {model.end_of_sim} ticks")
    print()
    
    return model


def test_agent_creation(model):
    """Test la création des différents types d'agents"""
    print("=" * 50)
    print("TEST 2: Création des agents")
    print("=" * 50)
    
    # Créer un agent de chaque type
    agents = []
    
    # Agent archipelago
    agent_archipelago = FisherAgent(
        model=model,
        style="archipelago"
    )
    agents.append(("Archipelago", agent_archipelago))
    
    # Agent coastal
    agent_coastal = FisherAgent(
        model=model,
        style="coastal"
    )
    agents.append(("Coastal", agent_coastal))
    
    # Agent trawler
    agent_trawler = FisherAgent(
        model=model,
        style="trawler"
    )
    agents.append(("Trawler", agent_trawler))
    
    print(f"✓ {len(agents)} agents créés avec succès\n")
    
    return agents


def test_agent_properties(agents):
    """Test les propriétés des agents"""
    print("=" * 50)
    print("TEST 3: Vérification des propriétés des agents")
    print("=" * 50)
    
    for style_name, agent in agents:
        print(f"\n{style_name} Fisher (ID: {agent.unique_id}):")
        print(f"  - Style: {agent.style}")
        print(f"  - Will Fish: {agent.willFish if hasattr(agent, 'willFish') else 'Non défini'}")
        print(f"  - At Home: {agent.atHome if hasattr(agent, 'atHome') else 'Non défini'}")
        print(f"  - Current Capital: {agent.currentCapital if hasattr(agent, 'currentCapital') else 'Non défini'}")
        print(f"  - Catch: {agent.catch if hasattr(agent, 'catch') else 'Non défini'}")
    
    print()


def test_agent_step_methods(agents):
    """Test les méthodes step des agents"""
    print("=" * 50)
    print("TEST 4: Test des méthodes step")
    print("=" * 50)
    
    for style_name, agent in agents:
        print(f"\n{style_name} Fisher:")
        try:
            # Vérifier que la méthode step existe
            if hasattr(agent, 'step'):
                print(f"  ✓ Méthode step() existe")
                
                # Vérifier que les méthodes spécifiques au style existent
                if agent.style == "archipelago" and hasattr(agent, 'archipelago'):
                    print(f"  ✓ Méthode archipelago() existe")
                elif agent.style == "coastal" and hasattr(agent, 'coastal'):
                    print(f"  ✓ Méthode coastal() existe")
                elif agent.style == "trawler" and hasattr(agent, 'trawler'):
                    print(f"  ✓ Méthode trawler() existe")
            else:
                print(f"  ✗ Méthode step() manquante")
        except Exception as e:
            print(f"  ✗ Erreur: {str(e)}")
    
    print()


def test_model_constants(model):
    """Test l'accès aux constantes du modèle"""
    print("=" * 50)
    print("TEST 5: Vérification des constantes du modèle")
    print("=" * 50)
    
    constants_to_check = [
        ('CATCHABILITY_ARCHEPELAGO', 5),
        ('CATCHABILITY_COASTAL', 10),
        ('CATCHABILITY_TRAWLER', 50),
        ('LOW_COST_EXISTENCE', 0.5),
        ('MEDIUM_COST_EXISTENCE', 1.0),
        ('HIGH_COST_EXISTENCE', 5.0),
        ('MSY_STOCK_A', 109500),
        ('MSY_STOCK_B', 219000),
        ('MSY_STOCK_C', 438000),
        ('MSY_STOCK_D', 438000),
    ]
    
    all_ok = True
    for const_name, expected_value in constants_to_check:
        if hasattr(model, const_name):
            actual_value = getattr(model, const_name)
            if actual_value == expected_value:
                print(f"  ✓ {const_name}: {actual_value}")
            else:
                print(f"  ⚠ {const_name}: {actual_value} (attendu: {expected_value})")
                all_ok = False
        else:
            print(f"  ✗ {const_name}: non défini")
            all_ok = False
    
    print()
    if all_ok:
        print("✓ Toutes les constantes sont correctement définies")
    else:
        print("⚠ Certaines constantes nécessitent une vérification")
    print()


def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "=" * 50)
    print("TESTS DE CRÉATION DES AGENTS")
    print("=" * 50 + "\n")
    
    try:
        # Test 1: Création du modèle
        model = test_model_creation()
        
        # Test 2: Création des agents
        agents = test_agent_creation(model)
        
        # Test 3: Propriétés des agents
        test_agent_properties(agents)
        
        # Test 4: Méthodes step
        test_agent_step_methods(agents)
        
        # Test 5: Constantes du modèle
        test_model_constants(model)
        
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
