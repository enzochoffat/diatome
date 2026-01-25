# Plan de Conversion NetLogo → Python

## Contexte

Conversion du modèle FIBE (Fishery and Individual-Based Ecological model) de NetLogo vers Python/Mesa. Le modèle simule la reproduction des poissons et les comportements de pêcheurs avec différents styles de pêche dans la mer Baltique suédoise.

## État Actuel

**Complété (~8%)**:
- Structure Mesa de base (Model, Agent)
- Constantes définies (coûts, capacités, catchability)
- Attributs des agents déclarés
- Tests de création basiques

**En cours**:
- Environnement spatial (Step 1)

## Étapes d'Implémentation

### Step 1: Créer l'environnement spatial ✓ (en cours)

**Fichier**: `code/python/model.py`

**Tâches**:
- [x] Implémenter MultiGrid Mesa (50x56)  
- [x] Définir les régions A/B/C/D/LAND par coordonnées
- [x] Créer dictionnaire `patches` avec propriétés par cellule:
  - `region`: A/B/C/D/LAND/NULL
  - `density`: LOW/MEDIUM/HIGH
  - `fish_stock`: stock actuel de poissons
  - `carrying_capacity`: capacité de charge (4/3276/8736)
  - `growth_rate`: taux de croissance (0.1)
- [x] Générer hotspots selon coordonnées prédéfinies
- [x] Initialiser stocks à 50% de capacité (niveau MSY)
- [ ] Tester et valider avec `test_fish_stock.py`

**Méthodes créées**:
- `init_patches()`: Initialisation de toutes les cellules
- `get_region(x, y)`: Déterminer la région d'une coordonnée
- `get_density(x, y, region)`: Calculer densité selon proximité hotspots
- `get_carrying_capacity(region, density)`: Retourner capacité selon densité
- `get_initial_fish_stock(x, y, region, density)`: Stock initial (K/2)
- `get_region_stock(region_name)`: Stock total par région
- `get_total_stock()`: Stock total du modèle

---

### Step 2: Implémenter les dynamiques des poissons

**Fichier**: `code/python/model.py`

**Tâches**:
- [x] Implémenter `update_fish_stock()`: Croissance logistique annuelle
  - Formule: `regen = stock * r * (1 - stock/K)`
  - Appeler pour chaque patch
  - Vérifier contraintes régionales
- [ ] Implémenter `reduce_stock(x, y, amount)`: Décompte après capture
  - Retourner montant réellement capturé (min de amount et stock)
  - Empêcher stock négatif
- [ ] Ajouter `get_region_carrying_capacity(region)`: Capacité totale région
- [ ] Implémenter `validate_regional_stocks()`: Vérifier limites régionales
- [ ] Tester sur 10 ans sans pêche (vérifier équilibre K)

**Considérations**:
- La croissance au niveau patch peut dépasser la capacité régionale
- Appliquer facteur d'échelle si nécessaire
- Régénération annuelle uniquement (pas quotidienne)

---

### Step 3: Développer le système de mémoire

**Fichier**: `code/python/agent.py`

**Tâches**:
- [ ] Implémenter `update_memory()`: Mémoire temporelle (FIFO)
  - `memoryCatch`: Liste captures (365 jours)
  - `memoryProfit`: Liste profits (365 jours)
  - `memoryCatchA/B/C/D`: Par région
  - `growthPerception`: Calcul tendance
  - `lowCatchCounter`: Compteur captures faibles
- [ ] Implémenter `update_memory_goodSpots()`: Mémoire spatiale
  - Ajouter spots réussis (>= catchability)
  - Retirer spots échecs (<< catchability)
  - Limite: 5 (archipelago), 3 (coastal), 2 (trawler)
  - Par région séparément
- [ ] Tester mémoire sur 100 jours simulés

**Structure mémoire**:
- Temporelle: FIFO queue, longueur fixe (365)
- Spatiale: Set de coordonnées, longueur selon type

---

### Step 4: Implémenter l'exécution de pêche (archipelago)

**Fichier**: `code/python/agent.py`

**Tâches**:
- [ ] Implémenter `go_fish()`: Exécution pêche simple
  - Calculer capture: `min(catchability, stock_disponible)`
  - Appeler `model.reduce_stock(pos, catch)`
  - Mettre à jour `self.catch`, `self.accumulatedCatch`
  - Calculer coûts (existence + activity + travel)
  - Calculer profit = catch - costs
  - Mettre à jour capital
