# SAFETY-001: Unified Action Validation System

**Date**: 14 décembre 2024  
**Status**: ✅ Implémenté  
**Priority**: P0 (Sécurité)

## Problème

Plusieurs systèmes de validation et de classification de risque coexistaient avec des décisions contradictoires:

1. **ActionRisk** (dans `action_validator.py`): 5 niveaux (SAFE, LOW, MEDIUM, HIGH, CRITICAL)
2. **RiskLevel** (dans `module_action_schema.py`): 3 niveaux (LOW, MEDIUM, HIGH)
3. **ActionValidator** et **StrictActionValidator**: deux validateurs parallèles avec logiques différentes
4. Classification par regex arbitraire qui pouvait bloquer des actions LOW/MEDIUM

Ceci créait de l'incohérence et des risques de sécurité.

## Solution

### Single Source of Truth (SSOT)

**RiskLevel** dans `module_action_schema.py` est maintenant le SEUL système de classification de risque:

```python
class RiskLevel(Enum):
    """
    Risk level for actions - SINGLE SOURCE OF TRUTH (SAFETY-001)
    """
    LOW = "low"       # Safe, read-only actions
    MEDIUM = "medium" # Modifying but reversible actions
    HIGH = "high"     # Dangerous actions requiring confirmation
    CRITICAL = "critical"  # System-level or irreversible actions
```

### UnifiedActionValidator

Un nouveau validateur unifié fusionnant les capacités de:
- **StrictActionValidator**: validation stricte contre le schéma
- **ActionValidator**: détection de commandes dangereuses

```python
from janus.validation import (
    UnifiedActionValidator,
    get_global_validator,
    validate_action,
    RiskLevel  # SSOT for risk levels
)

# Utilisation simple
step = {
    "module": "browser",
    "action": "open_url",
    "args": {"url": "https://example.com"}
}

is_valid, corrected_step, error, risk_level, user_confirmed = validate_action(step)
```

## Règles de Confirmation (SAFETY-001)

### Règles strictes

1. **HIGH et CRITICAL**: TOUJOURS requiert confirmation utilisateur
2. **LOW et MEDIUM**: PAS de confirmation requise (auto-approuvé)
3. **Pas de blocage arbitraire**: Seul le `risk_level` du schéma décide
4. **Détection de sécurité**: Commandes dangereuses peuvent élever le niveau de risque

### Exemples

```python
# LOW risk - Auto-approved
{"module": "browser", "action": "open_url"}  # ✅ Approuvé automatiquement

# MEDIUM risk - Auto-approved
{"module": "ui", "action": "click"}  # ✅ Approuvé automatiquement

# HIGH risk - Requires confirmation
{"module": "files", "action": "delete_file"}  # ❌ Requiert confirmation

# Command safety detection
{"action": "execute_command", "args": {"command": "rm -rf /"}}  # ❌ CRITICAL
```

## Logging et Traçabilité

Chaque validation enregistre:

```python
logger.info(
    f"Validating action: {module}.{action} "
    f"(risk_level={risk_level.value})"
)

logger.info(
    f"Action validated: {module}.{action} "
    f"requires_confirmation={requires_confirmation}"
)

# Si confirmation requise
logger.info(f"User confirmed action: {module}.{action}")
# ou
logger.warning(f"User denied action: {module}.{action}")
```

## Statistiques

Le validateur unifié suit les statistiques complètes:

```python
validator = get_global_validator()
stats = validator.get_validation_report()

# stats contient:
# - total_validations
# - valid_actions
# - corrected_actions
# - rejected_actions
# - confirmations_requested
# - confirmations_approved
# - confirmations_denied
# - success_rate
# - confirmation_approval_rate
```

## Détection de Commandes Dangereuses

Layer de sécurité additionnel pour les commandes shell:

```python
dangerous_patterns = [
    r"rm\s+-rf\s+/",        # Delete root
    r"rm\s+-rf\s+\*",       # Delete all
    r"mkfs\.",              # Format filesystem
    r"dd\s+if=.*of=/dev/",  # Disk write
    r"shutdown",            # System shutdown
    # ... etc
]
```

Ces patterns **élèvent** le risk_level si détectés, mais ne bloquent pas arbitrairement.

## Migration

### Ancien code (supprimé)

Les anciens validateurs `ActionValidator` et `StrictActionValidator` ont été **complètement supprimés**.

### Nouveau validateur unifié

```python
# ✅ Seule option (SAFETY-001)
from janus.validation import UnifiedActionValidator, RiskLevel, validate_action

# Simple
is_valid, step, error, risk, confirmed = validate_action(step_dict)

# Ou avec configuration
validator = UnifiedActionValidator(
    auto_correct=True,
    allow_fallback=True,
    strict_mode=False,
    confirmation_callback=my_custom_callback
)
```

## Acceptance Criteria

✅ **Toute action HIGH/CRITICAL requiert confirmation**
- Implémenté dans `_requires_confirmation()`
- Tests: `test_high_and_critical_require_confirmation()`

✅ **Aucune action LOW/MEDIUM bloquée par regex arbitraire**
- Seul le schéma définit le risk_level
- Tests: `test_no_arbitrary_blocking_of_low_medium()`

✅ **Un seul endroit décide la confirmation**
- `module_action_schema.py` est le SSOT
- Tests: `test_risk_level_from_ssot_only()`

✅ **Logs complets: risk_level, requires_confirmation, user_confirmed**
- Tous les logs implémentés
- Tests: `test_logging_of_validation_decision()`

## Fichiers Modifiés

1. **janus/core/module_action_schema.py**
   - Ajout de `CRITICAL` à `RiskLevel`
   - Documentation SSOT

2. **janus/validation/unified_action_validator.py** (nouveau)
   - Validateur unifié
   - ~580 lignes de code
   - Logging complet
   - Statistiques

3. **janus/validation/__init__.py**
   - Export du nouveau système uniquement

4. **janus/ui/confirmation_dialog.py**
   - Migration `ActionRisk` → `RiskLevel`
   - Couleurs adaptées

5. **tests/test_safety001_unified_validator.py** (nouveau)
   - 25+ tests
   - Couverture complète

## Documentation

- `/docs/developer/safety-001-unified-validation.md` (ce fichier)
- `FEATURES_AUDIT.md` (à mettre à jour)

## Tests

```bash
# Exécuter les tests
python run_tests.py --pattern "test_safety001*"
```

Tests couverts:
- ✅ Validation avec chaque niveau de risque (LOW, MEDIUM, HIGH, CRITICAL)
- ✅ Confirmation requise pour HIGH/CRITICAL
- ✅ Pas de confirmation pour LOW/MEDIUM
- ✅ Détection de commandes dangereuses
- ✅ Auto-correction d'actions
- ✅ Statistiques de validation
- ✅ Logging des décisions
- ✅ Callbacks de confirmation

## Références

- **Issue**: [P0] SAFETY-001
- **ADR**: ARCH-SAFETY-001
- **Checklist Ticket**: SAFETY-001 requirements
