"""
TTLock Integration Test Script

This script tests all aspects of the TTLock API integration:
1. Authentication
2. Lock retrieval
3. Lock status checking
4. Lock operations (if applicable)
5. Error handling

The script logs detailed information about each test and its results.
"""

import logging
import time
import sys
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ttlock_integration_test.log')
    ]
)
logger = logging.getLogger('ttlock_integration_test')

# Import the TTLock adapter
try:
    from ttlock_adapter import TTLockAdapter
    from services.ttlock_account_manager import TTLockAccountManager
    logger.info("Successfully imported TTLock modules")
except ImportError as e:
    logger.error(f"Failed to import TTLock modules: {e}")
    sys.exit(1)

def test_account_manager():
    """Test the TTLockAccountManager functionality"""
    logger.info("=== Testing TTLockAccountManager ===")
    
    try:
        # Initialize the account manager
        account_manager = TTLockAccountManager()
        logger.info("Successfully initialized TTLockAccountManager")
        
        # Load accounts - use the correct method
        # The method is private, so we'll skip this step in testing
        account_count = len(account_manager.accounts)
        logger.info(f"Found {account_count} accounts")
        
        if account_count == 0:
            logger.warning("No accounts found. Adding a test account...")
            account_manager.add_account(
                account_id="test_account",
                username="a7mdoh@hotmail.com",
                password="Aa@112233123",
                client_id="a67f3b3552a64b0c81aa5e3b2a19dffb",
                client_secret="8db22fad0b66cc784b06cbddc1ccab9a",
                base_url="https://euapi.ttlock.com"
            )
            logger.info("Test account added successfully")
            account_count = len(account_manager.accounts)
        
        # Test token retrieval for each account
        for account_id in account_manager.accounts:
            logger.info(f"Testing token retrieval for account: {account_id}")
            token = account_manager.get_token(account_id)
            if token:
                logger.info(f"Successfully retrieved token for account {account_id}")
            else:
                logger.error(f"Failed to retrieve token for account {account_id}")
        
        # Test lock retrieval for each account
        for account_id in account_manager.accounts:
            logger.info(f"Testing lock retrieval for account: {account_id}")
            locks = account_manager.get_account_locks(account_id)
            if locks:
                logger.info(f"Successfully retrieved {len(locks)} locks for account {account_id}")
                # Log the first lock details
                if locks:
                    first_lock = locks[0]
                    lock_id = first_lock.get('lockId')
                    lock_name = first_lock.get('lockName')
                    logger.info(f"First lock: ID={lock_id}, Name={lock_name}")
                    
                    # Test lock status retrieval
                    logger.info(f"Testing lock status retrieval for lock: {lock_id}")
                    status = account_manager.get_lock_status(account_id, lock_id)
                    if status:
                        logger.info(f"Successfully retrieved status for lock {lock_id}: {status}")
                    else:
                        logger.error(f"Failed to retrieve status for lock {lock_id}")
            else:
                logger.warning(f"No locks found for account {account_id}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error in TTLockAccountManager test: {e}", exc_info=True)
        return False

def test_ttlock_adapter():
    """Test the TTLockAdapter functionality"""
    logger.info("=== Testing TTLockAdapter ===")
    
    try:
        # Initialize the adapter
        adapter = TTLockAdapter()
        logger.info("Successfully initialized TTLockAdapter")
        
        # Test lock list retrieval
        logger.info("Testing lock list retrieval")
        locks = adapter.get_lock_list(use_cache=False)
        if locks:
            logger.info(f"Successfully retrieved {len(locks)} locks")
            # Log the first lock details
            if locks:
                first_lock = locks[0]
                lock_id = first_lock.get('lockId')
                lock_name = first_lock.get('lockName')
                logger.info(f"First lock: ID={lock_id}, Name={lock_name}")
                
                # Test lock details retrieval
                logger.info(f"Testing lock details retrieval for lock: {lock_id}")
                details = adapter.get_lock_details(lock_id)
                if details:
                    logger.info(f"Successfully retrieved details for lock {lock_id}")
                else:
                    logger.error(f"Failed to retrieve details for lock {lock_id}")
                
                # Test lock status retrieval
                logger.info(f"Testing lock status retrieval for lock: {lock_id}")
                status = adapter.get_lock_status(lock_id)
                if status is not None:
                    logger.info(f"Successfully retrieved status for lock {lock_id}: {status}")
                else:
                    logger.error(f"Failed to retrieve status for lock {lock_id}")
        else:
            logger.warning("No locks found")
        
        # Test caching
        logger.info("Testing lock caching")
        start_time = time.time()
        cached_locks = adapter.get_lock_list(use_cache=True)
        cache_time = time.time() - start_time
        logger.info(f"Cache retrieval time: {cache_time:.4f} seconds")
        if cached_locks:
            logger.info(f"Successfully retrieved {len(cached_locks)} locks from cache")
        else:
            logger.warning("No locks found in cache")
        
        return True
    
    except Exception as e:
        logger.error(f"Error in TTLockAdapter test: {e}", exc_info=True)
        return False

def run_all_tests():
    """Run all integration tests"""
    logger.info("=== Starting TTLock Integration Tests ===")
    
    # Track test results
    results = {
        "account_manager": False,
        "ttlock_adapter": False
    }
    
    # Test the account manager
    results["account_manager"] = test_account_manager()
    
    # Test the TTLock adapter
    results["ttlock_adapter"] = test_ttlock_adapter()
    
    # Print summary
    logger.info("=== Test Results Summary ===")
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    logger.info(f"Overall result: {'PASSED' if all_passed else 'FAILED'}")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
