"""
Database module for Face Login System
Provides both MySQL (via SQLAlchemy) and JSON storage options
"""

import os
import json
import numpy as np
from datetime import datetime
from config import DATA_DIR, USERS_FILE

# =============================================================================
# SQLAlchemy Database Operations (MySQL)
# =============================================================================

def get_db_session():
    """Get database session from Flask app context."""
    from models import db
    return db.session


def save_user_to_db(username, email, password=None, role='user', encoding=None):
    """
    Save a new user to MySQL database.
    
    Args:
        username: User's username
        email: User's email
        password: Optional password (for password login)
        role: User role ('admin' or 'user')
        encoding: Face encoding numpy array
    
    Returns:
        User object or None if failed
    """
    from models import User, db
    
    # Check if user already exists
    existing = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing:
        return None
    
    user = User(username=username, email=email, role=role)
    
    if password:
        user.set_password(password)
    
    if encoding is not None:
        user.set_face_encoding(encoding)
    
    db.session.add(user)
    db.session.commit()
    
    return user


def update_user_face_encoding(user_id, encoding):
    """Update a user's face encoding."""
    from models import User, db
    
    user = User.query.get(user_id)
    if not user:
        return False
    
    user.set_face_encoding(encoding)
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    return True


def get_all_users_with_faces():
    """
    Get all users with face encodings.
    
    Returns:
        Dictionary of {username: encoding_array}
    """
    from models import User
    
    users = User.query.filter(
        User.face_encoding.isnot(None),
        User.is_active == True
    ).all()
    
    return {user.username: user.get_face_encoding() for user in users}


def get_user_by_username(username):
    """Get user by username."""
    from models import User
    return User.query.filter_by(username=username).first()


def get_user_by_id(user_id):
    """Get user by ID."""
    from models import User
    return User.query.get(user_id)


def get_users_by_role(role):
    """Get all users with specific role."""
    from models import User
    return User.query.filter_by(role=role, is_active=True).all()


def delete_user_from_db(user_id):
    """Delete user from database."""
    from models import User, db
    
    user = User.query.get(user_id)
    if not user:
        return False
    
    db.session.delete(user)
    db.session.commit()
    return True


def log_attendance(user_id, login_method='face', liveness_score=None, 
                   face_confidence=None, ip_address=None, user_agent=None):
    """
    Create an attendance log entry for login.
    
    Args:
        user_id: User's ID
        login_method: 'face', 'password', or 'both'
        liveness_score: Liveness confidence (0-100)
        face_confidence: Face match confidence (0-100)
        ip_address: Client IP address
        user_agent: Browser user agent
    
    Returns:
        AttendanceLog object
    """
    from models import AttendanceLog, db
    
    log = AttendanceLog(
        user_id=user_id,
        login_method=login_method,
        liveness_score=liveness_score,
        face_confidence=face_confidence,
        ip_address=ip_address,
        user_agent=user_agent,
        is_active=True
    )
    
    db.session.add(log)
    db.session.commit()
    
    return log


def log_logout(attendance_id):
    """Mark attendance log as logged out."""
    from models import AttendanceLog, db
    
    log = AttendanceLog.query.get(attendance_id)
    if not log:
        return False
    
    log.logout_time = datetime.utcnow()
    log.is_active = False
    db.session.commit()
    
    return True


def get_user_active_session(user_id):
    """Get user's active attendance session."""
    from models import AttendanceLog
    
    return AttendanceLog.query.filter_by(
        user_id=user_id,
        is_active=True
    ).order_by(AttendanceLog.login_time.desc()).first()


def get_attendance_logs(user_id=None, start_date=None, end_date=None, limit=100):
    """
    Get attendance logs with optional filters.
    
    Args:
        user_id: Optional filter by user
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum records to return
    
    Returns:
        List of AttendanceLog objects
    """
    from models import AttendanceLog
    
    query = AttendanceLog.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if start_date:
        query = query.filter(AttendanceLog.login_time >= start_date)
    
    if end_date:
        query = query.filter(AttendanceLog.login_time <= end_date)
    
    return query.order_by(AttendanceLog.login_time.desc()).limit(limit).all()


