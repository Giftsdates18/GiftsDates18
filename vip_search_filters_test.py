#!/usr/bin/env python3
"""
Test VIP-only private search filters on GiftsDates backend.
Tests per-duration price filters, dick size/girth filters, and VIP gating.
"""
import requests
import secrets
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
import os

# Configuration
BACKEND_URL = "https://giftsdates-saver-1.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

def generate_unique_email():
    return f"testuser_{secrets.token_hex(4)}@example.com"

def register_user(email, password="TestPass123!", name="Test User", gender="male", interested_in="female"):
    """Register a new user and return the response."""
    response = requests.post(f"{BACKEND_URL}/auth/register", json={
        "email": email,
        "password": password,
        "name": name,
        "age": 25,
        "gender": gender,
        "interested_in": interested_in,
        "orientation": "straight",
        "city": "Test City",
        "country": "Test Country"
    })
    return response

def login_user(email, password="TestPass123!"):
    """Login and return JWT token."""
    response = requests.post(f"{BACKEND_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        return response.json().get("token")
    return None

def grant_vip_in_mongo(user_id):
    """Directly set VIP status in MongoDB with far-future vip_until."""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    far_future = "2030-01-01T00:00:00+00:00"
    result = db.users.update_one(
        {"id": user_id},
        {"$set": {"vip_until": far_future}}
    )
    client.close()
    return result.modified_count > 0

def create_vip_profile(token, profile_data):
    """Create/update VIP profile via PUT /api/vip/profile."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.put(f"{BACKEND_URL}/vip/profile", json=profile_data, headers=headers)
    return response

def search_profiles(token, **params):
    """Search profiles with given query parameters."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/profiles", params=params, headers=headers)
    return response

