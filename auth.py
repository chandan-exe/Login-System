"""
Authentication Module
Handles user registration and login with face recognition
"""

import cv2
import time
import numpy as np
from face_utils import (
    get_camera, capture_frame, detect_faces, encode_face,
    find_best_match, draw_face_box
)
from database import (
    save_user, load_users, user_exists, delete_user as db_delete_user,
    list_users, get_user_count
)
from liveness import verify_liveness
from config import (
    REGISTRATION_FRAMES,
    REGISTRATION_DELAY,
    FACE_MATCH_TOLERANCE,
    LIVENESS_ENABLED,
    SHOW_PREVIEW,
    PREVIEW_WINDOW_NAME
)


def register_user(username):
    """
    Register a new user by capturing their face.
    
    Args:
        username: Name to register
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check if user already exists
    if user_exists(username):
        return False, f"User '{username}' is already registered."
    
    print(f"\n📸 Registering user: {username}")
    print("Please look at the camera and remain still...")
    print(f"Capturing {REGISTRATION_FRAMES} frames for accuracy.\n")
    
    try:
        cap = get_camera()
    except RuntimeError as e:
        return False, str(e)
    
    encodings = []
    frames_captured = 0
    
    try:
        while frames_captured < REGISTRATION_FRAMES:
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Detect faces
            faces = detect_faces(frame)
            
            display_frame = frame.copy()
            
            if len(faces) == 0:
                cv2.putText(display_frame, "No face detected - Position your face", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            elif len(faces) > 1:
                cv2.putText(display_frame, "Multiple faces - Only one person please", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                for face in faces:
                    draw_face_box(display_frame, face, "", (0, 165, 255))
            else:
                # Single face detected
                face = faces[0]
                draw_face_box(display_frame, face, f"Capturing... {frames_captured+1}/{REGISTRATION_FRAMES}", (0, 255, 0))
                
                # Encode face
                encoding = encode_face(frame, face)
                
                if encoding is not None:
                    encodings.append(encoding)
                    frames_captured += 1
                    print(f"  ✓ Frame {frames_captured}/{REGISTRATION_FRAMES} captured")
                    time.sleep(REGISTRATION_DELAY)
            
            if SHOW_PREVIEW:
                cv2.putText(display_frame, f"Registration: {username}", (10, display_frame.shape[0] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                cv2.imshow(PREVIEW_WINDOW_NAME, display_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    if len(encodings) < REGISTRATION_FRAMES:
        return False, "Failed to capture enough frames. Please try again."
    
    # Average all encodings for a more robust representation
    average_encoding = np.mean(encodings, axis=0)
    
    # Save to database
    if save_user(username, average_encoding):
        return True, f"✓ User '{username}' registered successfully!"
    else:
        return False, "Failed to save user data."


def login():
    """
    Authenticate user by face recognition.
    
    Returns:
        Tuple of (success: bool, username: str or None, confidence: float)
    """
    users = load_users()
    
    if not users:
        print("\n⚠ No users registered. Please register first.")
        return False, None, 0.0
    
    print(f"\n🔐 Face Login")
    print(f"Registered users: {get_user_count()}")
    print("Please look at the camera...\n")
    
    try:
        cap = get_camera()
    except RuntimeError as e:
        print(f"Error: {e}")
        return False, None, 0.0
    
    try:
        # Liveness check first
        if LIVENESS_ENABLED:
            is_live, frame = verify_liveness(cap)
            
            if not is_live:
                print("\n✗ Liveness check failed. Access denied.")
                return False, None, 0.0
            
            print("\n✓ Liveness verified!")
        else:
            # Just capture a frame
            print("Capturing face...")
            time.sleep(1)
            ret, frame = cap.read()
            if not ret:
                return False, None, 0.0
        
        # Detect and encode face
        faces = detect_faces(frame)
        
        if not faces:
            print("✗ No face detected in captured frame.")
            return False, None, 0.0
        
        encoding = encode_face(frame, faces[0])
        
        if encoding is None:
            print("✗ Could not encode face.")
            return False, None, 0.0
        
        # Find best match
        username, distance, confidence = find_best_match(encoding, users, FACE_MATCH_TOLERANCE)
        
        # Show result
        display_frame = frame.copy()
        
        if username:
            draw_face_box(display_frame, faces[0], f"{username} ({confidence:.1f}%)", (0, 255, 0))
            cv2.putText(display_frame, "ACCESS GRANTED", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            print(f"\n✓ Welcome, {username}!")
            print(f"  Confidence: {confidence:.1f}%")
            print(f"  Distance: {distance:.4f}")
        else:
            draw_face_box(display_frame, faces[0], "Unknown", (0, 0, 255))
            cv2.putText(display_frame, "ACCESS DENIED", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            print(f"\n✗ Access Denied - Unknown face")
            print(f"  Closest distance: {distance:.4f}")
            print(f"  (Threshold: {FACE_MATCH_TOLERANCE})")
        
        if SHOW_PREVIEW:
            cv2.imshow(PREVIEW_WINDOW_NAME, display_frame)
            cv2.waitKey(2000)  # Show result for 2 seconds
        
        return username is not None, username, confidence
        
    finally:
        cap.release()
        cv2.destroyAllWindows()


def verify_specific_user(username):
    """
    Verify if the person in front of camera is a specific user.
    
    Args:
        username: Username to verify against
    
    Returns:
        Tuple of (verified: bool, confidence: float)
    """
    users = load_users()
    
    if username not in users:
        print(f"\n⚠ User '{username}' is not registered.")
        return False, 0.0
    
    print(f"\n🔐 Verifying: {username}")
    print("Please look at the camera...\n")
    
    try:
        cap = get_camera()
    except RuntimeError as e:
        print(f"Error: {e}")
        return False, 0.0
    
    try:
        # Liveness check
        if LIVENESS_ENABLED:
            is_live, frame = verify_liveness(cap)
            
            if not is_live:
                print("\n✗ Liveness check failed.")
                return False, 0.0
        else:
            time.sleep(1)
            ret, frame = cap.read()
            if not ret:
                return False, 0.0
        
        # Encode face
        faces = detect_faces(frame)
        
        if not faces:
            print("✗ No face detected.")
            return False, 0.0
        
        encoding = encode_face(frame, faces[0])
        
        if encoding is None:
            return False, 0.0
        
        # Compare with specific user
        known_encoding = np.array(users[username])
        distance = np.linalg.norm(known_encoding - encoding)
        
        is_match = distance <= FACE_MATCH_TOLERANCE
        confidence = max(0, (FACE_MATCH_TOLERANCE - distance) / FACE_MATCH_TOLERANCE) * 100 if is_match else 0
        
        if is_match:
            print(f"\n✓ Verified: You are {username}")
            print(f"  Confidence: {confidence:.1f}%")
        else:
            print(f"\n✗ Verification failed: You are NOT {username}")
            print(f"  Distance: {distance:.4f}")
        
        return is_match, confidence
        
    finally:
        cap.release()
        cv2.destroyAllWindows()


def remove_user(username):
    """Remove a registered user."""
    if db_delete_user(username):
        return True, f"✓ User '{username}' has been removed."
    return False, f"User '{username}' not found."


def get_all_users():
    """Get list of all registered users."""
    return list_users()
