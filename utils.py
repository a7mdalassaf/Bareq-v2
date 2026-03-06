"""
Utility functions for the Rettlock Smart Lock Management System
"""

import time
import logging
import functools
import json
from typing import Tuple, List, Callable, Any, Optional, Dict, Union

logger = logging.getLogger('utils')

def retry_with_backoff(max_retries: int = 3, base_delay: int = 2, max_delay: int = 60, 
                      rate_limit_codes: Tuple[int, ...] = (429, 1001)) -> Callable:
    """
    Decorator that retries a function call with exponential backoff when specific exceptions occur.
    
    Args:
        max_retries: Maximum number of retries before giving up
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        rate_limit_codes: HTTP error codes that trigger a retry (e.g., rate limiting)
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            delay = base_delay
            
            while retries <= max_retries:
                try:
                    response = func(*args, **kwargs)
                    
                    # Check for rate limiting in the response
                    if isinstance(response, dict):
                        error_code = response.get('code', 0)
                        if error_code in rate_limit_codes:
                            raise Exception(f"Rate limited with code {error_code}: {response.get('msg', 'No message')}")
                    
                    return response
                    
                except Exception as e:
                    error_message = str(e)
                    retries += 1
                    
                    # If we're out of retries, re-raise the exception
                    if retries > max_retries:
                        logger.error(f"Maximum retries ({max_retries}) exceeded: {error_message}")
                        raise
                    
                    # Calculate backoff delay (with jitter)
                    delay = min(max_delay, base_delay * (2 ** (retries - 1)))
                    sleep_time = delay + (hash(str(time.time())) % 1000) / 1000
                    
                    # Log retry information
                    logger.warning(f"Attempt {retries}/{max_retries} failed: {error_message}. Retrying in {sleep_time:.2f}s")
                    time.sleep(sleep_time)
            
            # This should not be reached due to the raise in the except block
            return None
            
        return wrapper
    return decorator

def validate_api_response(response: Dict[str, Any], 
                         required_fields: Optional[List[str]] = None) -> Tuple[bool, Union[str, Dict[str, Any]]]:
    """
    Validates an API response to ensure it has the required fields and is successful.
    
    Args:
        response: The API response dictionary to validate
        required_fields: List of field names that must be present in the response
    
    Returns:
        Tuple of (is_valid, error_message_or_data)
    """
    if not isinstance(response, dict):
        return False, f"Invalid response format: expected dictionary, got {type(response).__name__}"
    
    # Check if the response indicates an error
    if not response.get('success', False):
        return False, response.get('error', response.get('msg', 'Unknown error'))
    
    # If required fields are specified, check that they exist
    if required_fields:
        result = response.get('result', {})
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            return False, f"Response missing required fields: {', '.join(missing_fields)}"
    
    return True, response.get('result', response)

def format_json_response(data: Dict[str, Any], indent: int = 2) -> str:
    """
    Formats a dictionary as a pretty-printed JSON string
    
    Args:
        data: The dictionary to format
        indent: Number of spaces to use for indentation
    
    Returns:
        Formatted JSON string
    """
    return json.dumps(data, indent=indent)

def safe_get(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """
    Safely retrieve a nested key from a dictionary without raising KeyError
    
    Args:
        data: Dictionary to retrieve value from
        keys: List of keys to traverse
        default: Default value to return if key doesn't exist
    
    Returns:
        Value if found, otherwise default
    """
    if not data or not isinstance(data, dict):
        return default
    
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    
    return current
