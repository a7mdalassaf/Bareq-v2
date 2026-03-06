"""
Tests for the Authentication Service
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
from flask import Flask, request, session

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, User
from services.auth_service import AuthService
from app import create_app

class TestAuthService(unittest.TestCase):
    """Test cases for the Authentication Service"""
    
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
            
            # Create a test user
            test_user = User(
                username='test_user',
                password=AuthService.hash_password('test_password'),
                is_admin=False
            )
            
            # Create a test admin
            test_admin = User(
                username='test_admin',
                password=AuthService.hash_password('admin_password'),
                is_admin=True
            )
            
            db.session.add(test_user)
            db.session.add(test_admin)
            db.session.commit()
    
    def tearDown(self):
        """Clean up after tests"""
        # Remove database
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_hash_password(self):
        """Test password hashing"""
        # Hash a password
        password = 'test_password'
        hashed = AuthService.hash_password(password)
        
        # Check that the hash is different from the original
        self.assertNotEqual(password, hashed)
        
        # Check that hashing the same password twice gives the same result
        hashed2 = AuthService.hash_password(password)
        self.assertEqual(hashed, hashed2)
    
    def test_verify_password(self):
        """Test password verification"""
        # Hash a password
        password = 'test_password'
        hashed = AuthService.hash_password(password)
        
        # Verify the correct password
        self.assertTrue(AuthService.verify_password(password, hashed))
        
        # Verify an incorrect password
        self.assertFalse(AuthService.verify_password('wrong_password', hashed))
    
    def test_login_success(self):
        """Test successful login"""
        with self.app.app_context():
            # Create a test request context
            with self.app.test_request_context('/'):
                # Attempt login with correct credentials
                result = AuthService.login('test_user', 'test_password')
                
                # Check that login was successful
                self.assertTrue(result['success'])
                
                # Check that session was created
                self.assertEqual(session.get('username'), 'test_user')
                self.assertTrue(session.get('is_authenticated'))
                self.assertFalse(session.get('is_admin'))
    
    def test_login_admin(self):
        """Test login as admin"""
        with self.app.app_context():
            # Create a test request context
            with self.app.test_request_context('/'):
                # Attempt login with admin credentials
                result = AuthService.login('test_admin', 'admin_password')
                
                # Check that login was successful
                self.assertTrue(result['success'])
                
                # Check that session was created with admin flag
                self.assertEqual(session.get('username'), 'test_admin')
                self.assertTrue(session.get('is_authenticated'))
                self.assertTrue(session.get('is_admin'))
    
    def test_login_failure_wrong_password(self):
        """Test login failure due to wrong password"""
        with self.app.app_context():
            # Create a test request context
            with self.app.test_request_context('/'):
                # Attempt login with wrong password
                result = AuthService.login('test_user', 'wrong_password')
                
                # Check that login failed
                self.assertFalse(result['success'])
                
                # Check that session was not created
                self.assertIsNone(session.get('username'))
                self.assertIsNone(session.get('is_authenticated'))
    
    def test_login_failure_nonexistent_user(self):
        """Test login failure due to nonexistent user"""
        with self.app.app_context():
            # Create a test request context
            with self.app.test_request_context('/'):
                # Attempt login with nonexistent user
                result = AuthService.login('nonexistent_user', 'password')
                
                # Check that login failed
                self.assertFalse(result['success'])
                
                # Check that session was not created
                self.assertIsNone(session.get('username'))
                self.assertIsNone(session.get('is_authenticated'))
    
    def test_logout(self):
        """Test logout"""
        with self.app.app_context():
            # Create a test request context
            with self.app.test_request_context('/'):
                # Set up a session
                session['user_id'] = 1
                session['username'] = 'test_user'
                session['is_authenticated'] = True
                
                # Logout
                result = AuthService.logout()
                
                # Check that logout was successful
                self.assertTrue(result['success'])
                
                # Check that session was cleared
                self.assertIsNone(session.get('username'))
                self.assertIsNone(session.get('is_authenticated'))
    
    def test_create_user(self):
        """Test creating a new user"""
        with self.app.app_context():
            # Create a test request context
            with self.app.test_request_context('/'):
                # Create a new user
                result = AuthService.create_user('new_user', 'new_password')
                
                # Check that user creation was successful
                self.assertTrue(result['success'])
                
                # Check that the user was created in the database
                user = User.query.filter_by(username='new_user').first()
                self.assertIsNotNone(user)
                self.assertFalse(user.is_admin)
                
                # Check that the password was hashed
                self.assertTrue(AuthService.verify_password('new_password', user.password))
    
    def test_create_admin_user(self):
        """Test creating a new admin user"""
        with self.app.app_context():
            # Create a test request context
            with self.app.test_request_context('/'):
                # Create a new admin user
                result = AuthService.create_user('new_admin', 'admin_password', is_admin=True)
                
                # Check that user creation was successful
                self.assertTrue(result['success'])
                
                # Check that the user was created in the database as an admin
                user = User.query.filter_by(username='new_admin').first()
                self.assertIsNotNone(user)
                self.assertTrue(user.is_admin)
    
    def test_create_duplicate_user(self):
        """Test creating a user with a duplicate username"""
        with self.app.app_context():
            # Create a test request context
            with self.app.test_request_context('/'):
                # Attempt to create a user with an existing username
                result = AuthService.create_user('test_user', 'new_password')
                
                # Check that user creation failed
                self.assertFalse(result['success'])
                
                # Check that no new user was created
                count = User.query.filter_by(username='test_user').count()
                self.assertEqual(count, 1)
    
    def test_require_auth_decorator(self):
        """Test the require_auth decorator"""
        with self.app.app_context():
            # Create a mock function
            mock_func = MagicMock(return_value='function_result')
            
            # Apply the decorator
            decorated_func = AuthService.require_auth(mock_func)
            
            # Test with authenticated session
            with self.app.test_request_context('/'):
                session['is_authenticated'] = True
                
                # Call the decorated function
                result = decorated_func()
                
                # Check that the original function was called
                mock_func.assert_called_once()
                self.assertEqual(result, 'function_result')
            
            # Reset the mock
            mock_func.reset_mock()
            
            # Test with unauthenticated session
            with self.app.test_request_context('/'):
                session.clear()
                
                # Call the decorated function
                result = decorated_func()
                
                # Check that the original function was not called
                mock_func.assert_not_called()
                # The result should be a redirect response
                self.assertEqual(result.status_code, 302)
    
    def test_require_admin_decorator(self):
        """Test the require_admin decorator"""
        with self.app.app_context():
            # Create a mock function
            mock_func = MagicMock(return_value='function_result')
            
            # Apply the decorator
            decorated_func = AuthService.require_admin(mock_func)
            
            # Test with admin session
            with self.app.test_request_context('/'):
                session['is_authenticated'] = True
                session['is_admin'] = True
                
                # Call the decorated function
                result = decorated_func()
                
                # Check that the original function was called
                mock_func.assert_called_once()
                self.assertEqual(result, 'function_result')
            
            # Reset the mock
            mock_func.reset_mock()
            
            # Test with non-admin session
            with self.app.test_request_context('/'):
                session['is_authenticated'] = True
                session['is_admin'] = False
                
                # Call the decorated function
                result = decorated_func()
                
                # Check that the original function was not called
                mock_func.assert_not_called()
                # The result should be a redirect response
                self.assertEqual(result.status_code, 302)
            
            # Reset the mock
            mock_func.reset_mock()
            
            # Test with unauthenticated session
            with self.app.test_request_context('/'):
                session.clear()
                
                # Call the decorated function
                result = decorated_func()
                
                # Check that the original function was not called
                mock_func.assert_not_called()
                # The result should be a redirect response
                self.assertEqual(result.status_code, 302)

if __name__ == '__main__':
    unittest.main()
