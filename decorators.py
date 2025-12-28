"""
Flask Route Decorators for Role-Based Access Control
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models import User


def login_required(f):
    """Decorator to require authenticated user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'Authentication required',
                'error': str(e)
            }), 401
    return decorated_function


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(int(user_id))
            
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'User not found'
                }), 404
            
            if not user.is_admin():
                return jsonify({
                    'success': False,
                    'message': 'Admin access required'
                }), 403
            
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'Authentication required',
                'error': str(e)
            }), 401
    return decorated_function


def role_required(*roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                user = User.query.get(int(user_id))
                
                if not user:
                    return jsonify({
                        'success': False,
                        'message': 'User not found'
                    }), 404
                
                if user.role not in roles:
                    return jsonify({
                        'success': False,
                        'message': f'Required role: {", ".join(roles)}'
                    }), 403
                
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': 'Authentication required',
                    'error': str(e)
                }), 401
        return decorated_function
    return decorator


def get_current_user():
    """Get current authenticated user from JWT."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        # Ensure user_id is an integer
        if user_id is not None:
            return User.query.get(int(user_id))
        return None
    except Exception as e:
        print(f"get_current_user error: {e}")
        return None
