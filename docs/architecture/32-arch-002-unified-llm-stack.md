# ARCH-002: Unified LLM Stack Architecture

**Date**: 14 décembre 2024  
**Status**: ✅ Implémenté  
**Ticket**: [P0] ARCH-002

---

## Vue d'ensemble

L'architecture ARCH-002 introduit une stack LLM unifiée pour Janus, éliminant la complexité, les appels LLM cachés et les modèles multiples incohérents.

### Problème résolu

**Avant ARCH-002** :
- Plusieurs couches LLM coexistant (reasoning/reasoner_llm, llm/unified_client, llm/ollama_client, llm_text_corrector, content_analyzer)
- ContextRouter appelait llama3.2 pendant que le reste du système utilisait qwen2.5:7b-instruct
- Pas de visibilité sur les appels LLM (hidden calls)
- Latence et double facturation CPU/RAM
- Configurations contradictoires (ctx, temperature, etc.)

**Après ARCH-002** :
- ✅ Un seul modèle : qwen2.5:7b-instruct
- ✅ Configuration centralisée dans settings.llm.*
- ✅ Instrumentation complète de tous les appels LLM
- ✅ Métriques transparentes
- ✅ ContextRouter désactivable (pas d'appels cachés)

---

## Architecture

### Single Source of Truth (SSOT)

Deux points d'entrée valides pour les appels LLM :

1. **UnifiedLLMClient** : Interface unifiée pour tous les providers
   - Utilisation : Semantic correction, content analysis, text processing
   - Provider-agnostic (OpenAI, Anthropic, Ollama, local, mock)
   
2. **ReasonerLLM** : Moteur d'inférence spécialisé pour le raisonnement
   - Utilisation : Command parsing, decision making, replanning
   - Optimisé pour JSON mode et reasoning

**Important** : Les deux sont instrumentés et utilisent la même configuration centralisée.

### Instrumentation complète

Tous les appels LLM sont trackés avec :

```python
{
    "call_site": "pipeline.py:decide_next_action",  # Où l'appel a été fait
    "model": "ollama/qwen2.5:7b-instruct",         # Quel modèle
    "tokens_in": 142,                               # Tokens d'entrée (estimé)
    "tokens_out": 58,                               # Tokens de sortie (estimé)
    "latency_ms": 234.5,                            # Latence en millisecondes
    "json_mode": true                               # Mode JSON activé
}
```

### Métriques globales

```python
from janus.llm import get_llm_metrics, reset_llm_metrics

# Obtenir les métriques
metrics = get_llm_metrics()
# {
#     "total_calls": 42,
#     "total_tokens_in": 5420,
#     "total_tokens_out": 1832,
#     "total_latency_ms": 12450.8,
#     "calls_by_site": {
#         "pipeline.py:decide_next_action": 15,
#         "reasoner_llm.py:parse_command": 12,
#         ...
#     },
#     "calls_by_model": {
#         "ollama/qwen2.5:7b-instruct": 42
#     }
# }

# Reset pour les tests
reset_llm_metrics()
```

---

## Configuration centralisée

### config.ini

```ini
[features]
# ARCH-002: ContextRouter désactivé par défaut (pas d'appels LLM cachés)
enable_context_router = false

[llm]
# ARCH-002: Configuration centralisée
# Tous les composants LLM utilisent ces paramètres
provider = ollama
model = qwen2.5:7b-instruct
fallback_providers = 
model_path = 
temperature = 0.7
max_tokens = 2000
request_timeout = 120
retry_timeout = 60
enable_cache = true
cache_ttl = 300
auto_confirm_safe = true
```

### Utilisation

```python
from janus.llm import UnifiedLLMClient, create_unified_client_from_settings

# Créer le client depuis les settings
client = create_unified_client_from_settings(settings)

# Le client utilise automatiquement la config centralisée
response = client.generate(
    prompt="Analyse cette commande",
    system_prompt="Tu es un assistant IA"
)

# Chaque appel est automatiquement instrumenté
```

---

## ContextRouter

### Nouveau comportement

Le ContextRouter peut maintenant être :

1. **Désactivé** (recommandé par défaut) :
   ```python
   # Dans config.ini
   enable_context_router = false
   
   # OU programmatiquement
   router = ContextRouter(llm_client=None, enabled=False)
   # → Retourne tous les contextes (safe fallback), 0 appels LLM
   ```

2. **Activé avec client centralisé** :
   ```python
   from janus.llm import create_unified_client_from_settings
   
   # Utilise le même client que le reste du système
   llm_client = create_unified_client_from_settings(settings)
   router = ContextRouter(llm_client=llm_client, enabled=True)
   # → Utilise qwen2.5:7b-instruct, pas llama3.2
   ```

**Supprimé** : Plus d'instanciation directe d'OllamaClient avec hardcoded llama3.2.

---

## Modèle unique : Qwen2.5 7B Instruct

### Pourquoi Qwen2.5 ?

- **Raisonnement supérieur** : Meilleur que llama3.2 pour la compréhension et planification
- **Multilangue** : Excellent support français/anglais
- **Instruction following** : Suit mieux les consignes structurées (JSON mode)
- **Performance** : Bonne vitesse sur CPU/GPU
- **Taille raisonnable** : ~4.7 GB

### Migration

**Avant** :
- ReasonerLLM : qwen2.5:7b-instruct
- ContextRouter : llama3.2 (hardcoded)
- UnifiedLLMClient : configuré par utilisateur

**Après** :
- **Tous** : qwen2.5:7b-instruct (config centralisée)
- **Cohérence** : Un seul modèle en mémoire
- **Performance** : Pas de double chargement de modèles

---

## Vérification des appels LLM

### Acceptance Criteria

✅ **Une commande simple n'effectue pas d'appels LLM invisibles**

```python
from janus.llm import reset_llm_metrics, get_llm_metrics

# Reset avant test
reset_llm_metrics()

# Exécuter une commande
result = pipeline.process_command("Ouvre Chrome")

# Vérifier les appels LLM
metrics = get_llm_metrics()
print(f"LLM calls: {metrics['total_calls']}")  # Doit être = expected

# Vérifier par site
for site, count in metrics['calls_by_site'].items():
    print(f"  {site}: {count} calls")
```

✅ **Aucun composant n'utilise un second modèle sans décision explicite**

```python
# Tous les appels doivent utiliser qwen2.5:7b-instruct
metrics = get_llm_metrics()
assert list(metrics['calls_by_model'].keys()) == ["ollama/qwen2.5:7b-instruct"]
```

✅ **Les settings LLM sont cohérents**

```python
# Vérifier qu'il n'y a pas de contextes contradictoires
# Tous les composants utilisent settings.llm.*
```

---

## Exemples d'utilisation

### 1. UnifiedLLMClient avec instrumentation

```python
from janus.llm import UnifiedLLMClient, get_llm_metrics, reset_llm_metrics

reset_llm_metrics()

client = UnifiedLLMClient(
    provider="ollama",
    model="qwen2.5:7b-instruct",
    temperature=0.7
)

# Appel 1
response1 = client.generate("Analyse cette commande: ouvre Safari")

# Appel 2
messages = [
    {"role": "system", "content": "Tu es un assistant"},
    {"role": "user", "content": "Explique Docker"}
]
response2 = client.generate_chat(messages)

# Vérifier les metrics
metrics = get_llm_metrics()
print(f"Total calls: {metrics['total_calls']}")  # 2
print(f"Total tokens in: {metrics['total_tokens_in']}")
print(f"Total latency: {metrics['total_latency_ms']:.1f}ms")
```

### 2. ReasonerLLM avec logging

```python
from janus.reasoning.reasoner_llm import ReasonerLLM

# Le logging ARCH-002 est automatique
reasoner = ReasonerLLM(
    backend="ollama",
    model_name="qwen2.5:7b-instruct"
)

# Chaque appel est loggé :
# [ARCH-002] LLM call: model=ollama/qwen2.5:7b-instruct, 
#                      tokens_in≈142, tokens_out≈58, latency=234.5ms
response = reasoner.run_inference(prompt, json_mode=True)
```

### 3. ContextRouter désactivé

```python
from janus.reasoning.context_router import ContextRouter

# Désactivé - pas d'appels LLM
router = ContextRouter(llm_client=None, enabled=False)
requirements = router.get_requirements("Copie le texte")
# → ['vision', 'clipboard', 'browser_content', 'file_history', 'command_history']
# (tous les contextes, safe fallback)
```

---

## Tests

### Test Suite : test_arch_002_llm_instrumentation.py

```bash
python3 tests/test_arch_002_llm_instrumentation.py
```

Tests inclus :
- ✅ Métriques tracking (total_calls, tokens, latency)
- ✅ Accumulation de métriques sur plusieurs appels
- ✅ Reset de métriques
- ✅ ContextRouter désactivé (0 appels LLM)
- ✅ Configuration centralisée (qwen2.5:7b-instruct)
- ✅ Pas de hardcoded models dans ContextRouter

---

## Migration Guide

### Pour les développeurs

1. **Ne plus instancier OllamaClient directement** :
   ```python
   # ❌ Avant
   from janus.llm.ollama_client import OllamaClient
   client = OllamaClient()
   
   # ✅ Après
   from janus.llm import create_unified_client_from_settings
   client = create_unified_client_from_settings(settings)
   ```

2. **Utiliser la config centralisée** :
   ```python
   # ❌ Avant
   reasoner = ReasonerLLM(backend="ollama", model_name="llama3.2")
   
   # ✅ Après
   reasoner = ReasonerLLM(backend="ollama", model_name=settings.llm.model)
   ```

3. **ContextRouter désactivé par défaut** :
   ```ini
   # config.ini
   [features]
   enable_context_router = false  # Désactivé par défaut
   ```

---

## Performance

### Avant ARCH-002

- Latence : +20-50ms pour routing caché (llama3.2)
- Mémoire : 2 modèles chargés (~9 GB)
- Calls cachés : Oui (ContextRouter)
- Incohérence : llama3.2 vs qwen2.5

### Après ARCH-002

- Latence : 0ms si router désactivé, sinon utilise le même modèle
- Mémoire : 1 seul modèle (~4.7 GB)
- Calls cachés : **Non** (instrumentation complète)
- Cohérence : ✅ qwen2.5:7b-instruct partout

---

## Références

- **Issue** : [P0] ARCH-002 — LLM Stack unifiée
- **Code** :
  - `janus/llm/unified_client.py` : Client unifié avec instrumentation
  - `janus/reasoning/reasoner_llm.py` : Reasoner avec logging ARCH-002
  - `janus/reasoning/context_router.py` : Router sans appels cachés
  - `tests/test_arch_002_llm_instrumentation.py` : Tests
- **Config** : `config.ini` [llm] et [features]

---

## Maintenance

### Vérifier l'intégrité ARCH-002

```python
# 1. Vérifier qu'un seul modèle est utilisé
metrics = get_llm_metrics()
models = list(metrics['calls_by_model'].keys())
assert len(models) <= 1, f"Multiple models in use: {models}"

# 2. Vérifier le modèle correct
assert "qwen2.5:7b-instruct" in models[0] if models else True

# 3. Vérifier pas d'appels cachés
# Le nombre d'appels doit correspondre aux attentes
assert metrics['total_calls'] == expected_calls
```

### Debug

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Les logs ARCH-002 apparaîtront :
# DEBUG:unified_llm_client:[ARCH-002] LLM call: site=..., model=..., tokens_in≈..., tokens_out≈..., latency=...ms
# DEBUG:reasoner_llm:[ARCH-002] LLM call: model=..., tokens_in≈..., tokens_out≈..., latency=...ms, json_mode=...
```

---

**Status**: ✅ Implémenté et testé  
**Prochaines étapes** : Monitoring en production, ajustement des seuils de performance
