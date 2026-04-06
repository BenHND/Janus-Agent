# ARCH-003: Strict JSON Validation - Legacy Code Removed

**Date:** 14 décembre 2024  
**Status:** ✅ Implémenté (Code legacy complètement supprimé)  
**Priority:** P0

## Problème

`NLUParser` + `JSONPlanCorrector` faisaient de la "regex repair" et extraction JSON depuis texte. C'était fragile et source majeure de bugs.

## Solution

**Legacy code complètement supprimé.**

- En production, JSON invalide → **re-ask** au LLM (jamais de correction silencieuse)
- `ValidatorAgent` ne fait que de la **validation stricte**
- Plus de paramètre `auto_correct`, plus de `JSONPlanCorrector`

## Changements

### ValidatorAgent nettoyé

**Avant:**
```python
from janus.validation.json_plan_corrector import JSONPlanCorrector

class ValidatorAgent:
    def __init__(self, auto_correct=False, ...):
        self.corrector = JSONPlanCorrector() if auto_correct else None
```

**Après:**
```python
# Import removed
from janus.validation.json_plan_validator import JSONPlanValidator

class ValidatorAgent:
    def __init__(self, strict_mode=True, allow_missing_context=False):
        self.validator = JSONPlanValidator(...)
        # No corrector, no auto_correct
```

### Settings nettoyées

**Supprimé:**
- ❌ `LegacySettings` dataclass  
- ❌ `settings.legacy`
- ❌ Section `[legacy]` dans config.ini
- ❌ `_load_legacy_settings()` method

### Stats simplifiées

**Supprimé:**
- ❌ `legacy_mode_invocations`
- ❌ `legacy_mode_usage_rate`  
- ❌ `corrected_plans`
- ❌ `correction_rate`

**Gardé:**
- ✅ `total_validations`
- ✅ `valid_plans`
- ✅ `rejected_plans`
- ✅ `success_rate`

## Comportement

### Production (seul mode)

```
LLM génère JSON invalide
   ↓
ValidatorAgent rejette (JSON parse error)
   ↓
Pipeline déclenche re-ask au LLM
   ↓
LLM génère JSON valide
   ↓
Plan exécuté
```

**Pas de correction silencieuse. Pas de regex repair. Jamais.**

## Tests

Nouveau fichier: `tests/test_arch_003_legacy_removed.py`

Tests vérifient:
1. ✅ `ValidatorAgent` n'a plus `auto_correct` parameter
2. ✅ `ValidatorAgent` n'a plus `corrector` attribute
3. ✅ Stats ne contiennent plus de champs legacy
4. ✅ JSON invalide est rejeté (pas corrigé)
5. ✅ JSON valide est accepté

## Fichiers modifiés

1. **`janus/agents/validator_agent.py`**
   - Supprimé import `JSONPlanCorrector`
   - Supprimé paramètre `auto_correct`
   - Supprimé toutes les méthodes de correction
   - Simplifié `_parse_json()` (strict parsing only)
   - Supprimé constantes de messages legacy
   - Nettoyé stats

2. **`janus/core/settings.py`**
   - Supprimé `LegacySettings` dataclass
   - Supprimé `_load_legacy_settings()` method
   - Supprimé `self.legacy` initialization

3. **`config.ini`**
   - Supprimé section `[legacy]`

4. **`tests/test_arch_003_legacy_removed.py`** (nouveau)
   - 6 tests vérifiant suppression complète
   - Remplace `test_arch_003_no_corrector.py`

## Acceptance Criteria

✅ **En prod, JSON invalide déclenche re-ask**
- ValidatorAgent rejette JSON invalide sans correction
- Pipeline re-demande au LLM

✅ **Suppression du code legacy**
- `auto_correct` parameter removed
- `JSONPlanCorrector` import removed
- Aucune référence au legacy code dans ValidatorAgent
- `NLUParser` non utilisé (était déjà le cas)

✅ **Tests garantissant suppression**
- 6 tests dans `test_arch_003_legacy_removed.py`
- Tests vérifient absence de legacy code

## Code Legacy conservé (référence seulement)

Les fichiers suivants existent encore mais ne sont plus utilisés:
- `janus/validation/json_plan_corrector.py` (orphan)
- `janus/llm/nlu_parser.py` (orphan)

Ils sont conservés uniquement pour :
- Tests unitaires existants qui les testent directement
- Référence historique
- Peuvent être archivés/supprimés dans le futur

## Conclusion

ARCH-003 finalisé avec **suppression complète** du code legacy :

- ✅ Validation stricte uniquement
- ✅ Re-ask au lieu de correction silencieuse
- ✅ Code simplifié et maintenable
- ✅ Tests garantissant conformité
- ✅ Plus de configuration legacy
- ✅ Plus de métriques legacy

**Le système est maintenant plus robuste, prévisible et simple.**

---

**Prochaines étapes suggérées:**
1. Archiver `json_plan_corrector.py` et `nlu_parser.py` dans `/docs/archive/`
2. Supprimer leurs tests unitaires (ou les marquer comme deprecated)
3. Nettoyer références dans la documentation d'archive
