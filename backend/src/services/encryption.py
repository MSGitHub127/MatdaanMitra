from cryptography.fernet import Fernet
from typing import Optional
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting sensitive data like EPIC numbers."""

    def __init__(self):
        # Lazy init — Fernet crashes on empty key, which is the default in .env
        self._fernet: Optional[Fernet] = None

    def _get_fernet(self) -> Fernet:
        if self._fernet is None:
            key = settings.fernet_key
            if not key:
                raise ValueError(
                    "FERNET_KEY is not set in backend/.env. "
                    "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
            self._fernet = Fernet(key.encode())
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext and return ciphertext."""
        try:
            return self._get_fernet().encrypt(plaintext.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, ciphertext: str) -> Optional[str]:
        """Decrypt ciphertext and return plaintext."""
        try:
            return self._get_fernet().decrypt(ciphertext.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return None


# Singleton — safe to import even without FERNET_KEY configured
encryption_service = EncryptionService()