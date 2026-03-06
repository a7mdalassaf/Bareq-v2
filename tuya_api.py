import requests
import time
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from functools import lru_cache
import uuid

# Tuya API credentials
CLIENT_ID = "xrshhwwc3emqcg9qg3cy"
CLIENT_SECRET = "b5403f48d7164ea1aab97391dd1a38b6"
DEVICE_ID = "bf218614d2eb8bab41z4cs"
BASE_URL = "https://openapi.tuyaeu.com"

# Cache for access token
token_cache = {
    "access_token": None,
    "refresh_token": None,
    "expiry_time": None
}

# Cache storage for device status
_device_status_cache = {}
_cache_ttl = 5  # seconds

def _get_cached_status(device_id):
    """Get cached device status if available and not expired"""
    if device_id in _device_status_cache:
        cached_data, timestamp = _device_status_cache[device_id]
        if time.time() - timestamp <= _cache_ttl:
            return cached_data
    return None

def _cache_status(device_id, status):
    """Cache device status with current timestamp"""
    _device_status_cache[device_id] = (status, time.time())

def get_token():
    """
    Get access token using the complex method with proper string-to-sign format
    """
    # Check if we have a valid cached token
    current_time = datetime.now()
    if (token_cache["access_token"] and token_cache["expiry_time"] 
            and token_cache["expiry_time"] > current_time):
        return token_cache["access_token"]
    
    # Endpoint for token
    endpoint = "/v1.0/token?grant_type=1"
    url = f"{BASE_URL}{endpoint}"
    
    # Required headers
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    
    # For GET requests without body, the Content-SHA256 is the hash of empty string
    content_sha256 = hashlib.sha256(b"").hexdigest()
    
    # Create stringToSign according to Tuya docs
    string_to_sign = "GET" + "\n" + content_sha256 + "\n" + "\n" + endpoint
    
    # Create the string that includes string-to-sign (client_id + t + nonce + stringToSign)
    str_to_hash = CLIENT_ID + timestamp + nonce + string_to_sign
    
    # Generate signature using HMAC-SHA256
    signature = hmac.new(
        CLIENT_SECRET.encode('utf-8'),
        str_to_hash.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()
    
    # Create request headers
    headers = {
        "client_id": CLIENT_ID,
        "sign": signature,
        "t": timestamp,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success", False):
                token_info = data.get("result", {})
                
                # Cache the token
                token_cache["access_token"] = token_info.get("access_token")
                token_cache["refresh_token"] = token_info.get("refresh_token")
                
                # Set expiry time (subtract 5 minutes for safety)
                expire_seconds = token_info.get("expire_time", 7200)
                token_cache["expiry_time"] = current_time + timedelta(seconds=expire_seconds - 300)
                
                return token_cache["access_token"]
            else:
                print(f"Failed to get token: {data.get('msg')}")
        else:
            print(f"Failed to get token. Status code: {response.status_code}")
        
        return None
    except Exception as e:
        print(f"Error getting token: {str(e)}")
        return None

def make_api_request(method, endpoint, body=None):
    """
    Make a request to the Tuya API with proper authentication
    """
    access_token = get_token()
    if not access_token:
        return {"success": False, "error": "Failed to get access token"}
    
    url = f"{BASE_URL}{endpoint}"
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    
    # Calculate Content-SHA256 for the body
    content_sha256 = ""
    if body:
        content_sha256 = hashlib.sha256(json.dumps(body).encode('utf-8')).hexdigest()
    else:
        content_sha256 = hashlib.sha256(b"").hexdigest()
    
    # Create stringToSign
    string_to_sign = method + "\n" + content_sha256 + "\n" + "\n" + endpoint
    
    # Create the string that includes string-to-sign
    str_to_hash = CLIENT_ID + access_token + timestamp + nonce + string_to_sign
    
    # Generate signature
    signature = hmac.new(
        CLIENT_SECRET.encode('utf-8'),
        str_to_hash.encode('utf-8'),
        hashlib.sha256
    ).hexdigest().upper()
    
    # Create headers
    headers = {
        "client_id": CLIENT_ID,
        "access_token": access_token,
        "sign": signature,
        "t": timestamp,
        "sign_method": "HMAC-SHA256",
        "nonce": nonce
    }
    
    if body:
        headers["Content-Type"] = "application/json"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=body)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=body)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return {"success": False, "error": f"Unsupported method: {method}"}
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False, 
                "error": f"API request failed with status code {response.status_code}",
                "response": response.text
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_device_status(device_id=None):
    """
    Get device status with caching
    Args:
        device_id (str, optional): The device ID to get status for. If not provided, uses default DEVICE_ID.
    Returns:
        dict: A dict with success, status (boolean), and raw_response
    """
    target_device = device_id or DEVICE_ID
    
    # Check cache first
    cached_result = _get_cached_status(target_device)
    if cached_result:
        return cached_result

    endpoint = f"/v1.0/devices/{target_device}/status"
    response = make_api_request("GET", endpoint)
    
    if response.get('success'):
        try:
            result = response.get('result', [])
            if result and isinstance(result, list):
                # The status is directly in the result array
                for item in result:
                    if item.get('code') == 'switch_led':
                        # True means light is ON, False means light is OFF
                        is_light_on = bool(item.get('value'))
                        response_data = {
                            'success': True,
                            'status': is_light_on,  # Convert to boolean for consistent response
                            'raw_response': response,
                            'cached': False
                        }
                        # Cache the successful response
                        _cache_status(target_device, response_data)
                        return response_data
                
                # If we didn't find switch_led status
                return {
                    'success': False,
                    'error': 'No switch_led status found in device response',
                    'raw_response': response,
                    'cached': False
                }
        except Exception as e:
            response_data = {
                'success': False,
                'error': f'Error parsing response: {str(e)}',
                'raw_response': response,
                'cached': False
            }
            return response_data
    
    # Cache failed responses too, but with a shorter TTL
    response_data = {
        'success': False,
        'error': response.get('error', 'Unknown error'),
        'raw_response': response,
        'cached': False
    }
    _cache_status(target_device, response_data)
    return response_data

