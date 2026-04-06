"""Internationalization (i18n) - Centralized messages for Janus"""
from typing import Dict

# Current language (loaded from settings at runtime)
_current_language = "fr"


def set_language(lang: str):
    """Set the current language for all messages"""
    global _current_language
    if lang in MESSAGES:
        _current_language = lang
    else:
        raise ValueError(f"Unsupported language: {lang}")


def get_language() -> str:
    """Get the current language"""
    return _current_language


def t(key: str, **kwargs) -> str:
    """
    Translate a message key to the current language
    
    Args:
        key: Message key (e.g., 'tts.welcome')
        **kwargs: Format arguments for the message
    
    Returns:
        Translated and formatted message
    
    Example:
        t('tts.error', action='open Safari')
        # -> "Désolé, je n'ai pas pu exécuter 'open Safari'"
    """
    lang_messages = MESSAGES.get(_current_language, MESSAGES["en"])
    
    # Navigate nested keys (e.g., 'tts.welcome' -> MESSAGES[lang]['tts']['welcome'])
    keys = key.split(".")
    message = lang_messages
    
    for k in keys:
        if isinstance(message, dict):
            message = message.get(k)
        else:
            break
    
    if message is None:
        # Fallback to English
        message = MESSAGES["en"]
        for k in keys:
            if isinstance(message, dict):
                message = message.get(k)
            else:
                break
    
    if message is None:
        return f"[Missing: {key}]"
    
    # Format with kwargs if provided
    if kwargs:
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            return message
    
    return message


# Centralized messages dictionary
MESSAGES: Dict[str, Dict] = {
    "fr": {
        # TTS feedback messages
        "tts": {
            "welcome": "Tous les systèmes sont stables. Bonjour, je suis Janus. Comment puis-je vous aider aujourd’hui ?",
            "done": "C'est fait",
            "error": "Désolé, je n'ai pas pu exécuter votre demande",
            "error_with_action": "Désolé, je n'ai pas pu exécuter '{action}'",
            "undo": "Annulé",
            "redo": "Rétabli",
            "thinking": "Je réfléchis...",
            "listening": "Je vous écoute",
            "processing": "En cours de traitement...",
            "executing": "Très bien",
            # Progressive loading messages
            "loading_init": "Initialisation en cours. Veuillez patienter…",
            "loading_systems": "Chargement des modules cognitifs, visuels et auditifs..",
        },
        
        # Overlay status messages
        "status": {
            "ready": "Prêt",
            "idle": "En attente",
            "listening": "En écoute",
            "looking": "Observation",  # Vision/OCR in progress (TICKET-UX-001)
            "thinking": "Réflexion",
            "acting": "Exécution",
            "error": "Erreur",
            "offline": "Hors ligne",
            "loading": "Chargement...",
        },
        
        # UI messages
        "ui": {
            "welcome": "Bienvenue",
            "ready": "Prêt",
            "no_speech": "Aucune parole détectée",
            "recording_too_short": "Enregistrement trop court ({frames} segments). Parlez pendant au moins 0,3 seconde.",
            "no_audio_captured": "Aucun audio capturé en {duration}s",
            "command_success": "Commande exécutée avec succès",
            "command_failed": "Échec de la commande",
            "mic_unavailable": "Microphone non disponible",
            "shutting_down": "Arrêt de Janus...",
            "goodbye": "Au revoir !",
            # Text input dialog
            "text_input_title": "Entrer une commande",
            "text_input_placeholder": "Tapez votre commande ici...",
            "text_input_submit": "Envoyer",
        },
        
        # Terminal mode messages
        "terminal": {
            "banner_title": "Contrôle Vocal Janus",
            "banner_subtitle": "Mode Terminal • Session : {session_id}",
            "commands_section": "Commandes",
            "commands_list": [
                "Dites 'ouvre [app]' pour ouvrir une application",
                "Dites 'clique' pour cliquer",
                "Dites 'copie' pour copier le texte sélectionné",
                "Dites 'colle' pour coller",
                "Dites 'annule' ou 'undo' pour annuler",
                "Appuyez sur Ctrl+C pour quitter",
            ],
            "listening_prompt": "Écoute... (parlez maintenant)",
            "press_ctrl_c": "Appuyez sur Ctrl+C pour quitter",
        },
        
        # Configuration messages
        "config": {
            "llm_reasoning": "Raisonnement LLM",
            "vision_features": "Fonctionnalités de vision",
            "learning": "Apprentissage",
            "tts": "Synthèse vocale",
            "enabled": "activé",
            "disabled": "désactivé",
        },
        
        # Error messages
        "errors": {
            "mic_stream_unavailable": "Flux du microphone non disponible",
            "recording_error": "Erreur d'enregistrement : {error}",
            "transcription_failed": "Échec de la transcription",
            "execution_failed": "Échec de l'exécution : {error}",
            "fatal_error": "Erreur fatale : {error}",
            "missing_info": "Je ne peux pas exécuter la demande. Il manque : {missing}.",
        },
        
        # Action messages
        "actions": {
            "opening": "Ouverture de {target}",
            "clicking": "Clic",
            "copying": "Copie",
            "pasting": "Collage",
            "typing": "Saisie : {text}",
            "scrolling": "Défilement {direction}",
        },
    },
    
    "en": {
        # TTS feedback messages
        "tts": {
            "welcome": "Hello. I am Janus. What can I do for you?",
            "done": "Done",
            "error": "Sorry, I couldn't execute your request",
            "error_with_action": "Sorry, I couldn't execute '{action}'",
            "undo": "Undone",
            "redo": "Redone",
            "thinking": "Thinking...",
            "listening": "Listening",
            "processing": "Processing...",
            "executing": "Alright",
            # Progressive loading messages
            "loading_init": "Initializing Janus…",
            "loading_systems": "Loading cognitive modules, visual and audio systems.",
        },
        
        # Overlay status messages
        "status": {
            "ready": "Ready",
            "idle": "Idle",
            "listening": "Listening",
            "looking": "Looking",  # Vision/OCR in progress (TICKET-UX-001)
            "thinking": "Thinking",
            "acting": "Acting",
            "error": "Error",
            "offline": "Offline",
            "loading": "Loading...",
        },
        
        # UI messages
        "ui": {
            "no_speech": "No speech detected",
            "recording_too_short": "Recording too short ({frames} chunks). Please speak for at least 0.3 second.",
            "no_audio_captured": "No audio captured within {duration}s",
            "command_success": "Command executed successfully",
            "command_failed": "Command failed",
            "mic_unavailable": "Microphone not available",
            "shutting_down": "Shutting down Janus...",
            "goodbye": "Goodbye!",
            # Text input dialog
            "text_input_title": "Enter a command",
            "text_input_placeholder": "Type your command here...",
            "text_input_submit": "Submit",
        },
        
        # Terminal mode messages
        "terminal": {
            "banner_title": "Janus Voice Control",
            "banner_subtitle": "Terminal Mode • Session: {session_id}",
            "commands_section": "Commands",
            "commands_list": [
                "Say 'open [app]' to open an application",
                "Say 'click' to click",
                "Say 'copy' to copy selected text",
                "Say 'paste' to paste",
                "Say 'undo' to undo",
                "Press Ctrl+C to exit",
            ],
            "listening_prompt": "Listening... (speak now)",
            "press_ctrl_c": "Press Ctrl+C to exit",
        },
        
        # Configuration messages
        "config": {
            "llm_reasoning": "LLM reasoning",
            "vision_features": "Vision features",
            "learning": "Learning",
            "tts": "Text-to-Speech",
            "enabled": "enabled",
            "disabled": "disabled",
        },
        
        # Error messages
        "errors": {
            "mic_stream_unavailable": "Microphone stream not available",
            "recording_error": "Recording error: {error}",
            "transcription_failed": "Transcription failed",
            "execution_failed": "Execution failed: {error}",
            "fatal_error": "Fatal error: {error}",
            "missing_info": "I cannot execute the request. Missing: {missing}.",
        },
        
        # Action messages
        "actions": {
            "opening": "Opening {target}",
            "clicking": "Clicking",
            "copying": "Copying",
            "pasting": "Pasting",
            "typing": "Typing: {text}",
            "scrolling": "Scrolling {direction}",
        },
    },
}


