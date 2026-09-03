1. Créer `src/domain/agents/behavior/nom_de_la_flottille.py`
2. Créer la classe `NomDeLaFlottille` avec fonctions et arbre de décision
3. Ajouter l'import dans `src/domain/agents/behavior/__init__.py`
4. Ajouter l'import dans `src/core/agent.py`
5. Dans `agent.py`, ajouter un bloc `elif` dans `_set_type_attributes()`
6. Dans `agent.py`, ajouter les comportements spécifiques dans `return_home()` et `decide_fishSpot()` si nécessaire
7. Dans `agent.py`, ajouter l'appel dans `make_decision()`
8. Dans `agent.py`, mettre à jour le constructeur et `get_agent_summary()` si champs spécifiques
9. Dans `src/core/config.py`, ajouter les constantes et mettre à jour `get_fisher_config()` et `validate_config()` (sera supprimé un jour)
10. Dans `src/core/model.py`, ajouter `num_nom_flottille` et `nom_flottille_names` en paramètres
11. Dans `src/domain/agents/factory.py`, ajouter la boucle de création des agents
12. Dans `src/infrastructure/loader/loader.py`, mettre à jour les clés requises et les assignments
13. Dans `configs_json/config_default.json`, ajouter les champs de configuration
14. Dans `src/servicies/metrics.py`, ajouter la flottille dans les métriques
15. Dans `src/interfaces/cli/report.py`, ajouter dans les rapports (pas utile)
16. Dans `src/interfaces/gui/gui.py` (si utilisée), ajouter les contrôles UI (pas utile)
17. Dans `src/domain/agents/fishing.py`, ajouter des branches si comportement de pêche spécifique
18. Dans `src/domain/agents/movement.py`, ajouter une branche si coût de déplacement spécifique