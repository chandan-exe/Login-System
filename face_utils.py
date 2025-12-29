"""
Face Detection and Encoding Utilities
Core functions for face recognition operations using pure OpenCV (No dlib/face_recognition)
"""

import cv2
import numpy as np
import os
from config import (
    FACE_MATCH_TOLERANCE,
    CAMERA_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
)

# Load Haar Cascade for face detection
# Try to load from cv2 data, fallback to local file if needed
CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
if not os.path.exists(CASCADE_PATH):
    # Fallback to looking in local directory or common paths if cv2 data is missing
    CASCADE_PATH = 'haarcascade_frontalface_default.xml'

face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

def get_camera():
    """Initialize and return camera capture object."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    
    if not cap.isOpened():
        raise RuntimeError("Could not open camera. Please check if webcam is connected.")
    
    return cap


def capture_frame(cap):
    """Capture a single frame from camera."""
    ret, frame = cap.read()
    if not ret:
        raise RuntimeError("Failed to capture frame from camera.")
    return frame


def detect_faces(image, model="hog"):
    """
    Detect faces in an image using Haar Cascades.
    
    Args:
        image: BGR image from OpenCV
        model: Ignored (kept for compatibility signature)
    
    Returns:
        List of face locations as (top, right, bottom, left) tuples
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    # Convert (x, y, w, h) to (top, right, bottom, left)
    face_locations = []
    for (x, y, w, h) in faces:
        top = y
        right = x + w
        bottom = y + h
        left = x
        face_locations.append((top, right, bottom, left))
        
    return face_locations


def encode_face(image, face_location=None, num_jitters=1):
    """
    Generate a simplified face encoding by resizing and flattening the face image.
    WARNING: This is NOT a deep learning encoding and has low accuracy.
    
    Args:
        image: BGR image from OpenCV
        face_location: Optional specific face location (top, right, bottom, left)
        num_jitters: Ignored
    
    Returns:
        numpy array of floats representing face encoding, or None if no face found
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    if face_location is None:
        faces = detect_faces(image)
        if not faces:
            return None
        face_location = faces[0]
    
    top, right, bottom, left = face_location
    
    # Crop face
    face_roi = gray[top:bottom, left:right]
    
    if face_roi.size == 0:
        return None
        
    # Resize to fixed size for consistent encoding length (e.g., 64x64)
    # 64x64 = 4096 dimensions
    try:
        resized_face = cv2.resize(face_roi, (64, 64))
        
        # Flatten and normalize
        encoding = resized_face.flatten().astype('float32')
        encoding /= 255.0  # Normalize pixel values to 0-1
        
        return encoding
    except Exception as e:
        print(f"Error encoding face: {e}")
        return None


def compare_faces(known_encoding, unknown_encoding, tolerance=None):
    """
    Compare two face encodings using Mean Squared Error or correlation.
    
    Args:
        known_encoding: Stored face encoding
        unknown_encoding: Face encoding to compare
        tolerance: Distance threshold
    
    Returns:
        Tuple of (is_match: bool, distance: float)
    """
    if tolerance is None:
        # Use a default tolerance suitable for pixel comparison
        # MSE for identical images is 0. 
        # For different faces, it might be around 0.1-0.3 depending on lighting
        tolerance = 0.15 
        
    # Calculate Mean Squared Error
    # Check if shapes match
    if known_encoding.shape != unknown_encoding.shape:
        return False, 1.0
        
    mse = np.mean((known_encoding - unknown_encoding) ** 2)
    
    is_match = mse <= tolerance
    
    return is_match, mse


def find_best_match(unknown_encoding, known_encodings_dict, tolerance=0.15):
    """
    Find the best matching face.
    
    Args:
        unknown_encoding: Face encoding to identify
        known_encodings_dict: Dict of {username: encoding}
        tolerance: MSE threshold
    
    Returns:
        Tuple of (username: str or None, distance: float, confidence: float)
    """
    if not known_encodings_dict:
        return None, float('inf'), 0.0
    
    best_match = None
    best_distance = float('inf')
    
    for username, known_encoding in known_encodings_dict.items():
        known_encoding = np.array(known_encoding)
        
        # Ensure shapes match
        if known_encoding.shape != unknown_encoding.shape:
            continue
            
        is_match, distance = compare_faces(known_encoding, unknown_encoding, tolerance)
        
        if distance < best_distance:
            best_distance = distance
            best_match = username
    
    # Calculate confidence
    if best_distance <= tolerance:
        # Scale confidence based on how close it is to 0 relative to tolerance
        confidence = max(0, (tolerance - best_distance) / tolerance) * 100
        return best_match, best_distance, confidence
    
    return None, best_distance, 0.0


def draw_face_box(image, face_location, name="", color=(0, 255, 0)):
    """
    Draw bounding box around face.
    
    Args:
        image: BGR image
        face_location: (top, right, bottom, left) tuple
        name: Name to display
        color: BGR color tuple
    
    Returns:
        Image with drawn box
    """
    top, right, bottom, left = face_location
    
    # Draw rectangle
    cv2.rectangle(image, (left, top), (right, bottom), color, 2)
    
    # Draw label background
    cv2.rectangle(image, (left, bottom - 25), (right, bottom), color, cv2.FILLED)
    
    # Draw name
    cv2.putText(image, name, (left + 6, bottom - 6), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    
    return image


def get_face_landmarks(image):
    """
    Get facial landmarks.
    NOT SUPPORTED in OpenCV-only mode (requires dlib/mediapipe).
    
    Returns:
        None
    """
    return None
