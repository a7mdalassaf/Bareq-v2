#!/usr/bin/env python
import os
import sys
import datetime
from flask import Flask
from models import db, JobDefinition, JobExecution, SystemStatus, LockDeviceMapping

"""
Migration script to update database schema and initialize job tables
"""

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lockinfo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def migrate_database():
    """Create new tables and initialize data"""
    with app.app_context():
        print("Starting database migration...")
        
        # Create tables
        db.create_all()
        print("Created new tables")
        
        # Initialize SystemStatus if it doesn't exist
        system_status = SystemStatus.query.first()
        if not system_status:
            print("Initializing system status...")
            
            # Count active locks
            lock_count = LockDeviceMapping.query.filter_by(is_active=True).count()
            
            system_status = SystemStatus(
                led_status=False,
                locks_count=lock_count,
                active_passcodes_count=0,
                api_status="unknown",
                last_sync_time=None,
                last_sync_status=None
            )
            db.session.add(system_status)
            db.session.commit()
            print("System status initialized")
        
        # Initialize default job definitions if they don't exist
        if not JobDefinition.query.filter_by(job_id="check_active_passcodes").first():
            print("Creating default job definitions...")
            
            # Job to check active passcodes and control LED
            passcode_job = JobDefinition(
                job_id="check_active_passcodes",
                name="Check Active Passcodes",
                description="Check if any passcodes are active and update LED status accordingly",
                interval=5,
                interval_type="minutes",
                is_active=True,
                last_run=None,
                next_run=None
            )
            db.session.add(passcode_job)
            
            # Job to sync TTLock data
            sync_job = JobDefinition(
                job_id="sync_ttlock_data",
                name="Sync TTLock Data",
                description="Sync lock and passcode data from TTLock API",
                interval=30,
                interval_type="minutes",
                is_active=True,
                last_run=None,
                next_run=None
            )
            db.session.add(sync_job)
            
            db.session.commit()
            print("Default job definitions created")
        
        print("Database migration completed successfully!")

if __name__ == "__main__":
    try:
        migrate_database()
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)
