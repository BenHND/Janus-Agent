"""
Encryption utilities for Janus
Provides encryption/decryption for sensitive data stored in database
"""

import base64
import os
from pathlib import Path
from typing import Optional

from janus.utils.paths import get_encryption_key_path


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data

    Uses Fernet symmetric encryption from the cryptography library.
    The encryption key is derived from an environment variable or
    stored in a secure location.
    """

    def __init__(self, key: Optional[bytes] = None, key_file: Optional[str] = None):
        """
        Initialize encryption service

        Args:
            key: Encryption key (32 url-safe base64-encoded bytes)
            key_file: Path to file containing encryption key
        """
        self._fernet = None
        self._key = None

        # Try to initialize Fernet cipher
        try:
            from cryptography.fernet import Fernet

            self._Fernet = Fernet

            # Get or create encryption key
            if key:
                self._key = key
            elif key_file:
                self._key = self._load_key_from_file(key_file)
            else:
                # Try environment variable
                env_key = os.environ.get("SPECTRA_ENCRYPTION_KEY")
                if env_key:
                    self._key = env_key.encode()
                else:
                    # Try default key file location
                    default_key_file = self._get_default_key_path()
                    if default_key_file.exists():
                        self._key = self._load_key_from_file(str(default_key_file))
                    else:
                        # Generate and save new key
                        self._key = self._generate_and_save_key(str(default_key_file))

            # Initialize Fernet cipher
            self._fernet = Fernet(self._key)
            self._available = True

        except ImportError:
            # cryptography not installed
            self._available = False
            self._fernet = None
        except Exception as e:
            # Other initialization errors
            self._available = False
            self._fernet = None
            import warnings

            warnings.warn(f"Encryption service initialization failed: {e}. Encryption disabled.")

    @property
    def available(self) -> bool:
        """Check if encryption is available"""
        return self._available and self._fernet is not None

    def encrypt(self, data: str) -> Optional[str]:
        """
        Encrypt a string

        Args:
            data: Plain text string to encrypt

        Returns:
            Encrypted data as base64 string, or None if encryption unavailable
        """
        if not self.available or not data:
            return data

        try:
            encrypted_bytes = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception:
            # If encryption fails, return original data
            # This ensures the system continues to work even if encryption breaks
            return data

    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt a string

        Args:
            encrypted_data: Encrypted data as base64 string

        Returns:
            Decrypted plain text string, or None if decryption fails
        """
        if not self.available or not encrypted_data:
            return encrypted_data

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception:
            # If decryption fails, return original data
            # This handles cases where data wasn't encrypted
            return encrypted_data

    def encrypt_dict(self, data: dict, sensitive_keys: set) -> dict:
        """
        Encrypt sensitive fields in a dictionary

        Args:
            data: Dictionary with data to encrypt
            sensitive_keys: Set of keys that should be encrypted

        Returns:
            Dictionary with sensitive fields encrypted
        """
        if not self.available or not data:
            return data

        encrypted = data.copy()
        for key in sensitive_keys:
            if key in encrypted and isinstance(encrypted[key], str):
                encrypted[key] = self.encrypt(encrypted[key])

        return encrypted

    def decrypt_dict(self, data: dict, sensitive_keys: set) -> dict:
        """
        Decrypt sensitive fields in a dictionary

        Args:
            data: Dictionary with encrypted data
            sensitive_keys: Set of keys that should be decrypted

        Returns:
            Dictionary with sensitive fields decrypted
        """
        if not self.available or not data:
            return data

        decrypted = data.copy()
        for key in sensitive_keys:
            if key in decrypted and isinstance(decrypted[key], str):
                decrypted[key] = self.decrypt(decrypted[key])

        return decrypted

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new encryption key

        Returns:
            New encryption key as bytes
        """
        from cryptography.fernet import Fernet

        return Fernet.generate_key()

    def _load_key_from_file(self, key_file: str) -> bytes:
        """Load encryption key from file"""
        with open(key_file, "rb") as f:
            return f.read()

    def _get_default_key_path(self) -> Path:
        """Get default path for encryption key file"""
        # Use cross-platform data directory
        return get_encryption_key_path(ensure_dir_exists=True)

    def _generate_and_save_key(self, key_file: str) -> bytes:
        """Generate a new key and save it to file"""
        key = self.generate_key()

        # Ensure directory exists
        key_path = Path(key_file)
        key_path.parent.mkdir(parents=True, exist_ok=True)

        # Save key with restricted permissions
        with open(key_file, "wb") as f:
            f.write(key)

        # Set file permissions to owner read/write only (Unix)
        try:
            os.chmod(key_file, 0o600)
        except (AttributeError, NotImplementedError) as e:
            # Windows doesn't support chmod - this is expected
            pass
        except Exception as e:
            # Log other errors but don't fail
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to set file permissions on key file: {e}", exc_info=True)

        return key

    def rotate_key(self, new_key: bytes):
        """
        Rotate encryption key

        Note: This only updates the key used for new encryptions.
        Existing encrypted data will need to be re-encrypted with the new key.

        Args:
            new_key: New encryption key
        """
        if not self.available:
            return

        self._key = new_key
        self._fernet = self._Fernet(new_key)


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get or create the global encryption service instance

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_value(value: str) -> Optional[str]:
    """
    Convenience function to encrypt a value

    Args:
        value: Plain text value

    Returns:
        Encrypted value or original if encryption unavailable
    """
    service = get_encryption_service()
    return service.encrypt(value)


def decrypt_value(encrypted_value: str) -> Optional[str]:
    """
    Convenience function to decrypt a value

    Args:
        encrypted_value: Encrypted value

    Returns:
        Decrypted value or original if decryption fails
    """
    service = get_encryption_service()
    return service.decrypt(encrypted_value)
