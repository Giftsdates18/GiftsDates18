#!/usr/bin/env python3
"""
Test VIP individual-service filter (vip_services) on GiftsDates backend.
Tests the new query param that filters profiles by specific Russian service strings.
"""

import requests
import uuid
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

# Configuration
BASE_URL = "https://giftsdates-saver-1.preview.emergentagent.com/api"
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "test_database")

# Test data
test_users = {}

def log(msg):
    print(f"[TEST] {msg}")

def register_user(name_prefix):
    """Register a new user and return credentials + JWT token."""
    email = f"{name_prefix}_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"
    name = f"{name_prefix}_User"
    
    payload = {
        "email": email,
        "password": password,
        "name": name,
        "age": 25,
        "gender": "female",
        "interested_in": "men",
        "city": "Moscow",
        "country": "Russia"
    }
    
    resp = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert resp.status_code == 200, f"Registration failed: {resp.status_code} {resp.text}"
    
    data = resp.json()
    user_id = data["user"]["id"]
    token = data["token"]
    
    log(f"✓ Registered {name} (ID: {user_id}, email: {email})")
    return {"id": user_id, "email": email, "password": password, "token": token, "name": name}

def grant_vip_in_mongo(user_id):
    """Grant VIP status by setting vip_until to far future in MongoDB."""
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    far_future = "2030-01-01T00:00:00+00:00"
    result = db.users.update_one(
        {"id": user_id},
        {"$set": {"vip_until": far_future}}
    )
    
    assert result.modified_count == 1, f"Failed to grant VIP to user {user_id}"
    log(f"✓ Granted VIP to user {user_id} (vip_until: {far_future})")
    client.close()

