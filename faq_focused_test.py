#!/usr/bin/env python3
"""
Focused FAQ System Testing for Kurumsal Prosedür Asistanı
Tests the new FAQ system endpoints specifically.
"""

import requests
import json
import sys
import time

# Backend URL from environment
BACKEND_URL = "https://1070132c-1836-44b9-839f-410d8851049c.preview.emergentagent.com/api"

def test_faq_system():
    """Test all FAQ system endpoints"""
    print("🆕 FAQ SYSTEM COMPREHENSIVE TESTING")
    print("=" * 60)
    
    results = []
    
    # Test 1: GET /api/faq - List FAQ items
    print("1. Testing GET /api/faq - List FAQ items...")
    try:
        response = requests.get(f"{BACKEND_URL}/faq", timeout=10)
        if response.status_code == 200:
            data = response.json()
            faq_items = data.get("faq_items", [])
            statistics = data.get("statistics", {})
            
            required_stats = ["total_faqs", "active_faqs", "available_categories"]
            missing_stats = [stat for stat in required_stats if stat not in statistics]
            
            if not missing_stats:
                results.append("✅ GET /api/faq - Working perfectly")
                print(f"   ✅ FAQ items: {len(faq_items)}")
                print(f"   ✅ Statistics: {statistics}")
            else:
                results.append(f"❌ GET /api/faq - Missing stats: {missing_stats}")
        else:
            results.append(f"❌ GET /api/faq - HTTP {response.status_code}")
    except Exception as e:
        results.append(f"❌ GET /api/faq - Error: {str(e)}")
    
    # Test 2: GET /api/faq/analytics - FAQ analytics
    print("2. Testing GET /api/faq/analytics - FAQ analytics...")
    try:
        response = requests.get(f"{BACKEND_URL}/faq/analytics", timeout=10)
        if response.status_code == 200:
            data = response.json()
            required_fields = ["total_questions_analyzed", "total_chat_sessions", "top_questions", "category_distribution", "faq_recommendations"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                results.append("✅ GET /api/faq/analytics - Working perfectly")
                print(f"   ✅ Questions analyzed: {data.get('total_questions_analyzed', 0)}")
                print(f"   ✅ Chat sessions: {data.get('total_chat_sessions', 0)}")
                print(f"   ✅ Top questions: {len(data.get('top_questions', []))}")
            else:
                results.append(f"❌ GET /api/faq/analytics - Missing fields: {missing_fields}")
        else:
            results.append(f"❌ GET /api/faq/analytics - HTTP {response.status_code}")
    except Exception as e:
        results.append(f"❌ GET /api/faq/analytics - Error: {str(e)}")
    
    # Test 3: POST /api/faq/generate - Generate FAQ
    print("3. Testing POST /api/faq/generate - Generate FAQ...")
    try:
        response = requests.post(f"{BACKEND_URL}/faq/generate", 
                               json={"min_frequency": 1, "similarity_threshold": 0.6, "max_faq_items": 10},
                               timeout=15)
        if response.status_code == 200:
            data = response.json()
            required_fields = ["message", "generated_count", "new_items", "updated_items"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                results.append("✅ POST /api/faq/generate - Working perfectly")
                print(f"   ✅ Generated: {data.get('generated_count', 0)}")
                print(f"   ✅ New: {data.get('new_items', 0)}, Updated: {data.get('updated_items', 0)}")
            else:
                results.append(f"❌ POST /api/faq/generate - Missing fields: {missing_fields}")
        else:
            results.append(f"❌ POST /api/faq/generate - HTTP {response.status_code}")
    except Exception as e:
        results.append(f"❌ POST /api/faq/generate - Error: {str(e)}")
    
    # Get FAQ items for further testing
    faq_items = []
    try:
        response = requests.get(f"{BACKEND_URL}/faq", timeout=10)
        if response.status_code == 200:
            data = response.json()
            faq_items = data.get("faq_items", [])
    except:
        pass
    
    # Test 4: POST /api/faq/{id}/ask - Ask FAQ question
    print("4. Testing POST /api/faq/{id}/ask - Ask FAQ question...")
    if faq_items:
        try:
            faq_id = faq_items[0].get("id")
            response = requests.post(f"{BACKEND_URL}/faq/{faq_id}/ask", timeout=15)
            if response.status_code == 200:
                data = response.json()
                required_fields = ["message", "faq_id", "new_session_id", "result"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    results.append("✅ POST /api/faq/{id}/ask - Working perfectly")
                    print(f"   ✅ New session: {data.get('new_session_id', 'unknown')[:8]}...")
                else:
                    results.append(f"❌ POST /api/faq/{{id}}/ask - Missing fields: {missing_fields}")
            else:
                results.append(f"❌ POST /api/faq/{{id}}/ask - HTTP {response.status_code}")
        except Exception as e:
            results.append(f"❌ POST /api/faq/{{id}}/ask - Error: {str(e)}")
    else:
        results.append("⚠️ POST /api/faq/{id}/ask - No FAQ items to test")
    
    # Test 5: PUT /api/faq/{id} - Update FAQ item
    print("5. Testing PUT /api/faq/{id} - Update FAQ item...")
    if faq_items:
        try:
            faq_id = faq_items[0].get("id")
            response = requests.put(f"{BACKEND_URL}/faq/{faq_id}", 
                                  json={"category": "Test Category", "is_active": True},
                                  timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    results.append("✅ PUT /api/faq/{id} - Working perfectly")
                    print(f"   ✅ Update successful")
                else:
                    results.append("❌ PUT /api/faq/{id} - Missing message field")
            else:
                results.append(f"❌ PUT /api/faq/{{id}} - HTTP {response.status_code}")
        except Exception as e:
            results.append(f"❌ PUT /api/faq/{{id}} - Error: {str(e)}")
    else:
        results.append("⚠️ PUT /api/faq/{id} - No FAQ items to test")
    
    # Test 6: DELETE /api/faq/{id} - Delete FAQ item (test with non-existent ID)
    print("6. Testing DELETE /api/faq/{id} - Delete FAQ item...")
    try:
        fake_id = "non-existent-faq-id-12345"
        response = requests.delete(f"{BACKEND_URL}/faq/{fake_id}", timeout=10)
        if response.status_code == 404:
            results.append("✅ DELETE /api/faq/{id} - 404 handling working")
            print(f"   ✅ Correctly returns 404 for non-existent ID")
        else:
            results.append(f"❌ DELETE /api/faq/{{id}} - Expected 404, got {response.status_code}")
    except Exception as e:
        results.append(f"❌ DELETE /api/faq/{{id}} - Error: {str(e)}")
    
    # Test 7: Integration test - Category filtering
    print("7. Testing category filtering...")
    try:
        response = requests.get(f"{BACKEND_URL}/faq?category=İnsan Kaynakları", timeout=10)
        if response.status_code == 200:
            data = response.json()
            filtered_items = data.get("faq_items", [])
            results.append("✅ FAQ category filtering - Working perfectly")
            print(f"   ✅ Filtered items: {len(filtered_items)}")
        else:
            results.append(f"❌ FAQ category filtering - HTTP {response.status_code}")
    except Exception as e:
        results.append(f"❌ FAQ category filtering - Error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("FAQ SYSTEM TEST SUMMARY")
    print("=" * 60)
    
    passed = len([r for r in results if r.startswith("✅")])
    warnings = len([r for r in results if r.startswith("⚠️")])
    failed = len([r for r in results if r.startswith("❌")])
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Warnings: {warnings}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/(total-warnings)*100):.1f}%" if (total-warnings) > 0 else "No tests run")
    print()
    
    for result in results:
        print(result)
    
    return {
        "total": total,
        "passed": passed,
        "warnings": warnings,
        "failed": failed,
        "results": results
    }

if __name__ == "__main__":
    summary = test_faq_system()
    
    # Exit with error code if tests failed
    if summary["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)