def get_vip_catalog(token):
    """Get VIP service catalog."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}/vip/catalog", headers=headers)
    return response

print("=" * 80)
print("VIP SEARCH FILTERS TEST")
print("=" * 80)

# ============================================================================
# SETUP: Register users and grant VIP status
# ============================================================================
print("\n[SETUP] Registering users...")

# User A: Searcher with VIP
email_a = generate_unique_email()
print(f"1. Registering User A (searcher): {email_a}")
resp_a = register_user(email_a, name="Searcher VIP")
assert resp_a.status_code == 200, f"Failed to register User A: {resp_a.status_code} {resp_a.text}"
user_a_data = resp_a.json()
user_a_id = user_a_data["user"]["id"]
token_a = user_a_data["token"]
print(f"   ✓ User A registered: {user_a_id}")

# Grant VIP to User A
print(f"2. Granting VIP to User A in MongoDB...")
vip_granted_a = grant_vip_in_mongo(user_a_id)
assert vip_granted_a, "Failed to grant VIP to User A"
print(f"   ✓ User A granted VIP status")

# User B: Target VIP profile
email_b = generate_unique_email()
print(f"3. Registering User B (target VIP): {email_b}")
resp_b = register_user(email_b, name="VIP Provider")
assert resp_b.status_code == 200, f"Failed to register User B: {resp_b.status_code} {resp_b.text}"
user_b_data = resp_b.json()
user_b_id = user_b_data["user"]["id"]
token_b = user_b_data["token"]
print(f"   ✓ User B registered: {user_b_id}")

# Grant VIP to User B
print(f"4. Granting VIP to User B in MongoDB...")
vip_granted_b = grant_vip_in_mongo(user_b_id)
assert vip_granted_b, "Failed to grant VIP to User B"
print(f"   ✓ User B granted VIP status")

# Get VIP catalog to pick services
print(f"5. Fetching VIP catalog...")
catalog_resp = get_vip_catalog(token_b)
assert catalog_resp.status_code == 200, f"Failed to get VIP catalog: {catalog_resp.status_code}"
catalog = catalog_resp.json()
services = catalog["services"]
# Pick a couple of services from different categories
selected_services = []
if "basic" in services and len(services["basic"]) > 0:
    selected_services.append(services["basic"][0])
if "massage" in services and len(services["massage"]) > 0:
    selected_services.append(services["massage"][0])
print(f"   ✓ Selected services: {selected_services}")

# Create VIP profile for User B with specific attributes
print(f"6. Creating VIP profile for User B...")
vip_profile_data = {
    "services": selected_services,
    "price_hour": 500,
    "price_2h": 900,
    "price_3h": 1300,
    "price_night": 2000,
    "dick_size": "18 cm",
    "dick_girth": "14 cm",
    "eye_color": "blue",
    "hair_color": "brown",
    "intimate_haircut": "shaved",
    "breast_size": "C",
    "height": 170,
    "weight": 60,
    "published": True,
    "post_mode": "together",
    "nickname": "VIP Test",
    "bio": "Test VIP profile for search filters"
}
vip_resp = create_vip_profile(token_b, vip_profile_data)
assert vip_resp.status_code == 200, f"Failed to create VIP profile: {vip_resp.status_code} {vip_resp.text}"
vip_result = vip_resp.json()
assert vip_result.get("saved") == True, "VIP profile not saved"
assert vip_result.get("can_publish") == True, "User B cannot publish VIP profile"
print(f"   ✓ VIP profile created and published for User B")

# User C: Non-VIP user for gating tests
email_c = generate_unique_email()
print(f"7. Registering User C (non-VIP): {email_c}")
resp_c = register_user(email_c, name="Non-VIP User")
assert resp_c.status_code == 200, f"Failed to register User C: {resp_c.status_code} {resp_c.text}"
user_c_data = resp_c.json()
user_c_id = user_c_data["user"]["id"]
token_c = user_c_data["token"]
print(f"   ✓ User C registered: {user_c_id} (NO VIP)")

print("\n" + "=" * 80)
print("SETUP COMPLETE")
print("=" * 80)

# ============================================================================
# TEST A: Per-duration price filters
# ============================================================================
print("\n[TEST A] Per-duration price filters")
print("-" * 80)

# A1: vip_price1h_min=400 & vip_price1h_max=600 -> B (500) should appear
print("A1. Testing vip_price1h_min=400 & vip_price1h_max=600 (User B has 500)")
resp = search_profiles(token_a, vip_price1h_min=400, vip_price1h_max=600)
assert resp.status_code == 200, f"A1 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
user_b_found = any(p.get("id") == user_b_id for p in results)
assert user_b_found, f"A1 FAILED: User B (price_hour=500) should appear in results"
print(f"   ✓ A1 PASSED: User B found in results (price_hour=500 within 400-600)")

# A2: vip_price1h_min=600 -> B (500) should NOT appear
print("A2. Testing vip_price1h_min=600 (User B has 500, should NOT appear)")
resp = search_profiles(token_a, vip_price1h_min=600)
assert resp.status_code == 200, f"A2 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
user_b_found = any(p.get("id") == user_b_id for p in results)
assert not user_b_found, f"A2 FAILED: User B (price_hour=500) should NOT appear when min=600"
print(f"   ✓ A2 PASSED: User B correctly filtered out (500 < 600)")

# A3: vip_price2h_min=800 & vip_price2h_max=1000 -> B (900) should appear
print("A3. Testing vip_price2h_min=800 & vip_price2h_max=1000 (User B has 900)")
resp = search_profiles(token_a, vip_price2h_min=800, vip_price2h_max=1000)
assert resp.status_code == 200, f"A3 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
user_b_found = any(p.get("id") == user_b_id for p in results)
assert user_b_found, f"A3 FAILED: User B (price_2h=900) should appear in results"
print(f"   ✓ A3 PASSED: User B found in results (price_2h=900 within 800-1000)")

# A4: vip_price3h_max=1000 -> B (1300) should NOT appear
print("A4. Testing vip_price3h_max=1000 (User B has 1300, should NOT appear)")
resp = search_profiles(token_a, vip_price3h_max=1000)
assert resp.status_code == 200, f"A4 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
user_b_found = any(p.get("id") == user_b_id for p in results)
assert not user_b_found, f"A4 FAILED: User B (price_3h=1300) should NOT appear when max=1000"
print(f"   ✓ A4 PASSED: User B correctly filtered out (1300 > 1000)")

print("\n✅ TEST A: All per-duration price filter tests PASSED")

# ============================================================================
# TEST B: Dick size/girth range filters
# ============================================================================
print("\n[TEST B] Dick size/girth range filters")
print("-" * 80)

# B1: vip_min_dick=15 & vip_max_dick=20 -> B (18) should appear
print("B1. Testing vip_min_dick=15 & vip_max_dick=20 (User B has '18 cm')")
resp = search_profiles(token_a, vip_min_dick=15, vip_max_dick=20)
assert resp.status_code == 200, f"B1 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
user_b_found = any(p.get("id") == user_b_id for p in results)
assert user_b_found, f"B1 FAILED: User B (dick_size='18 cm') should appear in results"
print(f"   ✓ B1 PASSED: User B found in results (dick_size=18 within 15-20)")

# B2: vip_min_dick=20 -> B (18) should NOT appear
print("B2. Testing vip_min_dick=20 (User B has '18 cm', should NOT appear)")
resp = search_profiles(token_a, vip_min_dick=20)
assert resp.status_code == 200, f"B2 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
user_b_found = any(p.get("id") == user_b_id for p in results)
assert not user_b_found, f"B2 FAILED: User B (dick_size='18 cm') should NOT appear when min=20"
print(f"   ✓ B2 PASSED: User B correctly filtered out (18 < 20)")

# B3: vip_min_girth=13 & vip_max_girth=16 -> B (14) should appear
print("B3. Testing vip_min_girth=13 & vip_max_girth=16 (User B has '14 cm')")
resp = search_profiles(token_a, vip_min_girth=13, vip_max_girth=16)
assert resp.status_code == 200, f"B3 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
user_b_found = any(p.get("id") == user_b_id for p in results)
assert user_b_found, f"B3 FAILED: User B (dick_girth='14 cm') should appear in results"
print(f"   ✓ B3 PASSED: User B found in results (dick_girth=14 within 13-16)")

print("\n✅ TEST B: All dick size/girth filter tests PASSED")

# ============================================================================
# TEST C: VIP gating (403 VIP_REQUIRED for non-VIP users)
# ============================================================================
print("\n[TEST C] VIP gating (403 VIP_REQUIRED for non-VIP users)")
print("-" * 80)

# C1: Non-VIP user C tries vip_min_dick=15 -> 403 VIP_REQUIRED
print("C1. Testing vip_min_dick=15 as non-VIP User C (should get 403)")
resp = search_profiles(token_c, vip_min_dick=15)
assert resp.status_code == 403, f"C1 FAILED: Expected 403, got {resp.status_code}: {resp.text}"
error_detail = resp.json().get("detail", "")
assert error_detail == "VIP_REQUIRED", f"C1 FAILED: Expected 'VIP_REQUIRED', got '{error_detail}'"
print(f"   ✓ C1 PASSED: Non-VIP user correctly blocked with 403 VIP_REQUIRED")

# C2: Non-VIP user C tries vip_price1h_min=400 -> 403 VIP_REQUIRED
print("C2. Testing vip_price1h_min=400 as non-VIP User C (should get 403)")
resp = search_profiles(token_c, vip_price1h_min=400)
assert resp.status_code == 403, f"C2 FAILED: Expected 403, got {resp.status_code}: {resp.text}"
error_detail = resp.json().get("detail", "")
assert error_detail == "VIP_REQUIRED", f"C2 FAILED: Expected 'VIP_REQUIRED', got '{error_detail}'"
print(f"   ✓ C2 PASSED: Non-VIP user correctly blocked with 403 VIP_REQUIRED")

# C3: Non-VIP user C tries vip_min_girth=13 -> 403 VIP_REQUIRED
print("C3. Testing vip_min_girth=13 as non-VIP User C (should get 403)")
resp = search_profiles(token_c, vip_min_girth=13)
assert resp.status_code == 403, f"C3 FAILED: Expected 403, got {resp.status_code}: {resp.text}"
error_detail = resp.json().get("detail", "")
assert error_detail == "VIP_REQUIRED", f"C3 FAILED: Expected 'VIP_REQUIRED', got '{error_detail}'"
print(f"   ✓ C3 PASSED: Non-VIP user correctly blocked with 403 VIP_REQUIRED")

# C4: Non-VIP user C tries vip_price2h_min=800 -> 403 VIP_REQUIRED
print("C4. Testing vip_price2h_min=800 as non-VIP User C (should get 403)")
resp = search_profiles(token_c, vip_price2h_min=800)
assert resp.status_code == 403, f"C4 FAILED: Expected 403, got {resp.status_code}: {resp.text}"
error_detail = resp.json().get("detail", "")
assert error_detail == "VIP_REQUIRED", f"C4 FAILED: Expected 'VIP_REQUIRED', got '{error_detail}'"
print(f"   ✓ C4 PASSED: Non-VIP user correctly blocked with 403 VIP_REQUIRED")

print("\n✅ TEST C: All VIP gating tests PASSED")

# ============================================================================
# TEST D: Sanity checks (existing filters still work, plain GET works)
# ============================================================================
print("\n[TEST D] Sanity checks")
print("-" * 80)

# D1: Existing filter vip_min_height=160 & vip_max_height=180 as VIP User A -> B appears
print("D1. Testing existing filter vip_min_height=160 & vip_max_height=180 (User B has 170)")
resp = search_profiles(token_a, vip_min_height=160, vip_max_height=180)
assert resp.status_code == 200, f"D1 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
user_b_found = any(p.get("id") == user_b_id for p in results)
assert user_b_found, f"D1 FAILED: User B (height=170) should appear in results"
print(f"   ✓ D1 PASSED: Existing height filter works correctly")

# D2: Plain GET /api/profiles as VIP User A -> returns results without error
print("D2. Testing plain GET /api/profiles (no filters)")
resp = search_profiles(token_a)
assert resp.status_code == 200, f"D2 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
assert isinstance(results, list), f"D2 FAILED: Expected list of results, got {type(results)}"
print(f"   ✓ D2 PASSED: Plain GET returns {len(results)} profiles without error")

# D3: Plain GET /api/profiles as non-VIP User C -> returns results without error
print("D3. Testing plain GET /api/profiles as non-VIP user (no filters)")
resp = search_profiles(token_c)
assert resp.status_code == 200, f"D3 FAILED: Expected 200, got {resp.status_code}: {resp.text}"
results = resp.json()
assert isinstance(results, list), f"D3 FAILED: Expected list of results, got {type(results)}"
print(f"   ✓ D3 PASSED: Non-VIP user can access plain search without VIP filters")

print("\n✅ TEST D: All sanity checks PASSED")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("ALL TESTS PASSED ✅")
print("=" * 80)
print("\nSummary:")
print("  ✓ Per-duration price filters (vip_price1h, vip_price2h, vip_price3h) work correctly")
print("  ✓ Dick size/girth range filters work correctly (numeric extraction from free text)")
print("  ✓ VIP gating works correctly (403 VIP_REQUIRED for non-VIP users)")
print("  ✓ Existing filters and plain GET still work correctly")
print("\nTest users created:")
print(f"  - User A (VIP searcher): {email_a}")
print(f"  - User B (VIP provider): {email_b}")
print(f"  - User C (non-VIP): {email_c}")
