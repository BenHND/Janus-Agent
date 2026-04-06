"""
Speaker Verification Module (TICKET-STT-002)

This module provides voice fingerprinting functionality to verify speaker identity.
Uses resemblyzer for lightweight speaker recognition to prevent unauthorized voices
from triggering commands in open space environments.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import warnings

from janus.logging import get_logger

logger = get_logger("speaker_verifier")

# Try to import resemblyzer
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    HAS_RESEMBLYZER = True
except ImportError:
    HAS_RESEMBLYZER = False
    warnings.warn("resemblyzer not installed - speaker verification will be disabled")


class SpeakerVerifier:
    """
    Voice fingerprinting for speaker verification.
    
    Uses resemblyzer to extract voice embeddings and verify speaker identity
    via cosine similarity comparison.
    """
    
    def __init__(
        self,
        embedding_path: Optional[str] = None,
        similarity_threshold: float = 0.75,
        sample_rate: int = 16000,
    ):
        """
        Initialize speaker verifier.
        
        Args:
            embedding_path: Path to stored user voice embedding (.npy file)
            similarity_threshold: Minimum cosine similarity to accept voice (0.0-1.0)
            sample_rate: Audio sample rate in Hz
        """
        self.embedding_path = embedding_path
        self.similarity_threshold = similarity_threshold
        self.sample_rate = sample_rate
        self.user_embedding: Optional[np.ndarray] = None
        self.encoder: Optional['VoiceEncoder'] = None
        
        if not HAS_RESEMBLYZER:
            logger.warning("resemblyzer not available - speaker verification disabled")
            return
        
        # Initialize voice encoder
        try:
            self.encoder = VoiceEncoder()
            logger.info("Voice encoder initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize voice encoder: {e}")
            self.encoder = None
            return
        
        # Load user embedding if path provided
        if embedding_path and Path(embedding_path).exists():
            self.load_user_embedding(embedding_path)
    
    def is_available(self) -> bool:
        """Check if speaker verification is available"""
        return HAS_RESEMBLYZER and self.encoder is not None
    
    def load_user_embedding(self, embedding_path: str) -> bool:
        """
        Load user voice embedding from file.
        
        Args:
            embedding_path: Path to .npy embedding file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            embedding_file = Path(embedding_path)
            if not embedding_file.exists():
                logger.warning(f"Embedding file not found: {embedding_path}")
                return False
            
            self.user_embedding = np.load(embedding_path)
            self.embedding_path = embedding_path
            logger.info(f"User voice embedding loaded from {embedding_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load user embedding: {e}")
            return False
    
    def save_user_embedding(self, embedding: np.ndarray, embedding_path: str) -> bool:
        """
        Save user voice embedding to file.
        
        Args:
            embedding: Voice embedding array
            embedding_path: Path to save .npy file
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            embedding_file = Path(embedding_path)
            embedding_file.parent.mkdir(parents=True, exist_ok=True)
            
            np.save(embedding_path, embedding)
            self.user_embedding = embedding
            self.embedding_path = embedding_path
            logger.info(f"User voice embedding saved to {embedding_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user embedding: {e}")
            return False
    
    def extract_embedding(self, audio_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract voice embedding from audio data.
        
        Args:
            audio_data: Audio samples as numpy array (float32, normalized to [-1, 1])
            
        Returns:
            Voice embedding array or None if extraction failed
        """
        if not self.is_available():
            return None
        
        try:
            # Ensure audio is in the correct format for resemblyzer
            # resemblyzer expects float32 in [-1, 1] range
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Preprocess audio for resemblyzer
            # This handles resampling and normalization
            wav = preprocess_wav(audio_data, source_sr=self.sample_rate)
            
            # Extract embedding
            embedding = self.encoder.embed_utterance(wav)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to extract embedding: {e}")
            return None
    
    def verify_speaker(self, audio_data: np.ndarray) -> Tuple[bool, float]:
        """
        Verify if audio matches enrolled user voice.
        
        Args:
            audio_data: Audio samples as numpy array (float32, normalized to [-1, 1])
            
        Returns:
            Tuple of (is_verified, similarity_score)
            - is_verified: True if speaker is verified
            - similarity_score: Cosine similarity (0.0-1.0)
        """
        if not self.is_available():
            logger.warning("Speaker verification not available - accepting by default")
            return True, 1.0
        
        if self.user_embedding is None:
            logger.warning("No user embedding enrolled - accepting by default")
            return True, 1.0
        
        # Extract embedding from audio
        audio_embedding = self.extract_embedding(audio_data)
        if audio_embedding is None:
            logger.warning("Failed to extract audio embedding - accepting by default")
            return True, 1.0
        
        # Calculate cosine similarity
        try:
            similarity = self._cosine_similarity(self.user_embedding, audio_embedding)
            is_verified = similarity >= self.similarity_threshold
            
            if is_verified:
                logger.debug(f"Speaker verified (similarity: {similarity:.3f})")
            else:
                logger.warning(f"Voice mismatch detected (similarity: {similarity:.3f} < threshold: {self.similarity_threshold})")
            
            return is_verified, similarity
            
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return True, 1.0  # Accept by default on error
    
    def _cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (-1.0 to 1.0, where 1.0 means identical)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calculate cosine similarity (range: -1 to 1)
        # 1.0 = identical, 0.0 = orthogonal, -1.0 = opposite
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        
        # Clip to valid range
        similarity = np.clip(similarity, -1.0, 1.0)
        
        return float(similarity)
    
    def enroll_user(self, audio_samples: list) -> Optional[np.ndarray]:
        """
        Enroll user by averaging embeddings from multiple audio samples.
        
        Args:
            audio_samples: List of audio numpy arrays (3+ samples recommended)
            
        Returns:
            Average voice embedding or None if enrollment failed
        """
        if not self.is_available():
            logger.error("Speaker verification not available - cannot enroll")
            return None
        
        if len(audio_samples) < 2:
            logger.error("Need at least 2 audio samples for enrollment")
            return None
        
        embeddings = []
        for i, audio_data in enumerate(audio_samples):
            embedding = self.extract_embedding(audio_data)
            if embedding is not None:
                embeddings.append(embedding)
                logger.info(f"Extracted embedding {i+1}/{len(audio_samples)}")
            else:
                logger.warning(f"Failed to extract embedding {i+1}/{len(audio_samples)}")
        
        if len(embeddings) < 2:
            logger.error(f"Only {len(embeddings)} valid embeddings - need at least 2")
            return None
        
        # Average embeddings for robust user profile
        user_embedding = np.mean(embeddings, axis=0)
        logger.info(f"User enrolled with {len(embeddings)} audio samples")
        
        return user_embedding