- [ ] Implémenter `execute_decision()`: Actions agent
  - Si `willFish=True`: déplacer vers spot, exécuter pêche
  - Si `willFish=False`: rester home, coûts existence seulement
  - Gérer état `layLow` (archipelago)
  - Mettre à jour `atHome`, `goneFishing`
- [ ] Implémenter `move_to(x, y)`: Déplacement sur grille
- [ ] Tester avec 1 agent archipelago sur 30 jours

**Simplifications step 4**:
- Archipelago uniquement (1 patch, pas de décisions multi-jours)
- Sélection spot aléatoire depuis `memoryGoodSpotsA`
- Pas encore de décision intelligente

---

### Step 5: Créer la boucle de simulation

**Fichier**: `code/python/model.py`

**Tâches**:
- [ ] Implémenter `step()`: Boucle principale
  - Déterminer météo quotidienne (10% bad weather)
  - Appeler `schedule.step()` (agents agissent)
  - Si tick % YEAR == 0: régénération poissons
  - `datacollector.collect(self)`
  - Incrémenter `current_tick`
  - Vérifier condition arrêt (`end_of_sim`)
- [ ] Créer `determine_weather()`: Génération météo stochastique
- [ ] Ajouter `RandomActivation` scheduler dans `__init__`
- [ ] Configurer DataCollector avec variables clés:
  - Stocks par région
  - Nombre agents fishing/not fishing
  - Profits moyens
  - Captures moyennes
- [ ] Tester simulation 365 jours (1 an complet)

**Ordre exécution quotidienne**:
1. Météo
2. Décisions agents (parallèle avec RandomActivation)
3. Exécutions pêche
4. Mises à jour mémoires
5. Collecte données
6. (Si fin année) Régénération

---

### Step 6: Implémenter les modèles de décision

**Fichier**: `code/python/agent.py`

**Tâches décision archipelago**:
- [ ] Implémenter `satisfice_lifestyle()`: Décision satisficing
  - Calculer captures semaine passée
  - Comparer à `COST_EXISTENCE * 7`
  - Vérifier capital négatif
  - Vérifier `thinkFishIsScarce` (basé sur mémoire)
  - Vérifier `bad_weather`
  - Décision: pêcher si (besoin OU capital<0) ET non scarce ET non bad weather

**Tâches décision coastal**:
- [ ] Implémenter `optimise_lifestyle_and_growth()`: Trade-off home/profit
  - Calculer `expectedCatchA/B` depuis mémoire
  - Calculer coûts attendus par région
  - Calculer profits attendus
  - Déterminer `regionPreference` (max profit attendu)
  - Calculer satisfaction home vs growth
  - Décision: pêcher si (profit > staying home) ET (satisfaction conditions)
- [ ] Implémenter `decide_best_region()`: Choix région selon mémoire

**Tâches décision trawler**:
- [ ] Implémenter `optimise_growth()`: Profit pur
  - Si `atSea`: décision rester/changer région/rentrer
  - Si à terre: décision partir (quelle région?)
  - Gérer `storingCapacity` et `fishOnboard`
  - Calculer profits multi-jours
  - Gérer état `jumped` (changement région en mer)
- [ ] Implémenter `land_fish()`: Débarquement captures

**Tâches sélection spots**:
- [ ] Implémenter `decide_fishSpot()`: Sélection spot principale
  - Router vers knowledge/expertise/descriptive-norm
  - Avec technologie (trawler): uphill climbing
- [ ] Implémenter `get_fishSpot_knowledge()`: Depuis mémoire
  - Choisir depuis `memoryGoodSpots[Region]`
  - Si vide: exploration aléatoire
- [ ] Implémenter `get_fishSpot_expertise()`: Suivre expert
  - Trouver agent avec plus de captures
  - Copier son spot
- [ ] Implémenter `get_fishSpot_descriptive_norm()`: Suivre foule
  - Identifier spot avec le plus d'agents
  - Aller là-bas
- [ ] Implémenter `fishspot_with_most_fishers()`: Compter agents par spot

**Tests progressifs**:
1. Archipelago seul (satisficing) - 1 an
2. + Coastal (optimize lifestyle) - 1 an
3. + Trawler (optimize growth) - 1 an
4. Tous ensemble - 5 ans

