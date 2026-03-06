"""
Lock Status Model - Tracks the status history of locks
"""
from datetime import datetime
from models import db

class LockStatus(db.Model):
    """Model for tracking lock status history"""
    __tablename__ = 'lock_status'

    id = db.Column(db.Integer, primary_key=True)
    lock_id = db.Column(db.Integer, db.ForeignKey('lock_device_mapping.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # locked, unlocked, error
    battery_level = db.Column(db.Integer)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    error_code = db.Column(db.String(100))
    error_message = db.Column(db.Text)

    # Relationships
    lock = db.relationship('LockDeviceMapping', backref=db.backref('status_history', lazy=True))

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'lock_id': self.lock_id,
            'status': self.status,
            'battery_level': self.battery_level,
            'last_updated': self.last_updated.isoformat(),
            'error_code': self.error_code,
            'error_message': self.error_message
        } 