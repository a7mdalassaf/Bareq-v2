"""
TTLock Account Manager - Manages multiple TTLock accounts
"""
import logging
import requests
import time
import hashlib
import os
from dotenv import load_dotenv
from flask import current_app, has_app_context
from services.credential_service import CredentialService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ttlock_account_manager')

class TTLockAccountManager:
    """
    Manages multiple TTLock accounts and their credentials.
    Provides methods for token management and lock retrieval across all accounts.
    """
    def __init__(self):
        """Initialize the TTLock account manager"""
        self.accounts = {}
        
        # Get default values from environment variables or use fallbacks
        self._default_client_id = os.environ.get('TTLOCK_CLIENT_ID', "7946f0d923934a61baefb3303de4d155")
        self._default_client_secret = os.environ.get('TTLOCK_CLIENT_SECRET', "26db1e609e0e19365c18718d42760a0d")
        self._default_base_url = os.environ.get('TTLOCK_BASE_URL', "https://euapi.ttlock.com")
        
        # Token expiry management
        self._token_usage_history = {}  # Track token usage for dynamic expiry buffer
        self._min_buffer_seconds = 300  # Minimum buffer (5 minutes)
        self._max_buffer_seconds = 1800  # Maximum buffer (30 minutes)
        self._default_buffer_seconds = 600  # Default buffer (10 minutes)
        
        # Lock-to-account mapping cache
        self._lock_cache = {}  # Map lock_id to account_id and lock data
        self._lock_cache_expiry = 0  # Cache expiry timestamp
        self._lock_cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        
        # Load accounts from credential service
        self._load_accounts()
        
        logger.info(f"TTLockAccountManager initialized with {len(self.accounts)} accounts")
        logger.info(f"Using TTLock API endpoint: {self._default_base_url}")
    
    def _load_accounts(self):
        """Load all TTLock accounts from the credential service"""
        try:
            # Check if we're in an application context
            if not has_app_context():
                logger.warning("No application context available for loading accounts")
                return
            
            # Get all account identifiers (credential_type starting with 'account')
            account_types = CredentialService.get_all_credential_types_by_provider('ttlock')
            
            for account_type in account_types:
                if account_type.startswith('account'):
                    account_id = account_type
                    
                    # Get username and password for this account
                    username = CredentialService.get_credential('ttlock', account_id, 'username', default="")
                    password = CredentialService.get_credential('ttlock', account_id, 'password', default="")
                    
                    if username and password:
                        # Add account to the manager
                        self.add_account(account_id, username, password)
                        logger.info(f"Loaded account {account_id} from credential service")
                    else:
                        logger.warning(f"Incomplete credentials for account {account_id}")
            
            # If no accounts were loaded, try to load the default account
            if not self.accounts:
                username = CredentialService.get_credential('ttlock', 'account', 'username', default="")
                password = CredentialService.get_credential('ttlock', 'account', 'password', default="")
                
                if username and password:
                    self.add_account('account', username, password)
                    logger.info("Loaded default account from credential service")
                else:
                    logger.warning("No TTLock accounts found in credential service")
        
        except Exception as e:
            logger.error(f"Error loading TTLock accounts: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def add_account(self, account_id, username, password, client_id=None, client_secret=None, base_url=None):
        """
        Add a TTLock account to the manager
        
        Args:
            account_id (str): Unique identifier for this account
            username (str): TTLock account username
            password (str): TTLock account password
            client_id (str, optional): TTLock API client ID
            client_secret (str, optional): TTLock API client secret
            base_url (str, optional): TTLock API base URL
        """
        self.accounts[account_id] = {
            'username': username,
            'password': password,
            'client_id': client_id or self._get_client_id(),
            'client_secret': client_secret or self._get_client_secret(),
            'base_url': base_url or self._get_base_url(),
            'token': None,
            'token_expiry': 0
        }
        logger.info(f"Added TTLock account {account_id}")
    
    def _get_client_id(self):
        """Get TTLock client ID from credential service"""
        try:
            # Check if we're in an application context
            if not has_app_context():
                logger.warning("No application context available for getting client_id")
                return self._default_client_id
            
            client_id = CredentialService.get_credential(
                'ttlock', 'api', 'client_id', 
                default=self._default_client_id
            )
            logger.debug("Retrieved TTLock client_id from credential service")
            return client_id
        
        except Exception as e:
            logger.error(f"Error getting client_id: {str(e)}")
            return self._default_client_id
    
    def _get_client_secret(self):
        """Get TTLock client secret from credential service"""
        try:
            # Check if we're in an application context
            if not has_app_context():
                logger.warning("No application context available for getting client_secret")
                return self._default_client_secret
            
            client_secret = CredentialService.get_credential(
                'ttlock', 'api', 'client_secret', 
                default=self._default_client_secret
            )
            logger.debug("Retrieved TTLock client_secret from credential service")
            return client_secret
        
        except Exception as e:
            logger.error(f"Error getting client_secret: {str(e)}")
            return self._default_client_secret
    
    def _get_base_url(self):
        """Get TTLock API base URL from credential service"""
        try:
            # Check if we're in an application context
            if not has_app_context():
                logger.warning("No application context available for getting base_url")
                return self._default_base_url
            
            base_url = CredentialService.get_credential(
                'ttlock', 'api', 'base_url', 
                default=self._default_base_url
            )
            logger.debug("Retrieved TTLock base_url from credential service")
            return base_url
        
        except Exception as e:
            logger.error(f"Error getting base_url: {str(e)}")
            return self._default_base_url
    
    def get_token(self, account_id, force_refresh=False):
        """
        Get access token for a specific TTLock account
        
        Args:
            account_id (str): Account identifier
            force_refresh (bool): Whether to force token refresh
            
        Returns:
            str: Access token or None if failed
        """
        # Check if account exists
        if account_id not in self.accounts:
            logger.error(f"Account {account_id} not found")
            return None
            
        account = self.accounts[account_id]
        
        # Check if we have a valid token
        current_time = int(time.time())
        
        # Initialize token usage tracking if not exists
        if account_id not in self._token_usage_history:
            self._token_usage_history[account_id] = {
                'usage_count': 0,
                'last_refresh': 0,
                'buffer_seconds': self._default_buffer_seconds
            }
            
        # Track token usage
        self._token_usage_history[account_id]['usage_count'] += 1
        
        # Check if token is still valid with dynamic buffer
        buffer_seconds = self._token_usage_history[account_id]['buffer_seconds']
        if not force_refresh and account['token'] and account['token_expiry'] > (current_time + buffer_seconds):
            logger.debug(f"Using existing token for account {account_id} (buffer: {buffer_seconds}s)")
            return account['token']
        
        # Need to get a new token
        try:
            username = account['username']
            password = account['password']
            client_id = account['client_id']
            client_secret = account['client_secret']
            base_url = account['base_url']
            
            if not username or not password:
                logger.error(f"Missing username or password for account {account_id}")
                return None
                
            # Create MD5 hash of password
            password_md5 = hashlib.md5(password.encode()).hexdigest().lower()
            
            # Build request parameters
            url = f"{base_url}/oauth2/token"
            params = {
                'clientId': client_id,
                'clientSecret': client_secret,
                'username': username,
                'password': password_md5
            }
            
            # Log request details for debugging (sanitize sensitive data)
            sanitized_params = params.copy()
            sanitized_params['clientSecret'] = '********'
            sanitized_params['password'] = '********'
            logger.debug(f"Requesting token for account {account_id} with params: {sanitized_params}")
            
            # Make the request with the correct content type
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            response = requests.post(url, data=params, headers=headers)
            
            # Log response for debugging (sanitize sensitive data)
            logger.debug(f"Token response for account {account_id}: {response.status_code}")
            
            # Check if request was successful
            if response.status_code == 200:
                result = response.json()
                if 'access_token' in result:
                    # Store token and expiry time with dynamic buffer
                    token_expires_in = result.get('expires_in', 7200)
                    
                    # Update token usage history
                    usage_history = self._token_usage_history[account_id]
                    usage_history['last_refresh'] = current_time
                    
                    # Adjust buffer based on usage patterns
                    # If we're using the token frequently, increase the buffer
                    if usage_history['usage_count'] > 50:
                        # High usage - use larger buffer
                        new_buffer = min(self._max_buffer_seconds, usage_history['buffer_seconds'] * 1.2)
                    elif usage_history['usage_count'] > 20:
                        # Medium usage - maintain buffer
                        new_buffer = usage_history['buffer_seconds']
                    else:
                        # Low usage - decrease buffer but not below minimum
                        new_buffer = max(self._min_buffer_seconds, usage_history['buffer_seconds'] * 0.8)
                    
                    # Update buffer
                    usage_history['buffer_seconds'] = int(new_buffer)
                    logger.debug(f"Adjusted token buffer for account {account_id} to {usage_history['buffer_seconds']}s")
                    
                    # Reset usage count after adjustment
                    if usage_history['usage_count'] > 100:
                        usage_history['usage_count'] = 50  # Decay but maintain history
                    
                    # Store token with dynamic buffer
                    account['token'] = result['access_token']
                    account['token_expiry'] = current_time + token_expires_in - usage_history['buffer_seconds']
                    
                    logger.info(f"Successfully obtained token for account {account_id} (expires in {token_expires_in}s, buffer: {usage_history['buffer_seconds']}s)")
                    return account['token']
                else:
                    logger.error(f"No access_token in response for account {account_id}: {result}")
            else:
                logger.error(f"Failed to get token for account {account_id}: {response.status_code} {response.text}")
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting token for account {account_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _update_lock_cache(self, account_id, locks):
        """
        Update the lock cache with locks from an account
        
        Args:
            account_id (str): Account identifier
            locks (list): List of lock objects
        """
        current_time = int(time.time())
        
        # Update cache expiry
        self._lock_cache_expiry = current_time + self._lock_cache_ttl
        
        # Add locks to cache
        for lock in locks:
            if 'lockId' in lock:
                lock_id = lock['lockId']
                self._lock_cache[lock_id] = {
                    'account_id': account_id,
                    'data': lock,
                    'timestamp': current_time
                }
                
        logger.debug(f"Updated lock cache with {len(locks)} locks from account {account_id}")
        logger.debug(f"Lock cache now contains {len(self._lock_cache)} locks")
        
    def _is_cache_valid(self):
        """
        Check if the lock cache is still valid
        
        Returns:
            bool: True if cache is valid, False otherwise
        """
        return int(time.time()) < self._lock_cache_expiry and len(self._lock_cache) > 0
    
    def get_account_locks(self, account_id, page_size=10):
        """
        Get locks for a specific account with pagination support using an iterative approach
        
        Args:
            account_id (str): Account identifier
            page_size (int): Number of locks per page
            
        Returns:
            list: List of locks or empty list if failed
        """
        all_locks = []
        page_no = 1
        
        try:
            # Get token for this account
            token = self.get_token(account_id)
            if not token:
                logger.error(f"Failed to get token for account {account_id}")
                return []
                
            # Check if account exists
            if account_id not in self.accounts:
                logger.error(f"Account {account_id} not found")
                return []
                
            account = self.accounts[account_id]
            client_id = account['client_id']
            base_url = account['base_url']
            
            # Iterative approach to fetch all pages
            while True:
                # Build request parameters
                # Build request parameters
                if base_url.endswith('/v3'):
                    url = f"{base_url}/lock/list"
                else:
                    url = f"{base_url}/v3/lock/list"
                #url = f"{base_url}/v3/lock/list"
                params = {
                    'clientId': client_id,
                    'accessToken': token,
                    'pageNo': page_no,
                    'pageSize': page_size,
                    'date': int(time.time() * 1000)
                }
                
                # Log request details for debugging (sanitize sensitive data)
                sanitized_params = params.copy()
                sanitized_params['accessToken'] = '********'
                logger.debug(f"Requesting lock list for account {account_id} with params: {sanitized_params}")
                
                # Make the request with the correct content type
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                response = requests.post(url, data=params, headers=headers)
                
                # Log response for debugging
                logger.debug(f"Lock list response for account {account_id}: {response.status_code}")
                # Log full response for debugging during development
                logger.debug(f"Lock list response text: {response.text[:200]}...")
                
                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()
                    if 'list' in result:
                        page_locks = result['list']
                        all_locks.extend(page_locks)
                        logger.info(f"Retrieved {len(page_locks)} locks for account {account_id} (page {page_no})")
                        
                        # Check if there are more pages
                        if len(page_locks) < page_size:
                            # No more locks, we're done
                            break
                        else:
                            # More locks might exist, go to next page
                            page_no += 1
                            # Add rate limiting to avoid overwhelming the API
                            time.sleep(1)
                    else:
                        logger.warning(f"No 'list' in response for account {account_id}: {result}")
                        break
                else:
                    logger.error(f"Failed to get locks for account {account_id}: {response.status_code} {response.text}")
                    break
            
            # Update lock cache with the retrieved locks
            if all_locks:
                self._update_lock_cache(account_id, all_locks)
                
            logger.info(f"Retrieved a total of {len(all_locks)} locks for account {account_id}")
            return all_locks
            
        except Exception as e:
            logger.error(f"Error getting locks for account {account_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return all_locks  # Return any locks we've collected so far
    
    def get_all_locks(self, page_size=10, use_cache=True):
        """
        Get all locks from all accounts
        
        Args:
            page_size (int): Number of locks per page for each account
            use_cache (bool): Whether to use the lock cache if valid
            
        Returns:
            list: Combined list of locks from all accounts
        """
        # Check if we can use the cache
        if use_cache and self._is_cache_valid():
            logger.info(f"Using lock cache with {len(self._lock_cache)} locks (expires in {self._lock_cache_expiry - int(time.time())}s)")
            return [lock_data['data'] for lock_data in self._lock_cache.values()]
            
        # Cache is invalid or not requested, fetch locks from all accounts
        all_locks = []
        
        for account_id in self.accounts:
            try:
                locks = self.get_account_locks(account_id, page_size=page_size)
                all_locks.extend(locks)
                logger.info(f"Retrieved {len(locks)} locks from account {account_id}")
            except Exception as e:
                logger.error(f"Error getting locks from account {account_id}: {str(e)}")
                
        logger.info(f"Retrieved {len(all_locks)} locks from all accounts")
        return all_locks
    
    def get_lock_status(self, account_id, lock_id):
        """
        Get status of a specific lock
        
        Args:
            account_id (str): Account identifier
            lock_id (str): Lock identifier
            
        Returns:
            dict: Lock status or empty dict if failed
        """
        try:
            # Get token for this account
            token = self.get_token(account_id)
            if not token:
                logger.error(f"Failed to get token for account {account_id}")
                return {}
                
            # Check if account exists
            if account_id not in self.accounts:
                logger.error(f"Account {account_id} not found")
                return {}
                
            account = self.accounts[account_id]
            client_id = account['client_id']
            base_url = account['base_url']
            
            # Build request parameters
            url = f"{base_url}/v3/lock/queryOpenState"
            params = {
                'clientId': client_id,
                'accessToken': token,
                'lockId': lock_id,
                'date': int(time.time() * 1000)
            }
            
            # Log request details for debugging
            logger.debug(f"Requesting lock status for lock {lock_id} with params: {params}")
            
            # Make the request
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            response = requests.post(url, data=params, headers=headers)
            
            # Log response for debugging
            logger.debug(f"Lock status response for lock {lock_id}: {response.status_code}")
            logger.debug(f"Lock status response text: {response.text[:200]}...")
            
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
    
    def find_account_for_lock(self, lock_id):
        """
        Find which account a lock belongs to
        
        Args:
            lock_id (str): Lock identifier
            
        Returns:
            str: Account identifier or None if not found
        """
        # First check the lock cache
        if lock_id in self._lock_cache:
            account_id = self._lock_cache[lock_id]['account_id']
            logger.debug(f"Found lock {lock_id} in cache (account: {account_id})")
            return account_id
            
        # If not in cache, search through all accounts
        for account_id in self.accounts:
            try:
                # Try to get lock details directly first (more efficient)
                token = self.get_token(account_id)
                if not token:
                    logger.error(f"Failed to get token for account {account_id}")
                    continue
                    
                account = self.accounts[account_id]
                client_id = account['client_id']
                base_url = account['base_url']
                
                # Build request parameters
                url = f"{base_url}/v3/lock/detail"
                params = {
                    'clientId': client_id,
                    'accessToken': token,
                    'lockId': lock_id,
                    'date': int(time.time() * 1000)
                }
                
                # Make the request
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                response = requests.post(url, data=params, headers=headers)
                
                # Log response for debugging
                logger.debug(f"Lock details response for lock {lock_id}: {response.status_code}")
                logger.debug(f"Lock details response text: {response.text[:200]}...")
                
                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()
                    if 'lockId' in result:
                        # Add to cache
                        self._lock_cache[lock_id] = {
                            'account_id': account_id,
                            'data': result,
                            'timestamp': int(time.time())
                        }
                        logger.info(f"Lock {lock_id} belongs to account {account_id}")
                        return account_id
                
                # If direct lookup fails, try searching through all locks
                locks = self.get_account_locks(account_id)
                for lock in locks:
                    if str(lock.get('lockId')) == str(lock_id):
                        logger.info(f"Lock {lock_id} belongs to account {account_id}")
                        return account_id
            except Exception as e:
                logger.error(f"Error checking if lock {lock_id} belongs to account {account_id}: {str(e)}")
                    
        logger.warning(f"Lock {lock_id} not found in any account")
        return None
    
    def remove_account(self, account_id):
        """
        Remove an account from the manager
        
        Args:
            account_id (str): Account identifier to remove
            
        Returns:
            bool: True if account was removed, False if it didn't exist
        """
        try:
            if account_id in self.accounts:
                del self.accounts[account_id]
                logger.info(f"Removed account {account_id} from TTLockAccountManager")
                return True
            else:
                logger.warning(f"Account {account_id} not found in TTLockAccountManager")
                return False
        except Exception as e:
            logger.error(f"Error removing account {account_id}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def get_lock_details(self, lock_id):
        """
        Get details for a specific lock
        
        Args:
            lock_id (str): Lock ID
            
        Returns:
            dict: Lock details or None if not found
        """
        # Check if lock is in cache
        if lock_id in self._lock_cache:
            lock_data = self._lock_cache[lock_id]
            logger.debug(f"Found lock {lock_id} in cache (account: {lock_data['account_id']})")
            return lock_data['data']
            
        # Lock not in cache, try to find it in any account
        for account_id in self.accounts:
            try:
                # Get token for this account
                token = self.get_token(account_id)
                if not token:
                    logger.error(f"Failed to get token for account {account_id}")
                    continue
                    
                account = self.accounts[account_id]
                client_id = account['client_id']
                base_url = account['base_url']
                
                # Build request parameters
                url = f"{base_url}/v3/lock/detail"
                params = {
                    'clientId': client_id,
                    'accessToken': token,
                    'lockId': lock_id,
                    'date': int(time.time() * 1000)
                }
                
                # Make the request
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                response = requests.post(url, data=params, headers=headers)
                
                # Log response for debugging
                logger.debug(f"Lock details response for lock {lock_id}: {response.status_code}")
                logger.debug(f"Lock details response text: {response.text[:200]}...")
                
                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()
                    if 'lockId' in result:
                        # Add to cache
                        self._lock_cache[lock_id] = {
                            'account_id': account_id,
                            'data': result,
                            'timestamp': int(time.time())
                        }
                        logger.info(f"Found lock {lock_id} in account {account_id}")
                        return result
            except Exception as e:
                logger.error(f"Error getting lock details for lock {lock_id} from account {account_id}: {str(e)}")
                
        logger.warning(f"Lock {lock_id} not found in any account")
        return None
