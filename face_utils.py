"""
Face Detection and Encoding Utilities
Core functions for face recognition operations
"""

import cv2
import numpy as np
import face_recognition
from config import (
    FACE_RECOGNITION_MODEL,
    FACE_ENCODING_JITTERS,
    FACE_MATCH_TOLERANCE,
    CAMERA_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    SHOW_PREVIEW,
    PREVIEW_WINDOW_NAME
)


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


def detect_faces(image, model=FACE_RECOGNITION_MODEL):
    """
    Detect faces in an image.
    
    Args:
        image: BGR image from OpenCV
        model: "hog" (faster) or "cnn" (more accurate)
    
    Returns:
        List of face locations as (top, right, bottom, left) tuples
    """
    # Convert BGR to RGB for face_recognition
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Detect face locations
    face_locations = face_recognition.face_locations(rgb_image, model=model)
    
    return face_locations


def encode_face(image, face_location=None, num_jitters=FACE_ENCODING_JITTERS):
    """
    Generate 128-dimensional face encoding.
    
    Args:
        image: BGR image from OpenCV
        face_location: Optional specific face location to encode
        num_jitters: Number of times to re-sample face (higher = more accurate)
    
    Returns:
        numpy array of 128 floats representing face encoding, or None if no face found
    """
    # Convert BGR to RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Get face locations if not provided
    if face_location is None:
        face_locations = face_recognition.face_locations(rgb_image, model=FACE_RECOGNITION_MODEL)
        if not face_locations:
            return None
        face_locations = [face_locations[0]]  # Use first face
    else:
        face_locations = [face_location]
    
    # Generate encoding with jittering for accuracy
    encodings = face_recognition.face_encodings(
        rgb_image, 
        known_face_locations=face_locations,
        num_jitters=num_jitters
    )
    
    if not encodings:
        return None
    
    return encodings[0]


def compare_faces(known_encoding, unknown_encoding, tolerance=FACE_MATCH_TOLERANCE):
    """
    Compare two face encodings.
    
    Args:
        known_encoding: Stored face encoding
        unknown_encoding: Face encoding to compare
        tolerance: Distance threshold (lower = stricter)
    
    Returns:
        Tuple of (is_match: bool, distance: float)
    """
    # Calculate Euclidean distance
    distance = np.linalg.norm(known_encoding - unknown_encoding)
    
    is_match = distance <= tolerance
    
    return is_match, distance


def find_best_match(unknown_encoding, known_encodings_dict, tolerance=FACE_MATCH_TOLERANCE):
    """
    Find the best matching face from a dictionary of known encodings.
    
    Args:
        unknown_encoding: Face encoding to identify
        known_encodings_dict: Dict of {username: encoding}
        tolerance: Distance threshold
    
    Returns:
        Tuple of (username: str or None, distance: float, confidence: float)
    """
    if not known_encodings_dict:
        return None, float('inf'), 0.0
    
    best_match = None
    best_distance = float('inf')
    
    for username, known_encoding in known_encodings_dict.items():
        known_encoding = np.array(known_encoding)
        distance = np.linalg.norm(known_encoding - unknown_encoding)
        
        if distance < best_distance:
            best_distance = distance
            best_match = username
    
    # Calculate confidence (inverse of distance, scaled)
    if best_distance <= tolerance:
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
    Get facial landmarks for a face in the image.
    
    Args:
        image: BGR image
    
    Returns:
        Dictionary of facial landmarks or None if no face found
    """
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    face_landmarks_list = face_recognition.face_landmarks(rgb_image)
    
    if not face_landmarks_list:
        return None
    
    return face_landmarks_list[0]