def is_device_on(device_id=None):
    """
    Check if the device is currently on
    """
    response = get_device_status(device_id)
    return response.get('status', False) if response.get('success') else False

def toggle_device(device_id=None, turn_on=None):
    """
    Toggle the device on or off
    Args:
        device_id (str, optional): The device ID to toggle. If not provided, uses default DEVICE_ID.
        turn_on (bool, optional): If True, turn the device on. If False, turn it off.
                                If None, toggle the current state.
    Returns:
        dict: A dict with success status and any error message
    """
    target_device = device_id or DEVICE_ID
    
    try:
        # If no state specified, get current state and toggle it
        if turn_on is None:
            current_status = get_device_status(target_device)
            if not current_status['success']:
                return {
                    'success': False,
                    'error': f"Failed to get current status: {current_status.get('error', 'Unknown error')}",
                    'raw_response': current_status.get('raw_response', {})
                }
            turn_on = not current_status['status']
        
        # Prepare the command
        commands = [{
            "code": "switch_led",
            "value": turn_on
        }]
        
        endpoint = f"/v1.0/devices/{target_device}/commands"
        body = {
            "commands": commands
        }
        
        response = make_api_request("POST", endpoint, body)
        
        if response.get('success'):
            # Clear the cache for this device
            if target_device in _device_status_cache:
                del _device_status_cache[target_device]
            
            return {
                'success': True,
                'new_state': turn_on,
                'raw_response': response
            }
        else:
            return {
                'success': False,
                'error': response.get('error', 'Unknown error'),
                'raw_response': response
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Error toggling device: {str(e)}',
            'raw_response': {}
        }

def set_brightness(brightness, device_id=None):
    """
    Set the brightness of the device (0-100)
    """
    target_device = device_id or DEVICE_ID
    
    # Ensure brightness is within valid range
    brightness = max(0, min(100, brightness))
    
    commands = [
        {
            "code": "bright_value_v2",
            "value": brightness
        }
    ]
    
    endpoint = f"/v1.0/devices/{target_device}/commands"
    body = {"commands": commands}
    
    return make_api_request("POST", endpoint, body)

def set_color_temperature(temp_value, device_id=None):
    """
    Set the color temperature of the device (0-100)
    """
    target_device = device_id or DEVICE_ID
    
    # Ensure temp_value is within valid range
    temp_value = max(0, min(100, temp_value))
    
    commands = [
        {
            "code": "temp_value_v2",
            "value": temp_value
        }
    ]
    
    endpoint = f"/v1.0/devices/{target_device}/commands"
    body = {"commands": commands}
    
    return make_api_request("POST", endpoint, body)

def set_work_mode(mode, device_id=None):
    """
    Set the work mode of the device ('white' or 'colour')
    """
    target_device = device_id or DEVICE_ID
    
    if mode not in ['white', 'colour']:
        return {"success": False, "error": "Invalid mode. Must be 'white' or 'colour'"}
    
    commands = [
        {
            "code": "work_mode",
            "value": mode
        }
    ]
    
    endpoint = f"/v1.0/devices/{target_device}/commands"
    body = {"commands": commands}
    
    return make_api_request("POST", endpoint, body)

def get_device_info(device_id=None):
    """
    Get device information
    """
    target_device = device_id or DEVICE_ID
    
    endpoint = f"/v1.0/devices/{target_device}"
    return make_api_request("GET", endpoint)

# Test the API if run directly
if __name__ == "__main__":
    print("Testing Tuya API...")
    status = get_device_status()
    print(f"Device status: {json.dumps(status, indent=2)}")
    
    current_state = is_device_on()
    print(f"Device is currently {'ON' if current_state else 'OFF'}")
    
    # Toggle the device
    toggle_result = toggle_device()
    print(f"Toggle result: {json.dumps(toggle_result, indent=2)}")
    
    # Get the new state
    new_state = is_device_on()
    print(f"Device is now {'ON' if new_state else 'OFF'}")
