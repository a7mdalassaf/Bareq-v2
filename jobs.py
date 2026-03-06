import logging
import time
import traceback
from datetime import datetime, timedelta
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from models import db, JobExecution, JobDefinition, SystemStatus, Guest
from tuya_adapter import TuyaAdapter
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('rettlockinfo.jobs')

# Initialize scheduler with SQLAlchemy job store for persistence
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///lockinfo.db')
}
executors = {
    'default': ThreadPoolExecutor(20)
}
job_defaults = {
    'coalesce': True,
    'max_instances': 1,
    'misfire_grace_time': 30
}

scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults
)

def job_decorator(job_id):
    """
    Decorator that wraps jobs with proper execution tracking.
    Logs start/end times, catches exceptions, and records execution status.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create execution record
            execution = JobExecution(job_id=job_id, status='running')
            db.session.add(execution)
            db.session.commit()
            
            start_time = time.time()
            try:
                # Execute the job
                result = func(*args, **kwargs)
                
                # Record successful execution
                execution.status = 'success'
                execution.result = str(result) if result else None
                
                # Update job definition
                with current_app.app_context():
                    job_def = JobDefinition.query.filter_by(job_id=job_id).first()
                    if job_def:
                        job_def.last_run = datetime.now()
                        job_def.next_run = get_next_run_time(scheduler.get_job(job_id))
                        db.session.commit()
                
                logger.info(f"Job {job_id} completed successfully")
                return result
            
            except Exception as e:
                # Record failed execution
                execution.status = 'error'
                execution.error = f"{str(e)}\n{traceback.format_exc()}"
                logger.error(f"Job {job_id} failed: {str(e)}")
                logger.error(traceback.format_exc())
                
                # Still update job definition last run time
                with current_app.app_context():
                    job_def = JobDefinition.query.filter_by(job_id=job_id).first()
                    if job_def:
                        job_def.last_run = datetime.now()
                        job_def.next_run = get_next_run_time(scheduler.get_job(job_id))
                        db.session.commit()
            
            finally:
                # Always record execution time and end time
                end_time = time.time()
                execution.end_time = datetime.now()
                execution.execution_time = end_time - start_time
                db.session.commit()
        
        return wrapper
    return decorator

def get_next_run_time(job):
    """Get the next run time for a job"""
    if job and job.next_run_time:
        return job.next_run_time
    return None

def register_job(job_id, name, description, interval, interval_type, job_function, args=None):
    """
    Register a job with the scheduler
    
    Args:
        job_id (str): Unique ID for the job
        name (str): Human-readable name
        description (str): Job description
        interval (int): How often the job should run
        interval_type (str): seconds, minutes, hours, days
        job_function (callable): The function to execute
        args (tuple): Args to pass to the job function
    """
    # Check if job definition exists
    job_def = JobDefinition.query.filter_by(job_id=job_id).first()
    
    if not job_def:
        # Create new job definition
        job_def = JobDefinition(
            job_id=job_id,
            name=name,
            description=description,
            interval=interval,
            interval_type=interval_type,
            is_active=True
        )
        db.session.add(job_def)
        db.session.commit()
    
    # Get trigger parameters based on interval type
    trigger_args = {'seconds': 0, 'minutes': 0, 'hours': 0, 'days': 0}
    trigger_args[interval_type] = interval
    
    # Register job with scheduler
    scheduler.add_job(
        job_function,
        'interval',
        id=job_id,
        replace_existing=True,
        args=args if args else (),
        **trigger_args
    )
    
    # Update next run time
    job_def.next_run = get_next_run_time(scheduler.get_job(job_id))
    db.session.commit()
    
    logger.info(f"Registered job: {job_id} ('{name}') to run every {interval} {interval_type}")

def pause_job(job_id):
    """Pause a job"""
    scheduler.pause_job(job_id)
    job_def = JobDefinition.query.filter_by(job_id=job_id).first()
    if job_def:
        job_def.is_active = False
        db.session.commit()
    logger.info(f"Paused job: {job_id}")

def resume_job(job_id):
    """Resume a paused job"""
    scheduler.resume_job(job_id)
    job_def = JobDefinition.query.filter_by(job_id=job_id).first()
    if job_def:
        job_def.is_active = True
        job_def.next_run = get_next_run_time(scheduler.get_job(job_id))
        db.session.commit()
    logger.info(f"Resumed job: {job_id}")

def remove_job(job_id):
    """Remove a job from the scheduler"""
    scheduler.remove_job(job_id)
    job_def = JobDefinition.query.filter_by(job_id=job_id).first()
    if job_def:
        db.session.delete(job_def)
        db.session.commit()
    logger.info(f"Removed job: {job_id}")

def get_job_info(job_id):
    """Get information about a job"""
    job = scheduler.get_job(job_id)
    job_def = JobDefinition.query.filter_by(job_id=job_id).first()
    
    if not job or not job_def:
        return None
    
    return {
        'id': job_def.id,
        'job_id': job_id,
        'name': job_def.name,
        'description': job_def.description,
        'interval': job_def.interval,
        'interval_type': job_def.interval_type,
        'last_run': job_def.last_run.strftime('%Y-%m-%d %H:%M:%S') if job_def.last_run else None,
        'next_run': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job and job.next_run_time else None,
        'is_active': job_def.is_active,
        'created_at': job_def.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }

def get_all_jobs():
    """Get information about all jobs"""
    jobs = []
    for job_def in JobDefinition.query.all():
        job_info = get_job_info(job_def.job_id)
        if job_info:
            jobs.append(job_info)
    return jobs

def get_recent_executions(job_id=None, limit=20):
    """Get recent job executions"""
    query = JobExecution.query.order_by(JobExecution.start_time.desc())
    if job_id:
        query = query.filter_by(job_id=job_id)
    return [execution.to_dict() for execution in query.limit(limit).all()]

# ==========================================
# Built-in jobs implementation
# ==========================================

@job_decorator('check_active_passcodes')
def check_active_passcodes():
    """Check if any passcodes are active and update LED status"""
    with current_app.app_context():
        now = datetime.now()
        
        # Get all guests with valid passcodes
        active_guests = Guest.query.filter(
            Guest.start_date <= now,
            Guest.end_date >= now
        ).all()
        
        # Get or create system status
        system_status = SystemStatus.query.first()
        if not system_status:
            system_status = SystemStatus()
            db.session.add(system_status)
        
        # Update system status
        system_status.active_passcodes_count = len(active_guests)
        
        # Clean up expired guests
        expired_guests = Guest.query.filter(
            Guest.end_date < now
        ).all()
        
        if expired_guests:
            logger.info(f"Found {len(expired_guests)} expired guest(s)")
            for guest in expired_guests:
                logger.info(f"Removing expired guest: {guest.name}, end date: {guest.end_date}")
                db.session.delete(guest)
        
        # Control LED based on active passcodes
        tuya = TuyaAdapter()
        current_status = tuya.get_device_status()
        
        if bool(active_guests) != current_status:
            logger.info(f"Updating LED status: {'ON' if active_guests else 'OFF'}")
            success = tuya.control_led(bool(active_guests))
            
            # Update system status
            system_status.led_status = bool(active_guests) if success else current_status
            system_status.last_led_update = datetime.now()
        
        # Always commit session
        db.session.commit()
        
        return {
            'active_guests_count': len(active_guests),
            'expired_guests_count': len(expired_guests),
            'led_status': bool(active_guests)
        }

@job_decorator('sync_ttlock_data')
def sync_ttlock_data():
    """Synchronize TTLock data with the database"""
    from smart_lock_manager import TTLockManager
    from models import User

    with current_app.app_context():
        # Get current user
        current_user = User.query.filter_by(is_current=True).first()
        if not current_user:
            logger.error("No current user found in the database")
            return {'error': 'No current user found'}
        
        # Create TTLock manager
        ttlock_manager = TTLockManager(
            client_id="a67f3b3552a64b0c81aa5e3b2a19dffb",
            client_secret="8db22fad0b66cc784b06cbddc1ccab9a",
            username=current_user.username,
            password=current_user.password
        )
        
        # Get access token
        token_info = ttlock_manager.get_access_token()
        if not token_info or not token_info.get('access_token'):
            logger.error("Failed to get access token")
            return {'error': 'Failed to get access token'}
        
        # Get system status
        system_status = SystemStatus.query.first()
        if not system_status:
            system_status = SystemStatus()
            db.session.add(system_status)
        
        try:
            # Get locks
            locks_data = ttlock_manager.list_locks()
            if not locks_data or 'list' not in locks_data:
                logger.error("Failed to get locks list")
                system_status.last_sync_status = 'error'
                system_status.last_sync_time = datetime.now()
                db.session.commit()
                return {'error': 'Failed to get locks list'}
            
            # Update system status
            system_status.locks_count = len(locks_data.get('list', []))
            system_status.last_sync_time = datetime.now()
            system_status.last_sync_status = 'success'
            system_status.api_status = 'up'
            
            db.session.commit()
            
            logger.info(f"Synchronized {system_status.locks_count} locks from TTLock API")
            return {
                'locks_count': system_status.locks_count,
                'sync_time': system_status.last_sync_time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error in sync_ttlock_data: {str(e)}")
            system_status.last_sync_status = 'error'
            system_status.last_sync_time = datetime.now()
            system_status.api_status = 'down'
            db.session.commit()
            
            # Re-raise to be caught by the decorator
            raise
