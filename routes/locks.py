from flask import Blueprint, render_template, request, jsonify, flash
from models import db, LockDeviceMapping, Guest, LockStatus
from utils.auth import login_required
from datetime import datetime, timedelta
import json
import redis

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

locks_bp = Blueprint('locks', __name__)

@locks_bp.route('/locks')
@login_required
def list_locks():
    """List all active locks"""
    locks = LockDeviceMapping.query.filter_by(is_active=True).all()
    return render_template('locks/list.html', locks=locks)

@locks_bp.route('/check_lock/<lock_id>')
@login_required
def check_lock(lock_id):
    """Check lock status with caching and history tracking"""
    try:
        # Check cache first
        cached_status = redis_client.get(f"lock_status:{lock_id}")
        if cached_status:
            return jsonify(json.loads(cached_status))

        # Get lock from database
        lock = LockDeviceMapping.query.get_or_404(lock_id)
        
        # Get status from API
        status = ttlock_adapter.get_lock_status(lock.lock_id)
        
        # Create status record
        lock_status = LockStatus(
            lock_id=lock.id,
            status=status.get('status'),
            battery_level=status.get('battery_level'),
            error_code=status.get('error_code'),
            error_message=status.get('error_message')
        )
        db.session.add(lock_status)
        db.session.commit()
        
        # Cache the result
        redis_client.setex(
            f"lock_status:{lock_id}",
            300,  # 5 minutes TTL
            json.dumps(status)
        )
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@locks_bp.route('/lock/<lock_id>/history')
@login_required
def lock_history(lock_id):
    """Get lock status history"""
    history = LockStatus.query.filter_by(lock_id=lock_id)\
        .order_by(LockStatus.last_updated.desc())\
        .limit(100)\
        .all()
    return jsonify([h.to_dict() for h in history])

@locks_bp.route('/locks/<lock_id>/guests')
@login_required
def list_guests(lock_id):
    """List guests for a specific lock"""
    guests = Guest.query.filter_by(lock_id=lock_id, is_active=True).all()
    return render_template('locks/guests.html', guests=guests, lock_id=lock_id)

@locks_bp.route('/locks/<lock_id>/add_guest', methods=['POST'])
@login_required
def add_guest(lock_id):
    """Add a new guest to a lock"""
    try:
        data = request.get_json()
        guest = Guest(
            name=data['name'],
            passcode=data['passcode'],
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            lock_id=lock_id,
            is_active=True
        )
        db.session.add(guest)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400 