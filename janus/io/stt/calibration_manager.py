"""
Microphone calibration and accent personalization
Enhanced with Phase 15.4 - Dynamic Calibration
"""

import json
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# Silence threshold constants (in chunks at 20ms/chunk)
SILENCE_THRESHOLD_SHORT = 50   # ~1.0s - for quick responses
SILENCE_THRESHOLD_MEDIUM = 60  # ~1.2s - default/balanced (reduced from 125)
SILENCE_THRESHOLD_LONG = 75    # ~1.5s - for slower speakers/noisy environments


@dataclass
class CalibrationProfile:
    """User calibration profile
    
    Note: voice_activation_threshold and vad_aggressiveness removed.
    Recording now starts immediately without waiting for voice activation.
    Silence detection uses energy-based thresholds only (no VAD filtering).
    """

    user_id: str
    calibration_phrases: List[str]
    silence_threshold: int
    ambient_noise_level: float
    sample_count: int
    language: str

    # Phase 15.4 - Dynamic calibration fields
    noise_mean: float = 0.0
    noise_variance: float = 0.0
    last_recalibration: float = 0.0  # timestamp
    recalibration_count: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "CalibrationProfile":
        """Create from dictionary
        
        Handles legacy profiles that may contain deprecated fields:
        - voice_activation_threshold (removed - no longer used)
        - vad_aggressiveness (removed - no longer used)
        """
        # Remove deprecated fields if present
        deprecated_fields = ["voice_activation_threshold", "vad_aggressiveness"]
        for field in deprecated_fields:
            if field in data:
                data.pop(field)
        
        # Handle legacy profiles without new fields
        defaults = {
            "noise_mean": 0.0,
            "noise_variance": 0.0,
            "last_recalibration": 0.0,
            "recalibration_count": 0,
        }
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value
        return cls(**data)


class NoiseStatistics:
    """Rolling statistics for ambient noise (Phase 15.4)"""

    def __init__(self, window_size: int = 100):
        """
        Initialize noise statistics tracker

        Args:
            window_size: Number of samples to keep for rolling stats
        """
        self.window_size = window_size
        self.amplitude_history = deque(maxlen=window_size)
        self.mean = 0.0
        self.variance = 0.0
        self.std_dev = 0.0

    def add_sample(self, amplitude: float):
        """Add noise sample to rolling window"""
        self.amplitude_history.append(amplitude)
        self._update_statistics()

    def _update_statistics(self):
        """Update mean and variance"""
        if not self.amplitude_history:
            return

        if HAS_NUMPY:
            samples = np.array(list(self.amplitude_history))
            self.mean = np.mean(samples)
            self.variance = np.var(samples)
            self.std_dev = np.std(samples)
        else:
            # Pure Python fallback
            samples = list(self.amplitude_history)
            n = len(samples)
            self.mean = sum(samples) / n
            self.variance = sum((x - self.mean) ** 2 for x in samples) / n
            self.std_dev = self.variance**0.5

    def get_statistics(self) -> Dict[str, float]:
        """Get current statistics"""
        return {
            "mean": self.mean,
            "variance": self.variance,
            "std_dev": self.std_dev,
            "sample_count": len(self.amplitude_history),
        }

    def has_significant_deviation(self, threshold_std_devs: float = 2.0) -> bool:
        """
        Check if recent samples deviate significantly from mean

        Args:
            threshold_std_devs: Number of standard deviations for significance

        Returns:
            True if recent deviation is significant
        """
        if len(self.amplitude_history) < 10:
            return False

        # Check last 10 samples
        recent = list(self.amplitude_history)[-10:]
        recent_mean = sum(recent) / len(recent)

        # Check if recent mean deviates significantly
        deviation = abs(recent_mean - self.mean)
        threshold = threshold_std_devs * self.std_dev

        return deviation > threshold


