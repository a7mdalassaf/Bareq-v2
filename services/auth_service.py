"""
Authentication Service - Provides user authentication and authorization
"""
import logging
import hashlib
from flask import session, redirect, url_for, request
from functools import wraps
from models import db, User
from services.audit_service import AuditService

# Configure logging
logger = logging.getLogger('auth_service')

class AuthService:
    """Service for user authentication and authorization"""
    
    @staticmethod
    def hash_password(password):
        """
        Hash a password using SHA-256
        
        Args:
            password (str): The password to hash
            
        Returns:
            str: The hashed password
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    @staticmethod
    def verify_password(password, hashed_password):
        """
        Verify a password against a hash
        
        Args:
            password (str): The password to verify
            hashed_password (str): The hash to verify against
            
        Returns:
            bool: True if the password matches, False otherwise
        """
        return AuthService.hash_password(password) == hashed_password
    
    @staticmethod
    def login(username, password):
        """
        Authenticate a user and create a session
        
        Args:
            username (str): The username to authenticate
            password (str): The password to authenticate
            
        Returns:
            dict: Result with success flag and message
        """
        try:
            user = User.query.filter_by(username=username).first()
            
            if not user:
                return {
                    'success': False,
                    'message': 'Invalid username or password'
                }
                
            if not AuthService.verify_password(password, user.password):
                return {
                    'success': False,
                    'message': 'Invalid username or password'
                }
                
            # Create session
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_authenticated'] = True
            session['is_admin'] = user.is_admin
            
            # Log the login
            AuditService.log_action(
                'login', 
                'user', 
                user.id, 
                user.username, 
                {'ip': request.remote_addr if request else None}
            )
            
            return {
                'success': True,
                'message': f'Welcome, {user.username}!',
                'user': user.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred during login'
            }
    
    @staticmethod
    def logout():
        """
        Log out the current user
        
        Returns:
            dict: Result with success flag and message
        """
        try:
            # Log the logout if user is authenticated
            if 'user_id' in session:
                AuditService.log_action(
                    'logout', 
                    'user', 
                    session.get('user_id'), 
                    session.get('username'), 
                    {'ip': request.remote_addr if request else None}
                )
            
            # Clear session
            session.clear()
            
            return {
                'success': True,
                'message': 'You have been logged out'
            }
            
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return {
                'success': False,
                'message': 'An error occurred during logout'
            }
    
    @staticmethod
    def create_user(username, password, is_admin=False):
        """
        Create a new user
        
        Args:
            username (str): The username for the new user
            password (str): The password for the new user
            is_admin (bool): Whether the user is an admin
            
        Returns:
            dict: Result with success flag and message
        """
        try:
            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return {
                    'success': False,
                    'message': f'Username {username} already exists'
                }
                
            # Create new user
            hashed_password = AuthService.hash_password(password)
            new_user = User(
                username=username,
                password=hashed_password,
                is_admin=is_admin
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            # Log the user creation
            AuditService.log_action(
                'create', 
                'user', 
                new_user.id, 
                new_user.username, 
                {'is_admin': is_admin}
            )
            
            return {
                'success': True,
                'message': f'User {username} created successfully',
                'user': new_user.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return {
                'success': False,
                'message': f'Error creating user: {str(e)}'
            }
    
    @staticmethod
    def require_auth(f):
        """
        Decorator to require authentication for a route
        
        Args:
            f: The function to decorate
            
        Returns:
            function: The decorated function
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('is_authenticated'):
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def require_admin(f):
        """
        Decorator to require admin privileges for a route
        
        Args:
            f: The function to decorate
            
        Returns:
            function: The decorated function
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('is_authenticated'):
                return redirect(url_for('login', next=request.url))
                
            if not session.get('is_admin'):
                return redirect(url_for('index'))
                
            return f(*args, **kwargs)
        return decorated_function
