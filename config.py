"""
Configuration settings for Face Login System
"""

import os
from datetime import timedelta

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data storage (Legacy - for CLI mode)
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

# =============================================================================
# MySQL Database Settings (Unused - Switched to SQLite)
# MYSQL_HOST = "localhost"
# MYSQL_PORT = 3306
# MYSQL_USER = "root"
# MYSQL_PASSWORD = ""
# MYSQL_DATABASE = "face_login_db"

# SQLAlchemy Database URI
SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'face_login.db')}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# =============================================================================
# Flask Settings
# =============================================================================
SECRET_KEY = os.environ.get("SECRET_KEY", "face-login-secret-key-change-in-production")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

# =============================================================================
# User Roles
# =============================================================================
ROLE_ADMIN = "admin"
ROLE_USER = "user"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@facelogin.local"
DEFAULT_ADMIN_PASSWORD = "admin123"  # Change on first login!

# =============================================================================
# Face Recognition Settings
# =============================================================================
# FACE_RECOGNITION_MODEL = "hog"  # Removed: Not used in OpenCV-only mode
# FACE_ENCODING_JITTERS = 3  # Removed: Not used in OpenCV-only mode
FACE_MATCH_TOLERANCE = 0.5  # Lower = stricter (default is 0.6)

# Registration Settings
REGISTRATION_FRAMES = 5  # Number of frames to capture for registration
REGISTRATION_DELAY = 0.5  # Seconds between frame captures

# =============================================================================
# Liveness Detection Settings
# =============================================================================
LIVENESS_ENABLED = True
EYE_AR_THRESH = 0.25  # Eye aspect ratio threshold for blink detection
EYE_AR_CONSEC_FRAMES = 2  # Consecutive frames for blink
BLINK_REQUIRED = True  # Require blink to verify liveness

# Head Movement Detection (NEW)
HEAD_MOVEMENT_ENABLED = True
HEAD_MOVEMENT_THRESHOLD = 20  # Minimum pixels of nose movement
HEAD_MOVEMENT_TIMEOUT = 15  # Seconds to complete head movement

# Liveness challenge modes: "blink", "head", "random", "both"
LIVENESS_CHALLENGE_MODE = "random"

# =============================================================================
# Camera Settings
# =============================================================================
CAMERA_INDEX = 0  # Default camera
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# =============================================================================
# Display Settings
# =============================================================================
SHOW_PREVIEW = True  # Show camera preview during capture
PREVIEW_WINDOW_NAME = "Face Login System"

# =============================================================================
# Attendance Settings
# =============================================================================
ATTENDANCE_AUTO_CHECKOUT_HOURS = 8  # Auto checkout after N hours if not logged out
