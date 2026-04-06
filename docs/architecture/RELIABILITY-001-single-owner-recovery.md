# RELIABILITY-001: Single Owner Recovery/Replanning

**Date:** 2024-12-14  
**Status:** ✅ IMPLEMENTED  
**Ticket:** [P0] RELIABILITY-001

## Problème

Plusieurs mécanismes de recovery peuvent déclencher en parallèle, créant des boucles infinies et des comportements imprévisibles.

### Problèmes Identifiés

1. **Triggers multiples de replanning**
   - `ActionCoordinator` détecte la stagnation et force vision
   - `async_vision_monitor` peut signaler des erreurs via callbacks
   - Services `VisionRecoveryService`, `ReplanningService` étaient référencés mais n'existaient pas

2. **Pas de coordination centralisée**
   - Aucun propriétaire unique de la stratégie de recovery
   - Pas de machine à états pour prévenir les boucles
   - Pas de limitation du nombre de tentatives

3. **Risque de boucles infinies**
   - Recovery peut déclencher plus de recovery
   - Pas de mécanisme de prévention
   - Logs insuffisants pour tracer le propriétaire

## Solution

### ActionCoordinator devient le propriétaire unique

`ActionCoordinator` est désormais le **seul composant** responsable de la stratégie de recovery. Tous les autres composants sont des **helpers passifs** qui signalent uniquement.

### RecoveryState Machine

Nouvelle machine à états dans `janus/core/contracts.py`:

```python
class RecoveryState(Enum):
    """Recovery state machine for ActionCoordinator"""
    IDLE = "idle"           # No recovery in progress
    DETECTING = "detecting" # Detecting potential issues
    RECOVERING = "recovering" # Actively recovering
    RECOVERED = "recovered"  # Recovery succeeded
    FAILED = "failed"        # Recovery failed
```

### Implémentation dans ActionCoordinator

#### 1. État et Verrouillage

```python
# RELIABILITY-001: Recovery state machine
self._recovery_state = RecoveryState.IDLE
self._recovery_lock = asyncio.Lock()  # Prevent concurrent recovery
self._recovery_attempts = 0
self._max_recovery_attempts = 3
```

#### 2. Méthodes de Gestion d'État

- `_get_recovery_state()`: Obtenir l'état actuel
- `_set_recovery_state(new_state, reason)`: Transition avec logging
- `_reset_recovery_state()`: Réinitialisation pour nouveau goal
- `async _try_recovery(system_state, error_context)`: Logique de recovery

#### 3. Prévention de Recovery Concurrent

```python
async with self._recovery_lock:
    if self._recovery_state != RecoveryState.IDLE:
        logger.warning("Recovery already in progress, skipping")
        return False
```

#### 4. Limite de Tentatives

```python
if self._recovery_attempts >= self._max_recovery_attempts:
    logger.error("Max recovery attempts reached, giving up")
    self._set_recovery_state(RecoveryState.FAILED, "max attempts")
    return False
```

### Intégration dans execute_goal

1. **Réinitialisation au démarrage**
   ```python
   self._reset_recovery_state()
   ```

2. **Recovery sur Stagnation**
   ```python
   if is_stagnant:
       recovery_success = await self._try_recovery(system_state, "stagnation")
       if recovery_success:
           force_vision = True
   ```

3. **Recovery sur Erreur de Décision**
   ```python
   if "error" in decision:
       recovery_success = await self._try_recovery(
           system_state,
           f"decision_error: {error_type}"
       )
   ```

### Services Passifs

#### async_vision_monitor

✅ **Déjà passif** - signale uniquement via callbacks, ne déclenche pas de recovery

```python
# Event callbacks - PASSIVE signaling only
self._callbacks: Dict[MonitorEventType, List[Callable]] = {...}
```

#### Services Supprimés

Les imports suivants ont été **retirés** de `janus/services/__init__.py`:

