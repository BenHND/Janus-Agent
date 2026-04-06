"""
Example: Streaming STT with UI Overlay Integration (TICKET LOCAL-4)

This example demonstrates complete streaming transcription with visual feedback:
- Real-time progressive transcription
- UI overlay showing text as it appears
- Typing animation effect
- Sentence boundary detection
- Professional ChatGPT-like experience

Usage:
    python examples/example_streaming_with_ui.py --live
    python examples/example_streaming_with_ui.py --file audio.wav
"""
import sys
import time
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from janus.logging import get_logger
from janus.io.stt.realtime_stt_engine import RealtimeSTTEngine
from janus.io.stt.streaming_engine import PartialResult, StreamingSTT
from janus.ui.streaming_overlay import StreamingOverlay
from janus.utils.gpu_utils import get_optimal_compute_type, get_optimal_device

logger = get_logger("streaming_ui_example")


def example_with_ui_overlay():
    """
    Example: Streaming transcription with UI overlay

    Demonstrates:
    - Real-time microphone input
    - Progressive transcription
    - Visual feedback via overlay
    - ChatGPT-like experience
    """
    logger.info("=" * 60)
    logger.info("Streaming STT with UI Overlay")
    logger.info("=" * 60)

    try:
        import pyaudio
    except ImportError:
        logger.error("pyaudio not installed. Install with: pip install pyaudio")
        return

    # 1. Initialize STT engine
    logger.info("\n1. Initializing STT engine...")
    device = get_optimal_device()
    compute_type = get_optimal_compute_type(device)

    logger.info(f"   Device: {device}")
    logger.info(f"   Compute type: {compute_type}")

    # TICKET-1: Pass explicit language from config or default to "fr"
    from janus.runtime.core import Settings

    settings = Settings()
    language = settings.language.default  # Get language from settings

    engine = RealtimeSTTEngine(
        model_size="base",
        device=device,
        compute_type=compute_type,
        language=language,  # TICKET-1: Explicit language
        use_faster_whisper=True,
    )

    # 2. Create UI overlay
    logger.info("\n2. Creating UI overlay...")
    overlay = StreamingOverlay(
        position="top-center",
        max_width=700,
        max_lines=4,
        auto_hide_delay=5.0,
    )
    overlay.start()

    # Wait for overlay to initialize
    time.sleep(1.0)

    # 3. Create streaming STT with callbacks
    logger.info("\n3. Setting up streaming STT...")

    def on_partial(result: PartialResult):
        """Callback for partial results - update overlay"""
        overlay.update_text(
            result.text,
            is_final=result.is_final,
            confidence=result.confidence,
        )

        if result.is_final:
            logger.info(f"✓ Sentence #{result.segment_id}: {result.text}")

    def on_final(text: str):
        """Callback for final complete transcription"""
        logger.info(f"\n{'='*60}")
        logger.info(f"FINAL TRANSCRIPTION:")
        logger.info(f"{'='*60}")
        logger.info(text)
        logger.info(f"{'='*60}\n")

    streaming = StreamingSTT(
        stt_engine=engine,
        buffer_duration_sec=2.5,
        overlap_sec=0.5,
        on_partial_result=on_partial,
        on_final_result=on_final,
    )

    # 4. Setup audio input
    logger.info("\n4. Setting up microphone...")
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 1600  # 100ms at 16kHz

    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )

    # 5. Start streaming
    logger.info("\n5. Starting live transcription...")
    logger.info("\n" + "=" * 60)
    logger.info("🎤 SPEAK NOW - Watch the overlay for real-time transcription!")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60 + "\n")

    overlay.show()
    overlay.update_text("Listening... Speak now!", is_final=False, confidence=1.0)

    streaming.start()

    try:
        chunk_count = 0

        while True:
            # Read audio chunk
            audio_bytes = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_data.astype(np.float32) / 32768.0

            # Process
            streaming.add_audio(audio_float)

            chunk_count += 1

            # Log progress every 100 chunks (~10 seconds)
            if chunk_count % 100 == 0:
                stats = streaming.get_stats()
                logger.debug(
                    f"Progress: {chunk_count} chunks, "
                    f"{stats['segment_count']} segments, "
                    f"{len(streaming.get_current_text())} chars"
                )

    except KeyboardInterrupt:
        logger.info("\n\n⏹ Stopping...")

    finally:
        # 6. Cleanup
        logger.info("\n6. Cleaning up...")

        stream.stop_stream()
        stream.close()
        audio.terminate()

        final_text = streaming.stop()

        # Show final result in overlay for a bit longer
        overlay.update_text(final_text, is_final=True, confidence=1.0)
        time.sleep(3.0)

        overlay.stop()

        # 7. Display statistics
        stats = streaming.get_stats()
        logger.info("\n7. Session Statistics:")
        logger.info(f"   Total segments: {stats['segment_count']}")
        logger.info(f"   Final text: {len(final_text)} characters")
        logger.info(f"   {len(final_text.split())} words")

        logger.info("\n✓ Done!")


