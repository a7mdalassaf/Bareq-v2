from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from smart_lock_manager import TTLockManager
from tuya_adapter import TuyaAdapter
from ttlock_adapter import TTLockAdapter
from datetime import datetime, timedelta, timezone
from models import db, Guest, User, LockDeviceMapping, JobExecution, JobDefinition, SystemStatus
from routes.admin import admin
from services.credential_service import CredentialService
import os
import logging
import json
import smtplib
from email.message import EmailMessage
from tuya_api import get_device_status, toggle_device

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('rettlockinfo')

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lockinfo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Register blueprints
app.register_blueprint(admin, url_prefix='/admin')

db.init_app(app)

# Initialize adapters
tuya_manager = TuyaAdapter()
ttlock_adapter = TTLockAdapter()

def initialize_default_ttlock_account():
    """Initialize a default TTLock account if none exists"""
    try:
        # Check if we have any TTLock accounts
        from services.credential_service import CredentialService
        account_types = CredentialService.get_all_credential_types_by_provider('ttlock')
        
        # If no accounts exist, create a default one
        if not any(account_type.startswith('account') for account_type in account_types):
            logger.info("No TTLock accounts found, creating default account")
            
            # Use the working TTLock credentials from access_token.py
            default_username = "a7mdoh@hotmail.com"
            default_password = "Aa@112233123"
            
            # Store credentials
            CredentialService.set_credential('ttlock', 'account1', 'username', default_username)
            CredentialService.set_credential('ttlock', 'account1', 'password', default_password)
            
            # Set the correct client ID and client secret
            #CredentialService.set_credential('ttlock', 'api', 'client_id', "a67f3b3552a64b0c81aa5e3b2a19dffb")
            #CredentialService.set_credential('ttlock', 'api', 'client_secret', "8db22fad0b66cc784b06cbddc1ccab9a")
            #CredentialService.set_credential('ttlock', 'api', 'base_url', "https://euapi.ttlock.com/v3")
            # Set the correct client ID and client secret
            CredentialService.set_credential('ttlock', 'api', 'client_id', "a67f3b3552a64b0c81aa5e3b2a19dffb")
            CredentialService.set_credential('ttlock', 'api', 'client_secret', "8db22fad0b66cc784b06cbddc1ccab9a")
            CredentialService.set_credential('ttlock', 'api', 'base_url', "https://euapi.ttlock.com")
            # Reinitialize the TTLock adapter to load the new account
            ttlock_adapter._account_manager._load_accounts()
            
            logger.info("Default TTLock account created successfully")
            return True
        else:
            logger.info(f"Found {len(account_types)} existing TTLock account types")
            return False
    except Exception as e:
        logger.error(f"Error initializing default TTLock account: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

# Load all TTLock accounts
with app.app_context():
    # Get all credential types for TTLock provider
    from services.credential_service import CredentialService
    credential_types = CredentialService.get_all_credential_types_by_provider('ttlock')
    
    # Find account credential types (excluding 'api' which is for API settings)
    account_types = [ctype for ctype in credential_types if ctype != 'api']
    
    # Add each account to the TTLock adapter
    for account_type in account_types:
        try:
            username = CredentialService.get_credential('ttlock', account_type, 'username')
            password = CredentialService.get_credential('ttlock', account_type, 'password')
            
            if username and password:
                ttlock_adapter.add_account(account_type, username, password)
                app.logger.info(f"Added TTLock account: {account_type}")
            else:
                app.logger.warning(f"Incomplete credentials for TTLock account: {account_type}")
        except Exception as e:
            app.logger.error(f"Error loading TTLock account {account_type}: {str(e)}")

    # Initialize default TTLock account if needed
    initialize_default_ttlock_account()

# Global variable to hold scheduler instance
scheduler = None

# Create tables
with app.app_context():
    db.create_all()
    
    # Load credentials from file if no user exists
    if not User.query.first():
        try:
            with open('../cred', 'r') as f:
                cred_lines = f.readlines()
                username = None
                password = None
                for line in cred_lines:
                    if line.startswith('username='):
                        username = line.split('=')[1].strip()
                    elif line.startswith('password='):
                        password = line.split('=')[1].strip()
                
                if username and password:
                    # Clear any existing users and set new current user
                    User.query.delete()
                    user = User(username=username, password=password, is_current=True)
                    db.session.add(user)
                    db.session.commit()
                    logger.info(f"Created user {username} from credentials file")
                    
                    # Store TTLock credentials in the database
                    CredentialService.set_credential('ttlock', 'account', 'username', username)
                    CredentialService.set_credential('ttlock', 'account', 'password', password)
                    CredentialService.set_credential('ttlock', 'api', 'client_id', 'a67f3b3552a64b0c81aa5e3b2a19dffb')
                    CredentialService.set_credential('ttlock', 'api', 'client_secret', '8db22fad0b66cc784b06cbddc1ccab9a')
                    CredentialService.set_credential('ttlock', 'api', 'base_url', 'https://euapi.ttlock.com/v3')
                    
                    # Store Tuya credentials in the database
                    CredentialService.set_credential('tuya', 'api', 'client_id', 'xrshhwwc3emqcg9qg3cy')
                    CredentialService.set_credential('tuya', 'api', 'client_secret', 'b5403f48d7164ea1aab97391dd1a38b6')
                    CredentialService.set_credential('tuya', 'api', 'endpoint', 'https://openapi.tuyaeu.com')
                    CredentialService.set_credential('tuya', 'device', 'default_id', 'bf218614d2eb8bab41z4cs')
                    
                    logger.info("Stored API credentials in the database")
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")

def get_current_user():
    return User.query.filter_by(is_current=True).first()

def init_scheduler():
    """Initialize the background job scheduler and register default jobs"""
    global scheduler
    
    # Import here to avoid circular imports
    from jobs import scheduler as job_scheduler
    from jobs import register_job, check_active_passcodes, sync_ttlock_data
    
    # Start the scheduler
    job_scheduler.start()
    scheduler = job_scheduler
    logger.info("Started background job scheduler")
    
    # Register default jobs
    with app.app_context():
        # Job to check active passcodes and update LED status
        register_job(
            job_id='check_active_passcodes',
            name='Check Active Passcodes',
            description='Check if any passcodes are active and update LED status accordingly',
            interval=5,
            interval_type='minutes',
            job_function=check_active_passcodes
        )
        
        # Job to sync TTLock data
        register_job(
            job_id='sync_ttlock_data',
            name='Sync TTLock Data',
            description='Sync lock and passcode data from TTLock API',
            interval=30,
            interval_type='minutes',
            job_function=sync_ttlock_data
        )
        
        logger.info("Registered default background jobs")

# Deprecated functions - replaced by scheduled jobs
def check_active_passcodes():
    """
    Check passcode status and handle LED control
    Returns:
        bool: True if there are active passcodes, False otherwise
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Get all guests with valid passcodes
        active_guests = Guest.query.filter(
            Guest.start_date <= now,
            Guest.end_date >= now
        ).all()
        
        # Clean up expired guests
        expired_guests = Guest.query.filter(
            Guest.end_date < now
        ).all()
        
        if expired_guests:
            logger.info(f"Found {len(expired_guests)} expired guest(s)")
            for guest in expired_guests:
                logger.info(f"Removing expired guest: {guest.name}, end date: {guest.end_date}")
                db.session.delete(guest)
            db.session.commit()
            
            # Force LED update when guests expire
            tuya = TuyaAdapter()
            if not active_guests:  # No active guests left
                logger.info("No active guests remaining, turning off LED")
                tuya.control_led(False)
        
        return bool(active_guests)
        
    except Exception as e:
        logger.error(f"Error in check_active_passcodes: {e}")
        return False

def update_led_status():
    """Update LED status based on active passcodes"""
    with app.app_context():
        try:
            has_active_passcodes = check_active_passcodes()
            tuya = TuyaAdapter()
            
            # Get current LED status
            current_led_status = tuya.get_device_status()
            logger.info(f"Current LED status: {current_led_status}, Active passcodes: {has_active_passcodes}")
            
            if has_active_passcodes != current_led_status:
                success = tuya.control_led(has_active_passcodes)
                if success:
                    logger.info(f"LED status updated: {'ON' if has_active_passcodes else 'OFF'}")
                else:
                    logger.error("Failed to update LED status")
                    
        except Exception as e:
            logger.error(f"Error in update_led_status: {e}")

@app.route('/', methods=['GET'])
def index():
    guests = Guest.query.all()
    current_user = get_current_user()
    
    # Update LED status immediately
    update_led_status()
    
    # Get current LED status for display
    tuya = TuyaAdapter()
    led_status = tuya.get_device_status()
    
    # Get system status
    system_status = SystemStatus.query.first()
    if not system_status:
        system_status = SystemStatus()
        db.session.add(system_status)
        db.session.commit()
    
    # Get current LED status from system status
    led_status = system_status.led_status
    
    # Get device mappings
    device_mappings = LockDeviceMapping.query.all()
    
    return render_template(
        'index.html', 
        guests=guests, 
        current_user=current_user, 
        led_status=led_status,
        system_status=system_status.to_dict(),
        device_mappings=device_mappings
    )

@app.route('/check_lock', methods=['POST'])
def check_lock():
    """Check lock status and return JSON data"""
    try:
        # Use the TTLock adapter with multi-account support
        ttlock = TTLockAdapter()
        
        # Get all locks from all accounts
        locks = ttlock.get_lock_list()
        
        if not locks:
            logger.warning("No locks found in any TTLock account")
            return jsonify({'error': 'No locks found or error connecting to TTLock API'})
            
        # Process lock data
        lock_data = []
        for lock in locks:
            # Get lock status for each lock
            lock_id = lock.get('lockId')
            lock_status = ttlock.get_lock_status(lock_id)
            
            lock_info = {
                'id': lock_id,
                'name': lock.get('lockName', 'Unknown Lock'),
                'battery': lock.get('electricQuantity', 0),
                'status': 'Online' if lock.get('lockStatus') == 1 else 'Offline'
            }
            
            # Add additional status info if available
            if lock_status and 'state' in lock_status:
                lock_info['state'] = lock_status.get('state', 0)
                lock_info['state_text'] = 'Locked' if lock_status.get('state') == 0 else 'Unlocked'
            else:
                lock_info['state'] = None  # Handle case where status is not available
                lock_info['state_text'] = 'Unknown'  # Default state text if status is not available
            
            lock_data.append(lock_info)

        return jsonify({'lock_status': lock_data})  # Return processed lock data as JSON
        
    except Exception as e:
        logger.error(f"Error checking locks: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'An error occurred while checking locks. Please try again later.'}), 500

@app.route('/delete_guest/<int:guest_id>', methods=['POST'])
def delete_guest(guest_id):
    try:
        guest = Guest.query.get_or_404(guest_id)
        
        # Get current user credentials
        current_user = get_current_user()
        if not current_user:
            return jsonify({'error': 'No current user found'}), 400
            
        # Create TTLock manager instance
        manager = TTLockManager(
            client_id=CredentialService.get_credential('ttlock', 'api', 'client_id'),
            client_secret=CredentialService.get_credential('ttlock', 'api', 'client_secret'),
            username=current_user.username,
            password=current_user.password
        )
        
        # Get access token
        token_info = manager.get_access_token()
        if not token_info or not token_info.get('access_token'):
            return jsonify({'error': 'Failed to get access token'}), 400
            
        # Get passcode ID from TTLock API
        passcodes = manager.list_passcodes(guest.lock_id)
        passcode_id = None
        
        for code in passcodes.get('list', []):
            if code.get('keyboardPwd') == guest.passcode:
                passcode_id = code.get('keyboardPwdId')
                break
                
        if not passcode_id:
            return jsonify({'error': 'Passcode not found in TTLock system'}), 400
            
        # Delete passcode from TTLock
        delete_result = manager.delete_passcode(
            lock_id=guest.lock_id,
            keyboard_pwd_id=passcode_id
        )
        
        if not delete_result or delete_result.get('errcode') != 0:
            return jsonify({'error': 'Failed to delete passcode from TTLock'}), 400
            
        # Delete guest from database
        db.session.delete(guest)
        db.session.commit()
        
        # Update LED status after deleting guest
        update_led_status()
        
        # Update README after deletion
        update_readme()
        
        return jsonify({'message': 'Guest and passcode deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/sync_guests', methods=['POST'])
def sync_guests():
    try:
        # Get credentials from current user or form
        current_user = get_current_user()
        username = current_user.username if current_user else request.form.get('username')
        password = current_user.password if current_user else request.form.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Credentials not found'}), 400
        
        # Create TTLock manager instance
        manager = TTLockManager(
            client_id=CredentialService.get_credential('ttlock', 'api', 'client_id'),
            client_secret=CredentialService.get_credential('ttlock', 'api', 'client_secret'),
            username=username,
            password=password
        )
        
        # Get access token
        token_info = manager.get_access_token()
        if not token_info.get('access_token'):
            return jsonify({'error': 'Invalid credentials'}), 400
            
        # Get all locks
        locks_data = manager.list_locks()
        
        # Dictionary to store all valid passcodes
        valid_passcodes = {}
        
        # Get passcodes for each lock
        for lock in locks_data.get('list', []):
            lock_id = lock['lockId']
            passcodes = manager.list_passcodes(lock_id)
            
            for code in passcodes.get('list', []):
                if code.get('keyboardPwdType') == 3:  # Only process temporary passcodes
                    start_date = datetime.fromtimestamp(code['startDate']/1000, timezone.utc)
                    end_date = datetime.fromtimestamp(code['endDate']/1000, timezone.utc)
                    valid_passcodes[code['keyboardPwd']] = {
                        'name': code.get('keyboardPwdName', 'Guest'),
                        'start_date': start_date,
                        'end_date': end_date,
                        'lock_id': lock_id
                    }
        
        # Update database
        with app.app_context():
            # Remove guests whose passcodes are no longer in the lock
            Guest.query.filter(~Guest.passcode.in_(valid_passcodes.keys())).delete(synchronize_session=False)
            
            # Update or add guests from valid passcodes
            for passcode, info in valid_passcodes.items():
                guest = Guest.query.filter_by(passcode=passcode).first()
                
                if guest:
                    # Update existing guest
                    guest.name = info['name']
                    guest.start_date = info['start_date']
                    guest.end_date = info['end_date']
                    guest.lock_id = info['lock_id']
                else:
                    # Create new guest
                    guest = Guest(
                        name=info['name'],
                        passcode=passcode,
                        start_date=info['start_date'],
                        end_date=info['end_date'],
                        lock_id=info['lock_id']
                    )
                    db.session.add(guest)
            
            db.session.commit()
            
            # Update LED status after syncing guests
            update_led_status()
        
        # Update README
        update_readme()
        
        return jsonify({'message': 'Sync completed successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/get_locks', methods=['GET'])
def get_locks():
    """Get all locks from TTLock accounts"""
    try:
        # Create TTLock adapter instance with multi-account support
        ttlock = TTLockAdapter()
        
        # Get all locks from all accounts
        locks = ttlock.get_lock_list()
        
        if not locks:
            logger.warning("No locks found in any TTLock account")
            return jsonify({'locks': []})
            
        # Format locks for dropdown
        lock_list = []
        for lock in locks:
            lock_list.append({
                'id': lock.get('lockId'),
                'name': lock.get('lockName', 'Unnamed Lock'),
                'alias': lock.get('lockAlias', ''),
                'battery': lock.get('electricQuantity', 0)
            })
            
        logger.info(f"Retrieved {len(lock_list)} locks from all TTLock accounts")
        return jsonify({'locks': lock_list})
        
    except Exception as e:
        logger.error(f"Error getting locks: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 400

@app.route('/device_mappings', methods=['GET'])
def get_device_mappings():
    """Get all device mappings"""
    try:
        with app.app_context():
            mappings = LockDeviceMapping.query.all()
            return jsonify([mapping.to_dict() for mapping in mappings])
    except Exception as e:
        logger.error(f"Error getting device mappings: {str(e)}")
        return jsonify({'error': str(e), 'message': 'Failed to retrieve device mappings'}), 500

@app.route('/get_device_mappings', methods=['GET'])
def get_device_mappings_legacy():
    """Legacy endpoint for getting device mappings - redirects to /device_mappings"""
    logger.info("Legacy endpoint /get_device_mappings called, redirecting to /device_mappings")
    return get_device_mappings()

@app.route('/link_device', methods=['POST'])
def link_device():
    """Link a TTLock ID with a Tuya device ID"""
    try:
        data = request.get_json()
        if not data or 'lock_id' not in data or 'device_id' not in data:
            return jsonify({'error': 'Missing required fields'}), 400

        tuya = TuyaAdapter()
        result = tuya.link_device(
            lock_id=data['lock_id'],
            device_id=data['device_id'],
            lock_name=data.get('lock_name'),
            device_name=data.get('device_name'),
            skip_validation=True  # Skip validation to avoid API errors
        )
        
        # Update LED status after linking
        update_led_status()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/unlink_device/<lock_id>', methods=['DELETE', 'POST'])
def unlink_device(lock_id):
    """Unlink a TTLock ID from its Tuya device"""
    try:
        tuya = TuyaAdapter()
        result = tuya.unlink_device(lock_id)
        
        # Update LED status after unlinking
        update_led_status()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/toggle_led', methods=['POST'])
def toggle_led():
    """Toggle LED state manually"""
    try:
        data = request.json
        lock_id = data.get('lock_id')
        state = data.get('state')
        
        if lock_id is None or state is None:
            return jsonify({'status': 'error', 'message': 'Missing lock_id or state parameter'}), 400
        
        # Convert string state to boolean
        if isinstance(state, str):
            state = state.lower() == 'true'
        
        # Get the mapping for this lock
        mapping = LockDeviceMapping.query.filter_by(lock_id=lock_id).first()
        if not mapping:
            return jsonify({'status': 'error', 'message': f'No device mapping found for lock ID: {lock_id}'}), 404
        
        # Initialize Tuya manager
        tuya_manager = TuyaAdapter()
        
        # Log the request details
        print(f"--- LED Control Request ---")
        print(f"Lock ID: {lock_id}")
        print(f"Device ID: {mapping.device_id}")
        print(f"Requested state: {state}")
        
        # Control LED
        success = tuya_manager.control_led(state, lock_id)
        
        # Log the response
        print(f"--- LED Control Response ---")
        print(f"Success: {success}")
        
        if success:
            # Get updated LED status
            led_status = tuya_manager.get_device_status(lock_id)
            
            print(f"LED turned {'ON' if led_status else 'OFF'} for lock {lock_id}")
            return jsonify({
                'status': 'success', 
                'led_state': led_status
            }), 200
        else:
            print(f"Failed to control LED for lock {lock_id}")
            return jsonify({'status': 'error', 'message': 'Failed to control LED'}), 500
    except Exception as e:
        import traceback
        print(f"--- LED Control Error ---")
        print(f"Error toggling LED: {e}")
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/device/<device_id>/light/status')
def get_light_status(device_id):
    """Get the current status of a device's light"""
    app.logger.info(f"Fetching light status for device {device_id}")
    
    try:
        # Get the device status from Tuya API
        response = get_device_status(device_id)
        if response['success']:
            app.logger.debug(f"Successfully retrieved light status for device {device_id}: {response['status']}")
            return jsonify({
                'success': True,
                'status': response['status'],
                'raw_response': response.get('raw_response', {}),
                'cached': response.get('cached', False)
            })
        else:
            error_msg = f"Error getting light status for device {device_id}: {response.get('error', 'Unknown error')}"
            app.logger.error(error_msg)
            return jsonify({
                'success': False,
                'error': response.get('error', 'Unknown error'),
                'raw_response': response.get('raw_response', {}),
                'cached': response.get('cached', False)
            }), 500
    except Exception as e:
        error_msg = f"Unexpected error getting light status for device {device_id}: {str(e)}"
        app.logger.exception(error_msg)
        return jsonify({
            'success': False,
            'error': str(e),
            'details': error_msg
        }), 500

@app.route('/device/<device_id>/light/toggle', methods=['POST'])
def toggle_light(device_id):
    """Toggle a device's light on or off"""
    app.logger.info(f"Toggling light for device {device_id}")
    
    try:
        data = request.get_json()
        desired_state = data.get('state')  # True for ON, False for OFF
        
        # Toggle the device using Tuya API
        response = toggle_device(device_id, turn_on=desired_state)
        
        if response['success']:
            app.logger.info(f"Successfully toggled light for device {device_id} to {desired_state}")
            return jsonify({
                'success': True,
                'status': response['status'],
                'raw_response': response.get('raw_response', {}),
                'message': f"Successfully turned {'ON' if desired_state else 'OFF'} the light"
            })
        else:
            error_msg = f"Error toggling light for device {device_id}: {response.get('error', 'Unknown error')}"
            app.logger.error(error_msg)
            return jsonify({
                'success': False,
                'error': response.get('error', 'Unknown error'),
                'raw_response': response.get('raw_response', {}),
                'details': error_msg
            }), 500
    except Exception as e:
        error_msg = f"Unexpected error toggling light for device {device_id}: {str(e)}"
        app.logger.exception(error_msg)
        return jsonify({
            'success': False,
            'error': str(e),
            'details': error_msg
        }), 500

def update_readme():
    """Update README.md with current guest information"""
    try:
        guests = Guest.query.all()
        
        readme_content = """# TTLock Manager

A modern web application for managing TTLock smart locks and guest access.

## Features
- Real-time lock status monitoring
- Guest access management
- Temporary passcode creation
- Access history tracking
- LED indicator for active passcodes

## Current Active Guests
"""
        
        for guest in guests:
            readme_content += f"""
### {guest.name}
- Passcode: {guest.passcode}
- Duration: {guest.start_date.strftime('%Y-%m-%d %H:%M')} to {guest.end_date.strftime('%Y-%m-%d %H:%M')}
- Lock ID: {guest.lock_id}
"""
        
        with open('README.md', 'w') as f:
            f.write(readme_content)
            
    except Exception as e:
        print(f"Error updating README: {e}")

# TTLock account management routes
@app.route('/ttlock/accounts', methods=['GET'])
def ttlock_accounts():
    """View all TTLock accounts"""
    try:
        # Get all credential types for TTLock provider
        credential_types = CredentialService.get_all_credential_types_by_provider('ttlock')
        
        # Find account credential types (excluding 'api' which is for API settings)
        account_types = [ctype for ctype in credential_types if ctype != 'api']
        
        # Get account details
        accounts = []
        for account_type in account_types:
            try:
                username = CredentialService.get_credential('ttlock', account_type, 'username')
                if username:
                    accounts.append({
                        'id': account_type,
                        'username': username
                    })
            except Exception as e:
                app.logger.error(f"Error retrieving TTLock account {account_type}: {str(e)}")
                import traceback
                app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        return render_template('ttlock_accounts.html', accounts=accounts)
    except Exception as e:
        app.logger.error(f"Error loading TTLock accounts page: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return render_template('error.html', error="Failed to load TTLock accounts. Please check the logs for details.")

@app.route('/ttlock/accounts/add', methods=['GET', 'POST'])
def add_ttlock_account():
    """Add a new TTLock account"""
    if request.method == 'POST':
        try:
            account_id = request.form.get('account_id', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            
            # Validate input
            errors = []
            if not account_id:
                errors.append("Account ID is required")
            elif not account_id.isalnum():
                errors.append("Account ID must contain only letters and numbers")
                
            if not username:
                errors.append("Username is required")
            if not password:
                errors.append("Password is required")
                
            if errors:
                return render_template('add_ttlock_account.html', 
                                      error="<br>".join(errors), 
                                      account_id=account_id,
                                      username=username)
            
            # Check if account already exists
            try:
                existing_username = CredentialService.get_credential('ttlock', account_id, 'username')
                if existing_username:
                    return render_template('add_ttlock_account.html', 
                                          error=f"Account ID '{account_id}' already exists",
                                          account_id=account_id,
                                          username=username)
            except:
                # Account doesn't exist, which is what we want
                pass
                
            # Add account to the TTLock adapter
            success = ttlock_adapter.add_account(account_id, username, password)
            
            if success:
                flash(f"Successfully added TTLock account: {account_id}", "success")
                return redirect(url_for('ttlock_accounts'))
            else:
                return render_template('add_ttlock_account.html', 
                                      error="Failed to add account. Check the logs for details.",
                                      account_id=account_id,
                                      username=username)
        except Exception as e:
            app.logger.error(f"Error adding TTLock account: {str(e)}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            return render_template('add_ttlock_account.html', 
                                  error="An unexpected error occurred. Please check the logs for details.",
                                  account_id=account_id if 'account_id' in locals() else '',
                                  username=username if 'username' in locals() else '')
    else:
        return render_template('add_ttlock_account.html')

@app.route('/ttlock/accounts/delete/<account_id>', methods=['POST'])
def delete_ttlock_account(account_id):
    """Delete a TTLock account"""
    try:
        # Don't allow deleting the 'api' credentials
        if account_id == 'api':
            flash("Cannot delete API credentials", "error")
            return redirect(url_for('ttlock_accounts'))
        
        # Verify account exists before deleting
        try:
            username = CredentialService.get_credential('ttlock', account_id, 'username')
            if not username:
                flash(f"Account {account_id} not found", "error")
                return redirect(url_for('ttlock_accounts'))
        except Exception as e:
            app.logger.warning(f"Account {account_id} not found when attempting to delete: {str(e)}")
            flash(f"Account {account_id} not found", "error")
            return redirect(url_for('ttlock_accounts'))
            
        # Delete credentials from database with transaction
        try:
            db.session.begin_nested()  # Create a savepoint
            CredentialService.delete_credentials_by_type('ttlock', account_id)
            db.session.commit()
            
            # Remove from account manager
            if hasattr(ttlock_adapter, '_account_manager'):
                ttlock_adapter._account_manager.remove_account(account_id)
                
            flash(f"Successfully deleted TTLock account: {account_id}", "success")
        except Exception as db_error:
            db.session.rollback()
            app.logger.error(f"Database error deleting TTLock account {account_id}: {str(db_error)}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            flash(f"Error deleting account: Database operation failed", "error")
            
        return redirect(url_for('ttlock_accounts'))
    except Exception as e:
        app.logger.error(f"Error deleting TTLock account {account_id}: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f"Error deleting account: An unexpected error occurred", "error")
        return redirect(url_for('ttlock_accounts'))

@app.route('/ttlock/accounts/test/<account_id>', methods=['POST'])
def test_ttlock_account(account_id):
    """Test a TTLock account by retrieving locks"""
    try:
        # Verify account exists before testing
        try:
            username = CredentialService.get_credential('ttlock', account_id, 'username')
            if not username:
                flash(f"Account {account_id} not found", "error")
                return redirect(url_for('ttlock_accounts'))
        except Exception as e:
            app.logger.warning(f"Account {account_id} not found when attempting to test: {str(e)}")
            flash(f"Account {account_id} not found", "error")
            return redirect(url_for('ttlock_accounts'))
            
        # Get locks for this account
        locks = ttlock_adapter._account_manager.get_account_locks(account_id)
        
        if locks:
            flash(f"Successfully retrieved {len(locks)} locks for account {account_id}", "success")
        else:
            flash(f"No locks found for account {account_id} or authentication failed", "warning")
        
        return redirect(url_for('ttlock_accounts'))
    except Exception as e:
        app.logger.error(f"Error testing TTLock account {account_id}: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f"Error testing account: An unexpected error occurred", "error")
        return redirect(url_for('ttlock_accounts'))

# ==========================================
# Job Management Endpoints
# ==========================================

@app.route('/jobs', methods=['GET'])
def jobs_dashboard():
    """Render the jobs dashboard page"""
    from jobs import get_all_jobs, get_recent_executions
    
    jobs = get_all_jobs()
    recent_executions = get_recent_executions(limit=20)
    system_status = SystemStatus.query.first()
    
    return render_template(
        'jobs.html', 
        jobs=jobs, 
        executions=recent_executions,
        system_status=system_status.to_dict() if system_status else None
    )

@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """API endpoint to get all job definitions"""
    from jobs import get_all_jobs
    
    try:
        jobs = get_all_jobs()
        return jsonify({'jobs': jobs})
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """API endpoint to get a specific job definition"""
    from jobs import get_job_info
    
    try:
        job = get_job_info(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(job)
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/executions', methods=['GET'])
def get_job_executions(job_id):
    """API endpoint to get executions of a specific job"""
    from jobs import get_recent_executions
    
    try:
        limit = request.args.get('limit', 10, type=int)
        executions = get_recent_executions(job_id=job_id, limit=limit)
        return jsonify({'executions': executions})
    except Exception as e:
        logger.error(f"Error getting executions for job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/pause', methods=['POST'])
def pause_job_endpoint(job_id):
    """API endpoint to pause a job"""
    from jobs import pause_job, get_job_info
    
    try:
        pause_job(job_id)
        job = get_job_info(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(job)
    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/resume', methods=['POST'])
def resume_job_endpoint(job_id):
    """API endpoint to resume a paused job"""
    from jobs import resume_job, get_job_info
    
    try:
        resume_job(job_id)
        job = get_job_info(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(job)
    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/run', methods=['POST'])
def run_job_now(job_id):
    """API endpoint to run a job immediately"""
    try:
        # Get the job instance from scheduler
        if not scheduler:
            return jsonify({'error': 'Scheduler not initialized'}), 500
            
        job = scheduler.get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        # Run the job
        job.modify(next_run_time=datetime.now())
        
        return jsonify({'message': f'Job {job_id} scheduled to run now'})
    except Exception as e:
        logger.error(f"Error running job {job_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """API endpoint to get the current system status"""
    try:
        status = SystemStatus.query.first()
        if not status:
            status = SystemStatus()
            db.session.add(status)
            db.session.commit()
            
        return jsonify(status.to_dict())
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/demo-request', methods=['POST'])
def demo_request():
    # Accept demo request form submissions and email them
    data = request.get_json(silent=True) or request.form.to_dict()
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    building = (data.get('building') or '').strip()
    units = (data.get('units') or '').strip()
    notes = (data.get('notes') or '').strip()

    if not name or not email:
        return jsonify({'error': 'Name and email are required.'}), 400

    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')
    smtp_starttls = os.getenv('SMTP_STARTTLS', 'true').lower() in ('1', 'true', 'yes')
    mail_to = os.getenv('DEMO_MAIL_TO', 'ahmad@bareq.site')
    mail_from = os.getenv('DEMO_MAIL_FROM', 'Bareq Demo <no-reply@bareq.site>')

    if not smtp_host or not mail_to or not mail_from:
        logger.error('SMTP_HOST/DEMO_MAIL_TO/DEMO_MAIL_FROM not configured')
        return jsonify({'error': 'Email service is not configured yet.'}), 500

    msg = EmailMessage()
    msg['Subject'] = 'Bareq demo request'
    msg['From'] = mail_from
    msg['To'] = mail_to
    body = (
        f'New demo request:\n\n'
        f'Name: {name}\n'
        f'Email: {email}\n'
        f'Building type: {building}\n'
        f'Units: {units}\n'
        f'Notes: {notes}\n'
    )
    msg.set_content(body)

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
            if smtp_starttls:
                smtp.starttls()
            if smtp_user and smtp_pass:
                smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
    except Exception as e:
        logger.error(f'Failed to send demo request email: {e}')
        return jsonify({'error': 'Failed to send email.'}), 500

    return jsonify({'ok': True})

if __name__ == '__main__':
    init_scheduler()
    app.run(debug=True, port=5000)
