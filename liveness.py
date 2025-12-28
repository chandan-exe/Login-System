"""
Liveness Detection Module
Anti-spoofing measures to prevent photo/video attacks
Includes blink detection and head movement tracking
"""

import cv2
import numpy as np
import time
import random
from scipy.spatial import distance as dist
from face_utils import get_face_landmarks, detect_faces
from config import (
    EYE_AR_THRESH,
    EYE_AR_CONSEC_FRAMES,
    BLINK_REQUIRED,
    HEAD_MOVEMENT_ENABLED,
    HEAD_MOVEMENT_THRESHOLD,
    HEAD_MOVEMENT_TIMEOUT,
    LIVENESS_CHALLENGE_MODE,
    SHOW_PREVIEW
)


def eye_aspect_ratio(eye_points):
    """
    Calculate the eye aspect ratio (EAR).
    
    The EAR is a scalar that falls rapidly when the eye closes.
    
    Args:
        eye_points: List of 6 (x, y) points defining the eye
    
    Returns:
        Float value of EAR
    """
    # Convert to numpy array if needed
    eye = np.array(eye_points)
    
    # Compute vertical distances
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    
    # Compute horizontal distance
    C = dist.euclidean(eye[0], eye[3])
    
    # Calculate EAR
    ear = (A + B) / (2.0 * C)
    
    return ear