---

## Étapes Futures (Post Step 6)

### Step 7: Utilités et helpers
- Implémenter `getTravelCost()`: Coûts dynamiques
- Implémenter `getMyExistCost()`: Coûts par style
- Implémenter fonctions météo/random
- Implémenter satisfaction updates

### Step 8: Outputs et collecte données
- Implémenter `update_response_vars_tickly()`: Variables quotidiennes
- Implémenter `update_response_vars_periodicly()`: Variables annuelles
- Implémenter `calc_GINI()`: Coefficient Gini
- Configurer DataCollector complet

### Step 9: Validation et calibration
- Comparer outputs Python vs NetLogo
- Scénarios identiques (fuel subsidies, weather, initial stocks)
- Valider comportements agents
- Calibrer si écarts détectés
- Documentation divergences

---

## Défis Identifiés

### Architecture
1. **Spatial**: Patches NetLogo → dictionnaire Mesa
2. **Agent-patch interaction**: `patch-here` → grid lookups explicites
3. **Réseaux sociaux**: Expertise/norms nécessitent awareness agents
4. **States**: Multi-état agents (atSea, goneFishing, layLow, jumped)

### Logique
1. **Décisions complexes**: 3 modèles distincts, nested conditionals
2. **Multi-day trips**: Trawlers avec state persistence
3. **Mémoire**: Multiple types (temporal, spatial, par région)
4. **Coûts dynamiques**: 9 cas dans `getTravelCost()`

### Validation
1. **Pas de benchmarks**: Besoin runs NetLogo pour comparaison
2. **Stochasticité**: Initialisation random, météo, décisions
3. **Émergence**: Comportements collectifs difficiles à valider

---

## Métriques de Succès

### Environnement (Step 1-2)
- ✓ 2,800 patches créés (50x56)
- ✓ Régions correctement assignées (A:200, B:400, C:800, D:800, LAND:600)
- ✓ 22 hotspots générés avec densités HIGH/MEDIUM
- ✓ Stocks initiaux ≈ capacités régionales / 2
- ✓ Croissance logistique atteint équilibre K après 20-30 ans sans pêche

### Agents (Step 3-6)
- ✓ Mémoire FIFO fonctionne (365 jours)
- ✓ Mémoire spatiale mise à jour correctement
- ✓ Archipelago pêche quand nécessaire (satisficing logic)
- ✓ Coastal balance home/growth
- ✓ Trawler optimize profit pur
- ✓ Sélection spots utilise mémoire + social

### Simulation (Step 5+)
- ✓ 9,125 ticks (25 ans) s'exécutent sans erreur
- ✓ Stocks régionaux jamais négatifs ou > K
- ✓ Agents accumulent capital de manière réaliste
- ✓ Gini coefficients calculés correctement
- ✓ Outputs Python ≈ Outputs NetLogo (±10%)

---

## Estimation Travail Restant

**Lignes de code**:
- Step 2: ~50 lignes
- Step 3: ~150 lignes
- Step 4: ~200 lignes
- Step 5: ~100 lignes
- Step 6: ~400 lignes
- Steps 7-9: ~500 lignes
- **Total**: ~1,400 lignes

**Temps estimé**:
- Steps 1-2: 2-3 jours ✓
- Steps 3-4: 3-4 jours
- Steps 5-6: 5-7 jours
- Steps 7-9: 7-10 jours
- **Total**: 17-24 jours de développement

---

## Notes Techniques

### Différences NetLogo vs Mesa
- **Patches**: NetLogo = agents, Mesa = dictionnaire
- **Scheduling**: NetLogo implicite, Mesa = scheduler explicite
- **Random**: NetLogo built-in, Python = `random` module
- **Agentsets**: NetLogo collections, Python = listes/sets
- **Neighbors**: NetLogo `neighbors`, Mesa = calcul manuel

### Optimisations Possibles
- Utiliser NumPy pour calculs stocks (vectorisation)
- Caching pour régions/densités fréquemment accédées
- Spatial indexing pour recherche agents (KD-tree)
- Parallélisation décisions agents (si beaucoup d'agents)

### Tests Recommandés
- Unit tests pour chaque fonction
- Integration tests pour flows complets
- Property-based tests (invariants: stock ≥ 0, capital réaliste)
- Comparison tests (NetLogo vs Python sur scenarios identiques)
