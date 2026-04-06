"""
Example demonstrating TICKET A6 conversation mode enhancements

This example shows:
1. Timeout handling with wait_for_response
2. Microphone re-enable after TTS
3. Conversation history viewer

Note: This is a demonstration of the API. To run with real components,
ensure all dependencies are installed (pyaudio, whisper, etc.)
"""
import asyncio


async def example_timeout_handling():
    """Example: Using timeout handling in conversations"""
    print("\n=== Example 1: Timeout Handling ===\n")

    print("Code example:")
    print(
        """
    from janus.runtime.core.conversation_manager import ConversationManager, ClarificationQuestion
    from janus.runtime.core import MemoryEngine
    from janus.runtime.core.settings import DatabaseSettings

    # Setup
    db_settings = DatabaseSettings(path="conversations.db")
    memory = MemoryEngine(db_settings)
    manager = ConversationManager(memory)

    # Start a conversation
    session_id = memory.create_session()
    conversation = manager.start_conversation(session_id)

    # Create a clarification question
    question = ClarificationQuestion(
        question="Which file would you like to open?",
        options=["document.txt", "report.pdf", "notes.md"]
    )

    # Simulate user response callback
    async def get_user_response():
        # This would get input from STT or UI
        await asyncio.sleep(0.5)
        return "document.txt"

    # Wait for response with timeout
    response = await manager.wait_for_response(
        conversation.conversation_id,
        question,
        timeout=30,  # 30 second timeout (default)
        response_callback=get_user_response
    )

    if response:
        print(f"✓ Received response: {response}")
    else:
        print("✗ Timeout - conversation auto-cancelled with reason='timeout'")
    """
    )


async def example_tts_mic_reenable():
    """Example: Microphone re-enable after TTS"""
    print("\n=== Example 2: Mic Re-enable After TTS ===\n")

    print("Code example:")
    print(
        """
    from janus.io.tts.orchestrator_integration import TTSOrchestratorIntegration
    from janus.io.tts.adapter import TTSAdapter
    from janus.io.stt.whisper_stt import WhisperSTT

    # Setup TTS and STT
    tts_adapter = TTSAdapter()
    stt = WhisperSTT(model_size="base")

    # Create callback to re-enable microphone
    async def enable_mic_callback():
        await stt.enable_listening_async()
        print("🎤 Microphone re-enabled")

    # Create TTS orchestrator with callback
    tts_integration = TTSOrchestratorIntegration(
        tts_adapter=tts_adapter,
        enable_tts=True,
        stt_enable_callback=enable_mic_callback
    )

    # Ask clarification - automatically re-enables mic after speaking
    await tts_integration.ask_clarification(
        "Which application would you like to open?",
        priority=8,
        auto_enable_mic=True  # This triggers mic re-enable after TTS
    )

    # The mic is now automatically re-enabled and ready for user response
    """
    )


def example_whisper_stt_control():
    """Example: WhisperSTT enable/disable listening"""
    print("\n=== Example 3: WhisperSTT Listening Control ===\n")

    # Note: This example shows the API without actually loading Whisper
    print("Example WhisperSTT usage:")
    print(
        """
    # Create STT instance
    stt = WhisperSTT(model_size="base", lazy_load=True)

    # Enable listening
    stt.enable_listening()
    print("Listening enabled")

    # During TTS playback - disable listening
    stt.disable_listening()
    print("Listening disabled during TTS")

    # After TTS completes - re-enable
    stt.enable_listening()
    print("Listening re-enabled")

    # Async usage
    async def tts_integration():
        # Disable before TTS
        await stt.disable_listening_async()

        # ... TTS plays ...

        # Re-enable after TTS
        await stt.enable_listening_async()
    """
    )


def example_conversation_viewer():
    """Example: Using the conversation history viewer"""
    print("\n=== Example 4: Conversation History Viewer ===\n")

    print("To view conversation history:")
    print(
        """
    from janus.ui.conversation_viewer import ConversationViewer

    # Create viewer
    viewer = ConversationViewer(
        db_path="janus_data.db",
        auto_refresh=True
    )

    # Show viewer window (blocking)
    viewer.show()

    # Or programmatically refresh and export
    viewer.refresh_conversations()
    viewer._export_to_markdown()  # User will be prompted for file location
    """
    )

    print("\nViewer features:")
    print("- Filter by state (active, completed, needs_clarification)")
    print("- Filter by session ID")
    print("- Search conversations")
    print("- View conversation details and turns")
    print("- Export to markdown")
    print("- Auto-refresh every 3 seconds")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("TICKET A6 - Conversation Mode Enhancements Examples")
    print("=" * 60)

    # Run async examples
    await example_timeout_handling()
    await example_tts_mic_reenable()

    # Run sync examples
    example_whisper_stt_control()
    example_conversation_viewer()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
