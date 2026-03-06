from web_app import app
from models import db, LockDeviceMapping

def check_mappings():
    with app.app_context():
        # Check existing mappings
        mappings = LockDeviceMapping.query.all()
        print(f"Found {len(mappings)} device mappings:")
        
        for mapping in mappings:
            print(f"ID: {mapping.id}, Lock ID: {mapping.lock_id}, Device ID: {mapping.device_id}, Active: {mapping.is_active}")
        
        # If no active mappings, create one
        active_mappings = LockDeviceMapping.query.filter_by(is_active=True).all()
        if not active_mappings:
            print("\nNo active mappings found. Creating a default mapping...")
            
            # Create a default mapping
            default_mapping = LockDeviceMapping(
                lock_id="2000000001",  # Default lock ID
                device_id="bf218614d2eb8bab41z4cs",  # The device ID we've been using
                lock_name="SalonLock",
                device_name="SalonLED",
                is_active=True
            )
            
            db.session.add(default_mapping)
            db.session.commit()
            
            print(f"Created default mapping: Lock ID {default_mapping.lock_id} -> Device ID {default_mapping.device_id}")
        else:
            print(f"\nFound {len(active_mappings)} active mappings.")

if __name__ == "__main__":
    check_mappings()
