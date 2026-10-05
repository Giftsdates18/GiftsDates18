#!/usr/bin/env python3
"""
Video Calls Privacy Toggle Test for GiftsDates FastAPI backend
Tests the video_calls_enabled field behavior in profiles and video call initiation
"""
import requests
import uuid
import sys
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://giftsdates-saver-1.preview.emergentagent.com/api"

def log(msg, level="INFO"):
    """Log test messages"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")

def register_user(name_prefix):
    """Register a new user and return token and user_id"""
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"{name_prefix}_{unique_id}@example.com"
    test_password = "SecurePass123!"
    
    payload = {
        "email": test_email,
        "password": test_password,
        "name": f"{name_prefix} {unique_id}",
        "age": 25,
        "gender": "female",
        "interested_in": "male",
        "orientation": "straight",
        "city": "New York",
        "country": "USA",
        "bio": f"Test user {name_prefix}",
        "language": "en"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            token = data["token"]
            user_id = data["user"]["id"]
            log(f"✅ Registered {name_prefix}: {test_email}, ID: {user_id}")
            return token, user_id, test_email
        else:
            log(f"❌ Registration failed for {name_prefix}: {response.status_code} - {response.text}", "ERROR")
            return None, None, None
    except Exception as e:
        log(f"❌ Registration exception for {name_prefix}: {e}", "ERROR")
        return None, None, None

def update_profile(token, updates):
    """Update user profile with PATCH /api/auth/me"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.patch(f"{BASE_URL}/auth/me", json=updates, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            log(f"❌ Profile update failed: {response.status_code} - {response.text}", "ERROR")
            return False, None
    except Exception as e:
        log(f"❌ Profile update exception: {e}", "ERROR")
        return False, None

