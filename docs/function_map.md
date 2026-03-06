# RettLock Info - Function Map

## Web Application Core (web_app.py)

### Main Routes
- `index()`: Main dashboard view
  - Displays device mappings
  - Shows lock status
  - Handles LED control

### Device Management
- `get_device_mappings()`: Fetch all device mappings
- `get_device_mappings_legacy()`: Legacy endpoint for backward compatibility
- `link_device()`: Associate TTLock with Tuya device
- `unlink_device(lock_id)`: Remove device mapping

### Lock Operations
- `check_lock()`: Get lock status
- `get_locks()`: List all available locks
- `sync_guests()`: Synchronize guest access
- `delete_guest(guest_id)`: Remove guest access

### Light Control
- `get_light_status(device_id)`: Get device light state
- `toggle_light(device_id)`: Toggle device light
- `toggle_led()`: Manual LED control

### Account Management
- `ttlock_accounts()`: View TTLock accounts
- `add_ttlock_account()`: Add new TTLock account
- `delete_ttlock_account(account_id)`: Remove TTLock account
- `test_ttlock_account(account_id)`: Validate account

## Background Jobs (jobs.py)

### Scheduled Tasks
- `check_active_passcodes()`: Monitor passcode status
- `update_led_status()`: Update LED based on passcodes
- `sync_guests_job()`: Periodic guest synchronization
- `cleanup_expired_passcodes()`: Remove old passcodes

## Services

### Authentication (auth_service.py)
- `get_current_user()`: Get logged in user
- `login_user(username, password)`: User authentication
- `logout_user()`: End user session

### Audit (audit_service.py)
- `log_activity(action, details)`: Record system events
- `get_audit_logs()`: Retrieve activity history

### Credentials (credential_service.py)
- `get_credentials(provider)`: Get API credentials
- `save_credentials(provider, data)`: Store API credentials
- `validate_credentials(provider)`: Check credential validity

## API Adapters

### TTLock (ttlock_adapter.py)
- `get_token()`: Get API access token
- `get_lock_list()`: List available locks
- `get_lock_status(lock_id)`: Check lock state
- `add_passcode(lock_id, passcode)`: Create new passcode
- `delete_passcode(lock_id, passcode_id)`: Remove passcode

### Tuya (tuya_adapter.py)
- `get_device_status()`: Get device state
- `set_device_status(device_id, status)`: Update device
- `toggle_device(device_id)`: Toggle device state
- `get_device_info(device_id)`: Get device details

## Database Models (models.py)

### Core Models
- `Guest`: Guest access records
- `LockDeviceMapping`: TTLock-Tuya associations
- `TTLockAccount`: TTLock account credentials
- `SystemStatus`: Global system state
- `AuditLog`: Activity tracking

### Model Operations
- `to_dict()`: Convert model to dictionary
- `from_dict(data)`: Create model from dictionary
- `validate()`: Validate model data
- `save()`: Persist model changes
