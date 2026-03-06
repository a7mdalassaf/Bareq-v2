"""
Tests for the Audit Service
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
from flask import Flask, request, session

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, AuditLog
from services.audit_service import AuditService
from app import create_app

class TestAuditService(unittest.TestCase):
    """Test cases for the Audit Service"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Set test config
        test_config = {
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SECRET_KEY': 'test_secret_key'
        }
        
        # Create app with test config
        self.app = create_app(test_config)
        self.client = self.app.test_client()
        
        # Create application context
        with self.app.app_context():
            # Create tables
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_log_action(self):
        """Test logging an action"""
        with self.app.app_context():
            # Log an action
            action = 'create'
            resource_type = 'credential'
            resource_id = 123
            resource_name = 'test_credential'
            details = {'key': 'value'}
            
            # Create a test request context
            with self.app.test_request_context('/'):
                # Log the action
                audit_log = AuditService.log_action(
                    action, resource_type, resource_id, resource_name, details
                )
                
                # Check that the audit log was created
                self.assertIsNotNone(audit_log)
                self.assertEqual(audit_log.action, action)
                self.assertEqual(audit_log.resource_type, resource_type)
                self.assertEqual(audit_log.resource_id, resource_id)
                self.assertEqual(audit_log.resource_name, resource_name)
                
                # Check that the audit log was stored in the database
                db_log = AuditLog.query.filter_by(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id
                ).first()
                
                self.assertIsNotNone(db_log)
                self.assertEqual(db_log.id, audit_log.id)
    
    def test_log_action_with_user(self):
        """Test logging an action with a user ID in the session"""
        with self.app.app_context():
            # Log an action with a user in the session
            action = 'update'
            resource_type = 'user'
            resource_id = 456
            resource_name = 'test_user'
            
            # Create a test request context
            with self.app.test_request_context('/'):
                # Set user ID in session
                with self.client.session_transaction() as sess:
                    sess['user_id'] = 789
                
                # Log the action
                audit_log = AuditService.log_action(
                    action, resource_type, resource_id, resource_name
                )
                
                # Check that the user ID was recorded
                self.assertEqual(audit_log.user_id, 789)
    
    def test_log_action_with_ip(self):
        """Test logging an action with an IP address"""
        with self.app.app_context():
            # Log an action with an IP address
            action = 'delete'
            resource_type = 'credential'
            resource_id = 789
            
            # Create a test request context with a remote address
            with self.app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
                # Log the action
                audit_log = AuditService.log_action(
                    action, resource_type, resource_id
                )
                
                # Check that the IP address was recorded
                self.assertEqual(audit_log.ip_address, '127.0.0.1')
    
    def test_log_action_with_sensitive_data(self):
        """Test logging an action with sensitive data that should be redacted"""
        with self.app.app_context():
            # Log an action with sensitive data
            action = 'create'
            resource_type = 'credential'
            resource_id = 123
            details = {
                'credential_value': 'secret_password',
                'other_data': 'not_sensitive'
            }
            
            # Create a test request context
            with self.app.test_request_context('/'):
                # Log the action
                audit_log = AuditService.log_action(
                    action, resource_type, resource_id, details=details
                )
                
                # Check that the sensitive data was redacted
                self.assertIn('"credential_value": "[REDACTED]"', audit_log.details)
                self.assertIn('"other_data": "not_sensitive"', audit_log.details)
                self.assertNotIn('secret_password', audit_log.details)
    
    def test_get_logs(self):
        """Test retrieving logs"""
        with self.app.app_context():
            # Create some test logs
            with self.app.test_request_context('/'):
                AuditService.log_action('create', 'credential', 1, 'cred1')
                AuditService.log_action('update', 'credential', 2, 'cred2')
                AuditService.log_action('delete', 'credential', 3, 'cred3')
                AuditService.log_action('create', 'user', 4, 'user1')
            
            # Get all logs
            all_logs = AuditService.get_logs()
            
            # Check that all logs are returned
            self.assertEqual(len(all_logs), 4)
            
            # Get logs by resource type
            credential_logs = AuditService.get_logs(resource_type='credential')
            
            # Check that only credential logs are returned
            self.assertEqual(len(credential_logs), 3)
            for log in credential_logs:
                self.assertEqual(log['resource_type'], 'credential')
            
            # Get logs by action
            create_logs = AuditService.get_logs(action='create')
            
            # Check that only create logs are returned
            self.assertEqual(len(create_logs), 2)
            for log in create_logs:
                self.assertEqual(log['action'], 'create')
            
            # Get logs by resource ID
            resource_logs = AuditService.get_logs(resource_id=2)
            
            # Check that only logs for resource ID 2 are returned
            self.assertEqual(len(resource_logs), 1)
            self.assertEqual(resource_logs[0]['resource_id'], 2)
    
    def test_error_handling(self):
        """Test error handling in log_action"""
        with self.app.app_context():
            # Mock db.session.commit to raise an exception
            with patch('models.db.session.commit', side_effect=Exception('Test error')):
                # Create a test request context
                with self.app.test_request_context('/'):
                    # Log an action (should handle the exception gracefully)
                    result = AuditService.log_action('create', 'credential', 1)
                    
                    # Check that the result is None (error occurred)
                    self.assertIsNone(result)
    
    def test_to_dict_method(self):
        """Test the to_dict method of AuditLog"""
        with self.app.app_context():
            # Create a test log
            with self.app.test_request_context('/'):
                audit_log = AuditService.log_action('create', 'credential', 1, 'cred1')
            
            # Convert to dict
            log_dict = audit_log.to_dict()
            
            # Check that all fields are included
            self.assertEqual(log_dict['id'], audit_log.id)
            self.assertEqual(log_dict['action'], audit_log.action)
            self.assertEqual(log_dict['resource_type'], audit_log.resource_type)
            self.assertEqual(log_dict['resource_id'], audit_log.resource_id)
            self.assertEqual(log_dict['resource_name'], audit_log.resource_name)
            self.assertEqual(log_dict['user_id'], audit_log.user_id)
            self.assertEqual(log_dict['ip_address'], audit_log.ip_address)
            self.assertEqual(log_dict['details'], audit_log.details)
            self.assertIsNotNone(log_dict['timestamp'])

if __name__ == '__main__':
    unittest.main()
