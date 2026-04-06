"""
Voice Adaptation Cache for learning user corrections (Phase 16.3)

This module provides:
- SQLite database for storing (audio_hash, raw_text, corrected_text)
- Levenshtein distance similarity search
- Automatic application of learned corrections
- Auto-cleanup of old entries (> 90 days)
- AES256 encryption for privacy
"""

import hashlib
import json
import sqlite3
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from janus.logging import get_logger

# Try to import cryptography for encryption
try:
    import base64

    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    warnings.warn("cryptography not installed - VoiceAdaptationCache will store data unencrypted")


@dataclass
class CacheEntry:
    """Cache entry for voice corrections"""

    id: int
    audio_hash: str
    raw_text: str
    corrected_text: str
    timestamp: float
    use_count: int
    language: str
    confidence: float


class VoiceAdaptationCache:
    """
    SQLite-based cache for learning and applying voice corrections

    Features:
    - Stores audio hash → text corrections
    - Fuzzy matching using Levenshtein distance
    - Automatic cleanup of old entries
    - Optional AES256 encryption
    """

    def __init__(
        self,
        db_path: str = "voice_cache.db",
        user_id: str = "default",
        enable_encryption: bool = True,
        encryption_key: Optional[str] = None,
        similarity_threshold: float = 0.2,
        cleanup_days: int = 90,
        max_entries: int = 10000,
    ):
        """
        Initialize Voice Adaptation Cache

        Args:
            db_path: Path to SQLite database file
            user_id: User identifier (for multi-user support)
            enable_encryption: Enable AES256 encryption
            encryption_key: Encryption key (auto-generated if None)
            similarity_threshold: Levenshtein distance threshold (0.0-1.0)
            cleanup_days: Days after which to auto-delete old entries
            max_entries: Maximum number of entries per user (LRU eviction)
        """
        self.logger = get_logger("voice_adaptation_cache")
        self.db_path = Path(db_path)
        self.user_id = user_id
        self.enable_encryption = enable_encryption and HAS_CRYPTO
        self.similarity_threshold = similarity_threshold
        self.cleanup_days = cleanup_days
        self.max_entries = max_entries

        # Initialize encryption
        self.cipher = None
        if self.enable_encryption:
            self._initialize_encryption(encryption_key)
        elif enable_encryption and not HAS_CRYPTO:
            self.logger.warning("Encryption requested but cryptography not installed")

        # Initialize database
        self._initialize_database()

        # Statistics
        self.stats = {
            "total_entries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "corrections_applied": 0,
            "entries_added": 0,
            "entries_cleaned": 0,
        }

        # Update stats
        self._update_stats()

    def _initialize_encryption(self, encryption_key: Optional[str]):
        """Initialize Fernet cipher for encryption"""
        if encryption_key:
            # Derive key from password
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"janus_voice_cache",  # Fixed salt for consistent key derivation
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(encryption_key.encode()))
        else:
            # Generate random key
            key = Fernet.generate_key()
            # Store key in a secure location
            key_file = self.db_path.parent / f".cache_key_{self.user_id}"
            if not key_file.exists():
                key_file.write_bytes(key)
            else:
                key = key_file.read_bytes()

        self.cipher = Fernet(key)

    def _encrypt(self, text: str) -> str:
        """Encrypt text"""
        if not self.cipher:
            return text
        return self.cipher.encrypt(text.encode()).decode()

    def _decrypt(self, encrypted_text: str) -> str:
        """Decrypt text"""
        if not self.cipher:
            return encrypted_text
        try:
            return self.cipher.decrypt(encrypted_text.encode()).decode()
        except Exception:
            # Return as-is if decryption fails (backwards compatibility)
            return encrypted_text

    def _initialize_database(self):
        """Create database schema if not exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create corrections table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS voice_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                audio_hash TEXT NOT NULL,
                raw_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                timestamp REAL NOT NULL,
                use_count INTEGER DEFAULT 0,
                language TEXT DEFAULT 'unknown',
                confidence REAL DEFAULT 1.0,
                UNIQUE(user_id, audio_hash)
            )
        """
        )

        # Create indexes for performance
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_id
            ON voice_corrections(user_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audio_hash
            ON voice_corrections(user_id, audio_hash)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON voice_corrections(timestamp)
        """
        )

        conn.commit()
        conn.close()

        self.logger.info(f"Voice cache database initialized: {self.db_path}")

    def _compute_audio_hash(self, audio_data: bytes) -> str:
        """Compute SHA256 hash of audio data"""
        return hashlib.sha256(audio_data).hexdigest()

    def _compute_text_hash(self, text: str) -> str:
        """Compute hash of text for fuzzy matching"""
        # Normalize text before hashing
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def _evict_lru_if_needed(self):
        """Evict least recently used entries if cache exceeds max_entries"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Count current entries for this user
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM voice_corrections
                    WHERE user_id = ?
                """,
                    (self.user_id,),
                )

                count = cursor.fetchone()[0]

                # If over limit, delete oldest entries
                if count >= self.max_entries:
                    to_delete = count - self.max_entries + 1

                    cursor.execute(
                        """
                        DELETE FROM voice_corrections
                        WHERE id IN (
                            SELECT id FROM voice_corrections
                            WHERE user_id = ?
                            ORDER BY timestamp ASC, use_count ASC
                            LIMIT ?
                        )
                    """,
                        (self.user_id, to_delete),
                    )

                    conn.commit()

                    if cursor.rowcount > 0:
                        self.stats["entries_cleaned"] += cursor.rowcount
                        self.logger.debug(f"Evicted {cursor.rowcount} old entries (LRU)")

        except Exception as e:
            self.logger.warning(f"Failed to evict LRU entries: {e}")

    def add_correction(
        self,
        audio_data: bytes,
        raw_text: str,
        corrected_text: str,
        language: str = "unknown",
        confidence: float = 1.0,
    ) -> bool:
        """
        Add a correction to the cache

        Args:
            audio_data: Raw audio bytes
            raw_text: Original transcribed text
            corrected_text: Corrected text
            language: Language code
            confidence: Confidence score (0.0-1.0)

        Returns:
            True if added successfully
        """
        try:
            # Evict old entries if cache is full
            self._evict_lru_if_needed()

            audio_hash = self._compute_audio_hash(audio_data)

            # Encrypt sensitive data
            encrypted_raw = self._encrypt(raw_text)
            encrypted_corrected = self._encrypt(corrected_text)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert or update
                cursor.execute(
                    """
                    INSERT INTO voice_corrections
                    (user_id, audio_hash, raw_text, corrected_text, timestamp, language, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, audio_hash) DO UPDATE SET
                        corrected_text = excluded.corrected_text,
                        timestamp = excluded.timestamp,
                        confidence = excluded.confidence
                """,
                    (
                        self.user_id,
                        audio_hash,
                        encrypted_raw,
                        encrypted_corrected,
                        time.time(),
                        language,
                        confidence,
                    ),
                )

                conn.commit()

            self.stats["entries_added"] += 1
            self.stats["total_entries"] += 1

            return True

        except Exception as e:
            self.logger.error(f"Failed to add correction: {e}", exc_info=True)
            return False

    def get_correction(
        self,
        audio_data: bytes,
        raw_text: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get cached correction for audio

        Args:
            audio_data: Raw audio bytes
            raw_text: Optional text for fuzzy matching fallback

        Returns:
            Corrected text if found, None otherwise
        """
        try:
            audio_hash = self._compute_audio_hash(audio_data)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Try exact audio hash match first
                cursor.execute(
                    """
                    SELECT corrected_text, use_count FROM voice_corrections
                    WHERE user_id = ? AND audio_hash = ?
                """,
                    (self.user_id, audio_hash),
                )

                row = cursor.fetchone()

                if row:
                    corrected_text, use_count = row
                    decrypted = self._decrypt(corrected_text)

                    # Update use count
                    cursor.execute(
                        """
                        UPDATE voice_corrections
                        SET use_count = use_count + 1
                        WHERE user_id = ? AND audio_hash = ?
                    """,
                        (self.user_id, audio_hash),
                    )

                    conn.commit()

                    self.stats["cache_hits"] += 1
                    self.stats["corrections_applied"] += 1

                    return decrypted

            # Try fuzzy text matching if raw_text provided
            if raw_text:
                similar = self.find_similar_corrections(raw_text)
                if similar:
                    self.stats["cache_hits"] += 1
                    self.stats["corrections_applied"] += 1
                    return similar[0]["corrected_text"]

            self.stats["cache_misses"] += 1
            return None

        except Exception as e:
            self.logger.error(f"Failed to get correction: {e}", exc_info=True)
            self.stats["cache_misses"] += 1
            return None

    def find_similar_corrections(
        self,
        text: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find similar corrections using Levenshtein distance

        Args:
            text: Text to search for
            limit: Maximum number of results

        Returns:
            List of similar corrections with distance scores
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get all corrections for this user
                cursor.execute(
                    """
                    SELECT id, audio_hash, raw_text, corrected_text, timestamp,
                           use_count, language, confidence
                    FROM voice_corrections
                    WHERE user_id = ?
                    ORDER BY use_count DESC, timestamp DESC
                """,
                    (self.user_id,),
                )

                rows = cursor.fetchall()

            # Calculate Levenshtein distance for each
            similar = []
            text_lower = text.lower().strip()

            for row in rows:
                (
                    entry_id,
                    audio_hash,
                    raw_text_enc,
                    corrected_text_enc,
                    timestamp,
                    use_count,
                    language,
                    confidence,
                ) = row

                raw_text = self._decrypt(raw_text_enc).lower().strip()

                # Calculate normalized Levenshtein distance
                distance = self._levenshtein_distance(text_lower, raw_text)
                max_len = max(len(text_lower), len(raw_text))
                normalized_distance = distance / max_len if max_len > 0 else 0.0

                # Check if below threshold
                if normalized_distance <= self.similarity_threshold:
                    similar.append(
                        {
                            "id": entry_id,
                            "audio_hash": audio_hash,
                            "raw_text": self._decrypt(raw_text_enc),
                            "corrected_text": self._decrypt(corrected_text_enc),
                            "distance": normalized_distance,
                            "timestamp": timestamp,
                            "use_count": use_count,
                            "language": language,
                            "confidence": confidence,
                        }
                    )

            # Sort by distance (closest first) and limit
            similar.sort(key=lambda x: (x["distance"], -x["use_count"]))
            return similar[:limit]

        except Exception as e:
            self.logger.error(f"Failed to find similar corrections: {e}", exc_info=True)
            return []

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings

        Args:
            s1: First string
            s2: Second string

        Returns:
            Edit distance
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def cleanup_old_entries(self, days: Optional[int] = None) -> int:
        """
        Remove entries older than specified days

        Args:
            days: Number of days (uses cleanup_days if None)

        Returns:
            Number of entries deleted
        """
        try:
            days = days if days is not None else self.cleanup_days
            cutoff_time = time.time() - (days * 24 * 60 * 60)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Delete old entries
                cursor.execute(
                    """
                    DELETE FROM voice_corrections
                    WHERE user_id = ? AND timestamp < ?
                """,
                    (self.user_id, cutoff_time),
                )

                deleted = cursor.rowcount
                conn.commit()

            self.stats["entries_cleaned"] += deleted
            self.stats["total_entries"] -= deleted

            self.logger.info(f"Cleaned up {deleted} entries older than {days} days")

            return deleted

        except Exception as e:
            self.logger.error(f"Failed to cleanup entries: {e}", exc_info=True)
            return 0

    def get_all_corrections(self, limit: int = 100) -> List[CacheEntry]:
        """
        Get all corrections for this user

        Args:
            limit: Maximum number of entries

        Returns:
            List of CacheEntry objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT id, audio_hash, raw_text, corrected_text, timestamp,
                           use_count, language, confidence
                    FROM voice_corrections
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (self.user_id, limit),
                )

                rows = cursor.fetchall()

            entries = []
            for row in rows:
                (
                    entry_id,
                    audio_hash,
                    raw_text_enc,
                    corrected_text_enc,
                    timestamp,
                    use_count,
                    language,
                    confidence,
                ) = row

                entries.append(
                    CacheEntry(
                        id=entry_id,
                        audio_hash=audio_hash,
                        raw_text=self._decrypt(raw_text_enc),
                        corrected_text=self._decrypt(corrected_text_enc),
                        timestamp=timestamp,
                        use_count=use_count,
                        language=language,
                        confidence=confidence,
                    )
                )

            return entries

        except Exception as e:
            self.logger.error(f"Failed to get corrections: {e}", exc_info=True)
            return []

    def delete_correction(self, entry_id: int) -> bool:
        """
        Delete a specific correction entry

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    DELETE FROM voice_corrections
                    WHERE id = ? AND user_id = ?
                """,
                    (entry_id, self.user_id),
                )

                deleted = cursor.rowcount > 0
                conn.commit()

            if deleted:
                self.stats["total_entries"] -= 1

            return deleted

        except Exception as e:
            self.logger.error(f"Failed to delete correction: {e}", exc_info=True)
            return False

    def _update_stats(self):
        """Update statistics from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT COUNT(*) FROM voice_corrections
                    WHERE user_id = ?
                """,
                    (self.user_id,),
                )

                count = cursor.fetchone()[0]
                self.stats["total_entries"] = count

        except Exception as e:
            logger.warning(f"Failed to update cache statistics: {e}", exc_info=True)

    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        self._update_stats()

        hit_rate = 0.0
        if self.stats["cache_hits"] + self.stats["cache_misses"] > 0:
            hit_rate = self.stats["cache_hits"] / (
                self.stats["cache_hits"] + self.stats["cache_misses"]
            )

        return {
            **self.stats,
            "hit_rate": hit_rate,
            "db_path": str(self.db_path),
            "user_id": self.user_id,
            "encryption_enabled": self.enable_encryption,
            "similarity_threshold": self.similarity_threshold,
            "cleanup_days": self.cleanup_days,
        }

    def export_corrections(self, output_path: str) -> bool:
        """
        Export corrections to JSON file

        Args:
            output_path: Path to output JSON file

        Returns:
            True if exported successfully
        """
        try:
            entries = self.get_all_corrections(limit=10000)

            data = {
                "user_id": self.user_id,
                "export_time": time.time(),
                "total_entries": len(entries),
                "corrections": [
                    {
                        "id": entry.id,
                        "audio_hash": entry.audio_hash,
                        "raw_text": entry.raw_text,
                        "corrected_text": entry.corrected_text,
                        "timestamp": entry.timestamp,
                        "use_count": entry.use_count,
                        "language": entry.language,
                        "confidence": entry.confidence,
                    }
                    for entry in entries
                ],
            }

            Path(output_path).write_text(json.dumps(data, indent=2))
            self.logger.info(f"Exported {len(entries)} corrections to {output_path}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to export corrections: {e}", exc_info=True)
            return False


def create_voice_cache(
    user_id: str = "default",
    db_path: str = "voice_cache.db",
    enable_encryption: bool = True,
    **kwargs,
) -> VoiceAdaptationCache:
    """
    Factory function to create a VoiceAdaptationCache instance

    Args:
        user_id: User identifier
        db_path: Path to database file
        enable_encryption: Enable AES256 encryption
        **kwargs: Additional arguments

    Returns:
        VoiceAdaptationCache instance
    """
    return VoiceAdaptationCache(
        db_path=db_path, user_id=user_id, enable_encryption=enable_encryption, **kwargs
    )
