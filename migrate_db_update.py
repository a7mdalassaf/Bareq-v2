"""
Database migration script to update the schema with new fields
"""
import os
import sys
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('db_migration')

def migrate_database(db_path):
    """Perform database migrations on the specified database"""
    logger.info(f"Migrating database at {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        
        # Add is_admin column to User table
        add_column_if_not_exists(conn, 'user', 'is_admin', 'BOOLEAN DEFAULT 0')
        
        # Add is_encrypted column to api_credential table if it exists
        try:
            add_column_if_not_exists(conn, 'api_credential', 'is_encrypted', 'BOOLEAN DEFAULT 1')
        except Exception as e:
            logger.warning(f"Could not add is_encrypted column to api_credential: {str(e)}")
        
        # Create audit_log table if it doesn't exist
        try:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id INTEGER,
                resource_name TEXT,
                user_id INTEGER,
                ip_address TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
        except Exception as e:
            logger.warning(f"Could not create audit_log table: {str(e)}")
        
        conn.commit()
        conn.close()
        
        logger.info("Database migration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        return False

def add_column_if_not_exists(conn, table, column, column_type):
    """Add a column to a table if it doesn't already exist"""
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    
    if column not in columns:
        logger.info(f"Adding column {column} to table {table}")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        conn.commit()
        return True
    else:
        logger.info(f"Column {column} already exists in table {table}")
        return False

if __name__ == "__main__":
    # Migrate the main database in the instance folder
    instance_db = "instance/lockinfo.db"
    ttlock_db = "instance/ttlock.db"
    
    success = False
    
    if os.path.exists(instance_db):
        success = migrate_database(instance_db)
        
    if os.path.exists(ttlock_db):
        ttlock_success = migrate_database(ttlock_db)
        success = success or ttlock_success
    
    sys.exit(0 if success else 1)
