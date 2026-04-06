# ARCH-004: Canonical SystemState + Grounding Unique

**Date:** 14 décembre 2024  
**Status:** ✅ Implemented  
**Ticket:** ARCH-004

## Problème

Différentes parties du code lisaient l'état système via des chemins différents avec des clés non uniformes:

- `ActionCoordinator._observe_system_state()` retournait un dict avec certaines clés
- `ContextAnalyzer.capture_state()` retournait un dict différent avec d'autres clés
- Les stop conditions utilisaient des accès par clés string fragiles
- La détection de stagnation utilisait un hash calculé manuellement

Cela causait:
- Des stop conditions instables
- Des erreurs difficiles à debugger quand les clés changeaient
- Pas de single source of truth pour l'état système

## Solution Implémentée

### 1. SystemState Dataclass (Single Source of Truth)

Créé `SystemState` dans `janus/core/contracts.py`:

```python
@dataclass(frozen=True)
class SystemState:
    """Canonical system state representation - Single Source of Truth (ARCH-004)."""
    
    timestamp: str
    active_app: str
    window_title: str
    url: str
    domain: Optional[str]
    clipboard: str
    performance_ms: float
```

**Caractéristiques:**
- **Immutable** (`frozen=True`) pour garantir la cohérence des snapshots
- **Stable keys** : mêmes clés utilisées partout
- **Type-safe** : Dataclass avec typage explicite
- **Hashable** : Implémente `__hash__()` pour la détection de stagnation
- **Serializable** : Méthodes `to_dict()` et `from_dict()` pour la compatibilité

### 2. Mise à Jour d'ActionCoordinator

**Changements:**

```python
async def _observe_system_state(self) -> SystemState:
    """Return canonical SystemState instance"""
    # ... capture state ...
    return SystemState(
        timestamp=datetime.now().isoformat(),
        active_app=active_app,
        window_title=window_title,
        url=url,
        domain=self._extract_domain(url),
        clipboard=clipboard[:1000],
        performance_ms=round(performance_ms, 2)
    )
```

**Stop Conditions:**
```python
def _evaluate_single_stop_condition(
    self,
    condition: StopCondition,
    system_state: SystemState  # Was Dict[str, Any]
) -> bool:
    # Direct attribute access instead of dict.get()
    if cond_type == "url_contains":
        return cond_value.lower() in system_state.url.lower()
```

**Stagnation Detection:**
```python
def _detect_stagnation(
    self, 
    system_state: SystemState,  # Was Dict[str, Any]
    burst_metrics: BurstMetrics
) -> bool:
    state_hash = hash(system_state)  # Uses SystemState.__hash__()
    # ...
```

### 3. Suppression Complète de ContextAnalyzer

**Migration complète** - ContextAnalyzer a été entièrement supprimé (pas seulement déprécié):

**Fichiers supprimés:**
- `janus/memory/context_analyzer.py` : SUPPRIMÉ

**Fichiers migrés:**
- `janus/api/context_api.py` : Utilise maintenant `ActionCoordinator` pour l'observation d'état
  - `ContextEngine.coordinator = ActionCoordinator()`
  - `get_context()` utilise `await coordinator._observe_system_state()`
  - Retourne `SystemState.to_dict()` pour compatibilité API
  
- `janus/memory/__init__.py` : `ContextAnalyzer` retiré des exports

**Avantages:**
- Plus de code legacy ou deprecated
- Un seul chemin d'observation d'état
- Code plus propre et maintenable

## Acceptance Criteria

✅ **Une action et ses stop conditions utilisent les mêmes clés partout**
- SystemState définit les clés stables
- Stop conditions accèdent aux attributs directement
- Pas de dict.get() fragile

✅ **Un dump d'état unique pour debug**
- `system_state.to_dict()` donne une représentation consistente
- Même structure partout

✅ **Détection de stagnation fiable**
- `SystemState.__hash__()` basé sur l'état observable
- Hash consistant pour des états identiques
- Hash différent quand l'état change

## Bénéfices

1. **Stabilité** : Plus de KeyError ou de clés manquantes
2. **Maintenabilité** : Un seul endroit à modifier (SystemState)
3. **Type Safety** : Mypy peut vérifier les accès
4. **Testabilité** : État immutable facile à tester
5. **Debugging** : Dump d'état uniforme

## Compatibilité

- **Backward compatible** : SystemState.to_dict() pour code legacy
- **Migration graduelle** : ContextAnalyzer deprecated mais fonctionnel
- **Reasoner compatible** : Conversion automatique vers dict

## Tests

Créé `tests/test_arch_004_system_state.py` avec:
- Tests de création et immutabilité
- Tests de hashing pour stagnation
- Tests de serialization (to_dict/from_dict)
- Tests d'évaluation de stop conditions
- Tests d'extraction de domaine
- Tests de détection de stagnation

## Files Modified

1. `janus/core/contracts.py` : +120 lignes (SystemState dataclass)
2. `janus/core/action_coordinator.py` : ~200 lignes modifiées
   - Signature de `_observe_system_state()` → retourne SystemState
   - `_detect_stagnation()` → utilise SystemState
   - `_evaluate_stop_conditions()` → utilise SystemState
   - `_execute_burst()`, `_act_single()` → acceptent SystemState
   - Suppression de `_compute_state_hash()` (remplacé par `__hash__`)
3. `janus/memory/context_analyzer.py` : **SUPPRIMÉ** (migration complète)
4. `janus/api/context_api.py` : Migré vers ActionCoordinator
   - Utilise `ActionCoordinator._observe_system_state()` 
   - Retourne `SystemState.to_dict()` pour compatibilité API
5. `janus/memory/__init__.py` : ContextAnalyzer retiré des exports
6. `tests/test_arch_004_system_state.py` : +450 lignes (nouveau fichier)
7. `FEATURES_AUDIT.md` : Sections 2.1 et 5.1 mises à jour

## Documentation

- ✅ Architecture Decision Record (ce fichier)
- ✅ FEATURES_AUDIT.md updated

## Impact

**Performance:** Aucun impact négatif
- SystemState est léger (dataclass simple)
- Hash natif Python très rapide
- Pas de copie profonde (frozen)

**Code Quality:** Amélioration significative
- -200+ lignes nettes (suppression ContextAnalyzer + simplification)
- Type safety amélioré
- Moins de dictionnaires magiques

## Migration Path

Pour migrer du code existant:

```python
# Avant (fragile)
state = {"active_app": "Safari", "url": "..."}
if state.get("url", "").contains("example"):
    # ...

# Après (type-safe)
state = SystemState(...)
if "example" in state.url:
    # ...
```

## Prochaines Étapes

1. ✅ Implémenter SystemState
2. ✅ Migrer ActionCoordinator
3. ✅ Déprécier ContextAnalyzer
4. ✅ Ajouter tests
5. ⏳ Mettre à jour FEATURES_AUDIT.md
6. ⏳ Documenter dans /docs/architecture/

## Notes

- SystemState est **frozen** pour garantir l'immutabilité
- Le hash utilise seulement l'état observable (pas timestamp/performance)
- Domain extraction handle les cas edge (www, port, pas de protocole)
- Clipboard tronqué à 100 chars dans le hash, 1000 chars stocké