- ❌ `VisionRecoveryService` (n'existait pas)
- ❌ `ReplanningService` (n'existait pas)
- ❌ `ExecutionService` (n'existait pas)
- ❌ `ContextManagementService` (n'existait pas)
- ❌ `PreconditionService` (n'existait pas)

Seuls les services **existants et utiles** restent:

- ✅ `STTService`
- ✅ `VisionService`
- ✅ `MemoryServiceWrapper`
- ✅ `TTSService`
- ✅ `LifecycleService`
- ✅ `ToolRetrievalService`

## Logging Complet

Toutes les transitions d'état sont loggées avec le format:

```
🔄 Recovery State: idle → detecting | attempt 1/3
🔄 Recovery State: detecting → recovering | stagnation detected
🔄 Recovery State: recovering → recovered | vision forced
🔄 Recovery State: recovered → idle | recovery complete
```

## Tests

Fichier: `tests/test_reliability_001_single_owner_recovery.py`

### Tests Implémentés

1. ✅ `test_initial_recovery_state_is_idle` - État initial IDLE
2. ✅ `test_reset_recovery_state` - Réinitialisation d'état
3. ✅ `test_set_recovery_state_transitions` - Transitions loggées
4. ✅ `test_recovery_prevents_concurrent_attempts` - Prévention concurrent
5. ✅ `test_recovery_max_attempts_limit` - Limite de tentatives
6. ✅ `test_recovery_successful_flow` - Flow de succès
7. ✅ `test_stagnation_triggers_recovery` - Stagnation déclenche recovery
8. ✅ `test_recovery_state_reset_on_new_goal` - Reset sur nouveau goal
9. ✅ `test_decision_error_triggers_recovery` - Erreur déclenche recovery
10. ✅ `test_recovery_state_values` - Valeurs de l'enum
11. ✅ `test_recovery_state_count` - Nombre d'états

## Acceptance Criteria

### ✅ Aucune action relancée par plusieurs composants

- ✅ ActionCoordinator est le seul owner
- ✅ Recovery lock prévient les tentatives parallèles
- ✅ Services passifs ne font que signaler

### ✅ Logs montrent un owner unique

- ✅ Toutes les transitions loggées avec "🔄 Recovery State"
- ✅ Format uniforme: `old_state → new_state | reason`
- ✅ Traçabilité complète

### ✅ Pas de boucle infinie

- ✅ Limite de 3 tentatives max (`_max_recovery_attempts`)
- ✅ État FAILED après max tentatives
- ✅ Lock empêche recovery concurrent
- ✅ Reset sur nouveau goal

## Fichiers Modifiés

### 1. `janus/core/contracts.py`

**+33 lignes** - Ajout de `RecoveryState` enum

```python
class RecoveryState(Enum):
    IDLE = "idle"
    DETECTING = "detecting"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    FAILED = "failed"
```

### 2. `janus/core/action_coordinator.py`

**+117 lignes** - Recovery state machine

**Ajouts:**
- Import `RecoveryState`
- Variables d'état recovery dans `__init__`
- `_get_recovery_state()`
- `_set_recovery_state(new_state, reason)`
- `async _try_recovery(system_state, error_context)`
- `_reset_recovery_state()`
- Integration dans `execute_goal()`

**Modifications:**
- Stagnation detection appelle `_try_recovery()`
- Decision errors appellent `_try_recovery()`
- Reset recovery state au début de `execute_goal()`

### 3. `janus/services/__init__.py`

**-10 services, +1 service**

**Retiré:**
- `VisionRecoveryService`
- `ReplanningService`
- `ExecutionService`
- `ContextManagementService`
- `PreconditionService`

**Ajouté:**
- `ToolRetrievalService` (existait mais pas exporté)

**Docstring mis à jour** pour refléter RELIABILITY-001

### 4. `tests/test_reliability_001_single_owner_recovery.py`

**+389 lignes** - Tests complets

- 11 tests unitaires
- Couverture complète du state machine
- Tests de prévention de loops

### 5. `docs/architecture/RELIABILITY-001-single-owner-recovery.md`

**+280 lignes** (ce fichier) - Documentation complète

## Architecture Finale

```
┌─────────────────────────────────────────────────────┐
│           ActionCoordinator (OWNER)                 │
│  ┌───────────────────────────────────────────┐     │
│  │  RecoveryState Machine                    │     │
│  │  ┌─────┐  ┌──────────┐  ┌───────────┐   │     │
│  │  │IDLE │→ │DETECTING │→ │RECOVERING │   │     │
│  │  └─────┘  └──────────┘  └───────────┘   │     │
│  │     ↓                            ↓       │     │
│  │  ┌──────────┐           ┌─────────┐     │     │
│  │  │ FAILED   │          │RECOVERED│     │     │
│  │  └──────────┘           └─────────┘     │     │
│  │                              ↓           │     │
│  │                           ┌─────┐       │     │
│  │                           │IDLE │       │     │
│  │                           └─────┘       │     │
│  └───────────────────────────────────────────┘     │
│                                                     │
│  Recovery Lock: asyncio.Lock()                     │
│  Max Attempts: 3                                   │
└─────────────────────────────────────────────────────┘
                      ↑
                      │ SIGNALS ONLY (passive)
                      │
        ┌─────────────┴──────────────┐
        │                            │
┌───────┴────────┐         ┌────────┴──────────┐
│ async_vision_  │         │   Other Services  │
│    monitor     │         │   (STT, TTS, etc) │
│                │         │                   │
│  - Callbacks   │         │  - Helpers only   │
│  - Events      │         │  - No recovery    │
└────────────────┘         └───────────────────┘
```

## Impact

### Stabilité

- **Avant:** Risque de boucles infinies
- **Après:** Maximum 3 tentatives, puis FAILED

### Traçabilité

- **Avant:** Logs dispersés, pas de owner clair
- **Après:** Tous les logs préfixés "🔄 Recovery State"

### Maintenabilité

- **Avant:** Services référencés mais inexistants
- **Après:** Code propre, seuls les services existants exportés

### Performance

- **Impact minimal** - Lock asyncio très léger
- **Pas de overhead** - Recovery uniquement si nécessaire

## Migration

### Code Legacy

Aucune migration nécessaire - les services non-existants étaient déjà non-fonctionnels.

### Breaking Changes

✅ **Aucun breaking change** - Seulement suppression d'imports non-fonctionnels

## Prochaines Étapes (Optionnel)

1. **Métriques de Recovery**
   - Ajouter tracking du nombre de recovery réussies/échouées
   - Dashboard de monitoring des recovery

2. **Recovery Strategies**
   - Actuellement: force vision uniquement
   - Futur: Strategies configurables (retry, fallback, user prompt)

3. **Recovery Events**
   - Publier des events pour UI/monitoring
   - Notification utilisateur en cas de FAILED

## Références

- **Ticket:** RELIABILITY-001
- **Architecture:** ARCH-004 (SystemState)
- **Foundation:** CORE-FOUNDATION-002 (Burst OODA)

## Auteur

**Date:** 2024-12-14  
**Développeur:** GitHub Copilot  
**Reviewer:** BenHND
