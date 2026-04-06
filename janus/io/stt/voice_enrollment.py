"""
Voice Enrollment Module (TICKET-STT-002)

This module handles the enrollment process where users record 3 voice samples
to create their voice fingerprint for speaker verification.
"""

import time
from pathlib import Path
from typing import List, Optional, Tuple
import wave
import numpy as np

from janus.logging import get_logger
from janus.io.stt.speaker_verifier import SpeakerVerifier

logger = get_logger("voice_enrollment")

# Enrollment prompts for user to read
ENROLLMENT_PROMPTS = [
    "Bonjour Janus, ouvre mes applications favorites.",
    "Montre-moi les fichiers du projet en cours.",
    "Envoie un email à l'équipe de développement.",
]


class VoiceEnrollmentManager:
    """
    Manages the voice enrollment process for speaker verification.
    """
    
    def __init__(
        self,
        verifier: SpeakerVerifier,
        recorder=None,  # WhisperRecorder instance
        embedding_path: str = "user_data/user_voice.npy",
    ):
        """
        Initialize enrollment manager.
        
        Args:
            verifier: SpeakerVerifier instance
            recorder: Audio recorder instance (WhisperRecorder)
            embedding_path: Path to save user voice embedding
        """
        self.verifier = verifier
        self.recorder = recorder
        self.embedding_path = embedding_path
    
    def is_enrolled(self) -> bool:
        """
        Check if user is already enrolled.
        
        Returns:
            True if user voice embedding exists
        """
        return Path(self.embedding_path).exists()
    
    def load_audio_from_wav(self, wav_path: str) -> Optional[np.ndarray]:
        """
        Load audio data from WAV file.
        
        Args:
            wav_path: Path to WAV file
            
        Returns:
            Audio data as numpy array or None if loading failed
        """
        try:
            with wave.open(wav_path, 'rb') as wf:
                # Get audio parameters
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                
                # Read audio data
                audio_bytes = wf.readframes(n_frames)
                
                # Convert to numpy array
                if sample_width == 2:  # 16-bit audio
                    audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                else:
                    logger.error(f"Unsupported sample width: {sample_width}")
                    return None
                
                # Handle stereo by taking first channel
                if channels == 2:
                    audio_data = audio_data[::2]
                
                # Convert to float32 normalized to [-1, 1]
                audio_data = audio_data.astype(np.float32) / 32768.0
                
                logger.debug(f"Loaded audio: {len(audio_data)} samples at {framerate}Hz")
                return audio_data
                
        except Exception as e:
            logger.error(f"Failed to load WAV file: {e}")
            return None
    
    def record_sample(
        self,
        prompt_number: int,
        max_duration: int = 8,
        on_audio_chunk=None,
    ) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """
        Record a single voice sample for enrollment.
        
        Args:
            prompt_number: Which prompt to display (1-3)
            max_duration: Maximum recording duration in seconds
            on_audio_chunk: Optional callback for audio feedback
            
        Returns:
            Tuple of (audio_data, error_message)
        """
        if self.recorder is None:
            return None, "No audio recorder available"
        
        if not self.verifier.is_available():
            return None, "Speaker verification not available"
        
        # Get prompt text
        if 0 <= prompt_number < len(ENROLLMENT_PROMPTS):
            prompt_text = ENROLLMENT_PROMPTS[prompt_number]
        else:
            prompt_text = f"Please speak clearly for sample {prompt_number + 1}"
        
        logger.info(f"Recording sample {prompt_number + 1}")
        logger.info(f"Prompt: {prompt_text}")
        
        # Record audio
        audio_path, error = self.recorder.record_audio(
            max_duration=max_duration,
            on_audio_chunk=on_audio_chunk
        )
        
        if error or not audio_path:
            return None, error or "Recording failed"
        
        # Load audio data
        audio_data = self.load_audio_from_wav(audio_path)
        if audio_data is None:
            return None, "Failed to load recorded audio"
        
        # Verify audio is long enough (at least 1 second)
        min_samples = self.verifier.sample_rate * 1
        if len(audio_data) < min_samples:
            return None, f"Audio too short - please speak for at least 1 second"
        
        logger.info(f"Sample {prompt_number + 1} recorded successfully ({len(audio_data)/self.verifier.sample_rate:.1f}s)")
        return audio_data, None
    
    def enroll_user_interactive(
        self,
        on_audio_chunk=None,
        on_progress=None,
    ) -> Tuple[bool, str]:
        """
        Interactive enrollment process - records 3 samples and creates voice profile.
        
        Args:
            on_audio_chunk: Optional callback for audio feedback during recording
            on_progress: Optional callback(step, total, message) for progress updates
            
        Returns:
            Tuple of (success, message)
        """
        if not self.verifier.is_available():
            return False, "Speaker verification not available (resemblyzer not installed)"
        
        if self.recorder is None:
            return False, "No audio recorder available"
        
        logger.info("Starting voice enrollment process")
        
        # Record 3 samples
        audio_samples = []
        num_samples = 3
        
        for i in range(num_samples):
            if on_progress:
                on_progress(i + 1, num_samples, f"Recording sample {i + 1}/{num_samples}")
            
            # Give user a moment to prepare
            if i > 0:
                time.sleep(1.5)
            
            # Record sample
            audio_data, error = self.record_sample(
                prompt_number=i,
                on_audio_chunk=on_audio_chunk
            )
            
            if error or audio_data is None:
                logger.error(f"Failed to record sample {i + 1}: {error}")
                return False, f"Failed to record sample {i + 1}: {error}"
            
            audio_samples.append(audio_data)
            logger.info(f"Sample {i + 1}/{num_samples} completed")
        
        # Enroll user with collected samples
        if on_progress:
            on_progress(num_samples, num_samples, "Processing voice samples...")
        
        user_embedding = self.verifier.enroll_user(audio_samples)
        if user_embedding is None:
            return False, "Failed to create voice profile"
        
        # Save embedding
        success = self.verifier.save_user_embedding(user_embedding, self.embedding_path)
        if not success:
            return False, "Failed to save voice profile"
        
        logger.info("Voice enrollment completed successfully")
        return True, "Voice enrollment completed successfully"
    
    def get_enrollment_prompts(self) -> List[str]:
        """
        Get list of enrollment prompts.
        
        Returns:
            List of prompt strings
        """
        return ENROLLMENT_PROMPTS.copy()
