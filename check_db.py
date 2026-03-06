"""
Script to check database structure
"""
import os
import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('db_check')

def check_database(db_path):
    """Check database tables and structure"""
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get list of tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        logger.info(f"Tables in database: {tables}")
        
        # Check each table structure
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [(info[1], info[2]) for info in cursor.fetchall()]
            logger.info(f"Table {table} columns: {columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
        return False

if __name__ == "__main__":
    # Check all possible database files
    db_files = [
        'lockinfo.db',
        'instance/lockinfo.db',
        'instance/ttlock.db'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            logger.info(f"Checking database: {db_file}")
            check_database(db_file)
