"""
Example: Streaming STT with Progressive Display (TICKET LOCAL-4)

This example demonstrates real-time speech-to-text with progressive transcription:
- Audio is transcribed in chunks as the user speaks
- Text appears progressively (like ChatGPT voice mode)
- Automatic sentence boundary detection
- Duplicate elimination from overlapping chunks

Usage:
    python examples/example_streaming_stt.py
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
from janus.utils.gpu_utils import get_optimal_compute_type, get_optimal_device

logger = get_logger("streaming_example")


class ProgressiveDisplay:
    """Simple console-based progressive text display"""

    def __init__(self):
        self.current_text = ""
        self.line_length = 80

    def update(self, text: str, is_final: bool = False):
        """Update displayed text"""
        # Clear current line
        sys.stdout.write("\r" + " " * self.line_length + "\r")

        # Display text with indicator
        indicator = "✓" if is_final else "…"
        display_text = f"{indicator} {text}"

        # Truncate if too long
        if len(display_text) > self.line_length:
            display_text = display_text[: self.line_length - 3] + "..."

        sys.stdout.write(display_text)
        sys.stdout.flush()

        if is_final:
            sys.stdout.write("\n")

        self.current_text = text


def on_partial_result(result: PartialResult, display: ProgressiveDisplay):
    """Callback for partial transcription results"""
    display.update(result.text, is_final=result.is_final)

    if result.is_final:
        logger.info(f"Final segment #{result.segment_id}: '{result.text}'")


def on_final_result(text: str):
    """Callback for final complete transcription"""
    logger.info(f"\n{'='*60}")
    logger.info(f"FINAL TRANSCRIPTION ({len(text)} chars):")
    logger.info(f"{'='*60}")
    logger.info(text)
    logger.info(f"{'='*60}\n")


def simulate_audio_stream(audio_file: str, chunk_duration_ms: int = 100) -> np.ndarray:
    """
    Simulate streaming audio by yielding chunks from a file

    Args:
        audio_file: Path to audio file
        chunk_duration_ms: Chunk duration in milliseconds

    Yields:
        Audio chunks
    """
    import wave

    with wave.open(audio_file, "rb") as wf:
        sample_rate = wf.getframerate()
        chunk_size = int(sample_rate * chunk_duration_ms / 1000)

        logger.info(f"Audio: {sample_rate}Hz, chunk={chunk_duration_ms}ms ({chunk_size} samples)")

        while True:
            audio_bytes = wf.readframes(chunk_size)
            if not audio_bytes:
                break

            # Convert to numpy array
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)

            # Normalize to float32 [-1, 1]
            audio_float = audio_data.astype(np.float32) / 32768.0

            yield audio_float

            # Simulate real-time by sleeping
            time.sleep(chunk_duration_ms / 1000)


def example_streaming_from_file(audio_file: str):
    """
    Example: Stream audio from file with progressive transcription

    Args:
        audio_file: Path to audio file (WAV format)
    """
    logger.info("=" * 60)
    logger.info("Streaming STT Example - Progressive Transcription")
    logger.info("=" * 60)

    # 1. Initialize STT engine with optimal device
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

    # 2. Create streaming STT with display
    logger.info("\n2. Creating streaming STT...")
    display = ProgressiveDisplay()

    streaming = StreamingSTT(
        stt_engine=engine,
        buffer_duration_sec=2.5,
        overlap_sec=0.5,
        on_partial_result=lambda r: on_partial_result(r, display),
        on_final_result=on_final_result,
    )

    # 3. Start streaming
    logger.info("\n3. Starting streaming transcription...")
    logger.info(f"   Audio file: {audio_file}")
    logger.info("\n   Progressive transcription (watch text appear):")
    logger.info("   " + "-" * 60)

    streaming.start()

    try:
        # Process audio chunks
        chunk_count = 0
        for audio_chunk in simulate_audio_stream(audio_file, chunk_duration_ms=100):
            streaming.add_audio(audio_chunk)
            chunk_count += 1

            # Print progress every 50 chunks
            if chunk_count % 50 == 0:
                stats = streaming.get_stats()
                logger.debug(f"Processed {chunk_count} chunks, {stats['segment_count']} segments")

        # Allow last buffer to be processed
        time.sleep(1.0)

    finally:
        # 4. Stop and get final result
        logger.info("\n   " + "-" * 60)
        logger.info("\n4. Stopping streaming...")
        final_text = streaming.stop()

        # 5. Display statistics
        stats = streaming.get_stats()
        logger.info("\n5. Statistics:")
        logger.info(f"   Total segments: {stats['segment_count']}")
        logger.info(f"   Final text length: {len(final_text)} characters")
        logger.info(f"   Buffer info: {stats['buffer_info']}")


def example_streaming_live():
    """
    Example: Live streaming from microphone

    Note: Requires pyaudio and microphone access
    """
    logger.info("=" * 60)
    logger.info("Live Streaming STT Example")
    logger.info("=" * 60)
    logger.info("\nThis example requires:")
    logger.info("  - Microphone access")
    logger.info("  - pyaudio installed")
    logger.info("\nSpeak into your microphone to see real-time transcription!")
    logger.info("Press Ctrl+C to stop.\n")

    try:
        import pyaudio
    except ImportError:
        logger.error("pyaudio not installed. Install with: pip install pyaudio")
        return

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

    display = ProgressiveDisplay()

    streaming = StreamingSTT(
        stt_engine=engine,
        on_partial_result=lambda r: on_partial_result(r, display),
        on_final_result=on_final_result,
    )

    # Setup audio input
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

    logger.info("Listening... (speak now)")
    logger.info("-" * 60 + "\n")

    streaming.start()

    try:
        while True:
            # Read audio chunk
            audio_bytes = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float = audio_data.astype(np.float32) / 32768.0

            # Process
            streaming.add_audio(audio_float)

    except KeyboardInterrupt:
        logger.info("\n\nStopping...")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

        final_text = streaming.stop()

        logger.info(f"\nFinal transcription: {final_text}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Streaming STT Example with Progressive Display")
    parser.add_argument(
        "--file",
        type=str,
        help="Audio file to transcribe (WAV format)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live microphone input",
    )

    args = parser.parse_args()

    if args.live:
        example_streaming_live()
    elif args.file:
        if not Path(args.file).exists():
            logger.error(f"File not found: {args.file}")
            sys.exit(1)
        example_streaming_from_file(args.file)
    else:
        # Demo with simulated audio
        logger.info("No audio file specified. Use --file <path> or --live")
        logger.info("\nExample usage:")
        logger.info("  python examples/example_streaming_stt.py --file audio.wav")
        logger.info("  python examples/example_streaming_stt.py --live")
        sys.exit(0)


if __name__ == "__main__":
    main()
