"""
Encryption Service - Provides encryption and decryption functionality for sensitive data
"""
import os
import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logger = logging.getLogger('encryption_service')

class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    # Default salt for key derivation if none is provided
    _DEFAULT_SALT = b'RettLockInfoDefaultSalt'
    
    # Environment variable name for the encryption key
    _ENV_KEY_NAME = 'RETTLOCK_ENCRYPTION_KEY'
    
    @classmethod
    def _get_or_create_key(cls):
        """
        Get the encryption key from environment variable or create a new one
        
        Returns:
            bytes: The encryption key
        """
        # Check if key exists in environment
        env_key = os.environ.get(cls._ENV_KEY_NAME)
        
        if env_key:
            try:
                # Decode the key from base64
                return base64.urlsafe_b64decode(env_key)
            except Exception as e:
                logger.error(f"Error decoding encryption key: {str(e)}")
        
        # Generate a new key using PBKDF2
        salt = cls._DEFAULT_SALT
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        # Use a fallback password if environment variable is not set
        fallback_password = "RettLockInfoDefaultPassword"
        key = base64.urlsafe_b64encode(kdf.derive(fallback_password.encode()))
        
        # Log warning about using default key
        logger.warning(
            f"Using default encryption key. For production, set the {cls._ENV_KEY_NAME} "
            "environment variable with a secure key."
        )
        
        return key
    
    @classmethod
    def encrypt(cls, data):
        """
        Encrypt data using Fernet symmetric encryption
        
        Args:
            data (str): The data to encrypt
            
        Returns:
            str: Base64-encoded encrypted data
        """
        if not data:
            return None
            
        try:
            key = cls._get_or_create_key()
            f = Fernet(key)
            encrypted_data = f.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encrypting data: {str(e)}")
            # Return original data if encryption fails
            return data
    
    @classmethod
    def decrypt(cls, encrypted_data):
        """
        Decrypt data that was encrypted with the encrypt method
        
        Args:
            encrypted_data (str): Base64-encoded encrypted data
            
        Returns:
            str: The decrypted data
        """
        if not encrypted_data:
            return None
            
        try:
            key = cls._get_or_create_key()
            f = Fernet(key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = f.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            # Return original data if decryption fails
            return encrypted_data
