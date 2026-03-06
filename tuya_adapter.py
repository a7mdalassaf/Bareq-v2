
import logging
import tuya_api
from models import db, LockDeviceMapping
from services.credential_service import CredentialService
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('tuya_adapter')

class TuyaAdapter:
    """
    Adapter class that bridges between the existing application interface and the tuya_api module.
    This maintains compatibility with the existing code while using the proven API implementation.
    """
    def __init__(self):
        # Default values in case database isn't initialized yet
        self._default_client_id = "xrshhwwc3emqcg9qg3cy"
        self._default_client_secret = "b5403f48d7164ea1aab97391dd1a38b6"
        self._default_device_id = "bf218614d2eb8bab41z4cs"
        self._default_endpoint = "https://openapi.tuyaeu.com"
        
        # Initialize other needed attributes
        self._token = None
        
        # Initialize tuya_api with credentials
        try:
            self._initialize_api()
        except Exception as e:
            logger.error(f"Error initializing Tuya API: {str(e)}")
    
    def _initialize_api(self):
        """Initialize the tuya_api module with credentials from the database"""
        try:
            # Check if we're in an application context
            if current_app:
                with current_app.app_context():
                    tuya_api.CLIENT_ID = self._get_client_id()
                    tuya_api.CLIENT_SECRET = self._get_client_secret()
                    tuya_api.BASE_URL = self._get_endpoint()
                    tuya_api.DEVICE_ID = self._get_default_device_id()
                    logger.info("Initialized Tuya API with credentials from database")
            else:
                # Fall back to default values
                tuya_api.CLIENT_ID = self._default_client_id
                tuya_api.CLIENT_SECRET = self._default_client_secret
                tuya_api.BASE_URL = self._default_endpoint
                tuya_api.DEVICE_ID = self._default_device_id
                logger.info("Initialized Tuya API with default credentials (no app context)")
        except Exception as e:
            logger.error(f"Error in _initialize_api: {str(e)}")
            # Fall back to default values
            tuya_api.CLIENT_ID = self._default_client_id
            tuya_api.CLIENT_SECRET = self._default_client_secret
            tuya_api.BASE_URL = self._default_endpoint
            tuya_api.DEVICE_ID = self._default_device_id
    
    def _get_client_id(self):
        """Get Tuya client ID from credential service"""
        try:
            return CredentialService.get_credential(
                'tuya', 'api', 'client_id', 
                default=self._default_client_id
            )
        except Exception as e:
            logger.error(f"Error getting client ID: {str(e)}")
            return self._default_client_id
    
    def _get_client_secret(self):
        """Get Tuya client secret from credential service"""
        try:
            return CredentialService.get_credential(
                'tuya', 'api', 'client_secret', 
                default=self._default_client_secret
            )
        except Exception as e:
            logger.error(f"Error getting client secret: {str(e)}")
            return self._default_client_secret
    
    def _get_endpoint(self):
        """Get Tuya API endpoint"""
        try:
            return CredentialService.get_credential(
                'tuya', 'api', 'endpoint', 
                default=self._default_endpoint
            )
        except Exception as e:
            logger.error(f"Error getting endpoint: {str(e)}")
            return self._default_endpoint
    
    def _get_device_id(self, lock_id=None):
        """Get the mapped Tuya device ID for a TTLock ID or return the default"""
        if not lock_id:
            return self._get_default_device_id()
            
        try:
            # Check if we're in an application context
            if current_app:
                with current_app.app_context():
                    mapping = LockDeviceMapping.query.filter_by(lock_id=lock_id, is_active=True).first()
                    if not mapping:
                        logger.warning(f"No active device mapping found for lock ID: {lock_id}, using default")
                        return self._get_default_device_id()
                    return mapping.device_id
            else:
                logger.warning("No application context available for device ID lookup")
                return self._get_default_device_id()
        except Exception as e:
            logger.error(f"Error getting device ID for lock {lock_id}: {str(e)}")
            return self._get_default_device_id()
    
    def _get_default_device_id(self):
        """Get default device ID from credential service"""
        try:
            return CredentialService.get_credential(
                'tuya', 'device', 'default_id', 
                default=self._default_device_id
            )
        except Exception as e:
            logger.error(f"Error getting default device ID: {str(e)}")
            return self._default_device_id
    
    def _get_token(self):
        """Get or refresh access token using tuya_api"""
        # Ensure API is initialized with latest credentials
        try:
            self._initialize_api()
            self._token = tuya_api.get_token()
            return self._token
        except Exception as e:
            logger.error(f"Error getting token: {str(e)}")
            return None
    
    def get_device_status(self, lock_id=None):
        """
        Get the status of a device.
        Returns True if the device LED is on, False otherwise.
        """
        try:
            # Use tuya_api to get status
            response = tuya_api.get_device_status()
            
            if not response or not response.get('success', False):
                logger.error(f"API returned unsuccessful response: {response}")
                return False
                
            # Check if the response has the 'result' field with statuses
            if 'result' in response:
                status_list = response['result']
                # Look for 'switch_led' in status items
                for status_item in status_list:
                    if status_item.get('code') == 'switch_led':
                        return status_item.get('value', False)
            
            logger.warning(f"Could not determine LED status from response: {response}")
            return False
        except Exception as e:
            logger.error(f"Error getting device status: {str(e)}")
            return False
    
    def control_led(self, state, lock_id=None):
        """
        Control the LED state of a device.
        
        Args:
            state: Boolean indicating on (True) or off (False)
            lock_id: Optional lock ID to determine which device to control
            
        Returns:
            Boolean indicating success
        """
        try:
            # Use tuya_api to control LED
            response = tuya_api.toggle_device(state)
            
            # Proper response validation with detailed logging
            if not response:
                logger.error("No response received from toggle_device API call")
                return False
                
            if response.get('success', False):
                logger.info(f"Successfully set LED state to {state}")
                return True
            else:
                error_msg = response.get('msg', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                return False
        except Exception as e:
            logger.error(f"Error controlling LED: {str(e)}")
            return False
    
    def link_device(self, lock_id, device_id, lock_name=None, device_name=None, skip_validation=False):
        """Link a TTLock ID with a Tuya device ID"""
        try:
            # Validate the device first unless skip_validation is True
            if not skip_validation:
                # Get device status to validate it exists and is accessible
                device_info = tuya_api.get_device_info()
                if not device_info or not device_info.get('success', False):
                    return {
                        'success': False, 
                        'error': f"Unable to validate device {device_id}. Please check if the device ID is correct."
                    }
            
            # Create or update the mapping in the database
            try:
                # Check if we're in an application context
                if current_app:
                    with current_app.app_context():
                        existing_mapping = LockDeviceMapping.query.filter_by(lock_id=lock_id).first()
                        
                        if existing_mapping:
                            # Update existing mapping
                            existing_mapping.device_id = device_id
                            existing_mapping.is_active = True
                            if lock_name:
                                existing_mapping.lock_name = lock_name
                            if device_name:
                                existing_mapping.device_name = device_name
                        else:
                            # Create new mapping
                            new_mapping = LockDeviceMapping(
                                lock_id=lock_id,
                                device_id=device_id,
                                lock_name=lock_name or f"Lock {lock_id}",
                                device_name=device_name or f"Device {device_id}",
                                is_active=True
                            )
                            db.session.add(new_mapping)
                            
                        db.session.commit()
                        
                        return {
                            'success': True,
                            'message': f"Successfully linked lock {lock_id} with device {device_id}"
                        }
                else:
                    logger.warning("No application context available for linking device")
                    return {
                        'success': False,
                        'error': "No application context available for linking device"
                    }
            except Exception as e:
                logger.error(f"Error linking device: {str(e)}")
                return {
                    'success': False,
                    'error': f"Error linking device: {str(e)}"
                }
        except Exception as e:
            logger.error(f"Error linking device: {str(e)}")
            return {
                'success': False,
                'error': f"Error linking device: {str(e)}"
            }
    
    def unlink_device(self, lock_id):
        """Unlink a TTLock ID from its Tuya device"""
        try:
            try:
                # Check if we're in an application context
                if current_app:
                    with current_app.app_context():
                        mapping = LockDeviceMapping.query.filter_by(lock_id=lock_id).first()
                        
                        if not mapping:
                            return {
                                'success': False,
                                'error': f"No device mapping found for lock ID: {lock_id}"
                            }
                            
                        # Deactivate the mapping (soft delete)
                        mapping.is_active = False
                        db.session.commit()
                        
                        return {
                            'success': True,
                            'message': f"Successfully unlinked lock {lock_id} from device {mapping.device_id}"
                        }
                else:
                    logger.warning("No application context available for unlinking device")
                    return {
                        'success': False,
                        'error': "No application context available for unlinking device"
                    }
            except Exception as e:
                logger.error(f"Error unlinking device: {str(e)}")
                return {
                    'success': False,
                    'error': f"Error unlinking device: {str(e)}"
                }
        except Exception as e:
            logger.error(f"Error unlinking device: {str(e)}")
            return {
                'success': False,
                'error': f"Error unlinking device: {str(e)}"
            }
