"""
Flask Application for Face Login System
REST API with face recognition, role-based auth, and attendance tracking
"""

import os
import sys
import base64
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt_identity,
    verify_jwt_in_request
)

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    SECRET_KEY, JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES,
    SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS,
    FACE_MATCH_TOLERANCE, LIVENESS_ENABLED
)
from models import db, init_db, User, AttendanceLog, LoginAttempt
from decorators import login_required, admin_required, get_current_user
from face_utils import detect_faces, encode_face, find_best_match
from liveness import verify_liveness_api
from database import (
    save_user_to_db, get_all_users_with_faces, get_user_by_username,
    log_attendance, log_logout, get_user_active_session, get_attendance_logs,
    log_login_attempt, update_user_face_encoding
)

# =============================================================================
# Flask App Setup
# =============================================================================

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration
app.config['SECRET_KEY'] = SECRET_KEY
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = JWT_ACCESS_TOKEN_EXPIRES
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

# Initialize extensions
CORS(app)
jwt = JWTManager(app)


# =============================================================================
# Helper Functions
# =============================================================================

def decode_base64_image(base64_string):
    """Decode base64 image to OpenCV format."""
    try:
        # Remove data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        img_bytes = base64.b64decode(base64_string)
        nparr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None


def get_client_info():
    """Get client IP and user agent."""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')[:255]
    return ip_address, user_agent


# =============================================================================
# Web Routes (HTML Pages)
# =============================================================================

@app.route('/')
def index():
    """Home page."""
    return render_template('index.html')


@app.route('/login')
def login_page():
    """Login page."""
    return render_template('login.html')


@app.route('/register')
def register_page():
    """Registration page."""
    return render_template('register.html')


@app.route('/dashboard')
def dashboard_page():
    """User dashboard."""
    return render_template('dashboard.html')


@app.route('/admin')
def admin_page():
    """Admin panel."""
    return render_template('admin.html')


# =============================================================================
# API Routes - Authentication
# =============================================================================