class CalibrationManager:
    """Manages microphone calibration and user personalization"""

    # Standard calibration phrases (5 phrases as specified)
    DEFAULT_CALIBRATION_PHRASES_FR = [
        "Ouvre le navigateur Chrome",
        "Copie le texte sélectionné",
        "Lance l'application Visual Studio Code",
        "Clique sur le bouton suivant",
        "Ferme la fenêtre actuelle",
    ]

    DEFAULT_CALIBRATION_PHRASES_EN = [
        "Open the Chrome browser",
        "Copy the selected text",
        "Launch Visual Studio Code application",
        "Click on the next button",
        "Close the current window",
    ]

    def __init__(self, profile_dir: Optional[str] = None):
        """
        Initialize calibration manager

        Args:
            profile_dir: Directory to store calibration profiles
                        If None, uses Settings.calibration.profile_dir
        """
        # Use provided profile_dir, or fall back to Settings, or default
        if profile_dir is None:
            try:
                from janus.runtime.core import Settings

                settings = Settings()
                profile_dir = settings.calibration.profile_dir
            except Exception:
                # Fallback if Settings cannot be loaded
                profile_dir = "calibration_profiles"

        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(exist_ok=True)
        self.current_profile: Optional[CalibrationProfile] = None

        # Phase 15.4 - Dynamic calibration
        self.noise_stats = NoiseStatistics(window_size=100)
        self.recalibration_threshold_deviations = (
            3  # Number of consecutive deviations before recalibration
        )
        self.consecutive_deviations = 0

    def get_calibration_phrases(self, language: str = "fr") -> List[str]:
        """
        Get calibration phrases for a language

        Args:
            language: Language code (fr or en)

        Returns:
            List of calibration phrases
        """
        if language.lower() == "fr":
            return self.DEFAULT_CALIBRATION_PHRASES_FR.copy()
        else:
            return self.DEFAULT_CALIBRATION_PHRASES_EN.copy()

    def start_calibration(self, user_id: str, language: str = "fr") -> Tuple[List[str], str]:
        """
        Start a new calibration session

        Args:
            user_id: User identifier
            language: Language for calibration

        Returns:
            Tuple of (calibration_phrases, instructions)
        """
        phrases = self.get_calibration_phrases(language)

        instructions = f"""
=== Calibration de votre microphone ===

Vous allez prononcer {len(phrases)} phrases pour optimiser la reconnaissance vocale.

Instructions:
1. Trouvez un endroit calme
2. Positionnez-vous à une distance confortable du microphone (20-30 cm)
3. Parlez naturellement, comme vous le feriez normalement
4. Prononcez chaque phrase clairement
5. Attendez le signal entre chaque phrase

Phrases à prononcer:
"""
        for i, phrase in enumerate(phrases, 1):
            instructions += f"{i}. {phrase}\n"

        instructions += "\nAppuyez sur Entrée pour commencer..."

        return phrases, instructions

    def calibrate_from_samples(
        self, user_id: str, audio_samples: List[Tuple[bytes, float]], language: str = "fr"
    ) -> CalibrationProfile:
        """
        Perform calibration based on audio samples

        Args:
            user_id: User identifier
            audio_samples: List of (audio_data, energy_level) tuples
            language: Language used

        Returns:
            Calibration profile
            
        Note: No longer calculates voice_activation_threshold or vad_aggressiveness.
        Recording starts immediately without waiting for voice activation.
        """
        if not audio_samples:
            # Return default profile
            return self._create_default_profile(user_id, language)

        # Calculate statistics from samples
        energy_levels = [energy for _, energy in audio_samples]

        # Calculate ambient noise level (minimum energy)
        ambient_noise = min(energy_levels) if energy_levels else 100.0

        # Calculate energy statistics for silence detection
        if HAS_NUMPY:
            mean_energy = np.mean(energy_levels)
            std_energy = np.std(energy_levels)
        else:
            # Fallback to pure Python implementation
            mean_energy = sum(energy_levels) / len(energy_levels)
            variance = sum((x - mean_energy) ** 2 for x in energy_levels) / len(energy_levels)
            std_energy = variance**0.5

        # Calculate silence threshold based on energy variance
        # More consistent speakers get lower threshold, variable speakers get higher
        has_low_variance = (std_energy / mean_energy < 0.3) if mean_energy > 0 else False
        
        if has_low_variance:
            # Low variance - user speaks consistently
            silence_threshold = SILENCE_THRESHOLD_SHORT
        else:
            # High variance - use more tolerance
            silence_threshold = SILENCE_THRESHOLD_LONG

        # Create calibration profile
        profile = CalibrationProfile(
            user_id=user_id,
            calibration_phrases=self.get_calibration_phrases(language),
            silence_threshold=int(silence_threshold),
            ambient_noise_level=float(ambient_noise),
            sample_count=len(audio_samples),
            language=language,
        )

        # Save profile
        self.save_profile(profile)
        self.current_profile = profile

        return profile

    def _create_default_profile(self, user_id: str, language: str) -> CalibrationProfile:
        """Create a default calibration profile
        
        Note: No voice_activation_threshold or vad_aggressiveness.
        Recording starts immediately without waiting for voice activation.
        """
        return CalibrationProfile(
            user_id=user_id,
            calibration_phrases=self.get_calibration_phrases(language),
            silence_threshold=SILENCE_THRESHOLD_MEDIUM,
            ambient_noise_level=100.0,
            sample_count=0,
            language=language,
        )

    def save_profile(self, profile: CalibrationProfile):
        """
        Save calibration profile to file

        Args:
            profile: Calibration profile to save
        """
        profile_path = self.profile_dir / f"{profile.user_id}.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)

    def load_profile(self, user_id: str) -> Optional[CalibrationProfile]:
        """
        Load calibration profile from file

        Args:
            user_id: User identifier

        Returns:
            Calibration profile or None if not found
        """
        profile_path = self.profile_dir / f"{user_id}.json"

        if not profile_path.exists():
            return None

        with open(profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        profile = CalibrationProfile.from_dict(data)
        self.current_profile = profile
        return profile

    def get_profile(self, user_id: str) -> CalibrationProfile:
        """
        Get profile for user, creating default if not exists

        Args:
            user_id: User identifier

        Returns:
            Calibration profile
        """
        profile = self.load_profile(user_id)
        if profile is None:
            profile = self._create_default_profile(user_id, "fr")
        return profile

    def list_profiles(self) -> List[str]:
        """
        List all available user profiles

        Returns:
            List of user IDs
        """
        profiles = []
        for profile_file in self.profile_dir.glob("*.json"):
            profiles.append(profile_file.stem)
        return profiles

    def delete_profile(self, user_id: str) -> bool:
        """
        Delete a calibration profile

        Args:
            user_id: User identifier

        Returns:
            True if deleted, False if not found
        """
        profile_path = self.profile_dir / f"{user_id}.json"

        if not profile_path.exists():
            return False

        profile_path.unlink()

        if self.current_profile and self.current_profile.user_id == user_id:
            self.current_profile = None

        return True

    def generate_calibration_report(self, profile: CalibrationProfile) -> str:
        """
        Generate a human-readable calibration report

        Args:
            profile: Calibration profile

        Returns:
            Formatted report string
        """
        report = f"""
=== Profil de calibration ===
Utilisateur: {profile.user_id}
Langue: {profile.language}
Échantillons: {profile.sample_count}

Paramètres optimisés:
- Seuil de silence: {profile.silence_threshold} chunks (~{profile.silence_threshold * 20 / 1000:.1f}s)
- Niveau de bruit ambiant: {profile.ambient_noise_level:.1f}

Note: La détection de voix démarre immédiatement (pas d'attente d'activation).
      Seul le seuil de silence est utilisé pour arrêter l'enregistrement.

Phrases de calibration utilisées:
"""
        for i, phrase in enumerate(profile.calibration_phrases, 1):
            report += f"{i}. {phrase}\n"

        return report

    # Phase 15.4 - Dynamic Calibration Methods

    def update_noise_stats(self, amplitude: float):
        """
        Update rolling noise statistics (Phase 15.4)

        Args:
            amplitude: Ambient noise amplitude sample
        """
        self.noise_stats.add_sample(amplitude)

        # Check for significant deviation
        if self.noise_stats.has_significant_deviation():
            self.consecutive_deviations += 1
        else:
            self.consecutive_deviations = 0

    def should_recalibrate(self) -> bool:
        """
        Check if recalibration should be triggered (Phase 15.4)

        Returns:
            True if recalibration is recommended
        """
        # Trigger recalibration after N consecutive deviations
        return self.consecutive_deviations >= self.recalibration_threshold_deviations

    def auto_adjust_calibration(self, profile: CalibrationProfile) -> CalibrationProfile:
        """
        Automatically adjust calibration based on noise stats (Phase 15.4)
        
        Adjusts silence threshold based on noise variability.
        More stable environments get shorter thresholds, variable environments get longer.

        Args:
            profile: Current calibration profile

        Returns:
            Updated profile with adjusted silence threshold
        """
        stats = self.noise_stats.get_statistics()

        if stats["sample_count"] < 20:
            # Not enough data yet
            return profile

        # Calculate noise ratio
        if stats["mean"] > 0:
            noise_ratio = stats["std_dev"] / stats["mean"]
        else:
            noise_ratio = 0.5

        # Adjust silence threshold based on noise variability
        # More stable environment = shorter silence threshold
        # Variable noise = longer threshold to avoid false cutoffs
        if noise_ratio < 0.2:
            # Very stable environment
            new_silence_threshold = SILENCE_THRESHOLD_SHORT
        elif noise_ratio < 0.4:
            # Moderately stable
            new_silence_threshold = SILENCE_THRESHOLD_MEDIUM
        else:
            # Variable noise - need more tolerance
            new_silence_threshold = SILENCE_THRESHOLD_LONG

        # Update profile
        profile.silence_threshold = new_silence_threshold
        profile.noise_mean = stats["mean"]
        profile.noise_variance = stats["variance"]
        profile.ambient_noise_level = stats["mean"]
        profile.last_recalibration = time.time()
        profile.recalibration_count += 1

        return profile

    def get_calibration_parameters(self, profile: CalibrationProfile) -> Dict[str, any]:
        """
        Get current calibration parameters for API exposure (Phase 15.4)

        Args:
            profile: Calibration profile

        Returns:
            Dictionary of calibration parameters
        """
        noise_stats = self.noise_stats.get_statistics()

        return {
            "user_id": profile.user_id,
            "silence_threshold": profile.silence_threshold,
            "ambient_noise_level": profile.ambient_noise_level,
            "language": profile.language,
            "last_recalibration": profile.last_recalibration,
            "recalibration_count": profile.recalibration_count,
            "current_noise_mean": noise_stats["mean"],
            "current_noise_variance": noise_stats["variance"],
            "current_noise_std_dev": noise_stats["std_dev"],
            "noise_samples": noise_stats["sample_count"],
            "should_recalibrate": self.should_recalibrate(),
        }
