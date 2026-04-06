# 🌍 Système d'Internationalisation (i18n)

> **Traductions centralisées pour Janus** - Français 🇫🇷 & Anglais 🇬🇧

## 🚀 Quick Start

```python
from janus.i18n import t, tts_done, status_listening

# Messages simples
print(t("ui.welcome"))  # "Bienvenue"

# Feedbacks TTS
await speak_feedback(tts, tts_done())  # "C'est fait"

# Status overlay
overlay.set_status(StatusState.LISTENING, status_listening())  # "Écoute en cours"

# Messages avec paramètres
error = t("errors.fatal_error", error="Connection lost")
```

## 📁 Structure

```
janus/i18n/
├── __init__.py          # Module principal avec MESSAGES dict
└── README.md            # Ce fichier
```

## 🎯 Fonctions disponibles

### Core
- `t(key, **kwargs)` - Traduction générique
- `set_language(lang)` - Changer de langue ("fr" ou "en")
- `get_language()` - Obtenir la langue actuelle

### TTS Helpers
- `tts_welcome()` - Message de bienvenue
- `tts_done()` - "C'est fait"
- `tts_error(action=None)` - Message d'erreur
- `tts_no_speech()` - "Aucune parole détectée"
- `tts_undo()` - "Annulé"
- `tts_redo()` - "Rétabli"

### Status Helpers
- `status_ready()` - "Prêt"
- `status_idle()` - "En attente"
- `status_listening()` - "Écoute en cours"
- `status_thinking()` - "Réflexion"
- `status_acting()` - "Exécution"
- `status_error()` - "Erreur"

## 🧪 Tester

```bash
# Démo complète avec FR/EN
python examples/example_i18n_demo.py
```

## 📚 Documentation complète

Voir **[docs/developer/I18N_SYSTEM.md](../../docs/developer/I18N_SYSTEM.md)** pour :
- Guide d'utilisation détaillé
- Ajouter de nouvelles traductions
- Ajouter une nouvelle langue
- Bonnes pratiques
- Tableau complet des clés

## ✨ Exemple complet

```python
# Mode Terminal avec i18n
from janus.i18n import t, tts_done, tts_error

# Banner
print_banner(
    t("terminal.banner_title"),
    t("terminal.banner_subtitle", session_id="abc123")
)

# Commandes
for cmd in t("terminal.commands_list"):
    print(f"  • {cmd}")

# Execution
try:
    result = await pipeline.process_command_async(text)
    if result.success:
        await speak_feedback(tts, tts_done())
    else:
        await speak_feedback(tts, tts_error())
except Exception as e:
    logger.error(t("errors.execution_failed", error=str(e)))
```

## 🔧 Ajouter une traduction

1. Éditer `__init__.py` :
```python
MESSAGES = {
    "fr": {
        "my_category": {"my_key": "Mon message"}
    },
    "en": {
        "my_category": {"my_key": "My message"}
    }
}
```

2. Utiliser :
```python
msg = t("my_category.my_key")
```

---

**🎉 Le système i18n rend Janus accessible en français et en anglais !**
