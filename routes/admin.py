"""
Admin Routes - Provides admin interfaces for system configuration
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import (
    db, Guest, User, LockDeviceMapping, JobExecution, JobDefinition, 
    SystemStatus, ApiCredential, AuditLog
)
from services.credential_service import CredentialService
from sqlalchemy import inspect
from datetime import datetime
from tuya_api import get_device_status, toggle_device, is_device_on

admin = Blueprint('admin', __name__)

@admin.route('/')
def index():
    """Admin dashboard"""
    return render_template('admin/index.html')

# Database Management Routes
@admin.route('/database')
def database_management():
    """Database management dashboard"""
    # Get all tables in the database
    inspector = inspect(db.engine)
    tables = []
    for table_name in inspector.get_table_names():
        columns = []
        for column in inspector.get_columns(table_name):
            columns.append({
                'name': column['name'],
                'type': str(column['type']),
                'nullable': column.get('nullable', True),
                'default': column.get('default', None),
                'primary_key': column.get('primary_key', False)
            })
        tables.append({
            'name': table_name,
            'columns': columns
        })
    return render_template('admin/database.html', tables=tables)

@admin.route('/database/<table_name>')
def view_table(table_name):
    """View table contents"""
    try:
        # Get the table model class
        model_map = {
            'guest': Guest,
            'user': User,
            'lock_device_mapping': LockDeviceMapping,
            'job_execution': JobExecution,
            'job_definition': JobDefinition,
            'system_status': SystemStatus,
            'api_credential': ApiCredential,
            'audit_log': AuditLog
        }
        
        if table_name not in model_map:
            flash(f'Table {table_name} not found', 'danger')
            return redirect(url_for('admin.database_management'))
        
        model = model_map[table_name]
        
        # Get table data
        data = model.query.all()
        
        # Get column names and types
        columns = []
        column_types = {}
        for column in model.__table__.columns:
            columns.append(column.name)
            column_types[column.name] = str(column.type)
        
        return render_template('admin/table.html', 
                             table_name=table_name, 
                             columns=columns,
                             column_types=column_types,
                             data=data)
    except Exception as e:
        flash(f'Error viewing table: {str(e)}', 'danger')
        return redirect(url_for('admin.database_management'))

@admin.route('/database/<table_name>/new', methods=['GET', 'POST'])
def new_record(table_name):
    """Create a new database record"""
    try:
        # Get the table model class
        model_map = {
            'guest': Guest,
            'user': User,
            'lock_device_mapping': LockDeviceMapping,
            'job_execution': JobExecution,
            'job_definition': JobDefinition,
            'system_status': SystemStatus,
            'api_credential': ApiCredential,
            'audit_log': AuditLog
        }
        
        if table_name not in model_map:
            flash(f'Table {table_name} not found', 'danger')
            return redirect(url_for('admin.database_management'))
        
        model = model_map[table_name]
        
        if request.method == 'POST':
            # Create new record
            record = model()
            for column in model.__table__.columns:
                if not column.primary_key and column.name in request.form:
                    value = request.form[column.name]
                    if value == '' and column.nullable:
                        value = None
                    elif isinstance(column.type, db.Boolean):
                        value = value.lower() in ('true', 't', 'yes', 'y', 'on', '1')
                    elif isinstance(column.type, db.DateTime) and value:
                        value = datetime.strptime(value, '%Y-%m-%dT%H:%M')
                    setattr(record, column.name, value)
            
            db.session.add(record)
            db.session.commit()
            flash('Record created successfully', 'success')
            return redirect(url_for('admin.view_table', table_name=table_name))
        
        # Get column information for the form
        columns = []
        for column in model.__table__.columns:
            if not column.primary_key:  # Skip primary key columns for new records
                column_info = {
                    'name': column.name,
                    'type': str(column.type),
                    'nullable': column.nullable,
                    'default': column.default.arg if column.default else None
                }
                columns.append(column_info)
        
        return render_template('admin/edit_record.html', 
                             table_name=table_name,
                             columns=columns,
                             is_new=True)
    except Exception as e:
        flash(f'Error creating record: {str(e)}', 'danger')
        return redirect(url_for('admin.view_table', table_name=table_name))

@admin.route('/database/<table_name>/edit/<int:id>', methods=['GET', 'POST'])
def edit_record(table_name, id):
    """Edit a database record"""
    try:
        # Get the table model class
        model_map = {
            'guest': Guest,
            'user': User,
            'lock_device_mapping': LockDeviceMapping,
            'job_execution': JobExecution,
            'job_definition': JobDefinition,
            'system_status': SystemStatus,
            'api_credential': ApiCredential,
            'audit_log': AuditLog
        }
        
        if table_name not in model_map:
            flash(f'Table {table_name} not found', 'danger')
            return redirect(url_for('admin.database_management'))
        
        model = model_map[table_name]
        record = model.query.get(id)
        
        if not record:
            flash(f'Record not found', 'danger')
            return redirect(url_for('admin.view_table', table_name=table_name))
        
        if request.method == 'POST':
            # Update record with form data
            for column in model.__table__.columns:
                if column.name in request.form:
                    value = request.form[column.name]
                    # Convert empty strings to None for nullable columns
                    if value == '' and column.nullable:
                        value = None
                    # Handle boolean fields
                    elif isinstance(column.type, db.Boolean):
                        value = value.lower() in ('true', 't', 'yes', 'y', 'on', '1')
                    # Handle datetime fields
                    elif isinstance(column.type, db.DateTime) and value:
                        value = datetime.strptime(value, '%Y-%m-%dT%H:%M')
                    setattr(record, column.name, value)
            
            db.session.commit()
            flash('Record updated successfully', 'success')
            return redirect(url_for('admin.view_table', table_name=table_name))
        
        # Get column information for the form
        columns = []
        for column in model.__table__.columns:
            column_info = {
                'name': column.name,
                'type': str(column.type),
                'nullable': column.nullable,
                'primary_key': column.primary_key,
                'value': getattr(record, column.name)
            }
            # Format datetime values for the form
            if isinstance(column.type, db.DateTime) and column_info['value']:
                column_info['value'] = column_info['value'].strftime('%Y-%m-%dT%H:%M')
            columns.append(column_info)
        
        return render_template('admin/edit_record.html', 
                             table_name=table_name,
                             columns=columns,
                             is_new=False)
    except Exception as e:
        flash(f'Error editing record: {str(e)}', 'danger')
        return redirect(url_for('admin.view_table', table_name=table_name))

@admin.route('/database/<table_name>/delete/<int:id>', methods=['POST'])
def delete_record(table_name, id):
    """Delete a database record"""
    try:
        # Get the table model class
        model_map = {
            'guest': Guest,
            'user': User,
            'lock_device_mapping': LockDeviceMapping,
            'job_execution': JobExecution,
            'job_definition': JobDefinition,
            'system_status': SystemStatus,
            'api_credential': ApiCredential,
            'audit_log': AuditLog
        }
        
        if table_name not in model_map:
            flash(f'Table {table_name} not found', 'danger')
            return redirect(url_for('admin.database_management'))
        
        model = model_map[table_name]
        record = model.query.get(id)
        
        if record:
            db.session.delete(record)
            db.session.commit()
            flash('Record deleted successfully', 'success')
        else:
            flash('Record not found', 'danger')
            
        return redirect(url_for('admin.view_table', table_name=table_name))
    except Exception as e:
        flash(f'Error deleting record: {str(e)}', 'danger')
        return redirect(url_for('admin.view_table', table_name=table_name))

@admin.route('/credentials', methods=['GET'])
def list_credentials():
    """List all API credentials (without showing values)"""
    credentials = CredentialService.get_all_credentials(include_values=False)
    return render_template('admin/credentials.html', credentials=credentials)

@admin.route('/credentials/new', methods=['GET', 'POST'])
def new_credential():
    """Create a new credential"""
    if request.method == 'POST':
        try:
            provider = request.form['provider']
            credential_type = request.form['credential_type']
            credential_key = request.form['credential_key']
            credential_value = request.form['credential_value']
            description = request.form.get('description', '')
            
            CredentialService.set_credential(
                provider, credential_type, credential_key, 
                credential_value, description
            )
            
            flash('Credential created successfully', 'success')
            return redirect(url_for('admin.list_credentials'))
        except Exception as e:
            flash(f'Error creating credential: {str(e)}', 'danger')
    
    return render_template('admin/edit_credential.html', credential=None)

@admin.route('/credentials/<int:id>', methods=['GET', 'POST'])
def edit_credential(id):
    """Edit a specific credential"""
    credential = CredentialService.get_credential_by_id(id)
    if not credential:
        flash('Credential not found', 'danger')
        return redirect(url_for('admin.list_credentials'))
    
    if request.method == 'POST':
        try:
            provider = request.form['provider']
            credential_type = request.form['credential_type']
            credential_key = request.form['credential_key']
            credential_value = request.form['credential_value']
            description = request.form.get('description', '')
            
            CredentialService.set_credential(
                provider, credential_type, credential_key, 
                credential_value, description
            )
            
            flash('Credential updated successfully', 'success')
            return redirect(url_for('admin.list_credentials'))
        except Exception as e:
            flash(f'Error updating credential: {str(e)}', 'danger')
    
    return render_template('admin/edit_credential.html', credential=credential)

@admin.route('/credentials/<int:id>/delete', methods=['POST'])
def delete_credential(id):
    """Delete a credential"""
    if CredentialService.delete_credential(id):
        flash('Credential deleted successfully', 'success')
    else:
        flash('Credential not found', 'danger')
    return redirect(url_for('admin.list_credentials'))

# API endpoints for credential management
@admin.route('/api/credentials', methods=['GET'])
def api_list_credentials():
    """API endpoint to list credentials"""
    include_values = request.args.get('include_values', 'false').lower() == 'true'
    credentials = CredentialService.get_all_credentials(include_values=include_values)
    return jsonify({'credentials': credentials})

@admin.route('/api/credentials/<int:id>', methods=['GET'])
def api_get_credential(id):
    """API endpoint to get a specific credential"""
    include_value = request.args.get('include_value', 'true').lower() == 'true'
    credential = CredentialService.get_credential_by_id(id, include_value=include_value)
    if credential:
        return jsonify({'credential': credential})
    return jsonify({'error': 'Credential not found'}), 404

@admin.route('/api/credentials', methods=['POST'])
def api_create_credential():
    """API endpoint to create a new credential"""
    try:
        data = request.get_json()
        provider = data['provider']
        credential_type = data['credential_type']
        credential_key = data['credential_key']
        credential_value = data['credential_value']
        description = data.get('description', '')
        
        CredentialService.set_credential(
            provider, credential_type, credential_key, 
            credential_value, description
        )
        
        return jsonify({'message': 'Credential created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@admin.route('/api/credentials/<int:id>', methods=['PUT'])
def api_update_credential(id):
    """API endpoint to update a credential"""
    try:
        data = request.get_json()
        provider = data['provider']
        credential_type = data['credential_type']
        credential_key = data['credential_key']
        credential_value = data['credential_value']
        description = data.get('description', '')
        
        CredentialService.set_credential(
            provider, credential_type, credential_key, 
            credential_value, description
        )
        
        return jsonify({'message': 'Credential updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@admin.route('/api/credentials/<int:id>', methods=['DELETE'])
def api_delete_credential(id):
    """API endpoint to delete a credential"""
    if CredentialService.delete_credential(id):
        return jsonify({'message': 'Credential deleted successfully'})
    return jsonify({'error': 'Credential not found'}), 404

@admin.route('/device/<device_id>/light/status')
def get_light_status(device_id):
    """Get the current status of a device's light"""
    try:
        status = is_device_on()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin.route('/device/<device_id>/light/toggle', methods=['POST'])
def toggle_light(device_id):
    """Toggle a device's light on or off"""
    try:
        turn_on = request.json.get('turn_on')
        result = toggle_device(turn_on)
        if result.get('success', False):
            flash('Light toggled successfully', 'success')
            return jsonify({
                'success': True,
                'new_status': is_device_on()
            })
        else:
            error = result.get('error', 'Unknown error')
            flash(f'Failed to toggle light: {error}', 'danger')
            return jsonify({
                'success': False,
                'error': error
            }), 500
    except Exception as e:
        flash(f'Error toggling light: {str(e)}', 'danger')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