def example_file_with_ui(audio_file: str):
    """
    Example: Process audio file with UI overlay

    Args:
        audio_file: Path to audio file
    """
    import wave

    logger.info("=" * 60)
    logger.info("Streaming STT with UI - File Mode")
    logger.info("=" * 60)

    # Initialize
    device = get_optimal_device()
    compute_type = get_optimal_compute_type(device)

    # TICKET-1: Pass explicit language from config or default to "fr"
    from janus.runtime.core import Settings

    settings = Settings()
    language = settings.language.default  # Get language from settings

    engine = RealtimeSTTEngine(
        model_size="base",
        device=device,
        compute_type=compute_type,
        language=language,  # TICKET-1: Explicit language
        use_faster_whisper=True,
    )

    overlay = StreamingOverlay(
        position="top-center",
        max_width=700,
        auto_hide_delay=10.0,
    )
    overlay.start()
    time.sleep(1.0)

    def on_partial(result: PartialResult):
        overlay.update_text(result.text, result.is_final, result.confidence)

    def on_final(text: str):
        logger.info(f"\nFinal: {text}")

    streaming = StreamingSTT(
        stt_engine=engine,
        on_partial_result=on_partial,
        on_final_result=on_final,
    )

    logger.info(f"\nProcessing: {audio_file}")
    logger.info("Watch the overlay for progressive transcription...\n")

    overlay.show()
    streaming.start()

    try:
        # Read and process audio file
        with wave.open(audio_file, "rb") as wf:
            sample_rate = wf.getframerate()
            chunk_size = int(sample_rate * 0.1)  # 100ms chunks

            while True:
                audio_bytes = wf.readframes(chunk_size)
                if not audio_bytes:
                    break

                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_float = audio_data.astype(np.float32) / 32768.0

                streaming.add_audio(audio_float)
                time.sleep(0.1)  # Simulate real-time

        # Allow final processing
        time.sleep(2.0)

    finally:
        final_text = streaming.stop()

        # Show final result
        overlay.update_text(final_text, is_final=True, confidence=1.0)
        time.sleep(5.0)

        overlay.stop()

        logger.info(f"\n✓ Transcription complete: {len(final_text)} characters")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Streaming STT with UI Overlay - TICKET LOCAL-4 Demo"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live microphone input with UI overlay",
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Process audio file with UI overlay (WAV format)",
    )

    args = parser.parse_args()

    if args.live:
        example_with_ui_overlay()
    elif args.file:
        if not Path(args.file).exists():
            logger.error(f"File not found: {args.file}")
            sys.exit(1)
        example_file_with_ui(args.file)
    else:
        logger.info("Streaming STT with UI Overlay Example")
        logger.info("\nUsage:")
        logger.info("  Live microphone:  python examples/example_streaming_with_ui.py --live")
        logger.info(
            "  Process file:     python examples/example_streaming_with_ui.py --file audio.wav"
        )
        logger.info("\nThis demonstrates TICKET LOCAL-4 features:")
        logger.info("  ✓ Progressive transcription (text appears as you speak)")
        logger.info("  ✓ Rolling buffer with overlap (2.5s buffer, 0.5s overlap)")
        logger.info("  ✓ Result merging (no duplicate text)")
        logger.info("  ✓ Sentence boundary detection")
        logger.info("  ✓ UI overlay integration")
        logger.info("  ✓ ChatGPT-like visual experience")


if __name__ == "__main__":
    main()