def create_vip_profile(token, services, price_hour=500):
    """Create/update VIP profile with specified services."""
    payload = {
        "services": services,
        "published": True,
        "post_mode": "together",
        "price_hour": price_hour
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.put(f"{BASE_URL}/vip/profile", json=payload, headers=headers)
    assert resp.status_code == 200, f"VIP profile creation failed: {resp.status_code} {resp.text}"
    
    log(f"✓ Created VIP profile with services: {services}")
    return resp.json()

def search_profiles(token, vip_services=None, vip_categories=None):
    """Search profiles with optional vip_services or vip_categories filter."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {}
    
    if vip_services:
        params["vip_services"] = vip_services
    if vip_categories:
        params["vip_categories"] = vip_categories
    
    resp = requests.get(f"{BASE_URL}/profiles", params=params, headers=headers)
    return resp

def main():
    log("=" * 80)
    log("VIP SERVICES FILTER TEST - Testing individual-service filter (vip_services)")
    log("=" * 80)
    
    # ========== SETUP ==========
    log("\n[SETUP] Creating test users...")
    
    # 1. Register user A (searcher) and grant VIP
    user_a = register_user("searcher_a")
    grant_vip_in_mongo(user_a["id"])
    test_users["A"] = user_a
    
    # 2. Create target VIP user B with services ["Массаж классический", "Эскорт"]
    user_b = register_user("target_b")
    grant_vip_in_mongo(user_b["id"])
    create_vip_profile(
        user_b["token"],
        services=["Массаж классический", "Эскорт"],
        price_hour=500
    )
    test_users["B"] = user_b
    
    # 3. Create target VIP user C with services ["Бандаж", "Порка"]
    user_c = register_user("target_c")
    grant_vip_in_mongo(user_c["id"])
    create_vip_profile(
        user_c["token"],
        services=["Бандаж", "Порка"],
        price_hour=600
    )
    test_users["C"] = user_c
    
    # 4. Register NON-VIP user D for VIP gating test
    user_d = register_user("non_vip_d")
    test_users["D"] = user_d
    
    log("\n[SETUP COMPLETE] Users created:")
    log(f"  User A (VIP searcher): {user_a['id']}")
    log(f"  User B (VIP target, services: Массаж классический, Эскорт): {user_b['id']}")
    log(f"  User C (VIP target, services: Бандаж, Порка): {user_c['id']}")
    log(f"  User D (NON-VIP): {user_d['id']}")
    
    # ========== TESTS ==========
    results = []
    
    # TEST A: Single service filter - "Массаж классический" (B should appear, C should NOT)
    log("\n[TEST A] Single service filter: vip_services=Массаж классический")
    resp = search_profiles(user_a["token"], vip_services="Массаж классический")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    profiles = resp.json()
    profile_ids = [p["id"] for p in profiles]
    
    b_found = user_b["id"] in profile_ids
    c_found = user_c["id"] in profile_ids
    
    log(f"  Response: {len(profiles)} profiles returned")
    log(f"  User B found: {b_found} (expected: True)")
    log(f"  User C found: {c_found} (expected: False)")
    
    if b_found and not c_found:
        log("  ✅ TEST A PASSED")
        results.append(("A", True, "User B found, User C not found"))
    else:
        log("  ❌ TEST A FAILED")
        results.append(("A", False, f"User B found: {b_found}, User C found: {c_found}"))
    
    # TEST B: Single service filter - "Бандаж" (C should appear, B should NOT)
    log("\n[TEST B] Single service filter: vip_services=Бандаж")
    resp = search_profiles(user_a["token"], vip_services="Бандаж")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    profiles = resp.json()
    profile_ids = [p["id"] for p in profiles]
    
    b_found = user_b["id"] in profile_ids
    c_found = user_c["id"] in profile_ids
    
    log(f"  Response: {len(profiles)} profiles returned")
    log(f"  User B found: {b_found} (expected: False)")
    log(f"  User C found: {c_found} (expected: True)")
    
    if not b_found and c_found:
        log("  ✅ TEST B PASSED")
        results.append(("B", True, "User C found, User B not found"))
    else:
        log("  ❌ TEST B FAILED")
        results.append(("B", False, f"User B found: {b_found}, User C found: {c_found}"))
    
    # TEST C: Multiple services (OR) - "Эскорт||Порка" (BOTH B and C should appear)
    log("\n[TEST C] Multiple services (OR): vip_services=Эскорт||Порка")
    resp = search_profiles(user_a["token"], vip_services="Эскорт||Порка")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    profiles = resp.json()
    profile_ids = [p["id"] for p in profiles]
    
    b_found = user_b["id"] in profile_ids
    c_found = user_c["id"] in profile_ids
    
    log(f"  Response: {len(profiles)} profiles returned")
    log(f"  User B found: {b_found} (expected: True)")
    log(f"  User C found: {c_found} (expected: True)")
    
    if b_found and c_found:
        log("  ✅ TEST C PASSED")
        results.append(("C", True, "Both User B and User C found (OR semantics working)"))
    else:
        log("  ❌ TEST C FAILED")
        results.append(("C", False, f"User B found: {b_found}, User C found: {c_found}"))
    
    # TEST D: Service nobody offers - "Фистинг анальный" (neither B nor C should appear)
    log("\n[TEST D] Service nobody offers: vip_services=Фистинг анальный")
    resp = search_profiles(user_a["token"], vip_services="Фистинг анальный")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    profiles = resp.json()
    profile_ids = [p["id"] for p in profiles]
    
    b_found = user_b["id"] in profile_ids
    c_found = user_c["id"] in profile_ids
    
    log(f"  Response: {len(profiles)} profiles returned")
    log(f"  User B found: {b_found} (expected: False)")
    log(f"  User C found: {c_found} (expected: False)")
    
    if not b_found and not c_found:
        log("  ✅ TEST D PASSED")
        results.append(("D", True, "Neither User B nor User C found (correct filtering)"))
    else:
        log("  ❌ TEST D FAILED")
        results.append(("D", False, f"User B found: {b_found}, User C found: {c_found}"))
    
    # TEST E: Invalid value is ignored - "NotARealService" (should behave gracefully, 200)
    log("\n[TEST E] Invalid value: vip_services=NotARealService")
    resp = search_profiles(user_a["token"], vip_services="NotARealService")
    
    log(f"  Response status: {resp.status_code} (expected: 200)")
    
    if resp.status_code == 200:
        profiles = resp.json()
        log(f"  Response: {len(profiles)} profiles returned (invalid value ignored)")
        log("  ✅ TEST E PASSED")
        results.append(("E", True, "Invalid value ignored gracefully, no crash, 200 returned"))
    else:
        log("  ❌ TEST E FAILED")
        results.append(("E", False, f"Expected 200, got {resp.status_code}: {resp.text}"))
    
    # TEST F: VIP gating - NON-VIP user D tries to use vip_services (should get 403 VIP_REQUIRED)
    log("\n[TEST F] VIP gating: Non-VIP user D uses vip_services=Эскорт")
    resp = search_profiles(user_d["token"], vip_services="Эскорт")
    
    log(f"  Response status: {resp.status_code} (expected: 403)")
    
    if resp.status_code == 403:
        error_detail = resp.json().get("detail", "")
        log(f"  Error detail: {error_detail} (expected: VIP_REQUIRED)")
        
        if error_detail == "VIP_REQUIRED":
            log("  ✅ TEST F PASSED")
            results.append(("F", True, "Non-VIP user correctly blocked with 403 VIP_REQUIRED"))
        else:
            log("  ❌ TEST F FAILED (wrong error detail)")
            results.append(("F", False, f"Got 403 but wrong detail: {error_detail}"))
    else:
        log("  ❌ TEST F FAILED")
        results.append(("F", False, f"Expected 403, got {resp.status_code}: {resp.text}"))
    
    # TEST G: Sanity check - existing category filter still works (vip_categories=bdsm)
    log("\n[TEST G] Sanity check: vip_categories=bdsm (User C should appear)")
    resp = search_profiles(user_a["token"], vip_categories="bdsm")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    profiles = resp.json()
    profile_ids = [p["id"] for p in profiles]
    
    c_found = user_c["id"] in profile_ids
    
    log(f"  Response: {len(profiles)} profiles returned")
    log(f"  User C found: {c_found} (expected: True)")
    
    if c_found:
        log("  ✅ TEST G PASSED")
        results.append(("G", True, "Existing vip_categories filter still works"))
    else:
        log("  ❌ TEST G FAILED")
        results.append(("G", False, f"User C not found in bdsm category"))
    
    # ========== SUMMARY ==========
    log("\n" + "=" * 80)
    log("TEST SUMMARY")
    log("=" * 80)
    
    passed = sum(1 for _, status, _ in results if status)
    total = len(results)
    
    for test_id, status, comment in results:
        status_icon = "✅" if status else "❌"
        log(f"{status_icon} TEST {test_id}: {comment}")
    
    log(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        log("\n🎉 ALL TESTS PASSED! VIP services filter is working correctly.")
        return 0
    else:
        log(f"\n⚠️  {total - passed} test(s) failed. Please review the failures above.")
        return 1

if __name__ == "__main__":
    exit(main())
