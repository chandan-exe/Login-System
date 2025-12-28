"""
Face Login System - Main Entry Point
A secure face recognition authentication system
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import register_user, login, verify_specific_user, remove_user, get_all_users
from database import get_user_count


def print_banner():
    """Print application banner."""
    print("\n" + "="*60)
    print("""
    ███████╗ █████╗  ██████╗███████╗    ██╗      ██████╗  ██████╗ ██╗███╗   ██╗
    ██╔════╝██╔══██╗██╔════╝██╔════╝    ██║     ██╔═══██╗██╔════╝ ██║████╗  ██║
    █████╗  ███████║██║     █████╗      ██║     ██║   ██║██║  ███╗██║██╔██╗ ██║
    ██╔══╝  ██╔══██║██║     ██╔══╝      ██║     ██║   ██║██║   ██║██║██║╚██╗██║
    ██║     ██║  ██║╚██████╗███████╗    ███████╗╚██████╔╝╚██████╔╝██║██║ ╚████║
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝    ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝╚═╝  ╚═══╝
    """)
    print("                  Secure Face Recognition System")
    print("="*60)


def print_menu():
    """Print main menu."""
    user_count = get_user_count()
    print(f"\n📊 Registered Users: {user_count}")
    print("\n┌─────────────────────────────────────┐")
    print("│           MAIN MENU                 │")
    print("├─────────────────────────────────────┤")
    print("│  1. 📝 Register New User            │")
    print("│  2. 🔐 Login with Face              │")
    print("│  3. ✓  Verify Specific User         │")
    print("│  4. 👥 List Registered Users        │")
    print("│  5. 🗑  Delete User                  │")
    print("│  6. ⚙  Settings Info                │")
    print("│  7. 🚪 Exit                         │")
    print("└─────────────────────────────────────┘")


def show_settings():
    """Display current settings."""
    from config import (
        FACE_RECOGNITION_MODEL, FACE_ENCODING_JITTERS,
        FACE_MATCH_TOLERANCE, LIVENESS_ENABLED,
        REGISTRATION_FRAMES, CAMERA_INDEX
    )
    
    print("\n⚙ Current Settings:")
    print(f"  • Recognition Model: {FACE_RECOGNITION_MODEL}")
    print(f"  • Encoding Jitters: {FACE_ENCODING_JITTERS}")
    print(f"  • Match Tolerance: {FACE_MATCH_TOLERANCE}")
    print(f"  • Liveness Detection: {'Enabled' if LIVENESS_ENABLED else 'Disabled'}")
    print(f"  • Registration Frames: {REGISTRATION_FRAMES}")
    print(f"  • Camera Index: {CAMERA_INDEX}")
    print("\n  (Edit config.py to change settings)")


def main():
    """Main application loop."""
    print_banner()
    
    while True:
        print_menu()
        
        try:
            choice = input("\n👉 Enter your choice (1-7): ").strip()
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        
        if choice == "1":
            # Register new user
            print("\n" + "="*40)
            print("       REGISTER NEW USER")
            print("="*40)
            username = input("Enter username: ").strip()
            
            if not username:
                print("⚠ Username cannot be empty.")
                continue
            
            if len(username) < 2:
                print("⚠ Username must be at least 2 characters.")
                continue
            
            success, message = register_user(username)
            print(f"\n{message}")
            
        elif choice == "2":
            # Login with face
            print("\n" + "="*40)
            print("       FACE LOGIN")
            print("="*40)
            
            success, username, confidence = login()
            
            if success:
                print(f"\n🎉 Login successful!")
                print(f"   User: {username}")
                print(f"   Confidence: {confidence:.1f}%")
            else:
                print("\n❌ Login failed.")
                
        elif choice == "3":
            # Verify specific user
            print("\n" + "="*40)
            print("       VERIFY USER")
            print("="*40)
            
            users = get_all_users()
            if not users:
                print("⚠ No users registered.")
                continue
            
            print("Registered users:", ", ".join(users))
            username = input("Enter username to verify: ").strip()
            
            if not username:
                continue
            
            verified, confidence = verify_specific_user(username)
            
            if verified:
                print(f"\n✓ Identity verified: {username} ({confidence:.1f}%)")
            else:
                print("\n✗ Verification failed.")
                
        elif choice == "4":
            # List users
            print("\n" + "="*40)
            print("       REGISTERED USERS")
            print("="*40)
            
            users = get_all_users()
            
            if not users:
                print("No users registered yet.")
            else:
                for i, user in enumerate(users, 1):
                    print(f"  {i}. {user}")
                print(f"\nTotal: {len(users)} user(s)")
                
        elif choice == "5":
            # Delete user
            print("\n" + "="*40)
            print("       DELETE USER")
            print("="*40)
            
            users = get_all_users()
            if not users:
                print("⚠ No users to delete.")
                continue
            
            print("Registered users:", ", ".join(users))
            username = input("Enter username to delete: ").strip()
            
            if not username:
                continue
            
            confirm = input(f"Are you sure you want to delete '{username}'? (y/n): ").strip().lower()
            
            if confirm == 'y':
                success, message = remove_user(username)
                print(message)
            else:
                print("Deletion cancelled.")
                
        elif choice == "6":
            # Show settings
            show_settings()
            
        elif choice == "7":
            # Exit
            print("\n👋 Goodbye!")
            break
            
        else:
            print("⚠ Invalid choice. Please enter 1-7.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        import traceback
        traceback.print_exc()
