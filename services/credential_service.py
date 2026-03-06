"""
Credential Service - Manages API credentials stored in the database
"""
import logging
from models import db, ApiCredential
from services.encryption_service import EncryptionService
from services.audit_service import AuditService
from flask import current_app

# Configure logging
logger = logging.getLogger('credential_service')

class CredentialService:
    """Service for managing API credentials stored in the database"""
    
    @staticmethod
    def get_credential(provider, credential_type, credential_key, default=None):
        """
        Get a credential value from the database
        Falls back to default if not found
        
        Args:
            provider (str): Service provider (e.g., 'tuya', 'ttlock')
            credential_type (str): Type of credential (e.g., 'api', 'account')
            credential_key (str): Specific key name (e.g., 'client_id', 'client_secret')
            default (str, optional): Default value if credential not found
            
        Returns:
            str: The credential value or default
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.warning(f"No application context available for retrieving credential {provider}.{credential_type}.{credential_key}")
                return default
                
            with current_app.app_context():
                credential = ApiCredential.query.filter_by(
                    provider=provider,
                    credential_type=credential_type,
                    credential_key=credential_key,
                    is_active=True
                ).first()
                
                if credential:
                    # Decrypt the value if it's encrypted
                    if credential.is_encrypted:
                        return EncryptionService.decrypt(credential.credential_value)
                    return credential.credential_value
                
                if default:
                    logger.warning(f"Credential {provider}.{credential_type}.{credential_key} not found, using default")
                    return default
                    
                logger.error(f"Credential {provider}.{credential_type}.{credential_key} not found and no default provided")
                return None
            
        except Exception as e:
            logger.error(f"Error retrieving credential {provider}.{credential_type}.{credential_key}: {str(e)}")
            return default
    
    @staticmethod
    def set_credential(provider, credential_type, credential_key, credential_value, description=None, encrypt=True):
        """
        Set a credential in the database
        
        Args:
            provider (str): Service provider (e.g., 'tuya', 'ttlock')
            credential_type (str): Type of credential (e.g., 'api', 'account')
            credential_key (str): Specific key name (e.g., 'client_id', 'client_secret')
            credential_value (str): The actual credential value
            description (str, optional): Human-readable description
            encrypt (bool): Whether to encrypt the credential value
            
        Returns:
            ApiCredential: The created or updated credential object
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.error(f"No application context available for setting credential {provider}.{credential_type}.{credential_key}")
                raise RuntimeError("No application context available")
                
            with current_app.app_context():
                # Encrypt the value if requested
                stored_value = credential_value
                if encrypt:
                    stored_value = EncryptionService.encrypt(credential_value)
                
                # Check if credential already exists
                credential = ApiCredential.query.filter_by(
                    provider=provider,
                    credential_type=credential_type,
                    credential_key=credential_key
                ).first()
                
                action = 'update' if credential else 'create'
                
                if credential:
                    # Update existing
                    credential.credential_value = stored_value
                    credential.is_encrypted = encrypt
                    if description:
                        credential.description = description
                    credential.is_active = True
                    logger.info(f"Updated credential {provider}.{credential_type}.{credential_key}")
                else:
                    # Create new
                    credential = ApiCredential(
                        provider=provider,
                        credential_type=credential_type,
                        credential_key=credential_key,
                        credential_value=stored_value,
                        is_encrypted=encrypt,
                        description=description,
                        is_active=True
                    )
                    db.session.add(credential)
                    logger.info(f"Created credential {provider}.{credential_type}.{credential_key}")
                
                db.session.commit()
                
                # Log the action
                AuditService.log_action(
                    action,
                    'credential',
                    credential.id,
                    f"{provider}.{credential_type}.{credential_key}",
                    {
                        'provider': provider,
                        'credential_type': credential_type,
                        'credential_key': credential_key,
                        'description': description,
                        'is_encrypted': encrypt
                    }
                )
                
                return credential
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error setting credential {provider}.{credential_type}.{credential_key}: {str(e)}")
            raise
    
    @staticmethod
    def deactivate_credential(provider, credential_type, credential_key):
        """
        Deactivate a credential (set is_active=False)
        
        Args:
            provider (str): Service provider (e.g., 'tuya', 'ttlock')
            credential_type (str): Type of credential (e.g., 'api', 'account')
            credential_key (str): Specific key name (e.g., 'client_id', 'client_secret')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.error(f"No application context available for deactivating credential {provider}.{credential_type}.{credential_key}")
                return False
                
            with current_app.app_context():
                credential = ApiCredential.query.filter_by(
                    provider=provider,
                    credential_type=credential_type,
                    credential_key=credential_key
                ).first()
                
                if credential:
                    credential.is_active = False
                    db.session.commit()
                    logger.info(f"Deactivated credential {provider}.{credential_type}.{credential_key}")
                    
                    # Log the action
                    AuditService.log_action(
                        'deactivate',
                        'credential',
                        credential.id,
                        f"{provider}.{credential_type}.{credential_key}",
                        {
                            'provider': provider,
                            'credential_type': credential_type,
                            'credential_key': credential_key
                        }
                    )
                    
                    return True
                
                logger.warning(f"Credential {provider}.{credential_type}.{credential_key} not found for deactivation")
                return False
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deactivating credential {provider}.{credential_type}.{credential_key}: {str(e)}")
            return False
    
    @staticmethod
    def get_all_credentials(include_values=False):
        """
        Get all credentials, optionally including values
        
        Args:
            include_values (bool): Whether to include the actual credential values
            
        Returns:
            list: List of credential dictionaries
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.error("No application context available for retrieving all credentials")
                return []
                
            with current_app.app_context():
                credentials = ApiCredential.query.all()
                result = []
                for cred in credentials:
                    cred_dict = cred.to_dict(include_value=include_values)
                    if include_values and cred.is_encrypted:
                        cred_dict['credential_value'] = EncryptionService.decrypt(cred.credential_value)
                    result.append(cred_dict)
                return result
        except Exception as e:
            logger.error(f"Error retrieving all credentials: {str(e)}")
            return []
    
    @staticmethod
    def get_credential_by_id(credential_id, include_value=True):
        """
        Get a specific credential by ID
        
        Args:
            credential_id (int): The credential ID
            include_value (bool): Whether to include the actual credential value
            
        Returns:
            dict: Credential dictionary or None
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.error(f"No application context available for retrieving credential by ID {credential_id}")
                return None
                
            with current_app.app_context():
                credential = ApiCredential.query.get(credential_id)
                if credential:
                    cred_dict = credential.to_dict(include_value=include_value)
                    if include_value and credential.is_encrypted:
                        cred_dict['credential_value'] = EncryptionService.decrypt(credential.credential_value)
                    return cred_dict
                return None
        except Exception as e:
            logger.error(f"Error retrieving credential by ID {credential_id}: {str(e)}")
            return None
    
    @staticmethod
    def delete_credential(credential_id):
        """
        Delete a credential by ID
        
        Args:
            credential_id (int): The credential ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.error(f"No application context available for deleting credential by ID {credential_id}")
                return False
                
            with current_app.app_context():
                credential = ApiCredential.query.get(credential_id)
                if credential:
                    # Store credential info for audit log
                    cred_info = {
                        'provider': credential.provider,
                        'credential_type': credential.credential_type,
                        'credential_key': credential.credential_key
                    }
                    
                    db.session.delete(credential)
                    db.session.commit()
                    logger.info(f"Deleted credential ID {credential_id}")
                    
                    # Log the action
                    AuditService.log_action(
                        'delete',
                        'credential',
                        credential_id,
                        f"{cred_info['provider']}.{cred_info['credential_type']}.{cred_info['credential_key']}",
                        cred_info
                    )
                    
                    return True
                
                logger.warning(f"Credential ID {credential_id} not found for deletion")
                return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting credential ID {credential_id}: {str(e)}")
            return False

    @staticmethod
    def get_all_credential_types_by_provider(provider):
        """
        Get all credential types for a specific provider
        
        Args:
            provider (str): Service provider (e.g., 'tuya', 'ttlock')
            
        Returns:
            list: List of credential types
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.warning(f"No application context available for retrieving credential types for provider {provider}")
                return []
                
            with current_app.app_context():
                # Query for all unique credential_type values for this provider
                credentials = ApiCredential.query.filter_by(
                    provider=provider,
                    is_active=True
                ).with_entities(ApiCredential.credential_type).distinct().all()
                
                # Extract the credential_type values from the query result
                credential_types = [cred[0] for cred in credentials]
                
                logger.info(f"Retrieved {len(credential_types)} credential types for provider {provider}")
                return credential_types
            
        except Exception as e:
            logger.error(f"Error retrieving credential types for provider {provider}: {str(e)}")
            return []

    @staticmethod
    def delete_credentials_by_type(provider, credential_type):
        """
        Delete all credentials for a specific provider and credential type
        
        Args:
            provider (str): Service provider (e.g., 'tuya', 'ttlock')
            credential_type (str): Type of credential (e.g., 'api', 'account1')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.warning(f"No application context available for deleting credentials for {provider}/{credential_type}")
                return False
                
            with current_app.app_context():
                # Query for all credentials matching the provider and type
                credentials = ApiCredential.query.filter_by(
                    provider=provider,
                    credential_type=credential_type
                ).all()
                
                if not credentials:
                    logger.warning(f"No credentials found for {provider}/{credential_type}")
                    return True
                
                # Delete all matching credentials
                for credential in credentials:
                    db.session.delete(credential)
                
                # Commit the changes
                db.session.commit()
                
                logger.info(f"Deleted {len(credentials)} credentials for {provider}/{credential_type}")
                
                # Log the credential deletion for audit purposes
                try:
                    from services.audit_service import AuditService
                    AuditService.log_credential_action(
                        'delete_by_type',
                        f"Deleted all credentials for {provider}/{credential_type}"
                    )
                except ImportError:
                    # AuditService not available, just log
                    logger.info(f"Audit service not available, credential deletion not logged")
                
                return True
                
        except Exception as e:
            logger.error(f"Error deleting credentials for {provider}/{credential_type}: {str(e)}")
            db.session.rollback()
            return False
