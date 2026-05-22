from cryptography.fernet import Fernet
from typing import Optional
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting sensitive data like EPIC numbers."""

    def __init__(self):
        self.fernet = Fernet(settings.fernet_key.encode())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext and return ciphertext."""
        try:
            encrypted = self.fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, ciphertext: str) -> Optional[str]:
        """Decrypt ciphertext and return plaintext."""
        try:
            decrypted = self.fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return None


# Singleton instance
encryption_service = EncryptionService()