def log_login_attempt(user_id=None, attempt_type='face', success=False,
                      failure_reason=None, ip_address=None, user_agent=None):
    """
    Log a login attempt for security monitoring.
    
    Args:
        user_id: User ID (None if unknown user)
        attempt_type: 'face' or 'password'
        success: Whether attempt was successful
        failure_reason: Reason for failure if applicable
        ip_address: Client IP address
        user_agent: Browser user agent
    
    Returns:
        LoginAttempt object
    """
    from models import LoginAttempt, db
    
    attempt = LoginAttempt(
        user_id=user_id,
        attempt_type=attempt_type,
        success=success,
        failure_reason=failure_reason,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.session.add(attempt)
    db.session.commit()
    
    return attempt


def get_login_attempts(user_id=None, success=None, limit=100):
    """Get login attempts with optional filters."""
    from models import LoginAttempt
    
    query = LoginAttempt.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if success is not None:
        query = query.filter_by(success=success)
    
    return query.order_by(LoginAttempt.timestamp.desc()).limit(limit).all()


# =============================================================================
# JSON File Storage (Legacy - for CLI mode)
# =============================================================================

def ensure_data_dir():
    """Ensure data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def load_users():
    """
    Load all registered users from JSON file.
    
    Returns:
        Dictionary of {username: encoding_list}
    """
    ensure_data_dir()
    
    if not os.path.exists(USERS_FILE):
        return {}
    
    try:
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
        
        # Convert lists back to numpy arrays for face comparison
        return {username: np.array(encoding) for username, encoding in data.items()}
    except (json.JSONDecodeError, IOError):
        return {}


def save_users(users_dict):
    """
    Save users dictionary to JSON file.
    
    Args:
        users_dict: Dictionary of {username: encoding}
    """
    ensure_data_dir()
    
    # Convert numpy arrays to lists for JSON serialization
    serializable = {}
    for username, encoding in users_dict.items():
        if isinstance(encoding, np.ndarray):
            serializable[username] = encoding.tolist()
        else:
            serializable[username] = encoding
    
    with open(USERS_FILE, 'w') as f:
        json.dump(serializable, f, indent=2)


def save_user(username, encoding):
    """
    Save a single user to JSON file.
    
    Args:
        username: User's name/identifier
        encoding: 128-dimensional face encoding
    
    Returns:
        True if saved successfully, False if user already exists
    """
    users = load_users()
    
    if username.lower() in [u.lower() for u in users.keys()]:
        return False
    
    if isinstance(encoding, np.ndarray):
        users[username] = encoding.tolist()
    else:
        users[username] = encoding
    
    save_users(users)
    return True


def update_user(username, encoding):
    """
    Update an existing user's encoding in JSON file.
    
    Args:
        username: User's name
        encoding: New face encoding
    
    Returns:
        True if updated, False if user doesn't exist
    """
    users = load_users()
    
    if username not in users:
        return False
    
    if isinstance(encoding, np.ndarray):
        users[username] = encoding.tolist()
    else:
        users[username] = encoding
    
    save_users(users)
    return True


def delete_user(username):
    """
    Delete a user from JSON file.
    
    Args:
        username: User to delete
    
    Returns:
        True if deleted, False if user not found
    """
    users = load_users()
    
    # Case-insensitive search
    found_key = None
    for key in users.keys():
        if key.lower() == username.lower():
            found_key = key
            break
    
    if found_key is None:
        return False
    
    del users[found_key]
    save_users(users)
    return True


def user_exists(username):
    """
    Check if a user is registered in JSON file.
    
    Args:
        username: User to check
    
    Returns:
        Boolean indicating if user exists
    """
    users = load_users()
    return username.lower() in [u.lower() for u in users.keys()]


def get_user_count():
    """Get total number of registered users from JSON file."""
    return len(load_users())


def list_users():
    """Get list of all registered usernames from JSON file."""
    return list(load_users().keys())
