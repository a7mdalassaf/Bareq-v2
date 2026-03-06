import requests
import hashlib
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ttlock_api_test')

# Working credentials
client_id = "a67f3b3552a64b0c81aa5e3b2a19dffb"
client_secret = "8db22fad0b66cc784b06cbddc1ccab9a"
username = "a7mdoh@hotmail.com"
password = "Aa@112233123"
base_url = "https://euapi.ttlock.com"

# Test authentication
password_md5 = hashlib.md5(password.encode()).hexdigest().lower()
auth_url = f"{base_url}/oauth2/token"
auth_params = {
    'clientId': client_id,
    'clientSecret': client_secret,
    'username': username,
    'password': password_md5
}
headers = {"Content-Type": "application/x-www-form-urlencoded"}

logger.info(f"Testing authentication with URL: {auth_url}")
logger.info(f"Using client ID: {client_id}")
response = requests.post(auth_url, data=auth_params, headers=headers)
logger.info(f"Auth response: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    logger.info(f"Authentication success! Token: {result.get('access_token', 'N/A')[:10]}...")
    
    # If authentication works, test getting locks
    if 'access_token' in result:
        token = result['access_token']
        locks_url = f"{base_url}/v3/lock/list"
        locks_params = {
            'clientId': client_id,
            'accessToken': token,
            'pageNo': 1,
            'pageSize': 20,
            'date': int(time.time() * 1000)
        }
        logger.info(f"Testing lock list with URL: {locks_url}")
        locks_response = requests.post(locks_url, data=locks_params, headers=headers)
        logger.info(f"Locks response: {locks_response.status_code}")
        
        if locks_response.status_code == 200:
            locks_result = locks_response.json()
            if 'list' in locks_result:
                locks = locks_result['list']
                logger.info(f"Success! Found {len(locks)} locks")
                for i, lock in enumerate(locks):
                    logger.info(f"Lock {i+1}: ID={lock.get('lockId')}, Name={lock.get('lockName')}")
            else:
                logger.error(f"No 'list' field in response: {locks_result}")
        else:
            logger.error(f"Failed to get locks: {locks_response.text}")
    else:
        logger.error("No access_token in response")
else:
    logger.error(f"Authentication failed: {response.text}")