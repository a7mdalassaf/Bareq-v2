import requests
import hashlib
import time
from pprint import pprint
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('ttlock_api_test')

# TTLock API credentials
CLIENT_ID = "a67f3b3552a64b0c81aa5e3b2a19dffb"
CLIENT_SECRET = "8db22fad0b66cc784b06cbddc1ccab9a"
USERNAME = "a7mdoh@hotmail.com"
RAW_PASSWORD = "Aa@112233123"

# Convert the raw password to MD5 (lowercase, 32 characters)
MD5_PASSWORD = hashlib.md5(RAW_PASSWORD.encode('utf-8')).hexdigest().lower()

# TTLock API base URL
BASE_URL = "https://euapi.ttlock.com"

def get_access_token():
    """Get an access token from the TTLock API"""
    url = f"{BASE_URL}/oauth2/token"
    
    # Prepare the form data
    data = {
        "clientId": CLIENT_ID,
        "clientSecret": CLIENT_SECRET,
        "username": USERNAME,
        "password": MD5_PASSWORD
    }
    
    # The request should use x-www-form-urlencoded content type
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    logger.debug(f"Requesting token with params: {data}")
    
    try:
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        token_info = response.json()
        
        logger.debug(f"Token response: {token_info}")
        
        # Extract relevant fields
        access_token = token_info.get("access_token")
        expires_in = token_info.get("expires_in")
        uid = token_info.get("uid")
        
        logger.info(f"Access Token: {access_token[:10]}... (expires in {expires_in} seconds)")
        logger.info(f"User ID: {uid}")
        
        return access_token
    
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred while requesting the access token: {e}")
        return None

def get_lock_list(access_token):
    """Get a list of locks from the TTLock API"""
    url = f"{BASE_URL}/v3/lock/list"
    
    # Current time in milliseconds
    current_time_millis = int(time.time() * 1000)
    
    # Build the query parameters
    params = {
        "clientId": CLIENT_ID,
        "accessToken": access_token,
        "pageNo": 1,
        "pageSize": 20,
        "date": current_time_millis
    }
    
    logger.debug(f"Requesting lock list with params: {params}")
    
    try:
        # Make the GET request with query parameters
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"Lock list response: {data}")
        
        # Extract pagination info
        page_no = data.get("pageNo")
        page_size = data.get("pageSize")
        total_pages = data.get("pages")
        total_records = data.get("total")
        
        logger.info(f"Page: {page_no}/{total_pages}, Size: {page_size}, Total Records: {total_records}")
        
        # Iterate over the lock records
        locks = data.get("list", [])
        for lock in locks:
            lock_id = lock.get("lockId")
            lock_name = lock.get("lockName")
            lock_mac = lock.get("lockMac")
            
            logger.info(f"Lock ID: {lock_id}, Name: {lock_name}, MAC: {lock_mac}")
        
        return locks
    
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred while retrieving the lock list: {e}")
        return []

def get_lock_status(access_token, lock_id):
    """Get the status of a specific lock"""
    url = f"{BASE_URL}/v3/lock/queryOpenState"
    
    # Current time in milliseconds
    current_time_millis = int(time.time() * 1000)
    
    # Build the query parameters
    params = {
        "clientId": CLIENT_ID,
        "accessToken": access_token,
        "lockId": lock_id,
        "date": current_time_millis
    }
    
    logger.debug(f"Requesting lock status with params: {params}")
    
    try:
        # Make the GET request with query parameters
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"Lock status response: {data}")
        
        state = data.get("state")
        battery_level = data.get("batteryLevel")
        
        logger.info(f"Lock {lock_id} - State: {state}, Battery Level: {battery_level}%")
        
        return data
    
    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred while retrieving the lock status: {e}")
        return {}

if __name__ == "__main__":
    print("=== TTLock API Test ===")
    
    # Step 1: Get access token
    print("\n1. Getting access token...")
    access_token = get_access_token()
    
    if not access_token:
        print("Failed to get access token. Exiting.")
        exit(1)
    
    # Step 2: Get lock list
    print("\n2. Getting lock list...")
    locks = get_lock_list(access_token)
    
    if not locks:
        print("No locks found or error occurred. Exiting.")
        exit(1)
    
    # Step 3: Get status of the first lock
    first_lock_id = locks[0].get("lockId")
    print(f"\n3. Getting status of lock {first_lock_id}...")
    lock_status = get_lock_status(access_token, first_lock_id)
    
    print("\nTest completed successfully!")
