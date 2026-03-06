from flask import Flask
from services.credential_service import CredentialService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('update_credentials')

# Create a minimal Flask app for context
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lockinfo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import models after creating app
from models import db
db.init_app(app)

def update_ttlock_credentials():
    """Update TTLock API credentials in the database"""
    with app.app_context():
        # Update API credentials
        logger.info("Updating TTLock API credentials in database...")
        
        # Set correct client ID
        CredentialService.set_credential(
            'ttlock', 'api', 'client_id', 
            "a67f3b3552a64b0c81aa5e3b2a19dffb"
        )
        logger.info("Updated client_id")
        
        # Set correct client secret
        CredentialService.set_credential(
            'ttlock', 'api', 'client_secret', 
            "8db22fad0b66cc784b06cbddc1ccab9a"
        )
        logger.info("Updated client_secret")
        
        # Set correct base URL
        CredentialService.set_credential(
            'ttlock', 'api', 'base_url', 
            "https://euapi.ttlock.com"
        )
        logger.info("Updated base_url")
        
        # Check if we have any TTLock accounts
        account_types = CredentialService.get_all_credential_types_by_provider('ttlock')
        account_types = [ctype for ctype in account_types if ctype != 'api']
        
        if account_types:
            logger.info(f"Found {len(account_types)} existing TTLock account types")
            # We have accounts, no need to create a default one
        else:
            # Create a default account if none exists
            logger.info("No TTLock accounts found, creating default account")
            
            # Use the working TTLock credentials
            CredentialService.set_credential('ttlock', 'account1', 'username', "a7mdoh@hotmail.com")
            CredentialService.set_credential('ttlock', 'account1', 'password', "Aa@112233123")
            
            logger.info("Created default TTLock account")
        
        logger.info("TTLock API credentials updated successfully")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    update_ttlock_credentials()
    logger.info("Credential update completed")