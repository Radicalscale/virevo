"""
API Key Encryption/Decryption Utilities
Uses Fernet (symmetric encryption) to secure API keys at rest
"""
import os
import logging
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Get or generate encryption key from environment
def get_encryption_key() -> bytes:
    """
    Get encryption key from environment or generate one
    In production, this should be stored securely (e.g., AWS Secrets Manager)
    """
    key_str = os.environ.get('ENCRYPTION_KEY')
    
    if not key_str:
        # Generate from a password or use a default (NOT SECURE FOR PRODUCTION)
        password = os.environ.get('JWT_SECRET_KEY', 'default-secret-key-change-in-production').encode()
        salt = b'api_key_encryption_salt'  # Should be random and stored securely
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    return key_str.encode()

# Initialize Fernet cipher
_cipher = None

def get_cipher() -> Fernet:
    """Get or create Fernet cipher instance"""
    global _cipher
    if _cipher is None:
        _cipher = Fernet(get_encryption_key())
    return _cipher

def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key for storage
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Encrypted API key (base64 encoded)
    """
    try:
        cipher = get_cipher()
        encrypted = cipher.encrypt(api_key.encode())
        return encrypted.decode()
    except Exception as e:
        logger.error(f"Error encrypting API key: {e}")
        # Fallback: store as-is (not recommended)
        return api_key

def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key for use
    
    Args:
        encrypted_key: Encrypted API key (base64 encoded)
        
    Returns:
        Plain text API key
    """
    try:
        cipher = get_cipher()
        decrypted = cipher.decrypt(encrypted_key.encode())
        return decrypted.decode()
    except Exception as e:
        # Key might not be encrypted (legacy keys)
        logger.warning(f"Failed to decrypt key, assuming unencrypted: {e}")
        return encrypted_key

def is_encrypted(key: str) -> bool:
    """
    Check if a key appears to be encrypted
    
    Args:
        key: Potential encrypted key
        
    Returns:
        True if likely encrypted
    """
    try:
        # Fernet tokens are base64 and start with 'gAAAAA'
        cipher = get_cipher()
        cipher.decrypt(key.encode())
        return True
    except:
        return False