def detect_blink(cap, timeout=10):
    """
    Detect if user blinks within timeout period.
    
    Args:
        cap: OpenCV VideoCapture object
        timeout: Maximum seconds to wait for blink
    
    Returns:
        Tuple of (blink_detected: bool, frames_captured: list, liveness_score: float)
    """
    print("\n🔍 Liveness Check: Please BLINK your eyes...")
    
    blink_counter = 0
    blink_detected = False
    frames_captured = []
    below_threshold_frames = 0
    ear_values = []
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        if not ret:
            continue
        
        # Store frame for later use
        frames_captured.append(frame.copy())
        
        # Get face landmarks
        landmarks = get_face_landmarks(frame)
        
        if landmarks is None:
            # No face detected
            if SHOW_PREVIEW:
                cv2.putText(frame, "No face detected - Look at camera", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("Liveness Check", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue
        
        # Get eye landmarks
        left_eye = landmarks.get('left_eye', [])
        right_eye = landmarks.get('right_eye', [])
        
        if len(left_eye) >= 6 and len(right_eye) >= 6:
            # Calculate EAR for both eyes
            left_ear = eye_aspect_ratio(left_eye)
            right_ear = eye_aspect_ratio(right_eye)
            
            # Average EAR
            ear = (left_ear + right_ear) / 2.0
            ear_values.append(ear)
            
            # Check for blink
            if ear < EYE_AR_THRESH:
                below_threshold_frames += 1
            else:
                if below_threshold_frames >= EYE_AR_CONSEC_FRAMES:
                    blink_counter += 1
                    blink_detected = True
                    print(f"✓ Blink detected! (Count: {blink_counter})")
                below_threshold_frames = 0
            
            # Display status
            if SHOW_PREVIEW:
                status = f"EAR: {ear:.2f} | Blinks: {blink_counter}"
                color = (0, 255, 0) if blink_detected else (0, 165, 255)
                cv2.putText(frame, status, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                if blink_detected:
                    cv2.putText(frame, "BLINK DETECTED - Liveness Verified!", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if SHOW_PREVIEW:
            cv2.imshow("Liveness Check", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        # Exit early if blink detected
        if blink_detected:
            time.sleep(0.5)  # Show success message briefly
            break
    
    if SHOW_PREVIEW:
        cv2.destroyWindow("Liveness Check")
    
    if not blink_detected:
        print("✗ No blink detected within timeout period.")
    
    # Calculate liveness score based on EAR variance and blink detection
    liveness_score = 0.0
    if blink_detected:
        # Base score for detecting blink
        liveness_score = 70.0
        # Bonus for EAR variance (natural eye movement)
        if ear_values:
            ear_variance = np.var(ear_values)
            liveness_score += min(30.0, ear_variance * 1000)
    
    return blink_detected, frames_captured, liveness_score


def detect_head_movement(cap, timeout=None):
    """
    Detect head movement (turn left then right) for liveness verification.
    Tracks nose position across frames to detect natural movement.
    
    Args:
        cap: OpenCV VideoCapture object
        timeout: Maximum seconds to wait (uses config default if None)
    
    Returns:
        Tuple of (movement_detected: bool, frames_captured: list, liveness_score: float)
    """
    if timeout is None:
        timeout = HEAD_MOVEMENT_TIMEOUT
    
    print("\n🔍 Liveness Check: Please TURN YOUR HEAD left, then right...")
    
    frames_captured = []
    nose_positions = []
    
    # Movement tracking
    initial_nose_x = None
    turned_left = False
    turned_right = False
    movement_detected = False
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        if not ret:
            continue
        
        frames_captured.append(frame.copy())
        
        # Get face landmarks
        landmarks = get_face_landmarks(frame)
        
        display_frame = frame.copy()
        
        if landmarks is None:
            if SHOW_PREVIEW:
                cv2.putText(display_frame, "No face detected - Look at camera", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.imshow("Liveness Check", display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue
        
        # Get nose tip position (center of face tracking)
        nose_bridge = landmarks.get('nose_bridge', [])
        
        if nose_bridge:
            # Use bottom of nose bridge as reference point
            nose_tip = nose_bridge[-1] if len(nose_bridge) > 0 else None
            
            if nose_tip:
                nose_x = nose_tip[0]
                nose_positions.append(nose_x)
                
                # Initialize reference position
                if initial_nose_x is None:
                    initial_nose_x = nose_x
                
                # Calculate movement from initial position
                movement = nose_x - initial_nose_x
                
                # Check for left turn (nose moves right in mirrored camera)
                if movement > HEAD_MOVEMENT_THRESHOLD and not turned_left:
                    turned_left = True
                    print("✓ Left turn detected!")
                
                # Check for right turn (nose moves left in mirrored camera)
                if movement < -HEAD_MOVEMENT_THRESHOLD and turned_left and not turned_right:
                    turned_right = True
                    movement_detected = True
                    print("✓ Right turn detected!")
                
                # Draw visualization
                if SHOW_PREVIEW:
                    # Draw nose position indicator
                    cv2.circle(display_frame, nose_tip, 5, (0, 255, 0), -1)
                    
                    # Draw movement bar
                    bar_width = int(abs(movement))
                    bar_color = (0, 255, 0) if turned_left else (0, 165, 255)
                    cv2.rectangle(display_frame, (320, 50), (320 + int(movement), 70), bar_color, -1)
                    
                    # Status text
                    status = f"Movement: {movement:.0f}px | Left: {'✓' if turned_left else '○'} | Right: {'✓' if turned_right else '○'}"
                    cv2.putText(display_frame, status, (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    if movement_detected:
                        cv2.putText(display_frame, "HEAD MOVEMENT VERIFIED!", (10, 100),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        if SHOW_PREVIEW:
            cv2.imshow("Liveness Check", display_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        if movement_detected:
            time.sleep(0.5)
            break
    
    if SHOW_PREVIEW:
        cv2.destroyWindow("Liveness Check")
    
    if not movement_detected:
        if not turned_left:
            print("✗ No left turn detected.")
        elif not turned_right:
            print("✗ No right turn detected.")
    
    # Calculate liveness score
    liveness_score = 0.0
    if movement_detected:
        liveness_score = 80.0
        # Bonus for smooth movement (low position variance indicates natural motion)
        if len(nose_positions) > 5:
            # Check for continuous movement pattern
            position_changes = [abs(nose_positions[i] - nose_positions[i-1]) 
                               for i in range(1, len(nose_positions))]
            avg_change = np.mean(position_changes) if position_changes else 0
            liveness_score += min(20.0, avg_change)
    elif turned_left:
        # Partial credit for completing one direction
        liveness_score = 30.0
    
    return movement_detected, frames_captured, liveness_score


def check_face_movement(frames, threshold=5):
    """
    Check if face has natural movement across frames.
    Static images (photos) won't show natural micro-movements.
    
    Args:
        frames: List of captured frames
        threshold: Minimum pixel movement expected
    
    Returns:
        Boolean indicating if natural movement detected
    """
    if len(frames) < 5:
        return False
    
    face_positions = []
    
    for frame in frames:
        faces = detect_faces(frame)
        if faces:
            top, right, bottom, left = faces[0]
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2
            face_positions.append((center_x, center_y))
    
    if len(face_positions) < 3:
        return False
    
    # Calculate total movement
    total_movement = 0
    for i in range(1, len(face_positions)):
        dx = abs(face_positions[i][0] - face_positions[i-1][0])
        dy = abs(face_positions[i][1] - face_positions[i-1][1])
        total_movement += (dx + dy)
    
    # Average movement per frame transition
    avg_movement = total_movement / (len(face_positions) - 1)
    
    return avg_movement >= threshold


def verify_liveness(cap, require_blink=None, challenge_mode=None):
    """
    Perform liveness verification with configurable challenge.
    
    Args:
        cap: OpenCV VideoCapture object
        require_blink: Whether to require blink detection (uses config if None)
        challenge_mode: Challenge type - "blink", "head", "random", "both" (uses config if None)
    
    Returns:
        Tuple of (is_live: bool, best_frame: numpy array or None, liveness_score: float)
    """
    if require_blink is None:
        require_blink = BLINK_REQUIRED
    
    if challenge_mode is None:
        challenge_mode = LIVENESS_CHALLENGE_MODE
    
    print("\n" + "="*50)
    print("       LIVENESS VERIFICATION")
    print("="*50)
    
    # Determine which challenge to perform
    if challenge_mode == "random":
        challenge = random.choice(["blink", "head"])
    else:
        challenge = challenge_mode
    
    total_score = 0.0
    frames = []
    is_live = False
    
    if challenge == "blink" or challenge == "both":
        if require_blink:
            blink_ok, blink_frames, blink_score = detect_blink(cap)
            frames.extend(blink_frames)
            total_score += blink_score
            
            if not blink_ok:
                return False, None, 0.0
            
            is_live = True
    
    if challenge == "head" or challenge == "both":
        if HEAD_MOVEMENT_ENABLED:
            head_ok, head_frames, head_score = detect_head_movement(cap)
            frames.extend(head_frames)
            total_score += head_score
            
            if challenge == "head" and not head_ok:
                return False, None, 0.0
            
            if head_ok:
                is_live = True
    
    # Also check for natural micro-movements
    if frames:
        movement_ok = check_face_movement(frames)
        if not movement_ok:
            print("⚠ Warning: Limited movement detected. This might be a photo.")
            total_score *= 0.8  # Reduce score but don't fail
    
    # Normalize score to 0-100
    if challenge == "both":
        total_score = min(100.0, total_score / 2)
    else:
        total_score = min(100.0, total_score)
    
    # Get best frame (one from middle of capture)
    best_frame = None
    if frames:
        best_frame = frames[len(frames) // 2]
    
    if is_live:
        print(f"\n✓ Liveness verified! Score: {total_score:.1f}%")
    
    return is_live, best_frame, total_score


def verify_liveness_api(frame_data):
    """
    API-friendly liveness verification for single frame analysis.
    Used by Flask API for web-based verification.
    
    Args:
        frame_data: Base64 encoded image or numpy array
    
    Returns:
        Tuple of (is_live: bool, liveness_score: float, message: str)
    """
    import base64
    
    # Decode if base64
    if isinstance(frame_data, str):
        try:
            img_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except:
            return False, 0.0, "Invalid image data"
    else:
        frame = frame_data
    
    # Basic checks for single frame
    faces = detect_faces(frame)
    
    if not faces:
        return False, 0.0, "No face detected"
    
    if len(faces) > 1:
        return False, 0.0, "Multiple faces detected"
    
    # Get landmarks
    landmarks = get_face_landmarks(frame)
    
    if not landmarks:
        return False, 0.0, "Could not detect facial landmarks"
    
    # Check for eyes (basic liveness indicator)
    left_eye = landmarks.get('left_eye', [])
    right_eye = landmarks.get('right_eye', [])
    
    if not left_eye or not right_eye:
        return False, 0.0, "Eyes not detected"
    
    # Calculate EAR
    if len(left_eye) >= 6 and len(right_eye) >= 6:
        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0
        
        # Very open or very closed eyes might indicate photo
        if avg_ear > 0.35:  # Eyes too wide open
            return True, 60.0, "Face detected - additional verification recommended"
        elif avg_ear < 0.15:  # Eyes too closed
            return False, 20.0, "Eyes appear closed"
        else:
            return True, 75.0, "Face detected with normal eye aspect ratio"
    
    return True, 50.0, "Face detected - landmark analysis incomplete"