@app.route('/api/register', methods=['POST'])
def api_register():
    """
    Register a new user with face encoding.
    
    Request JSON:
        {
            "username": "john",
            "email": "john@example.com",
            "password": "optional_password",
            "role": "user",
            "face_image": "base64_encoded_image"
        }
    """
    try:
        data = request.get_json()
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'user')
        face_image_b64 = data.get('face_image', '')
        
        # Validation
        if not username or len(username) < 2:
            return jsonify({
                'success': False,
                'message': 'Username must be at least 2 characters'
            }), 400
        
        if not email or '@' not in email:
            return jsonify({
                'success': False,
                'message': 'Valid email required'
            }), 400
        
        # Check if user exists
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'Username or email already registered'
            }), 409
        
        # Process face image
        encoding = None
        if face_image_b64:
            image = decode_base64_image(face_image_b64)
            if image is None:
                return jsonify({
                    'success': False,
                    'message': 'Invalid face image'
                }), 400
            
            # Detect and encode face
            faces = detect_faces(image)
            if not faces:
                return jsonify({
                    'success': False,
                    'message': 'No face detected in image'
                }), 400
            
            if len(faces) > 1:
                return jsonify({
                    'success': False,
                    'message': 'Multiple faces detected. Please use an image with only one face.'
                }), 400
            
            encoding = encode_face(image, faces[0])
            if encoding is None:
                return jsonify({
                    'success': False,
                    'message': 'Failed to encode face'
                }), 400
        
        # Only admins can create admin users
        if role == 'admin':
            try:
                verify_jwt_in_request()
                current_user = get_current_user()
                if not current_user or not current_user.is_admin():
                    role = 'user'  # Downgrade to user if not admin
            except:
                role = 'user'
        
        # Create user
        user = save_user_to_db(username, email, password, role, encoding)
        
        if user:
            return jsonify({
                'success': True,
                'message': f'User {username} registered successfully!',
                'user': user.to_dict()
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create user'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/login/face', methods=['POST'])
def api_login_face():
    """
    Login with face recognition.
    
    Request JSON:
        {
            "face_image": "base64_encoded_image"
        }
    """
    try:
        data = request.get_json()
        face_image_b64 = data.get('face_image', '')
        
        if not face_image_b64:
            return jsonify({
                'success': False,
                'message': 'Face image required'
            }), 400
        
        # Decode image
        image = decode_base64_image(face_image_b64)
        if image is None:
            log_login_attempt(attempt_type='face', failure_reason='invalid_image', 
                            *get_client_info())
            return jsonify({
                'success': False,
                'message': 'Invalid image data'
            }), 400
        
        # Liveness check
        liveness_score = 0.0
        if LIVENESS_ENABLED:
            is_live, liveness_score, msg = verify_liveness_api(image)
            if not is_live:
                log_login_attempt(attempt_type='face', failure_reason='liveness_failed',
                                *get_client_info())
                return jsonify({
                    'success': False,
                    'message': f'Liveness check failed: {msg}'
                }), 401
        
        # Detect face
        faces = detect_faces(image)
        if not faces:
            log_login_attempt(attempt_type='face', failure_reason='no_face_detected',
                            *get_client_info())
            return jsonify({
                'success': False,
                'message': 'No face detected'
            }), 400
        
        # Encode face
        encoding = encode_face(image, faces[0])
        if encoding is None:
            log_login_attempt(attempt_type='face', failure_reason='encoding_failed',
                            *get_client_info())
            return jsonify({
                'success': False,
                'message': 'Failed to process face'
            }), 400
        
        # Find matching user
        known_faces = get_all_users_with_faces()
        if not known_faces:
            return jsonify({
                'success': False,
                'message': 'No registered users with face data'
            }), 404
        
        username, distance, confidence = find_best_match(
            encoding, known_faces, FACE_MATCH_TOLERANCE
        )
        
        if username is None:
            log_login_attempt(attempt_type='face', failure_reason='unknown_face',
                            *get_client_info())
            return jsonify({
                'success': False,
                'message': 'Face not recognized'
            }), 401
        
        # Get user
        user = get_user_by_username(username)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        if not user.is_active:
            log_login_attempt(user_id=user.id, attempt_type='face', 
                            failure_reason='account_disabled', *get_client_info())
            return jsonify({
                'success': False,
                'message': 'Account is disabled'
            }), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log successful attempt
        ip_address, user_agent = get_client_info()
        log_login_attempt(user_id=user.id, attempt_type='face', success=True,
                         ip_address=ip_address, user_agent=user_agent)
        
        # Create attendance log
        attendance = log_attendance(
            user_id=user.id,
            login_method='face',
            liveness_score=liveness_score,
            face_confidence=confidence,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Generate JWT token (use str for identity for compatibility)
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'message': f'Welcome, {username}!',
            'access_token': access_token,
            'user': user.to_dict(),
            'confidence': confidence,
            'liveness_score': liveness_score,
            'attendance_id': attendance.id
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/login/password', methods=['POST'])
def api_login_password():
    """
    Login with username/email and password.
    
    Request JSON:
        {
            "username": "john or john@example.com",
            "password": "password123"
        }
    """
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'Username and password required'
            }), 400
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        ip_address, user_agent = get_client_info()
        
        if not user:
            log_login_attempt(attempt_type='password', failure_reason='user_not_found',
                            ip_address=ip_address, user_agent=user_agent)
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
        
        if not user.check_password(password):
            log_login_attempt(user_id=user.id, attempt_type='password', 
                            failure_reason='wrong_password',
                            ip_address=ip_address, user_agent=user_agent)
            return jsonify({
                'success': False,
                'message': 'Invalid credentials'
            }), 401
        
        if not user.is_active:
            log_login_attempt(user_id=user.id, attempt_type='password',
                            failure_reason='account_disabled',
                            ip_address=ip_address, user_agent=user_agent)
            return jsonify({
                'success': False,
                'message': 'Account is disabled'
            }), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log successful attempt
        log_login_attempt(user_id=user.id, attempt_type='password', success=True,
                         ip_address=ip_address, user_agent=user_agent)
        
        # Create attendance log
        attendance = log_attendance(
            user_id=user.id,
            login_method='password',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Generate JWT token (use str for identity for compatibility)
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'success': True,
            'message': f'Welcome, {user.username}!',
            'access_token': access_token,
            'user': user.to_dict(),
            'attendance_id': attendance.id
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout():
    """Logout and close attendance session."""
    try:
        user_id = get_jwt_identity()
        
        # Close active attendance session
        active_session = get_user_active_session(user_id)
        if active_session:
            log_logout(active_session.id)
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/me', methods=['GET'])
@login_required
def api_me():
    """Get current user info."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# API Routes - User Management (Admin)
# =============================================================================

@app.route('/api/users', methods=['GET'])
@admin_required
def api_list_users():
    """List all users (admin only)."""
    try:
        role = request.args.get('role', None)
        
        if role:
            users = User.query.filter_by(role=role).all()
        else:
            users = User.query.all()
        
        return jsonify({
            'success': True,
            'users': [u.to_dict() for u in users],
            'total': len(users)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def api_get_user(user_id):
    """Get user by ID (admin only)."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def api_update_user(user_id):
    """Update user (admin only)."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        data = request.get_json()
        
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = data['role']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User updated',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def api_delete_user(user_id):
    """Delete user (admin only)."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Prevent deleting self
        current_user = get_current_user()
        if current_user.id == user_id:
            return jsonify({
                'success': False,
                'message': 'Cannot delete your own account'
            }), 400
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User {username} deleted'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# API Routes - Attendance
# =============================================================================

@app.route('/api/attendance', methods=['GET'])
@login_required
def api_get_attendance():
    """Get attendance logs."""
    try:
        current_user = get_current_user()
        
        # Regular users can only see their own logs
        if current_user.is_admin():
            user_id = request.args.get('user_id', type=int)
        else:
            user_id = current_user.id
        
        limit = request.args.get('limit', 100, type=int)
        
        logs = get_attendance_logs(user_id=user_id, limit=limit)
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs],
            'total': len(logs)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/attendance/today', methods=['GET'])
