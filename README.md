# Face Login System

A secure, accurate face recognition authentication system with Flask backend, MySQL database, role-based access control, and attendance tracking.

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Face Recognition** | 128D encoding with 99.38% accuracy using face_recognition library |
| **Liveness Detection** | Anti-spoofing with blink detection + head movement tracking |
| **Flask REST API** | Complete backend with JWT authentication |
| **MySQL Database** | SQLAlchemy ORM with user, attendance, and login attempt tables |
| **Role-Based Access** | Admin and User roles with permission decorators |
| **Attendance Logs** | Automatic login/logout tracking with timestamps |
| **Web Interface** | Modern dark-themed UI with camera integration |
| **CLI Mode** | Original command-line interface still works |

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MySQL (XAMPP recommended)
- Webcam

### Installation

```bash
cd facelogin

# Install dependencies
pip install -r requirements.txt

# Create MySQL database
mysql -u root -e "CREATE DATABASE face_login_db"

# Run Flask app
python app.py
```

### Access
- **Web UI**: http://localhost:5000
- **CLI Mode**: `python main.py`
- **Default Admin**: username: `admin`, password: `admin123`

## 📁 Project Structure

```
facelogin/
├── app.py              # Flask REST API server
├── models.py           # SQLAlchemy database models
├── decorators.py       # Auth decorators (@admin_required)
├── auth.py             # Registration/login logic (CLI)
├── database.py         # MySQL + JSON storage operations
├── face_utils.py       # Face detection/encoding utilities
├── liveness.py         # Blink + head movement detection
├── config.py           # All configuration settings
├── main.py             # CLI application entry point
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   ├── index.html      # Home page
│   ├── login.html      # Face/password login
│   ├── register.html   # User registration
│   ├── dashboard.html  # User dashboard
│   └── admin.html      # Admin panel
└── static/
    ├── css/style.css   # Dark theme styles
    └── js/camera.js    # Camera utilities
```

## 🔌 API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/register` | POST | - | Register new user with face |
| `/api/login/face` | POST | - | Login with face recognition |
| `/api/login/password` | POST | - | Login with password |
| `/api/logout` | POST | ✓ | End session |
| `/api/me` | GET | ✓ | Get current user |
| `/api/users` | GET | Admin | List all users |
| `/api/users/<id>` | DELETE | Admin | Delete user |
| `/api/attendance` | GET | ✓ | Get attendance logs |
| `/api/stats` | GET | Admin | System statistics |

## ⚙️ Configuration

Edit `config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `FACE_MATCH_TOLERANCE` | 0.5 | Lower = stricter matching |
| `LIVENESS_ENABLED` | True | Enable anti-spoofing |
| `LIVENESS_CHALLENGE_MODE` | "random" | "blink", "head", "random", "both" |
| `HEAD_MOVEMENT_ENABLED` | True | Enable head turn detection |
| `MYSQL_DATABASE` | face_login_db | MySQL database name |

## 🔐 Security

- **Anti-Spoofing**: Blink detection + head movement prevents photo attacks
- **JWT Tokens**: 24-hour expiring access tokens
- **Password Hashing**: bcrypt with salt
- **Login Attempts**: All attempts logged for security monitoring
- **Role-Based Access**: Admin-only routes protected with decorators

## 📊 Database Schema

```
users
├── id, username, email, password_hash
├── role (admin/user), face_encoding
└── created_at, last_login, is_active

attendance_logs
├── id, user_id, login_time, logout_time
├── login_method, liveness_score, face_confidence
└── ip_address, user_agent, is_active

login_attempts
├── id, user_id, timestamp, attempt_type
├── success, failure_reason
└── ip_address, user_agent
```

## 📝 License

MIT License - Feel free to use and modify.
