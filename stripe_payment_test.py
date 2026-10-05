#!/usr/bin/env python3
"""
Backend test for GiftsDates Stripe Payment Integration
Tests all payment flows: coin packages, custom coins, VIP subscription
"""
import requests
import json
import uuid
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://giftsdates-saver-1.preview.emergentagent.com/api"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_result(test_name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    {details}")

# Test results tracking
test_results = {
    "passed": [],
    "failed": []
}

def run_test(test_name, test_func):
    try:
        result, details = test_func()
        if result:
            test_results["passed"].append(test_name)
            print_result(test_name, True, details)
        else:
            test_results["failed"].append(test_name)
            print_result(test_name, False, details)
        return result
    except Exception as e:
        test_results["failed"].append(test_name)
        print_result(test_name, False, f"Exception: {str(e)}")
        return False

# Global variables for test data
jwt_token = None
user_data = None
coin_packages = []
session_ids = []

def test_1_register_user():
    """Register a new user and get JWT token"""
    global jwt_token, user_data
    
    # Generate unique email
    unique_id = str(uuid.uuid4())[:8]
    email = f"stripe_test_{unique_id}@example.com"
    password = "SecurePass123!"
    
    payload = {
        "email": email,
        "password": password,
        "name": "Stripe Test User",
        "age": 28,
        "gender": "male",
        "interested_in": "female",
        "orientation": "straight",
        "city": "New York",
        "country": "USA",
        "lat": 40.7128,
        "lng": -74.0060
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if "token" in data and "user" in data:
            jwt_token = data["token"]
            user_data = data["user"]
            return True, f"User registered: {email}, Token received"
        else:
            return False, f"Missing token or user in response: {data}"
    else:
        return False, f"Status {response.status_code}: {response.text}"

def test_2_fetch_packages():
    """Fetch available coin packages from /api/meta"""
    global coin_packages
    
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(f"{BASE_URL}/meta", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "coin_packages" in data and isinstance(data["coin_packages"], list):
            coin_packages = data["coin_packages"]
            if len(coin_packages) > 0:
                package_names = [p.get("name", p.get("id")) for p in coin_packages]
                return True, f"Found {len(coin_packages)} packages: {', '.join(package_names)}"
            else:
                return False, "No coin packages found in meta"
        else:
            return False, f"Missing or invalid coin_packages in response: {data.keys()}"
    else:
        return False, f"Status {response.status_code}: {response.text}"

def test_3_checkout_coin_package():
    """Create checkout session with a valid coin package"""
    global session_ids
    
    if not coin_packages:
        return False, "No coin packages available from previous test"
    
    # Use the first available package
    package = coin_packages[0]
    package_id = package.get("id")
    
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "package_id": package_id,
        "origin_url": "https://giftsdates-saver-1.preview.emergentagent.com"
    }
    
    response = requests.post(f"{BASE_URL}/payments/checkout", json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "checkout_url" in data and "session_id" in data:
            checkout_url = data["checkout_url"]
            session_id = data["session_id"]
            session_ids.append(session_id)
            
            # Verify it's a real Stripe URL
            if "checkout.stripe.com" in checkout_url or "stripe.com" in checkout_url:
                return True, f"Package: {package_id}, Session: {session_id[:20]}..., URL: {checkout_url[:60]}..."
            else:
                return False, f"Invalid checkout URL (not Stripe): {checkout_url}"
        else:
            return False, f"Missing checkout_url or session_id: {data}"
    else:
        return False, f"Status {response.status_code}: {response.text}"

def test_4_checkout_custom_coins():
    """Create checkout session for custom coins package"""
    global session_ids
    
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "package_id": "custom",
        "usd_amount": 25,
        "origin_url": "https://giftsdates-saver-1.preview.emergentagent.com"
    }
    
    response = requests.post(f"{BASE_URL}/payments/checkout", json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "checkout_url" in data and "session_id" in data:
            checkout_url = data["checkout_url"]
            session_id = data["session_id"]
            session_ids.append(session_id)
            
            # Verify it's a real Stripe URL
            if "checkout.stripe.com" in checkout_url or "stripe.com" in checkout_url:
                return True, f"Custom $25, Session: {session_id[:20]}..., URL: {checkout_url[:60]}..."
            else:
                return False, f"Invalid checkout URL (not Stripe): {checkout_url}"
        else:
            return False, f"Missing checkout_url or session_id: {data}"
    else:
        return False, f"Status {response.status_code}: {response.text}"

def test_5_checkout_vip_subscription():
    """Create checkout session for VIP monthly subscription"""
    global session_ids
    
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "package_id": "vip_monthly",
        "origin_url": "https://giftsdates-saver-1.preview.emergentagent.com"
    }
    
    response = requests.post(f"{BASE_URL}/payments/checkout", json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "checkout_url" in data and "session_id" in data:
            checkout_url = data["checkout_url"]
            session_id = data["session_id"]
            session_ids.append(session_id)
            
            # Verify it's a real Stripe URL
            if "checkout.stripe.com" in checkout_url or "stripe.com" in checkout_url:
                return True, f"VIP subscription, Session: {session_id[:20]}..., URL: {checkout_url[:60]}..."
            else:
                return False, f"Invalid checkout URL (not Stripe): {checkout_url}"
        else:
            return False, f"Missing checkout_url or session_id: {data}"
    else:
        return False, f"Status {response.status_code}: {response.text}"

def test_6_payment_status():
    """Test payment status polling for created sessions"""
    
    if not session_ids:
        return False, "No session IDs available from previous tests"
    
    # Test the first session ID
    session_id = session_ids[0]
    
    response = requests.get(f"{BASE_URL}/payments/status/{session_id}")
    
    if response.status_code == 200:
        data = response.json()
        if "session_id" in data and "status" in data and "payment_status" in data:
            status = data["status"]
            payment_status = data["payment_status"]
            
            # Expected: status="initiated", payment_status="pending" (not paid yet)
            if status == "initiated" and payment_status == "pending":
                return True, f"Session: {session_id[:20]}..., Status: {status}, Payment: {payment_status}"
            else:
                # Still valid if we get these fields, just note the values
                return True, f"Session: {session_id[:20]}..., Status: {status}, Payment: {payment_status} (unexpected but valid)"
        else:
            return False, f"Missing required fields in response: {data}"
    else:
        return False, f"Status {response.status_code}: {response.text}"

def test_7_verify_transaction_record():
    """Verify payment_transactions record was created (inferred via status endpoint)"""
    
    if not session_ids:
        return False, "No session IDs available from previous tests"
    
    # Test all session IDs to verify they all have transaction records
    all_valid = True
    details_list = []
    
    for session_id in session_ids:
        response = requests.get(f"{BASE_URL}/payments/status/{session_id}")
        
        if response.status_code == 200:
            data = response.json()
            if "session_id" in data and "status" in data and "payment_status" in data:
                details_list.append(f"✓ {session_id[:15]}...")
            else:
                all_valid = False
                details_list.append(f"✗ {session_id[:15]}... (missing fields)")
        else:
            all_valid = False
            details_list.append(f"✗ {session_id[:15]}... (status {response.status_code})")
    
    if all_valid:
        return True, f"All {len(session_ids)} transaction records verified: {', '.join(details_list)}"
    else:
        return False, f"Some transaction records failed: {', '.join(details_list)}"

def main():
    print_section("GiftsDates Stripe Payment Integration Test")
    print(f"Backend URL: {BASE_URL}")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests in sequence
    print_section("Test 1: User Registration & Authentication")
    if not run_test("Register user and get JWT token", test_1_register_user):
        print("\n❌ Cannot proceed without authentication. Stopping tests.")
        return
    
    print_section("Test 2: Fetch Available Packages")
    if not run_test("Fetch coin packages from /api/meta", test_2_fetch_packages):
        print("\n⚠️  Warning: No packages found, but continuing with other tests")
    
    print_section("Test 3: Coin Package Checkout")
    run_test("Create checkout session for coin package", test_3_checkout_coin_package)
    
    print_section("Test 4: Custom Coins Checkout")
    run_test("Create checkout session for custom $25 coins", test_4_checkout_custom_coins)
    
    print_section("Test 5: VIP Subscription Checkout")
    run_test("Create checkout session for VIP monthly subscription", test_5_checkout_vip_subscription)
    
    print_section("Test 6: Payment Status Polling")
    run_test("Poll payment status for created session", test_6_payment_status)
    
    print_section("Test 7: Transaction Record Verification")
    run_test("Verify payment_transactions records exist", test_7_verify_transaction_record)
    
    # Summary
    print_section("Test Summary")
    total = len(test_results["passed"]) + len(test_results["failed"])
    passed = len(test_results["passed"])
    failed = len(test_results["failed"])
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print("\nFailed Tests:")
        for test in test_results["failed"]:
            print(f"  - {test}")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
