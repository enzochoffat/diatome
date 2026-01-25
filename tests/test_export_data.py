"""
Tests pour Step 8: Outputs et collecte de données
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model import FisheryModel
import pandas as pd

def test_datacollector_basic():
    """Test collecte données de base"""
    print("=" * 60)
    print("TEST 1: DataCollector basique")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=30,
        num_archipelago=2,
        num_coastal=1,
        num_trawler=1
    )
    
    print("\nSimulation 30 jours...")
    for _ in range(30):
        model.step()
    
    # Vérifier données collectées
    model_df = model.datacollector.get_model_vars_dataframe()
    agent_df = model.datacollector.get_agent_vars_dataframe()
    
    print(f"\nDonnées collectées:")
    print(f"  Model vars: {len(model_df)} rows, {len(model_df.columns)} columns")
    print(f"  Agent vars: {len(agent_df)} rows, {len(agent_df.columns)} columns")
    
    # Vérifier colonnes clés
    required_model_cols = ['stock_A', 'stock_B', 'total_catch_cumulative', 
                           'avg_capital', 'gini_capital', 'num_fishing']
    for col in required_model_cols:
        assert col in model_df.columns, f"Colonne manquante: {col}"
    
    required_agent_cols = ['fisher_type', 'capital', 'total_catch', 
                           'gone_fishing', 'will_fish']
    for col in required_agent_cols:
        assert col in agent_df.columns, f"Colonne manquante: {col}"
    
    print("\n✓ Toutes les colonnes requises présentes")
    
    # Afficher échantillon
    print("\nÉchantillon données model (5 derniers jours):")
    print(model_df[['current_step', 'stock_A', 'total_catch_cumulative', 
                    'avg_capital', 'num_fishing']].tail())
    
    print("✓ Test réussi\n")

def test_gini_calculation():
    """Test calcul coefficient Gini"""
    print("=" * 60)
    print("TEST 2: Calcul Gini")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=10,
        num_archipelago=1,
        num_coastal=0,
        num_trawler=0
    )
    
    # Test cas parfaite égalité
    print("\nTest 1: Égalité parfaite")
    equal_values = [100, 100, 100, 100]
    gini_equal = model.calculate_gini(equal_values)
    print(f"  Values: {equal_values}")
    print(f"  Gini: {gini_equal:.3f} (attendu: ~0.000)")
    assert gini_equal < 0.01, "Gini devrait être proche de 0 pour égalité"
    
    # Test cas parfaite inégalité
    print("\nTest 2: Inégalité maximale")
    unequal_values = [0, 0, 0, 1000]
    gini_unequal = model.calculate_gini(unequal_values)
    print(f"  Values: {unequal_values}")
    print(f"  Gini: {gini_unequal:.3f} (attendu: ~0.750)")
    assert gini_unequal > 0.7, "Gini devrait être élevé pour inégalité"
    
    # Test cas intermédiaire
    print("\nTest 3: Inégalité modérée")
    moderate_values = [50, 100, 150, 200]
    gini_moderate = model.calculate_gini(moderate_values)
    print(f"  Values: {moderate_values}")
    print(f"  Gini: {gini_moderate:.3f} (attendu: 0.2-0.4)")
    assert 0.2 < gini_moderate < 0.4, "Gini devrait être modéré"
    
    # Test valeurs négatives
    print("\nTest 4: Avec valeurs négatives")
    negative_values = [-50, 100, 200, 300]
    gini_negative = model.calculate_gini(negative_values)
    print(f"  Values: {negative_values}")
    print(f"  Gini: {gini_negative:.3f}")
    print(f"  Note: valeurs négatives traitées comme 0")
    
    print("\n✓ Test réussi\n")

def test_yearly_data_collection():
    """Test collecte données annuelles"""
    print("=" * 60)
    print("TEST 3: Collecte données annuelles")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=730,  # 2 ans
        num_archipelago=3,
        num_coastal=2,
        num_trawler=1
    )
    
    print("\nSimulation 2 ans...")
    for _ in range(730):
        model.step()
        if not model.running:
            break
    
    print(f"\nDonnées annuelles collectées: {len(model.yearly_data)} années")
    
    assert len(model.yearly_data) == 2, "Devrait avoir 2 années de données"
    
    # Vérifier structure
    year1 = model.yearly_data[0]
    print(f"\nAnnée 1 summary:")
    print(f"  Year: {year1['year']}")
    print(f"  Total stock: {year1['total_stock']:,.0f}")
    print(f"  Total catch: {year1['total_catch_all']:,.0f}")
    print(f"  Total capital: {year1['total_capital']:,.2f}")
    print(f"  Gini capital: {year1['gini_capital']:.3f}")
    print(f"  Success rate: {year1['avg_success_rate']:.1%}")
    
    # Vérifier clés requises
    required_keys = ['year', 'stock_A', 'total_catch_all', 'gini_capital', 
                     'avg_success_rate', 'num_agents']
    for key in required_keys:
        assert key in year1, f"Clé manquante: {key}"
    
    print("\n✓ Test réussi\n")

def test_data_export():
    """Test export données vers CSV"""
    print("=" * 60)
    print("TEST 4: Export données CSV")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=100,
        num_archipelago=2,
        num_coastal=1,
        num_trawler=1
    )
    
    print("\nSimulation 100 jours...")
    for _ in range(100):
        model.step()
    
    # Export
    print("\nExport données...")
    model.export_data(filename_prefix="test_output")
    
    # Vérifier fichiers créés
    import glob
    csv_files = glob.glob("test_output_*.csv")
    print(f"\nFichiers créés: {len(csv_files)}")
    for f in csv_files:
        size = os.path.getsize(f)
        print(f"  {f}: {size:,} bytes")
    
    assert len(csv_files) >= 2, "Devrait avoir au moins 2 fichiers CSV"
    
    # Nettoyer
    print("\nNettoyage fichiers test...")
    for f in csv_files:
        os.remove(f)
        print(f"  Supprimé: {f}")
    
    print("\n✓ Test réussi\n")

def test_periodic_metrics():
    """Test métriques périodiques avancées"""
    print("=" * 60)
    print("TEST 5: Métriques périodiques")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=365,
        num_archipelago=5,
        num_coastal=3,
        num_trawler=2
    )
    
    print("\nSimulation 1 an...")
    for _ in range(365):
        model.step()
    
    # Récupérer données
    model_df = model.datacollector.get_model_vars_dataframe()
    
    # Analyser tendances
    print(f"\n--- TENDANCES ANNUELLES ---")
    
    # Stocks
    stock_start = model_df['total_stock'].iloc[0]
    stock_end = model_df['total_stock'].iloc[-1]
    stock_change = ((stock_end - stock_start) / stock_start) * 100
    print(f"Stock total: {stock_start:,.0f} → {stock_end:,.0f} ({stock_change:+.1f}%)")
    
    # Catches
    total_catch = model_df['total_catch_cumulative'].iloc[-1]
    avg_daily_catch = model_df['total_catch_daily'].mean()
    print(f"Capture totale: {total_catch:,.0f} (moy. {avg_daily_catch:.0f}/jour)")
    
    # Capital
    capital_start = model_df['avg_capital'].iloc[0]
    capital_end = model_df['avg_capital'].iloc[-1]
    capital_change = ((capital_end - capital_start) / capital_start) * 100 if capital_start != 0 else 0
    print(f"Capital moyen: {capital_start:,.2f} → {capital_end:,.2f} ({capital_change:+.1f}%)")
    
    # Gini
    gini_start = model_df['gini_capital'].iloc[0]
    gini_end = model_df['gini_capital'].iloc[-1]
    gini_change = gini_end - gini_start
    print(f"Gini capital: {gini_start:.3f} → {gini_end:.3f} ({gini_change:+.3f})")
    
    # Activity
    avg_fishing = model_df['num_fishing'].mean()
    max_fishing = model_df['num_fishing'].max()
    print(f"Agents pêchant: moy={avg_fishing:.1f}, max={max_fishing}")
    
    # Bad weather days
    bad_weather_days = model_df['bad_weather'].sum()
    print(f"Jours mauvais temps: {bad_weather_days} ({bad_weather_days/365:.1%})")
    
    print("\n✓ Test réussi\n")

def test_integrated_simulation():
    """Test simulation intégrée complète avec analyse"""
    print("=" * 60)
    print("TEST 6: Simulation intégrée (5 ans)")
    print("=" * 60)
    
    model = FisheryModel(
        end_of_sim=1825,  # 5 ans
        num_archipelago=10,
        num_coastal=5,
        num_trawler=3
    )
    
    print(f"\nConfiguration:")
    print(f"  Archipelago: {model.num_archipelago}")
    print(f"  Coastal: {model.num_coastal}")
    print(f"  Trawler: {model.num_trawler}")
    print(f"  Total: {model.num_archipelago + model.num_coastal + model.num_trawler}")
    
    print(f"\nSimulation 5 ans ({1825} jours)...")
    print("(Affichage résumé annuel uniquement)\n")
    
    for _ in range(1825):
        model.step()
        if not model.running:
            break
    
    # Analyse finale
    print(f"\n--- ANALYSE FINALE ---")
    
    model_df = model.datacollector.get_model_vars_dataframe()
    
    # Evolution stocks
    print(f"\nÉvolution stocks par région:")
    for region in ['A', 'B', 'C', 'D']:
        start = model_df[f'stock_{region}'].iloc[0]
        end = model_df[f'stock_{region}'].iloc[-1]
        change = ((end - start) / start) * 100
        msy = getattr(model, f'MSY_STOCK_{region}')
        pct_msy = (end / msy) * 100
        print(f"  Region {region}: {start:>8,.0f} → {end:>8,.0f} ({change:>+6.1f}%) [{pct_msy:>5.1f}% MSY]")
    
    # Distribution catches par type
    agent_df = model.datacollector.get_agent_vars_dataframe()
    final_agents = agent_df.xs(model.current_step - 1, level='Step')
    
    print(f"\nDistribution captures finales:")
    for ftype in ['archipelago', 'coastal', 'trawler']:
        type_agents = final_agents[final_agents['fisher_type'] == ftype]
        if len(type_agents) > 0:
            total = type_agents['total_catch'].sum()
            avg = type_agents['total_catch'].mean()
            median = type_agents['total_catch'].median()
            print(f"  {ftype:>11}: total={total:>10,.0f}, avg={avg:>8,.0f}, median={median:>8,.0f}")
    
    # Inequality trends
    print(f"\nÉvolution inégalités:")
    gini_initial = model_df['gini_capital'].iloc[0]
    gini_final = model_df['gini_capital'].iloc[-1]
    print(f"  Gini capital: {gini_initial:.3f} → {gini_final:.3f} ({gini_final - gini_initial:+.3f})")
    
    # Success rates
    print(f"\nTaux de succès:")
    success_initial = model_df['avg_success_rate'].iloc[0]
    success_final = model_df['avg_success_rate'].iloc[-1]
    print(f"  Initial: {success_initial:.1%}")
    print(f"  Final: {success_final:.1%}")
    
    # Bankruptcies
    bankrupt_final = final_agents['bankrupt'].sum()
    print(f"\nFaillites: {bankrupt_final} agents")
    
    print("\n✓ Test réussi\n")

def run_all_tests():
    """Exécute tous les tests du Step 8"""
    print("\n" + "=" * 60)
    print("TESTS STEP 8: OUTPUTS ET COLLECTE DE DONNÉES")
    print("=" * 60 + "\n")
    
    try:
        test_datacollector_basic()
        test_gini_calculation()
        test_yearly_data_collection()
        test_data_export()
        test_periodic_metrics()
        test_integrated_simulation()
        
        print("=" * 60)
        print("RÉSUMÉ")
        print("=" * 60)
        print("✓ Tous les tests du Step 8 ont été exécutés avec succès")
        print("\n🎉 Step 8 COMPLÉTÉ!")
        print("\nProchaines étapes:")
        print("  - Step 9: Validation et calibration")
        print("  - Comparaison avec outputs NetLogo")
        print("  - Analyses de sensibilité")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERREUR lors des tests: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()