@admin_required
def api_attendance_today():
    """Get today's attendance (admin only)."""
    try:
        from datetime import date
        today = datetime.combine(date.today(), datetime.min.time())
        
        logs = AttendanceLog.query.filter(
            AttendanceLog.login_time >= today
        ).order_by(AttendanceLog.login_time.desc()).all()
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs],
            'total': len(logs),
            'date': today.strftime('%Y-%m-%d')
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/login-attempts', methods=['GET'])
@admin_required
def api_login_attempts():
    """Get login attempts (admin only)."""
    try:
        success = request.args.get('success', type=lambda x: x.lower() == 'true')
        limit = request.args.get('limit', 100, type=int)
        
        query = LoginAttempt.query
        
        if success is not None:
            query = query.filter_by(success=success)
        
        attempts = query.order_by(LoginAttempt.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'attempts': [a.to_dict() for a in attempts],
            'total': len(attempts)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# API Routes - Dashboard Stats (Admin)
# =============================================================================

@app.route('/api/stats', methods=['GET'])
@admin_required
def api_stats():
    """Get system statistics (admin only)."""
    try:
        from datetime import date, timedelta
        today = datetime.combine(date.today(), datetime.min.time())
        week_ago = today - timedelta(days=7)
        
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        admin_count = User.query.filter_by(role='admin').count()
        
        today_logins = AttendanceLog.query.filter(
            AttendanceLog.login_time >= today
        ).count()
        
        week_logins = AttendanceLog.query.filter(
            AttendanceLog.login_time >= week_ago
        ).count()
        
        failed_attempts = LoginAttempt.query.filter(
            LoginAttempt.success == False,
            LoginAttempt.timestamp >= today
        ).count()
        
        active_sessions = AttendanceLog.query.filter_by(is_active=True).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'admin_count': admin_count,
                'today_logins': today_logins,
                'week_logins': week_logins,
                'failed_attempts_today': failed_attempts,
                'active_sessions': active_sessions
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# API Routes - Settings
# =============================================================================

@app.route('/api/settings', methods=['GET'])
@admin_required
def api_get_settings():
    """Get system settings (admin only)."""
    try:
        from config import (
            FACE_RECOGNITION_MODEL, FACE_ENCODING_JITTERS,
            FACE_MATCH_TOLERANCE, LIVENESS_ENABLED,
            HEAD_MOVEMENT_ENABLED, LIVENESS_CHALLENGE_MODE
        )
        
        return jsonify({
            'success': True,
            'settings': {
                'face_recognition_model': FACE_RECOGNITION_MODEL,
                'face_encoding_jitters': FACE_ENCODING_JITTERS,
                'face_match_tolerance': FACE_MATCH_TOLERANCE,
                'liveness_enabled': LIVENESS_ENABLED,
                'head_movement_enabled': HEAD_MOVEMENT_ENABLED,
                'liveness_challenge_mode': LIVENESS_CHALLENGE_MODE
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Resource not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    # Initialize database
    init_db(app)
    
    print("\n" + "="*60)
    print("       Face Login System - Flask API")
    print("="*60)
    print(f"  Server: http://localhost:5000")
    print(f"  API Docs: http://localhost:5000/api")
    print("="*60 + "\n")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
