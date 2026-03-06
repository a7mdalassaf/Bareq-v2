"""
Audit Service - Provides logging of important system actions for security and compliance
"""
import logging
import json
from flask import request, session, g, current_app
from models import db, AuditLog

# Configure logging
logger = logging.getLogger('audit_service')

class AuditService:
    """Service for tracking and logging system actions"""
    
    @staticmethod
    def log_action(action, resource_type, resource_id=None, resource_name=None, details=None):
        """
        Log an action to the audit log
        
        Args:
            action (str): The action performed ('create', 'update', 'delete', 'access')
            resource_type (str): Type of resource affected ('credential', 'user', etc.)
            resource_id (int, optional): ID of the affected resource
            resource_name (str, optional): Name/identifier of the resource
            details (dict, optional): Additional details about the action
            
        Returns:
            AuditLog: The created audit log entry
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.warning(f"No application context available for logging action {action} on {resource_type}")
                return None
                
            with current_app.app_context():
                # Get user ID from session if available
                user_id = session.get('user_id') if hasattr(session, 'get') else None
                
                # Get IP address from request if available
                ip_address = None
                if request:
                    ip_address = request.remote_addr
                    
                # Convert details to JSON string if it's a dict
                details_str = None
                if details:
                    if isinstance(details, dict):
                        # Remove sensitive data from details
                        sanitized_details = details.copy()
                        if 'credential_value' in sanitized_details:
                            sanitized_details['credential_value'] = '[REDACTED]'
                        details_str = json.dumps(sanitized_details)
                    else:
                        details_str = str(details)
                
                # Create audit log entry
                audit_log = AuditLog(
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    user_id=user_id,
                    ip_address=ip_address,
                    details=details_str
                )
                
                db.session.add(audit_log)
                db.session.commit()
                
                logger.info(f"Audit log created: {action} {resource_type} {resource_name or resource_id}")
                return audit_log
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating audit log: {str(e)}")
            # Don't raise the exception - audit logging should never break the application
            return None
    
    @staticmethod
    def get_logs(resource_type=None, resource_id=None, action=None, limit=100):
        """
        Get audit logs with optional filtering
        
        Args:
            resource_type (str, optional): Filter by resource type
            resource_id (int, optional): Filter by resource ID
            action (str, optional): Filter by action
            limit (int, optional): Maximum number of logs to return
            
        Returns:
            list: List of audit log dictionaries
        """
        try:
            # Check if we're in an application context
            if not current_app:
                logger.warning("No application context available for retrieving audit logs")
                return []
                
            with current_app.app_context():
                query = AuditLog.query
                
                if resource_type:
                    query = query.filter_by(resource_type=resource_type)
                    
                if resource_id:
                    query = query.filter_by(resource_id=resource_id)
                    
                if action:
                    query = query.filter_by(action=action)
                    
                # Order by timestamp descending (newest first)
                query = query.order_by(AuditLog.timestamp.desc())
                
                # Limit the number of results
                query = query.limit(limit)
                
                logs = query.all()
                return [log.to_dict() for log in logs]
            
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {str(e)}")
            return []
