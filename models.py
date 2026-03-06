from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'is_current': self.is_current,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    passcode = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    lock_id = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        now = datetime.utcnow()
        is_currently_active = self.start_date <= now <= self.end_date
        
        return {
            'id': self.id,
            'name': self.name,
            'passcode': self.passcode,
            'start_date': self.start_date.strftime('%Y-%m-%d %H:%M'),
            'end_date': self.end_date.strftime('%Y-%m-%d %H:%M'),
            'lock_id': self.lock_id,
            'is_active': is_currently_active
        }

class LockDeviceMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lock_id = db.Column(db.String(50), nullable=False, unique=True)
    device_id = db.Column(db.String(50), nullable=False, unique=True)
    lock_name = db.Column(db.String(100))
    device_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'lock_id': self.lock_id,
            'device_id': self.device_id,
            'lock_name': self.lock_name,
            'device_name': self.device_name,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M')
        }

class JobExecution(db.Model):
    """Tracks the execution of scheduled jobs"""
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, running, success, error
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    result = db.Column(db.Text, nullable=True)
    error = db.Column(db.Text, nullable=True)
    execution_time = db.Column(db.Float, nullable=True)  # in seconds
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'status': self.status,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time
        }

class JobDefinition(db.Model):
    """Defines scheduled jobs and their configuration"""
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    interval = db.Column(db.Integer, nullable=False)  # in seconds
    interval_type = db.Column(db.String(20), nullable=False)  # seconds, minutes, hours, days
    last_run = db.Column(db.DateTime, nullable=True)
    next_run = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'name': self.name,
            'description': self.description,
            'interval': self.interval,
            'interval_type': self.interval_type,
            'last_run': self.last_run.strftime('%Y-%m-%d %H:%M:%S') if self.last_run else None,
            'next_run': self.next_run.strftime('%Y-%m-%d %H:%M:%S') if self.next_run else None,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class ApiCredential(db.Model):
    """Stores API credentials for different services"""
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)  # 'tuya', 'ttlock', etc.
    credential_type = db.Column(db.String(50), nullable=False)  # 'api', 'account', etc.
    credential_key = db.Column(db.String(100), nullable=False)  # Specific key name
    credential_value = db.Column(db.Text, nullable=False)  # The actual value (encrypted)
    is_encrypted = db.Column(db.Boolean, default=True)  # Whether the value is encrypted
    description = db.Column(db.String(255))  # Human-readable description
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('provider', 'credential_type', 'credential_key', name='unique_credential'),
    )
    
    def to_dict(self, include_value=False):
        result = {
            'id': self.id,
            'provider': self.provider,
            'credential_type': self.credential_type,
            'credential_key': self.credential_key,
            'description': self.description,
            'is_active': self.is_active,
            'is_encrypted': self.is_encrypted,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }
        # Only include the actual credential value when explicitly requested
        if include_value:
            result['credential_value'] = self.credential_value
        return result

class SystemStatus(db.Model):
    """Tracks the overall system status and key metrics"""
    id = db.Column(db.Integer, primary_key=True)
    led_status = db.Column(db.Boolean, default=False)
    locks_count = db.Column(db.Integer, default=0)
    active_passcodes_count = db.Column(db.Integer, default=0)
    last_sync_time = db.Column(db.DateTime, nullable=True)
    last_sync_status = db.Column(db.String(20), nullable=True)  # success, error
    last_led_update = db.Column(db.DateTime, nullable=True)
    api_status = db.Column(db.String(20), default='unknown')  # up, down, unknown
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'led_status': self.led_status,
            'locks_count': self.locks_count,
            'active_passcodes_count': self.active_passcodes_count,
            'last_sync_time': self.last_sync_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_sync_time else None,
            'last_sync_status': self.last_sync_status,
            'last_led_update': self.last_led_update.strftime('%Y-%m-%d %H:%M:%S') if self.last_led_update else None,
            'api_status': self.api_status,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

class AuditLog(db.Model):
    """Tracks changes to sensitive data like credentials"""
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(20), nullable=False)  # 'create', 'update', 'delete', 'access'
    resource_type = db.Column(db.String(50), nullable=False)  # 'credential', 'user', etc.
    resource_id = db.Column(db.Integer, nullable=True)  # ID of the affected resource
    resource_name = db.Column(db.String(255), nullable=True)  # Name/identifier of the resource
    user_id = db.Column(db.Integer, nullable=True)  # User who performed the action, if authenticated
    ip_address = db.Column(db.String(50), nullable=True)  # IP address of the client
    details = db.Column(db.Text, nullable=True)  # Additional details about the action
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'details': self.details,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None
        }
