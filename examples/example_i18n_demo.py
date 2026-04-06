#!/usr/bin/env python3
"""
Demo: Système d'internationalisation (i18n) de Janus

Ce script démontre le système centralisé de traduction pour:
- Messages TTS (feedbacks vocaux)
- Status de l'overlay UI
- Messages console
- Messages d'erreur

Usage:
    python examples/example_i18n_demo.py
"""

from janus.i18n import (
    # Status overlay
    status_idle,
    status_listening,
    status_thinking,
    status_acting,
    
    # Feedbacks TTS
    tts_done,
    tts_error,
    tts_no_speech,
    tts_undo,
    tts_redo,
    
    # Messages UI
    t,
    
    # Configuration
    set_language,
    get_language,  # Fixed: was get_current_language
)


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def demo_overlay_status():
    """Démo des status de l'overlay"""
    print_section("📊 Status de l'Overlay")
    
    print(f"🟢 Idle:      {status_idle()}")
    print(f"🎤 Listening: {status_listening()}")
    print(f"🧠 Thinking:  {status_thinking()}")
    print(f"⚡ Acting:    {status_acting()}")


def demo_tts_feedback():
    """Démo des feedbacks TTS"""
    print_section("🔊 Feedbacks TTS (Vocal)")
    
    print(f"✅ Done:       {tts_done()}")
    print(f"❌ Error:      {tts_error()}")
    print(f"🔇 No Speech:  {tts_no_speech()}")
    print(f"↩️  Undo:       {tts_undo()}")
    print(f"↪️  Redo:       {tts_redo()}")


def demo_ui_messages():
    """Démo des messages UI"""
    print_section("💬 Messages UI")
    
    print(f"Welcome:       {t('ui.welcome')}")
    print(f"Ready:         {t('ui.ready')}")
    print(f"Shutting down: {t('ui.shutting_down')}")
    print(f"Command success: {t('ui.command_success')}")
    print(f"Command failed:  {t('ui.command_failed')}")


def demo_error_messages():
    """Démo des messages d'erreur"""
    print_section("⚠️  Messages d'Erreur")
    
    print(f"No speech:     {t('errors.no_speech_detected')}")
    print(f"STT failed:    {t('errors.stt_failed')}")
    print(f"TTS failed:    {t('errors.tts_failed')}")
    print(f"Fatal error:   {t('errors.fatal_error', error='Example error')}")


def demo_terminal_banner():
    """Démo du banner terminal"""
    print_section("🖥️  Banner Terminal")
    
    print(f"Title:         {t('terminal.banner_title')}")
    print(f"Subtitle:      {t('terminal.banner_subtitle', session_id='abc12345')}")
    print(f"Commands:      {t('terminal.commands_section')}")
    
    commands = t('terminal.commands_list')
    for cmd in commands:
        print(f"  • {cmd}")


def main():
    """Main demo function"""
    print("\n" + "="*60)
    print("  🌍 SPECTRA i18n DEMO - Système de Traduction")
    print("="*60)
    
    # Test French (default)
    print(f"\n📍 Langue actuelle: {get_language()}")
    
    demo_overlay_status()
    demo_tts_feedback()
    demo_ui_messages()
    demo_error_messages()
    demo_terminal_banner()
    
    # Switch to English
    print("\n" + "="*60)
    print("  🇬🇧 Switching to English...")
    print("="*60)
    set_language("en")
    print(f"\n📍 Current language: {get_language()}")
    
    demo_overlay_status()
    demo_tts_feedback()
    demo_ui_messages()
    demo_error_messages()
    demo_terminal_banner()
    
    # Back to French
    print("\n" + "="*60)
    print("  🇫🇷 Retour au Français...")
    print("="*60)
    set_language("fr")
    print(f"\n📍 Langue actuelle: {get_language()}")
    
    print("\n✅ Démo terminée!")
    print("\n💡 Pour ajouter de nouvelles traductions:")
    print("   1. Éditer janus/i18n.py")
    print("   2. Ajouter les clés dans TRANSLATIONS['fr'] et TRANSLATIONS['en']")
    print("   3. Utiliser t('votre.cle') ou les fonctions helper (tts_*, status_*)")
    print("\n📖 Documentation: docs/developer/I18N_SYSTEM.md\n")


if __name__ == "__main__":
    main()
