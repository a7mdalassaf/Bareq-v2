import logging
import requests
import time
import hashlib
from models import db, User, Guest
from services.credential_service import CredentialService
from services.ttlock_account_manager import TTLockAccountManager
from flask import current_app, has_app_context
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ttlock_adapter')

class TTLockAdapter:
    """
    Adapter class for TTLock API integration.
    Provides a clean interface for interacting with TTLock while using the credential service.
    """
    def __init__(self):
        # Default values in case database isn't initialized yet
        #self._default_client_id = "a67f3b3552a64b0c81aa5e3b2a19dffb"
        #self._default_client_secret = "8db22fad0b66cc784b06cbddc1ccab9a"
        #self._default_base_url = os.environ.get('TTLOCK_BASE_URL', "https://euapi.ttlock.com")
        
        # Get default values from environment variables or use fallbacks
        self._default_client_id = os.environ.get('TTLOCK_CLIENT_ID', "a67f3b3552a64b0c81aa5e3b2a19dffb")
        self._default_client_secret = os.environ.get('TTLOCK_CLIENT_SECRET', "8db22fad0b66cc784b06cbddc1ccab9a")
        self._default_base_url = os.environ.get('TTLOCK_BASE_URL', "https://euapi.ttlock.com")
        
        # Default username and password
        self._default_username = ""
        self._default_password = ""
        
        # Initialize other needed attributes
        self._token = None
        self._token_expiry = 0
        
        # Initialize account manager
        self._account_manager = TTLockAccountManager()
        
        logger.info("TTLockAdapter initialized with default values")
    
    def _get_client_id(self):
        """Get TTLock client ID from credential service"""
        try:
            # Check if we're in an application context
            if current_app:
                with current_app.app_context():
                    client_id = CredentialService.get_credential(
                        'ttlock', 'api', 'client_id', 
                        default=self._default_client_id
                    )
                    logger.debug("Retrieved TTLock client_id from credential service")
                    return client_id
            else:
                logger.warning("No application context available for getting client_id")
                return self._default_client_id
        except Exception as e:
            logger.error(f"Error getting client_id: {str(e)}")
            return self._default_client_id
    
    def _get_client_secret(self):
        """Get TTLock client secret from credential service"""
        try:
            # Check if we're in an application context
            if current_app:
                with current_app.app_context():
                    client_secret = CredentialService.get_credential(
                        'ttlock', 'api', 'client_secret', 
                        default=self._default_client_secret
                    )
                    logger.debug("Retrieved TTLock client_secret from credential service")
                    return client_secret
            else:
                logger.warning("No application context available for getting client_secret")
                return self._default_client_secret
        except Exception as e:
            logger.error(f"Error getting client_secret: {str(e)}")
            return self._default_client_secret
    
    def _get_base_url(self):
        """Get TTLock API base URL from credential service"""
        try:
            # Check if we're in an application context
            if current_app:
                with current_app.app_context():
                    base_url = CredentialService.get_credential(
                        'ttlock', 'api', 'base_url', 
                        default=self._default_base_url
                    )
                    logger.debug("Retrieved TTLock base_url from credential service")
                    return base_url
            else:
                logger.warning("No application context available for getting base_url")
                return self._default_base_url
        except Exception as e:
            logger.error(f"Error getting base_url: {str(e)}")
            return self._default_base_url
    
    def _get_username(self):
        """Get TTLock account username"""
        try:
            # Try to get application context
            if current_app:
                with current_app.app_context():
                    username = CredentialService.get_credential(
                        'ttlock', 'account', 'username', 
                        default=self._default_username
                    )
                    logger.debug(f"Retrieved TTLock username from credential service")
                    if not username:
                        logger.warning("TTLock username not found in credential service")
                    return username
            else:
                logger.warning("No application context available for getting username")
                return self._default_username
        except Exception as e:
            logger.error(f"Error getting username: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._default_username
    
    def _get_password(self):
        """Get TTLock account password"""
        try:
            # Try to get application context
            if current_app:
                with current_app.app_context():
                    password = CredentialService.get_credential(
                        'ttlock', 'account', 'password', 
                        default=self._default_password
                    )
                    logger.debug(f"Retrieved TTLock password from credential service")
                    if not password:
                        logger.warning("TTLock password not found in credential service")
                    return password
            else:
                logger.warning("No application context available for getting password")
                return self._default_password
        except Exception as e:
            logger.error(f"Error getting password: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._default_password
    
    def _get_token(self, force_refresh=False):
        """
        Get access token for TTLock API
        For backward compatibility, uses the default account
        
        Args:
            force_refresh (bool): Whether to force token refresh
            
        Returns:
            str: Access token or None if failed
        """
        # For backward compatibility, try to get token for the default account
        token = self._account_manager.get_token('account', force_refresh)
        if token:
            return token
            
        # If that fails, try the legacy method
        try:
            # Check if we have a valid token
            current_time = int(time.time())
            if not force_refresh and self._token and self._token_expiry > current_time:
                logger.debug("Using existing token")
                return self._token
            
            # Need to get a new token
            username = self._get_username()
            password = self._get_password()
            
            if not username or not password:
                logger.error("Missing username or password for TTLock API")
                return None
                
            # Create MD5 hash of password
            password_md5 = hashlib.md5(password.encode()).hexdigest()
            
            # Build request parameters
            url = f"{self._get_base_url()}/oauth2/token"
            params = {
                'clientId': self._get_client_id(),
                'clientSecret': self._get_client_secret(),
                'username': username,
                'password': password_md5,
                'grant_type': 'password'
            }
            
            # Log request details for debugging
            logger.debug(f"Requesting token with params: {params}")
            
            # Make the request
            response = requests.post(url, params=params)
            
            # Log response for debugging
            logger.debug(f"Token response: {response.status_code} {response.text}")
            
            # Check if request was successful
            if response.status_code == 200:
                result = response.json()
                if 'access_token' in result:
                    # Store token and expiry time
                    self._token = result['access_token']
                    self._token_expiry = current_time + result.get('expires_in', 7200) - 300  # Subtract 5 minutes for safety
                    logger.info("Successfully obtained token")
                    return self._token
                else:
                    logger.error(f"No access_token in response: {result}")
            else:
                logger.error(f"Failed to get token: {response.status_code} {response.text}")
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def get_lock_list(self, use_cache=True):
        """
        Get list of all locks from all accounts
        
        Args:
            use_cache (bool): Whether to use the lock cache if valid
            
        Returns:
            list: List of locks or empty list if failed
        """
        try:
            # Get locks from all accounts
            locks = self._account_manager.get_all_locks(use_cache=use_cache)
            
            if locks:
                logger.info(f"Retrieved {len(locks)} locks from all accounts")
                return locks
            else:
                logger.warning("No locks found or error connecting to TTLock API")
                return []
                
        except Exception as e:
            logger.error(f"Error getting lock list: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def get_lock_details(self, lock_id):
        """
        Get details for a specific lock
        
        Args:
            lock_id (str): Lock ID
            
        Returns:
            dict: Lock details or None if not found
        """
        try:
            # Use the account manager to get lock details
            lock_details = self._account_manager.get_lock_details(lock_id)
            
            if lock_details:
                logger.info(f"Retrieved details for lock {lock_id}")
                return lock_details
            else:
                logger.warning(f"Lock {lock_id} not found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting lock details for lock {lock_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def get_lock_status(self, lock_id):
        """
        Get status of a specific lock
        
        Args:
            lock_id (str): Lock identifier
            
        Returns:
            dict: Lock status or empty dict if failed
        """
        # Find which account this lock belongs to
        account_id = self._account_manager.find_account_for_lock(lock_id)
        if account_id:
            # Get status using the account manager
            status = self._account_manager.get_lock_status(account_id, lock_id)
            if status:
                return status
        
        # If that fails, try the legacy method
        try:
            token = self._get_token()
            if not token:
                logger.error("Failed to get token for TTLock API")
                return {}
                
            # Build the URL based on base URL format
            base_url = self._get_base_url()
            if base_url.endswith('/v3'):
                url = f"{base_url}/lock/queryOpenState"
            else:
                url = f"{base_url}/v3/lock/queryOpenState"
            params = {
                'clientId': self._get_client_id(),
                'accessToken': token,
                'lockId': lock_id,
                'date': int(time.time() * 1000)
            }
            
            # Log request details for debugging
            logger.debug(f"Requesting lock status for lock {lock_id} with params: {params}")
            
            response = requests.get(url, params=params)
            
            # Log response for debugging
            logger.debug(f"Lock status response for lock {lock_id}: {response.status_code} {response.text}")
            
            # Check if request was successful
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Retrieved status for lock {lock_id}")
                return result
            else:
                logger.error(f"Failed to get status for lock {lock_id}: {response.status_code} {response.text}")
                
            return {}
            
        except Exception as e:
            logger.error(f"Error getting status for lock {lock_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def add_account(self, account_id, username, password, client_id=None, client_secret=None, base_url=None):
        """
        Add a TTLock account to the adapter and store credentials in the database
        
        Args:
            account_id (str): Unique identifier for this account
            username (str): TTLock account username
            password (str): TTLock account password
            client_id (str, optional): TTLock API client ID
            client_secret (str, optional): TTLock API client secret
            base_url (str, optional): TTLock API base URL
            
        Returns:
            bool: True if account was added successfully, False otherwise
        """
        try:
            # Add account to the account manager
            self._account_manager.add_account(
                account_id, 
                username, 
                password, 
                client_id or self._get_client_id(), 
                client_secret or self._get_client_secret(), 
                base_url or self._get_base_url()
            )
            
            # Store credentials in the database
            if not has_app_context():
                logger.warning("No application context available for storing credentials")
                return False
                
            # Store credentials in the database
            try:
                CredentialService.set_credential(
                    'ttlock', account_id, 'username', 
                    username, 
                    f'TTLock account username for {account_id}'
                )
                CredentialService.set_credential(
                    'ttlock', account_id, 'password', 
                    password, 
                    f'TTLock account password for {account_id}'
                )
                logger.info(f"Stored credentials for account {account_id}")
                return True
            except Exception as db_error:
                logger.error(f"Database error storing credentials for account {account_id}: {str(db_error)}")
                # Remove account from account manager since we couldn't store it in the database
                self._account_manager.remove_account(account_id)
                return False
                
        except Exception as e:
            logger.error(f"Error adding account {account_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def get_user_list(self):
        """
        Get list of users in the system
        
        Returns:
            list: List of User objects from the database
        """
        try:
            if current_app:
                with current_app.app_context():
                    return User.query.all()
            else:
                logger.warning("No application context available for getting user list")
                return []
        except Exception as e:
            logger.error(f"Error getting user list: {str(e)}")
            return []
    
    def get_guest_list(self):
        """
        Get list of guests in the system
        
        Returns:
            list: List of Guest objects from the database
        """
        try:
            if current_app:
                with current_app.app_context():
                    return Guest.query.all()
            else:
                logger.warning("No application context available for getting guest list")
                return []
        except Exception as e:
            logger.error(f"Error getting guest list: {str(e)}")
            return []
    
    def create_ekey(self, lock_id, username, start_time, end_time, remarks=""):
        """
        Create an eKey for a user
        
        Args:
            lock_id: The ID of the lock
            username: The username to grant access to
            start_time: Start time for access (timestamp in milliseconds)
            end_time: End time for access (timestamp in milliseconds)
            remarks: Optional remarks
            
        Returns:
            dict: Response data or empty dict on failure
        """
        token = self._get_token()
        if not token:
            return {}
            
        try:
            url = f"{self._get_base_url()}/key/send"
            data = {
                'clientId': self._get_client_id(),
                'accessToken': token,
                'lockId': lock_id,
                'username': username,
                'startDate': start_time,
                'endDate': end_time,
                'remarks': remarks
            }
            
            response = requests.post(url, data=data)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('errcode') == 0:
                logger.info(f"Successfully created eKey for user {username}")
                return response_data
            else:
                error_msg = response_data.get('errmsg', 'Unknown error')
                logger.error(f"Failed to create eKey: {error_msg}")
                return {}
        except Exception as e:
            logger.error(f"Error creating eKey: {str(e)}")
            return {}
    
    def delete_ekey(self, key_id):
        """
        Delete an eKey
        
        Args:
            key_id: The ID of the eKey to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        token = self._get_token()
        if not token:
            return False
            
        try:
            url = f"{self._get_base_url()}/key/delete"
            data = {
                'clientId': self._get_client_id(),
                'accessToken': token,
                'keyId': key_id
            }
            
            response = requests.post(url, data=data)
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('errcode') == 0:
                logger.info(f"Successfully deleted eKey {key_id}")
                return True
            else:
                error_msg = response_data.get('errmsg', 'Unknown error')
                logger.error(f"Failed to delete eKey: {error_msg}")
                return False
        except Exception as e:
            logger.error(f"Error deleting eKey: {str(e)}")
            return False
