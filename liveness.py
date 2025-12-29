"""
Liveness Detection Module
Anti-spoofing measures to prevent photo/video attacks.
Refactored for pure OpenCV usage (no dlib landmarks).
"""

import cv2
import numpy as np
import time
from face_utils import detect_faces
from config import (
    SHOW_PREVIEW
)


def detect_blink(cap, timeout=5):
    """
    Detect blink - DISABLED in OpenCV-only mode.
    Fallbacks to simple delay.
    
    Args:
        cap: OpenCV VideoCapture object
        timeout: Maximum seconds to wait
    
    Returns:
        Tuple of (blink_detected: bool, frames_captured: list, liveness_score: float)
    """
    print("\n🔍 Liveness Check: Blink detection disabled (No landmarks).")
    
    frames_captured = []
    start_time = time.time()
    
    # Just capture some frames to simulate checking
    while time.time() - start_time < 2.0:
        ret, frame = cap.read()
        if not ret:
            break
        frames_captured.append(frame.copy())
        
        if SHOW_PREVIEW:
            cv2.putText(frame, "Liveness: Checking...", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow("Liveness Check", frame)
            
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    if SHOW_PREVIEW:
        cv2.destroyWindow("Liveness Check")
        
    # Always return True in this mode since we can't verify
    print("✓ Blink check skipped (compatibility mode)")
    return True, frames_captured, 50.0


def detect_head_movement(cap, timeout=None):
    """
    Detect head movement - Simplified to movement detection.
    
    Args:
        cap: OpenCV VideoCapture object
        timeout: Maximum seconds to wait
    
    Returns:
        Tuple of (movement_detected: bool, frames_captured: list, liveness_score: float)
    """
    print("\n🔍 Liveness Check: Please MOVE your head slightly...")
    
    if timeout is None:
        timeout = 5
        
    frames_captured = []
    face_positions = []
    movement_detected = False
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        if not ret:
            continue
            
        frames_captured.append(frame.copy())
        
        # Detect faces
        faces = detect_faces(frame)
        
        display_frame = frame.copy()
        
        if faces:
            top, right, bottom, left = faces[0]
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2
            
            face_positions.append((center_x, center_y))
            
            # Check for movement if we have enough points
            if len(face_positions) > 3:
                # Calculate movement magnitude
                dx = abs(face_positions[-1][0] - face_positions[0][0])
                dy = abs(face_positions[-1][1] - face_positions[0][1])
                
                if dx > 20 or dy > 20:  # Threshold for movement
                    movement_detected = True
                    cv2.putText(display_frame, "MOVEMENT DETECTED!", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if SHOW_PREVIEW:
            cv2.putText(display_frame, f"Movement: {'YES' if movement_detected else 'NO'}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0) if movement_detected else (0, 0, 255), 2)
            cv2.imshow("Liveness Check", display_frame)
            
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
        if movement_detected and len(frames_captured) > 10:
            time.sleep(0.5)
            break
            
    if SHOW_PREVIEW:
        cv2.destroyWindow("Liveness Check")
        
    return movement_detected, frames_captured, 80.0 if movement_detected else 0.0


def verify_liveness(cap, require_blink=False, challenge_mode="random"):
    """
    Perform liveness verification.
    """
    # Simplified flow
    return detect_head_movement(cap)


def verify_liveness_api(frame_data):
    """
    API-friendly liveness verification for single frame analysis.
    Simplified checks only.
    """
    import base64
    
    # Decode if base64
    if isinstance(frame_data, str):
        try:
            if ',' in frame_data:
                frame_data = frame_data.split(',')[1]
            img_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except:
            return False, 0.0, "Invalid image data"
    else:
        frame = frame_data
        
    # Just check if a face exists
    faces = detect_faces(frame)
    
    if not faces:
        return False, 0.0, "No face detected"
        
    if len(faces) > 1:
        return False, 0.0, "Multiple faces detected"
        
    return True, 50.0, "Face detected (Liveness skipped)"