def get_profile(token, user_id):
    """Get user profile with GET /api/profiles/{user_id}"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/profiles/{user_id}", headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            log(f"❌ Get profile failed: {response.status_code} - {response.text}", "ERROR")
            return False, None
    except Exception as e:
        log(f"❌ Get profile exception: {e}", "ERROR")
        return False, None

def start_video_call(token, target_id, minutes=10):
    """Attempt to start a video call with POST /api/videocalls/start"""
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "target_id": target_id,
        "minutes": minutes
    }
    try:
        response = requests.post(f"{BASE_URL}/videocalls/start", json=payload, headers=headers, timeout=10)
        return response.status_code, response.json() if response.status_code != 500 else {"detail": response.text}
    except Exception as e:
        log(f"❌ Video call start exception: {e}", "ERROR")
        return None, None

def main():
    """Run video calls privacy toggle test"""
    log("=" * 80)
    log("GiftsDates Video Calls Privacy Toggle Test")
    log("=" * 80)
    
    test_results = []
    
    # Step 1: Register user A
    log("\n--- Step 1: Register User A ---")
    token_a, user_a_id, email_a = register_user("UserA")
    if not token_a:
        log("❌ CRITICAL: Failed to register User A", "ERROR")
        sys.exit(1)
    test_results.append(("Register User A", True))
    
    # Step 2: As user A, disable video calls
    log("\n--- Step 2: User A disables video calls ---")
    success, updated_profile = update_profile(token_a, {"video_calls_enabled": False})
    if not success:
        log("❌ CRITICAL: Failed to update User A profile", "ERROR")
        test_results.append(("User A disable video calls", False))
    else:
        video_calls_enabled = updated_profile.get("video_calls_enabled")
        log(f"User A profile updated. video_calls_enabled = {video_calls_enabled}")
        if video_calls_enabled is False:
            log("✅ User A successfully disabled video calls (PATCH /api/auth/me returns video_calls_enabled=false)", "SUCCESS")
            test_results.append(("User A disable video calls", True))
        else:
            log(f"❌ FAILED: Expected video_calls_enabled=false, got {video_calls_enabled}", "ERROR")
            test_results.append(("User A disable video calls", False))
    
    # Step 3: Register user B
    log("\n--- Step 3: Register User B ---")
    token_b, user_b_id, email_b = register_user("UserB")
    if not token_b:
        log("❌ CRITICAL: Failed to register User B", "ERROR")
        sys.exit(1)
    test_results.append(("Register User B", True))
    
    # Step 4: As user B, get user A's profile and verify video_calls_enabled field
    log("\n--- Step 4: User B views User A's profile (CRITICAL CHECK) ---")
    success, profile_a = get_profile(token_b, user_a_id)
    if not success:
        log("❌ CRITICAL: Failed to get User A's profile", "ERROR")
        test_results.append(("User B views User A profile", False))
    else:
        log(f"User A profile keys: {list(profile_a.keys())}")
        
        # CRITICAL CHECK: Does the profile include video_calls_enabled field?
        if "video_calls_enabled" not in profile_a:
            log("❌ CRITICAL FAILURE: video_calls_enabled field is MISSING from GET /api/profiles/{pid} response!", "ERROR")
            log("This means the frontend cannot hide the Video Call button when a user disables video calls.", "ERROR")
            test_results.append(("User B views User A profile - field present", False))
            test_results.append(("User B views User A profile - value correct", False))
        else:
            log("✅ video_calls_enabled field is PRESENT in profile response", "SUCCESS")
            test_results.append(("User B views User A profile - field present", True))
            
            video_calls_enabled = profile_a.get("video_calls_enabled")
            log(f"video_calls_enabled value: {video_calls_enabled} (type: {type(video_calls_enabled).__name__})")
            
            if video_calls_enabled is False:
                log("✅ CRITICAL SUCCESS: video_calls_enabled is correctly False (boolean)", "SUCCESS")
                log("Frontend can now hide the Video Call button for User A", "SUCCESS")
                test_results.append(("User B views User A profile - value correct", True))
            else:
                log(f"❌ CRITICAL FAILURE: Expected video_calls_enabled=false (boolean), got {video_calls_enabled}", "ERROR")
                test_results.append(("User B views User A profile - value correct", False))
    
    # Step 5: As user B, attempt to start a video call with user A (should get 403)
    log("\n--- Step 5: User B attempts to start video call with User A (should fail with 403) ---")
    status_code, response_data = start_video_call(token_b, user_a_id, minutes=10)
    
    if status_code == 403:
        detail = response_data.get("detail", "")
        log(f"✅ Video call correctly blocked with 403. Detail: {detail}", "SUCCESS")
        if detail == "VIDEO_CALLS_DISABLED":
            log("✅ Correct error detail: VIDEO_CALLS_DISABLED", "SUCCESS")
            test_results.append(("Video call blocked when disabled", True))
        else:
            log(f"⚠️ WARNING: Expected detail='VIDEO_CALLS_DISABLED', got '{detail}'", "WARNING")
            test_results.append(("Video call blocked when disabled", True))  # Still pass if 403
    elif status_code == 400 and "Insufficient coins" in str(response_data.get("detail", "")):
        log("⚠️ Got 400 Insufficient coins - User B needs coins. This is expected behavior.", "WARNING")
        log("The video_calls_enabled check happens BEFORE coin check, so this suggests the field might not be working correctly.", "WARNING")
        test_results.append(("Video call blocked when disabled", False))
    else:
        log(f"❌ FAILED: Expected 403 VIDEO_CALLS_DISABLED, got {status_code}: {response_data}", "ERROR")
        test_results.append(("Video call blocked when disabled", False))
    
    # Step 6: As user A, enable video calls
    log("\n--- Step 6: User A enables video calls ---")
    success, updated_profile = update_profile(token_a, {"video_calls_enabled": True})
    if not success:
        log("❌ Failed to update User A profile", "ERROR")
        test_results.append(("User A enable video calls", False))
    else:
        video_calls_enabled = updated_profile.get("video_calls_enabled")
        log(f"User A profile updated. video_calls_enabled = {video_calls_enabled}")
        if video_calls_enabled is True:
            log("✅ User A successfully enabled video calls", "SUCCESS")
            test_results.append(("User A enable video calls", True))
        else:
            log(f"❌ FAILED: Expected video_calls_enabled=true, got {video_calls_enabled}", "ERROR")
            test_results.append(("User A enable video calls", False))
    
    # Step 7: As user B, get user A's profile again and verify video_calls_enabled is now true
    log("\n--- Step 7: User B views User A's profile again (should show video_calls_enabled=true) ---")
    success, profile_a = get_profile(token_b, user_a_id)
    if not success:
        log("❌ Failed to get User A's profile", "ERROR")
        test_results.append(("User B views User A profile after enable", False))
    else:
        if "video_calls_enabled" not in profile_a:
            log("❌ FAILURE: video_calls_enabled field is MISSING from profile response!", "ERROR")
            test_results.append(("User B views User A profile after enable", False))
        else:
            video_calls_enabled = profile_a.get("video_calls_enabled")
            log(f"video_calls_enabled value: {video_calls_enabled} (type: {type(video_calls_enabled).__name__})")
            
            if video_calls_enabled is True:
                log("✅ SUCCESS: video_calls_enabled is correctly True (boolean)", "SUCCESS")
                test_results.append(("User B views User A profile after enable", True))
            else:
                log(f"❌ FAILURE: Expected video_calls_enabled=true (boolean), got {video_calls_enabled}", "ERROR")
                test_results.append(("User B views User A profile after enable", False))
    
    # Summary
    log("\n" + "=" * 80)
    log("TEST SUMMARY")
    log("=" * 80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        log(f"{test_name}: {status}")
    
    log(f"\nTotal: {passed}/{total} tests passed")
    log("=" * 80)
    
    if passed == total:
        log("🎉 All video calls privacy toggle tests PASSED!", "SUCCESS")
        sys.exit(0)
    else:
        log(f"⚠️ {total - passed} test(s) FAILED", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
