"""
SQLAlchemy Models for Face Login System
Defines database schema for users, roles, and attendance logs
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import bcrypt
import numpy as np
import json

db = SQLAlchemy()


class User(db.Model):
    """User model with face encoding and role support."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Optional for face-only users
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    
    # Face encoding stored as JSON string (128 floats)
    face_encoding = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    attendance_logs = db.relationship('AttendanceLog', backref='user', lazy='dynamic')
    login_attempts = db.relationship('LoginAttempt', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        """Verify password."""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def set_face_encoding(self, encoding):
        """Store face encoding as JSON."""
        if isinstance(encoding, np.ndarray):
            self.face_encoding = json.dumps(encoding.tolist())
        else:
            self.face_encoding = json.dumps(encoding)
    
    def get_face_encoding(self):
        """Retrieve face encoding as numpy array."""
        if self.face_encoding:
            return np.array(json.loads(self.face_encoding))
        return None
    
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'has_face': self.face_encoding is not None,
            'has_password': self.password_hash is not None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


class AttendanceLog(db.Model):
    """Track user attendance/login sessions."""
    __tablename__ = 'attendance_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Login/Logout times
    login_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    logout_time = db.Column(db.DateTime, nullable=True)
    
    # Login method and verification
    login_method = db.Column(db.String(20), default='face')  # 'face', 'password', 'both'
    liveness_score = db.Column(db.Float, nullable=True)  # 0-100 liveness confidence
    face_confidence = db.Column(db.Float, nullable=True)  # Face match confidence
    
    # Session info
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)  # Currently logged in
    
    def duration_minutes(self):
        """Calculate session duration in minutes."""
        if self.logout_time:
            delta = self.logout_time - self.login_time
            return delta.total_seconds() / 60
        return None
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'login_time': self.login_time.isoformat() if self.login_time else None,
            'logout_time': self.logout_time.isoformat() if self.logout_time else None,
            'duration_minutes': self.duration_minutes(),
            'login_method': self.login_method,
            'liveness_score': self.liveness_score,
            'face_confidence': self.face_confidence,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<AttendanceLog {self.user_id} @ {self.login_time}>'


class LoginAttempt(db.Model):
    """Track all login attempts for security monitoring."""
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Null if unknown user
    
    # Attempt details
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    attempt_type = db.Column(db.String(20), default='face')  # 'face', 'password'
    success = db.Column(db.Boolean, default=False)
    
    # Failure info
    failure_reason = db.Column(db.String(100), nullable=True)
    # Reasons: 'unknown_face', 'wrong_password', 'liveness_failed', 'no_face_detected', 'account_disabled'
    
    # Session info
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    def to_dict(self):
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'attempt_type': self.attempt_type,
            'success': self.success,
            'failure_reason': self.failure_reason,
            'ip_address': self.ip_address
        }
    
    def __repr__(self):
        return f'<LoginAttempt {self.id} - {"Success" if self.success else "Failed"}>'


def init_db(app):
    """Initialize database and create tables."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _create_default_admin()
        print("[OK] Database initialized successfully!")


def _create_default_admin():
    """Create default admin user if not exists."""
    from config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, ROLE_ADMIN
    
    admin = User.query.filter_by(username=DEFAULT_ADMIN_USERNAME).first()
    if not admin:
        admin = User(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            role=ROLE_ADMIN
        )
        admin.set_password(DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()
        print(f"[OK] Default admin user created: {DEFAULT_ADMIN_USERNAME}")