# Convenience functions for common use cases

def tts_welcome() -> str:
    """Get the welcome TTS message"""
    return t("tts.welcome")

def tts_done() -> str:
    """Get the 'done' TTS message"""
    return t("tts.done")

def tts_error(action: str = None) -> str:
    """Get the error TTS message"""
    if action:
        return t("tts.error_with_action", action=action)
    return t("tts.error")

def tts_no_speech() -> str:
    """Get the 'no speech detected' TTS message"""
    return t("ui.no_speech")

def tts_undo() -> str:
    """Get the 'undo' TTS message"""
    return t("tts.undo")

def tts_redo() -> str:
    """Get the 'redo' TTS message"""
    return t("tts.redo")

def tts_loading_init() -> str:
    """Get the 'initializing' TTS message"""
    return t("tts.loading_init")

def tts_loading_systems() -> str:
    """Get the 'loading cognitive modules' TTS message"""
    return t("tts.loading_systems")

def tts_executing() -> str:
    """Get the 'executing' TTS message (e.g., 'Très bien' in French)"""
    return t("tts.executing")

def status_ready() -> str:
    """Get the 'ready' status message"""
    return t("status.ready")

def status_idle() -> str:
    """Get the 'idle' status message"""
    return t("status.idle")

def status_listening() -> str:
    """Get the 'listening' status message"""
    return t("status.listening")

def status_looking() -> str:
    """Get the 'looking' status message (Vision/OCR in progress)"""
    return t("status.looking")

def status_thinking() -> str:
    """Get the 'thinking' status message"""
    return t("status.thinking")

def status_acting() -> str:
    """Get the 'acting' status message"""
    return t("status.acting")

def status_error() -> str:
    """Get the 'error' status message"""
    return t("status.error")

def status_loading() -> str:
    """Get the 'loading' status message"""
    return t("status.loading")

# Export all public functions
__all__ = [
    "t",
    "set_language",
    "get_language",
    "tts_welcome",
    "tts_done",
    "tts_error",
    "tts_no_speech",
    "tts_undo",
    "tts_redo",
    "tts_loading_init",
    "tts_loading_systems",
    "tts_executing",
    "status_ready",
    "status_idle",
    "status_listening",
    "status_looking",
    "status_thinking",
    "status_acting",
    "status_error",
    "status_loading",
]
