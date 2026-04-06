"""
Overlay UI Constants
Centralized text strings and configuration for overlay UI
For easy maintenance and translation support
"""

# Status text strings (without trailing "..." as these are added by animation)
STATUS_TEXTS = {
    "en": {
        "ready": "Ready",
        "listening": "Listening",
        "looking": "Looking",  # Vision/OCR in progress (TICKET-UX-001)
        "thinking": "Thinking",
        "acting": "Executing",
        "loading": "Loading",
        "error": "Error",
    },
    "fr": {
        "ready": "Prêt",
        "listening": "En écoute",
        "looking": "Observation",  # Vision/OCR in progress (TICKET-UX-001)
        "thinking": "Réflexion",
        "acting": "Exécution",
        "loading": "Chargement",
        "error": "Erreur",
    },
}

# Default language
DEFAULT_LANGUAGE = "en"

# SVG Icons for microphone states
# Outline version for mic off
MIC_OFF_SVG = '''<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M8 1C6.89543 1 6 1.89543 6 3V8C6 9.10457 6.89543 10 8 10C9.10457 10 10 9.10457 10 8V3C10 1.89543 9.10457 1 8 1Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M12 8C12 10.2091 10.2091 12 8 12C5.79086 12 4 10.2091 4 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M8 12V15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M6 15H10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>'''

# Solid version for mic on
MIC_ON_SVG = '''<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
<path d="M8 1C6.89543 1 6 1.89543 6 3V8C6 9.10457 6.89543 10 8 10C9.10457 10 10 9.10457 10 8V3C10 1.89543 9.10457 1 8 1Z"/>
<path d="M12 8C12 10.2091 10.2091 12 8 12C5.79086 12 4 10.2091 4 8H3C3 10.7614 5.23858 13 8 13V15H6V16H10V15H8V13C10.7614 13 13 10.7614 13 8H12Z"/>
</svg>'''


def get_status_text(key: str, language: str = DEFAULT_LANGUAGE) -> str:
    """
    Get status text for the given key and language

    Args:
        key: One of "ready", "listening", "thinking", "acting"
        language: Language code (default: "en")

    Returns:
        Status text string
    """
    return STATUS_TEXTS.get(language, STATUS_TEXTS[DEFAULT_LANGUAGE]).get(key, key.upper())
