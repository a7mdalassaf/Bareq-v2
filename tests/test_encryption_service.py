"""
Tests for the Encryption Service
"""
import unittest
import os
import sys
import base64
from unittest.mock import patch, MagicMock

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.encryption_service import EncryptionService

class TestEncryptionService(unittest.TestCase):
    """Test cases for the Encryption Service"""
    
    def setUp(self):
        """Set up test environment"""
        # Generate a test key
        self.test_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        
        # Save original environment
        self.original_env = os.environ.copy()
        
        # Set test environment variable
        os.environ['RETTLOCK_ENCRYPTION_KEY'] = self.test_key
    
    def tearDown(self):
        """Clean up after tests"""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_encrypt_decrypt(self):
        """Test encrypting and decrypting a value"""
        # Test data
        original_value = "sensitive_data_123"
        
        # Encrypt the value
        encrypted_value = EncryptionService.encrypt(original_value)
        
        # Check that the encrypted value is different from the original
        self.assertNotEqual(original_value, encrypted_value)
        
        # Decrypt the value
        decrypted_value = EncryptionService.decrypt(encrypted_value)
        
        # Check that the decrypted value matches the original
        self.assertEqual(original_value, decrypted_value)
    
    def test_encrypt_decrypt_empty_string(self):
        """Test encrypting and decrypting an empty string"""
        # Test data
        original_value = ""
        
        # Encrypt the value
        encrypted_value = EncryptionService.encrypt(original_value)
        
        # Check that the encrypted value is not empty
        self.assertNotEqual(original_value, encrypted_value)
        
        # Decrypt the value
        decrypted_value = EncryptionService.decrypt(encrypted_value)
        
        # Check that the decrypted value is an empty string
        self.assertEqual(original_value, decrypted_value)
    
    def test_encrypt_decrypt_special_characters(self):
        """Test encrypting and decrypting a string with special characters"""
        # Test data with special characters
        original_value = "!@#$%^&*()_+{}[]|\\:;\"'<>,.?/~`"
        
        # Encrypt the value
        encrypted_value = EncryptionService.encrypt(original_value)
        
        # Check that the encrypted value is different from the original
        self.assertNotEqual(original_value, encrypted_value)
        
        # Decrypt the value
        decrypted_value = EncryptionService.decrypt(encrypted_value)
        
        # Check that the decrypted value matches the original
        self.assertEqual(original_value, decrypted_value)
    
    def test_encrypt_decrypt_long_string(self):
        """Test encrypting and decrypting a long string"""
        # Generate a long string (10KB)
        original_value = "x" * 10240
        
        # Encrypt the value
        encrypted_value = EncryptionService.encrypt(original_value)
        
        # Check that the encrypted value is different from the original
        self.assertNotEqual(original_value, encrypted_value)
        
        # Decrypt the value
        decrypted_value = EncryptionService.decrypt(encrypted_value)
        
        # Check that the decrypted value matches the original
        self.assertEqual(original_value, decrypted_value)
    
    def test_default_key_warning(self):
        """Test that a warning is logged when using the default key"""
        # Remove the environment variable to force use of default key
        if 'RETTLOCK_ENCRYPTION_KEY' in os.environ:
            del os.environ['RETTLOCK_ENCRYPTION_KEY']
        
        # Mock the logger
        with patch('services.encryption_service.logger') as mock_logger:
            # Encrypt a value to trigger the warning
            EncryptionService.encrypt("test_value")
            
            # Check that a warning was logged
            mock_logger.warning.assert_called_with(
                "Using default encryption key. Set RETTLOCK_ENCRYPTION_KEY environment variable for production."
            )
    
    def test_invalid_encrypted_value(self):
        """Test decrypting an invalid encrypted value"""
        # Try to decrypt an invalid value
        with self.assertRaises(Exception):
            EncryptionService.decrypt("not_a_valid_encrypted_value")
    
    def test_key_derivation(self):
        """Test that the key is properly derived from the environment variable"""
        # Set a known key
        known_key = "knownkey123knownkey123knownkey123knownk="
        os.environ['RETTLOCK_ENCRYPTION_KEY'] = known_key
        
        # Get the derived key
        derived_key = EncryptionService._get_key()
        
        # Check that the derived key is not None
        self.assertIsNotNone(derived_key)
        
        # Encrypt with the derived key
        original_value = "test_value"
        encrypted_value = EncryptionService.encrypt(original_value)
        
        # Change the key
        os.environ['RETTLOCK_ENCRYPTION_KEY'] = "differentkey123differentkey123differentk="
        
        # Try to decrypt with the new key (should fail)
        with self.assertRaises(Exception):
            EncryptionService.decrypt(encrypted_value)
        
        # Restore the original key
        os.environ['RETTLOCK_ENCRYPTION_KEY'] = known_key
        
        # Decrypt with the original key (should succeed)
        decrypted_value = EncryptionService.decrypt(encrypted_value)
        self.assertEqual(original_value, decrypted_value)

if __name__ == '__main__':
    unittest.main()
