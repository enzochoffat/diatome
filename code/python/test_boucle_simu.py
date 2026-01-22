"""
Tests pour Step 5: Boucle de simulation
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model import FisheryModel

def test_weather_generation():
    """Test la génération de météo stochastique"""
    print("=" * 60)
    print("TEST 1: Génération de météo")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    # Simuler 1000 jours et compter mauvais temps
    bad_weather_count = 0
    for _ in range(1000):
        model.determine_weather()
        if model.bad_weather:
            bad_weather_count += 1
    
    bad_weather_rate = bad_weather_count / 1000
    
    print(f"Jours simulés: 1000")
    print(f"Jours de mauvais temps: {bad_weather_count}")
    print(f"Taux: {bad_weather_rate:.1%}")
    print(f"Attendu: {model.bad_weather_probability:.1%}")
    
    # Vérifier que le taux est proche de 10% (avec marge d'erreur)
    assert 0.05 < bad_weather_rate < 0.15, "Le taux de mauvais temps devrait être proche de 10%"
    
    print("✓ Test réussi\n")

def test_daily_step_execution():
    """Test l'exécution d'un step quotidien"""
    print("=" * 60)
    print("TEST 2: Exécution step quotidien")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=2,
        num_coastal=1,
        num_trawler=0
    )
    
    initial_steps = model.current_step
    initial_stock = model.get_total_stock()
    
    print(f"État initial:")
    print(f"  Steps: {initial_steps}")
    print(f"  Stock total: {initial_stock:,.0f}")
    print(f"  Nombre agents: {len(list(model.agents))}")
    
    # Exécuter 1 step
    model.step()
    
    print(f"\nAprès 1 step:")
    print(f"  Steps: {model.current_step}")
    print(f"  Météo: {'Mauvais' if model.bad_weather else 'Bon'}")
    print(f"  Stock total: {model.get_total_stock():,.0f}")
    
    # Vérifications
    assert model.current_step == initial_steps + 1, "Le compteur de steps devrait augmenter"
    assert model.bad_weather in [True, False], "La météo devrait être définie"
    
    # Vérifier que les agents ont agi
    for agent in model.agents:
        assert agent.at_home or agent.gone_fishing, "Les agents devraient avoir un état défini"
    
    print("✓ Test réussi\n")

def test_data_collection():
    """Test la collecte de données"""
    print("=" * 60)
    print("TEST 3: Collecte de données")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=2,
        num_coastal=1,
        num_trawler=1
    )
    
    # Exécuter 10 jours
    for _ in range(10):
        model.step()
    
    # Récupérer données
    model_data = model.datacollector.get_model_vars_dataframe()
    agent_data = model.datacollector.get_agent_vars_dataframe()
    
    print(f"Jours simulés: {len(model_data)}")
    print(f"\nColonnes model data: {list(model_data.columns)}")
    print(f"Colonnes agent data: {list(agent_data.columns.get_level_values(0).unique())}")
    
    print(f"\nDernières valeurs:")
    print(f"  Stock A: {model_data['stock_A'].iloc[-1]:,.0f}")
    print(f"  Stock total: {model_data['total_stock'].iloc[-1]:,.0f}")
    print(f"  Agents pêchant: {model_data['num_fishing'].iloc[-1]}")
    print(f"  Agents à la maison: {model_data['num_at_home'].iloc[-1]}")
    print(f"  Capital moyen: {model_data['avg_capital'].iloc[-1]:.2f}")
    
    # Vérifications
    assert len(model_data) == 10, "Devrait avoir 10 lignes de données"
    assert not model_data['total_stock'].isna().any(), "Le stock ne devrait pas être NaN"
    assert (model_data['stock_A'] >= 0).all(), "Les stocks ne devraient pas être négatifs"
    
    print("✓ Test réussi\n")

def test_annual_regeneration():
    """Test la régénération annuelle des stocks"""
    print("=" * 60)
    print("TEST 4: Régénération annuelle")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=5,
        num_coastal=0,
        num_trawler=0
    )
    
    print("Simulation de 3 ans avec pêche intensive...")
    
    # Simuler 3 ans
    years_data = []
    
    for year in range(3):
        # Stock début d'année
        start_stock = model.get_region_stock("A")
        
        # Simuler 1 an
        for day in range(365):
            model.step()
        
        # Stock fin d'année (après régénération)
        end_stock = model.get_region_stock("A")
        
        total_catch = sum(a.total_catch for a in model.agents)
        
        years_data.append({
            'year': year + 1,
            'start_stock': start_stock,
            'end_stock': end_stock,
            'regeneration': end_stock - start_stock,
            'total_catch': total_catch
        })
        
        print(f"\nAnnée {year+1}:")
        print(f"  Stock début: {start_stock:,.0f}")
        print(f"  Stock fin: {end_stock:,.0f}")
        print(f"  Régénération: {end_stock - start_stock:+,.0f}")
        print(f"  Capture totale cumulative: {total_catch:,.0f}")
    
    # Vérifications
    for data in years_data:
        assert data['end_stock'] > 0, "Le stock ne devrait pas s'épuiser complètement"
        # Avec pêche, la régénération peut être positive ou négative selon l'intensité
    
    print("✓ Test réussi\n")

def test_full_year_simulation():
    """Test simulation complète sur 1 an (365 jours)"""
    print("=" * 60)
    print("TEST 5: Simulation 1 an complet")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=3,
        num_coastal=2,
        num_trawler=1
    )
    
    print(f"Configuration:")
    print(f"  Archipelago: {model.num_archipelago}")
    print(f"  Coastal: {model.num_coastal}")
    print(f"  Trawler: {model.num_trawler}")
    print(f"  Total agents: {len(list(model.agents))}")
    
    initial_stocks = {
        'A': model.get_region_stock("A"),
        'B': model.get_region_stock("B"),
        'C': model.get_region_stock("C"),
        'D': model.get_region_stock("D"),
        'total': model.get_total_stock()
    }
    
    print(f"\nStocks initiaux:")
    for region, stock in initial_stocks.items():
        print(f"  {region}: {stock:,.0f}")
    
    # Simuler 1 an
    print("\nSimulation en cours...")
    model.run_model(steps=365)
    
    final_stocks = {
        'A': model.get_region_stock("A"),
        'B': model.get_region_stock("B"),
        'C': model.get_region_stock("C"),
        'D': model.get_region_stock("D"),
        'total': model.get_total_stock()
    }
    
    print(f"\nStocks finaux:")
    for region, stock in final_stocks.items():
        change = stock - initial_stocks[region]
        print(f"  {region}: {stock:,.0f} ({change:+,.0f})")
    
    # Statistiques agents
    print(f"\nStatistiques agents:")
    for agent in model.agents:
        print(f"  Agent {agent.unique_id} ({agent.fisher_type}):")
        print(f"    Capital: {agent.capital:.2f}")
        print(f"    Total catch: {agent.total_catch}")
        print(f"    Days at sea: {agent.days_at_sea}")
        print(f"    Memory size: {len(agent.memory)}")
        print(f"    Known spots: {len(agent.good_spots_memory)}")
    
    # Analyse données collectées
    model_data = model.datacollector.get_model_vars_dataframe()
    
    print(f"\nAnalyse temporelle:")
    print(f"  Jours de mauvais temps: {model_data['bad_weather'].sum()}")
    print(f"  Taux mauvais temps: {model_data['bad_weather'].mean():.1%}")
    print(f"  Capture totale: {model_data['total_catch'].iloc[-1]:,.0f}")
    print(f"  Capital moyen final: {model_data['avg_capital'].iloc[-1]:,.2f}")
    
    # Vérifications
    assert model.current_step == 365, "Devrait avoir simulé 365 jours"
    assert final_stocks['total'] > 0, "Le stock total ne devrait pas être épuisé"
    assert all(final_stocks[r] >= 0 for r in ['A', 'B', 'C', 'D']), "Aucun stock ne devrait être négatif"
    
    print("✓ Test réussi\n")

def test_multi_year_simulation():
    """Test simulation sur plusieurs années"""
    print("=" * 60)
    print("TEST 6: Simulation multi-années (3 ans)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*3,
        num_archipelago=2,
        num_coastal=1,
        num_trawler=0
    )
    
    print("Simulation de 3 ans...")
    model.run_model(steps=365*3)
    
    # Analyser données
    model_data = model.datacollector.get_model_vars_dataframe()
    
    print(f"\nRésumé 3 ans:")
    print(f"  Steps total: {model.steps}")
    print(f"  Années: {model.steps // 365}")
    
    # Grouper par année
    model_data['year'] = model_data['current_year']
    yearly_summary = model_data.groupby('year').agg({
        'total_stock': ['mean', 'min', 'max'],
        'total_catch': 'max',
        'avg_capital': 'mean',
        'bad_weather': 'sum'
    })
    
    print(f"\nRésumé annuel:")
    print(yearly_summary)
    
    # Vérifier stabilité du système
    final_stock = model.get_total_stock()
    initial_stock = model_data['total_stock'].iloc[0]
    
    print(f"\nÉvolution stock:")
    print(f"  Initial: {initial_stock:,.0f}")
    print(f"  Final: {final_stock:,.0f}")
    print(f"  Variation: {(final_stock - initial_stock) / initial_stock * 100:+.1f}%")
    
    assert model.current_step == 365*3, "Devrait avoir simulé 3 ans"
    assert final_stock > initial_stock * 0.5, "Le stock ne devrait pas s'effondrer"
    
    print("✓ Test réussi\n")

def test_model_summary():
    """Test la fonction get_model_summary"""
    print("=" * 60)
    print("TEST 7: Résumé du modèle")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365*25,
        num_archipelago=2,
        num_coastal=1,
        num_trawler=1
    )
    
    # Simuler quelques jours
    for _ in range(50):
        model.step()
    
    summary = model.get_model_summary()
    
    print("Résumé du modèle:")
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"  {key}: {value:,.2f}")
        else:
            print(f"  {key}: {value:,}")
    
    # Vérifications
    assert summary['current_step'] == 50
    assert summary['current_year'] == 0
    assert summary['current_day'] == 50
    assert summary['num_agents'] == 4
    assert 'total_stock' in summary
    assert 'avg_capital' in summary
    
    print("✓ Test réussi\n")

def run_all_tests():
    """Exécute tous les tests du Step 5"""
    print("\n" + "=" * 60)
    print("TESTS STEP 5: BOUCLE DE SIMULATION")
    print("=" * 60 + "\n")
    
    try:
        test_weather_generation()
        test_daily_step_execution()
        test_data_collection()
        test_annual_regeneration()
        test_full_year_simulation()
        test_multi_year_simulation()
        test_model_summary()
        
        print("=" * 60)
        print("RÉSUMÉ")
        print("=" * 60)
        print("✓ Tous les tests du Step 5 ont été exécutés avec succès")
        print("✓ Le système de simulation est opérationnel")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()