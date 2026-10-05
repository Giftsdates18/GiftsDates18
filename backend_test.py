#!/usr/bin/env python3
"""
Backend smoke test for GiftsDates FastAPI backend
Tests: health check, auth signup, auth login, authenticated endpoints
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

def test_health_check():
    """Test 1: GET /api/ health check"""
    log("Testing health check endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        log(f"Health check status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log(f"Health check response: {data}")
            if data.get("ok") and data.get("service") == "GiftsDates":
                log("✅ Health check PASSED", "SUCCESS")
                return True
            else:
                log(f"❌ Health check returned unexpected data: {data}", "ERROR")
                return False
        else:
            log(f"❌ Health check failed with status {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            return False
    except Exception as e:
        log(f"❌ Health check exception: {e}", "ERROR")
        return False

def test_auth_signup():
    """Test 2: POST /api/auth/register - Create new user"""
    log("Testing auth signup...")
    
    # Generate unique email for this test
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"testuser_{unique_id}@example.com"
    test_password = "SecurePass123!"
    
    payload = {
        "email": test_email,
        "password": test_password,
        "name": f"Test User {unique_id}",
        "age": 25,
        "gender": "female",
        "interested_in": "male",
        "orientation": "straight",
        "city": "New York",
        "country": "USA",
        "bio": "Test user for smoke testing",
        "language": "en"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=payload, timeout=15)
        log(f"Signup status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log(f"Signup response keys: {list(data.keys())}")
            
            if "token" in data and "user" in data:
                token = data["token"]
                user = data["user"]
                log(f"✅ Signup PASSED - User created: {user.get('email')}")
                log(f"Token received: {token[:20]}...")
                return True, test_email, test_password, token
            else:
                log(f"❌ Signup response missing token or user: {data}", "ERROR")
                return False, None, None, None
        else:
            log(f"❌ Signup failed with status {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            return False, None, None, None
    except Exception as e:
        log(f"❌ Signup exception: {e}", "ERROR")
        return False, None, None, None

def test_auth_login(email, password):
    """Test 3: POST /api/auth/login - Login with created credentials"""
    log(f"Testing auth login with email: {email}...")
    
    payload = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=payload, timeout=10)
        log(f"Login status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log(f"Login response keys: {list(data.keys())}")
            
            if "token" in data and "user" in data:
                token = data["token"]
                user = data["user"]
                log(f"✅ Login PASSED - Token received for: {user.get('email')}")
                log(f"Token: {token[:20]}...")
                return True, token
            else:
                log(f"❌ Login response missing token or user: {data}", "ERROR")
                return False, None
        else:
            log(f"❌ Login failed with status {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            return False, None
    except Exception as e:
        log(f"❌ Login exception: {e}", "ERROR")
        return False, None

def test_authenticated_endpoints(token):
    """Test 4: Call authenticated endpoints with Bearer token"""
    log("Testing authenticated endpoints...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Test 4a: GET /api/auth/me - Get current user profile
    log("Testing GET /api/auth/me...")
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        log(f"GET /api/auth/me status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log(f"User profile keys: {list(data.keys())}")
            log(f"User email: {data.get('email')}, Name: {data.get('name')}")
            log("✅ GET /api/auth/me PASSED", "SUCCESS")
            me_passed = True
        else:
            log(f"❌ GET /api/auth/me failed with status {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            me_passed = False
    except Exception as e:
        log(f"❌ GET /api/auth/me exception: {e}", "ERROR")
        me_passed = False
    
    # Test 4b: GET /api/meta - Get app metadata (doesn't require auth but testing with token)
    log("Testing GET /api/meta...")
    try:
        response = requests.get(f"{BASE_URL}/meta", headers=headers, timeout=10)
        log(f"GET /api/meta status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            log(f"Meta response keys: {list(data.keys())}")
            log(f"Gifts count: {len(data.get('gifts', []))}, Coin packages: {len(data.get('coin_packages', []))}")
            log("✅ GET /api/meta PASSED", "SUCCESS")
            meta_passed = True
        else:
            log(f"❌ GET /api/meta failed with status {response.status_code}", "ERROR")
            log(f"Response: {response.text}", "ERROR")
            meta_passed = False
    except Exception as e:
        log(f"❌ GET /api/meta exception: {e}", "ERROR")
        meta_passed = False
    
    return me_passed and meta_passed

def main():
    """Run all backend smoke tests"""
    log("=" * 60)
    log("GiftsDates Backend Smoke Test Suite")
    log("=" * 60)
    
    results = {
        "health_check": False,
        "signup": False,
        "login": False,
        "authenticated": False
    }
    
    # Test 1: Health check
    log("\n--- Test 1: Health Check ---")
    results["health_check"] = test_health_check()
    
    # Test 2: Signup
    log("\n--- Test 2: Auth Signup ---")
    signup_success, test_email, test_password, signup_token = test_auth_signup()
    results["signup"] = signup_success
    
    if not signup_success:
        log("⚠️ Signup failed, skipping login and authenticated tests", "WARNING")
    else:
        # Test 3: Login
        log("\n--- Test 3: Auth Login ---")
        login_success, login_token = test_auth_login(test_email, test_password)
        results["login"] = login_success
        
        # Test 4: Authenticated endpoints
        if login_success:
            log("\n--- Test 4: Authenticated Endpoints ---")
            results["authenticated"] = test_authenticated_endpoints(login_token)
        else:
            log("⚠️ Login failed, skipping authenticated endpoint tests", "WARNING")
    
    # Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        log(f"{test_name.upper()}: {status}")
    
    log(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    log("=" * 60)
    
    # Exit with appropriate code
    if passed_tests == total_tests:
        log("🎉 All tests PASSED!", "SUCCESS")
        sys.exit(0)
    else:
        log(f"⚠️ {total_tests - passed_tests} test(s) FAILED", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
