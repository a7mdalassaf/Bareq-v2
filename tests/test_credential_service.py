"""
Tests for the Credential Service
"""
import unittest
import os
from unittest.mock import patch, MagicMock
import sys
import tempfile
import base64

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, ApiCredential
from services.credential_service import CredentialService
from services.encryption_service import EncryptionService
from app import create_app

class TestCredentialService(unittest.TestCase):
    """Test cases for the Credential Service"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Set test config
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SECRET_KEY': 'test_secret_key',
            'RETTLOCK_ENCRYPTION_KEY': base64.urlsafe_b64encode(os.urandom(32)).decode()
        }
        
        # Create app with test config
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        
        # Create application context
        with self.app.app_context():
            # Create tables
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_set_and_get_credential(self):
        """Test setting and retrieving a credential"""
        with self.app.app_context():
            # Set a credential
            provider = 'test_provider'
            cred_type = 'test_type'
            cred_key = 'test_key'
            cred_value = 'test_value'
            description = 'Test credential'
            
            # Set the credential
            CredentialService.set_credential(
                provider, cred_type, cred_key, cred_value, 
                description=description, encrypt=True
            )
            
            # Get the credential
            retrieved_value = CredentialService.get_credential(
                provider, cred_type, cred_key
            )
            
            # Check that the retrieved value matches the original
            self.assertEqual(cred_value, retrieved_value)
            
            # Check that the credential was stored in the database
            credential = ApiCredential.query.filter_by(
                provider=provider,
                credential_type=cred_type,
                credential_key=cred_key
            ).first()
            
            self.assertIsNotNone(credential)
            self.assertEqual(credential.description, description)
            self.assertTrue(credential.is_encrypted)
            self.assertNotEqual(credential.credential_value, cred_value)  # Should be encrypted
    
    def test_update_credential(self):
        """Test updating an existing credential"""
        with self.app.app_context():
            # Set initial credential
            provider = 'test_provider'
            cred_type = 'test_type'
            cred_key = 'test_key'
            cred_value = 'initial_value'
            
            CredentialService.set_credential(
                provider, cred_type, cred_key, cred_value
            )
            
            # Update the credential
            new_value = 'updated_value'
            new_description = 'Updated description'
            
            CredentialService.set_credential(
                provider, cred_type, cred_key, new_value,
                description=new_description
            )
            
            # Get the updated credential
            retrieved_value = CredentialService.get_credential(
                provider, cred_type, cred_key
            )
            
            # Check that the retrieved value matches the updated value
            self.assertEqual(new_value, retrieved_value)
            
            # Check that the credential was updated in the database
            credential = ApiCredential.query.filter_by(
                provider=provider,
                credential_type=cred_type,
                credential_key=cred_key
            ).first()
            
            self.assertEqual(credential.description, new_description)
    
    def test_get_nonexistent_credential(self):
        """Test getting a credential that doesn't exist"""
        with self.app.app_context():
            # Try to get a nonexistent credential
            default_value = 'default_value'
            retrieved_value = CredentialService.get_credential(
                'nonexistent', 'nonexistent', 'nonexistent',
                default=default_value
            )
            
            # Check that the default value was returned
            self.assertEqual(retrieved_value, default_value)
    
    def test_deactivate_credential(self):
        """Test deactivating a credential"""
        with self.app.app_context():
            # Set a credential
            provider = 'test_provider'
            cred_type = 'test_type'
            cred_key = 'test_key'
            cred_value = 'test_value'
            
            CredentialService.set_credential(
                provider, cred_type, cred_key, cred_value
            )
            
            # Deactivate the credential
            result = CredentialService.deactivate_credential(
                provider, cred_type, cred_key
            )
            
            # Check that deactivation was successful
            self.assertTrue(result)
            
            # Check that the credential is inactive in the database
            credential = ApiCredential.query.filter_by(
                provider=provider,
                credential_type=cred_type,
                credential_key=cred_key
            ).first()
            
            self.assertFalse(credential.is_active)
            
            # Try to get the deactivated credential
            retrieved_value = CredentialService.get_credential(
                provider, cred_type, cred_key
            )
            
            # Check that None was returned (deactivated credentials aren't returned)
            self.assertIsNone(retrieved_value)
    
    def test_delete_credential(self):
        """Test deleting a credential"""
        with self.app.app_context():
            # Set a credential
            provider = 'test_provider'
            cred_type = 'test_type'
            cred_key = 'test_key'
            cred_value = 'test_value'
            
            credential = CredentialService.set_credential(
                provider, cred_type, cred_key, cred_value
            )
            
            # Delete the credential
            result = CredentialService.delete_credential(credential.id)
            
            # Check that deletion was successful
            self.assertTrue(result)
            
            # Check that the credential is no longer in the database
            credential = ApiCredential.query.filter_by(
                provider=provider,
                credential_type=cred_type,
                credential_key=cred_key
            ).first()
            
            self.assertIsNone(credential)
    
    @patch('services.encryption_service.EncryptionService.encrypt')
    @patch('services.encryption_service.EncryptionService.decrypt')
    def test_encryption_integration(self, mock_decrypt, mock_encrypt):
        """Test integration with encryption service"""
        # Set up mocks
        mock_encrypt.return_value = 'encrypted_value'
        mock_decrypt.return_value = 'decrypted_value'
        
        with self.app.app_context():
            # Set a credential with encryption
            provider = 'test_provider'
            cred_type = 'test_type'
            cred_key = 'test_key'
            cred_value = 'test_value'
            
            CredentialService.set_credential(
                provider, cred_type, cred_key, cred_value,
                encrypt=True
            )
            
            # Check that encrypt was called
            mock_encrypt.assert_called_once_with(cred_value)
            
            # Get the credential
            CredentialService.get_credential(
                provider, cred_type, cred_key
            )
            
            # Check that decrypt was called
            mock_decrypt.assert_called_once_with('encrypted_value')
    
    def test_list_credentials(self):
        """Test listing credentials"""
        with self.app.app_context():
            # Set multiple credentials
            CredentialService.set_credential('provider1', 'type1', 'key1', 'value1')
            CredentialService.set_credential('provider1', 'type1', 'key2', 'value2')
            CredentialService.set_credential('provider2', 'type2', 'key1', 'value3')
            
            # List all credentials
            all_credentials = CredentialService.list_credentials()
            
            # Check that all credentials are returned
            self.assertEqual(len(all_credentials), 3)
            
            # List credentials by provider
            provider1_credentials = CredentialService.list_credentials(provider='provider1')
            
            # Check that only provider1 credentials are returned
            self.assertEqual(len(provider1_credentials), 2)
            for cred in provider1_credentials:
                self.assertEqual(cred.provider, 'provider1')
            
            # List credentials by type
            type1_credentials = CredentialService.list_credentials(credential_type='type1')
            
            # Check that only type1 credentials are returned
            self.assertEqual(len(type1_credentials), 2)
            for cred in type1_credentials:
                self.assertEqual(cred.credential_type, 'type1')

if __name__ == '__main__':
    unittest.main()
