"""
Encryption Module for Smart Clinic Management System.

This module provides secure encryption/decryption services following
best practices for key management, rotation, and validation.

IMPORTANT: ENCRYPTION_KEY must be set in environment for production.
Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, String
from typing import Optional
from functools import lru_cache
import os
import base64
import logging

logger = logging.getLogger(__name__)


# ============================================
# CUSTOM EXCEPTIONS
# ============================================

class EncryptionError(Exception):
    """Base exception for encryption operations."""
    pass


class InvalidKeyError(EncryptionError):
    """Raised when encryption key is invalid."""
    pass


class KeyNotConfiguredError(EncryptionError):
    """Raised when encryption key is not configured."""
    pass


class KeyRotationError(EncryptionError):
    """Raised when key rotation fails."""
    pass


class DecryptionError(EncryptionError):
    """Raised when decryption fails."""
    pass


# ============================================
# ENCRYPTION MANAGER
# ============================================

class EncryptionManager:
    """
    Manages all encryption operations for the application.
    
    Features:
    - Key validation
    - Encryption/decryption
    - Key rotation support
    - Graceful fallback for legacy data
    
    Usage:
        manager = EncryptionManager()
        encrypted = manager.encrypt("sensitive data")
        decrypted = manager.decrypt(encrypted)
    """
    
    def __init__(self, key: Optional[str] = None):
        """
        Initialize the encryption manager.
        
        Args:
            key: Optional encryption key. If not provided, reads from ENCRYPTION_KEY env var.
            
        Raises:
            KeyNotConfiguredError: If no key is provided and ENCRYPTION_KEY is not set (in production).
        """
        self._key = key or os.getenv("ENCRYPTION_KEY")
        self._environment = os.getenv("ENVIRONMENT", "development")
        self._fernet: Optional[Fernet] = None
        
        # Validate and initialize
        if self._key:
            if not self.validate_key(self._key):
                raise InvalidKeyError("Invalid encryption key format. Must be 32-byte base64 encoded.")
            self._fernet = Fernet(self._key.encode() if isinstance(self._key, str) else self._key)
            logger.info("Encryption manager initialized successfully")
        elif self._environment == "production":
            raise KeyNotConfiguredError(
                "CRITICAL: ENCRYPTION_KEY is not set in production environment. "
                "Application cannot start without encryption key."
            )
        else:
            # Development mode: generate temporary key with warning
            logger.warning(
                "⚠️ ENCRYPTION_KEY not set. Using temporary key for development. "
                "DO NOT use in production!"
            )
            temp_key = Fernet.generate_key()
            self._key = temp_key.decode()
            self._fernet = Fernet(temp_key)
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.
        
        Returns:
            Base64-encoded 32-byte key string.
        """
        return Fernet.generate_key().decode()
    
    @staticmethod
    def validate_key(key: str) -> bool:
        """
        Validate that a key is properly formatted for Fernet.
        
        Args:
            key: The key to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        try:
            # Fernet keys must be 32 bytes, base64-encoded (44 chars with padding)
            if not key or len(key) != 44:
                return False
            
            # Try to decode and create Fernet instance
            decoded = base64.urlsafe_b64decode(key.encode())
            if len(decoded) != 32:
                return False
            
            Fernet(key.encode())
            return True
        except Exception:
            return False
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string value.
        
        Args:
            data: The plaintext string to encrypt.
            
        Returns:
            Encrypted string (base64 encoded).
            
        Raises:
            EncryptionError: If encryption fails.
        """
        if not self._fernet:
            raise EncryptionError("Encryption manager not initialized")
        
        if data is None:
            return None
        
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            encrypted = self._fernet.encrypt(data)
            return encrypted.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}") from e
    
    def decrypt(self, encrypted_data: str, allow_plaintext_fallback: bool = True) -> str:
        """
        Decrypt an encrypted string value.
        
        Args:
            encrypted_data: The encrypted string to decrypt.
            allow_plaintext_fallback: If True, returns data as-is if decryption fails
                                     (useful for legacy/migration data).
            
        Returns:
            Decrypted plaintext string.
            
        Raises:
            DecryptionError: If decryption fails and fallback is disabled.
        """
        if not self._fernet:
            raise EncryptionError("Encryption manager not initialized")
        
        if encrypted_data is None:
            return None
        
        try:
            decrypted = self._fernet.decrypt(encrypted_data.encode('utf-8'))
            return decrypted.decode('utf-8')
        except InvalidToken:
            if allow_plaintext_fallback:
                # Graceful fallback for legacy/plain-text data during migration
                logger.debug("Decryption failed, returning as plaintext (legacy data)")
                return encrypted_data
            raise DecryptionError("Failed to decrypt data. Invalid token or corrupted data.")
        except Exception as e:
            if allow_plaintext_fallback:
                return encrypted_data
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt data: {e}") from e
    
    def rotate_key(self, new_key: str, data_list: list[str]) -> list[str]:
        """
        Rotate encryption key by re-encrypting data with new key.
        
        Args:
            new_key: The new encryption key to use.
            data_list: List of encrypted strings to re-encrypt.
            
        Returns:
            List of re-encrypted strings with new key.
            
        Raises:
            KeyRotationError: If rotation fails.
        """
        if not self.validate_key(new_key):
            raise KeyRotationError("New key is invalid")
        
        try:
            new_fernet = Fernet(new_key.encode())
            rotated = []
            
            for encrypted_data in data_list:
                # Decrypt with old key
                plaintext = self.decrypt(encrypted_data, allow_plaintext_fallback=False)
                # Encrypt with new key
                new_encrypted = new_fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')
                rotated.append(new_encrypted)
            
            logger.info(f"Successfully rotated {len(rotated)} encrypted values")
            return rotated
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise KeyRotationError(f"Failed to rotate encryption key: {e}") from e
    
    @property
    def is_configured(self) -> bool:
        """Check if encryption is properly configured."""
        return self._fernet is not None


# ============================================
# SINGLETON INSTANCE
# ============================================

@lru_cache(maxsize=1)
def get_encryption_manager() -> EncryptionManager:
    """Get singleton encryption manager instance."""
    return EncryptionManager()


# ============================================
# SQLALCHEMY TYPE DECORATOR
# ============================================

class EncryptedString(TypeDecorator):
    """
    SQLAlchemy type that encrypts data on write and decrypts on read.
    
    Usage:
        class Patient(Base):
            medical_notes = Column(EncryptedString, nullable=True)
    """
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Encrypt on insert/update."""
        if value is None:
            return None
        try:
            manager = get_encryption_manager()
            return manager.encrypt(value)
        except Exception as e:
            logger.error(f"Failed to encrypt field: {e}")
            # In dev mode, allow plaintext fallback
            if os.getenv("ENVIRONMENT") != "production":
                return value
            raise

    def process_result_value(self, value, dialect):
        """Decrypt on select."""
        if value is None:
            return None
        try:
            manager = get_encryption_manager()
            return manager.decrypt(value, allow_plaintext_fallback=True)
        except Exception as e:
            logger.error(f"Failed to decrypt field: {e}")
            # Graceful fallback for legacy data
            return value


# ============================================
# BACKWARD COMPATIBILITY
# ============================================

# Legacy support: Create encryption manager and fernet for existing code
try:
    _manager = get_encryption_manager()
    fernet = _manager._fernet
    ENC_KEY = _manager._key
except Exception as e:
    logger.warning(f"Could not initialize default encryption: {e}")
    fernet = None
    ENC_KEY = None
