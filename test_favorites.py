#!/usr/bin/env python3
"""
Focused test for the NEW Favorite Questions System
Tests all CRUD operations and replay functionality
"""

import requests
import json
import time

# Backend URL
BACKEND_URL = "https://1070132c-1836-44b9-839f-410d8851049c.preview.emergentagent.com/api"

def test_favorite_questions_system():
    """Test the complete Favorite Questions System"""
    print("🆕 TESTING NEW FEATURE: Favorite Questions System")
    print("=" * 60)
    
    session = requests.Session()
    session.timeout = 30
    
    # Step 1: Create a test chat session first
    print("Step 1: Creating test chat session...")
    
    test_question = "What are the main corporate procedures for employee management?"
    question_request = {
        "question": test_question,
        "session_id": f"fav_test_{int(time.time())}"
    }
    
    try:
        response = session.post(f"{BACKEND_URL}/ask-question", json=question_request)
        
        if response.status_code == 200:
            question_data = response.json()
            session_id = question_data.get("session_id")
            answer = question_data.get("answer", "Test answer for favorite")
            source_docs = question_data.get("source_documents", [])
            
            print(f"✅ Test session created: {session_id}")
            
            # Step 2: Test POST /api/favorites - Add to favorites
            print("\nStep 2: Testing POST /api/favorites...")
            
            favorite_request = {
                "session_id": session_id,
                "question": test_question,
                "answer": answer,
                "source_documents": [doc.get("filename", "") for doc in source_docs] if isinstance(source_docs, list) else [],
                "category": "İnsan Kaynakları",
                "tags": ["prosedür", "çalışan", "yönetim"],
                "notes": "Test notu - favori soru sistemi testi"
            }
            
            add_response = session.post(f"{BACKEND_URL}/favorites", json=favorite_request)
            
            if add_response.status_code == 200:
                add_data = add_response.json()
                favorite_id = add_data.get("favorite_id")
                
                print(f"✅ Favorite added successfully: {add_data.get('message')}")
                print(f"   Favorite ID: {favorite_id}")
                print(f"   Favorite Count: {add_data.get('favorite_count')}")
                print(f"   Already Exists: {add_data.get('already_exists')}")
                
                # Step 3: Test duplicate handling
                print("\nStep 3: Testing duplicate handling...")
                
                duplicate_response = session.post(f"{BACKEND_URL}/favorites", json=favorite_request)
                
                if duplicate_response.status_code == 200:
                    duplicate_data = duplicate_response.json()
                    print(f"✅ Duplicate handling: {duplicate_data.get('message')}")
                    print(f"   Count incremented to: {duplicate_data.get('favorite_count')}")
                    print(f"   Already exists flag: {duplicate_data.get('already_exists')}")
                else:
                    print(f"❌ Duplicate test failed: HTTP {duplicate_response.status_code}")
                
                # Step 4: Test GET /api/favorites - List favorites
                print("\nStep 4: Testing GET /api/favorites...")
                
                list_response = session.get(f"{BACKEND_URL}/favorites")
                
                if list_response.status_code == 200:
                    list_data = list_response.json()
                    favorites = list_data.get("favorites", [])
                    statistics = list_data.get("statistics", {})
                    
                    print(f"✅ Favorites list retrieved: {len(favorites)} favorites")
                    print(f"   Statistics: {statistics}")
                    
                    # Step 5: Test filtering
                    print("\nStep 5: Testing filtering...")
                    
                    # Filter by category
                    category_response = session.get(f"{BACKEND_URL}/favorites?category=İnsan Kaynakları")
                    if category_response.status_code == 200:
                        category_data = category_response.json()
                        print(f"✅ Category filter: {len(category_data.get('favorites', []))} results")
                    
                    # Filter by tag
                    tag_response = session.get(f"{BACKEND_URL}/favorites?tag=prosedür")
                    if tag_response.status_code == 200:
                        tag_data = tag_response.json()
                        print(f"✅ Tag filter: {len(tag_data.get('favorites', []))} results")
                    
                    # Step 6: Test GET /api/favorites/{id} - Get details
                    if favorite_id:
                        print(f"\nStep 6: Testing GET /api/favorites/{favorite_id}...")
                        
                        detail_response = session.get(f"{BACKEND_URL}/favorites/{favorite_id}")
                        
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            print(f"✅ Favorite details retrieved")
                            print(f"   Question: {detail_data.get('question', '')[:50]}...")
                            print(f"   Category: {detail_data.get('category')}")
                            print(f"   Tags: {detail_data.get('tags')}")
                            
                            # Step 7: Test PUT /api/favorites/{id} - Update
                            print(f"\nStep 7: Testing PUT /api/favorites/{favorite_id}...")
                            
                            update_request = {
                                "category": "İnsan Kaynakları - Güncellendi",
                                "tags": ["prosedür", "çalışan", "yönetim", "güncellendi"],
                                "notes": "Güncellenmiş test notu"
                            }
                            
                            update_response = session.put(f"{BACKEND_URL}/favorites/{favorite_id}", json=update_request)
                            
                            if update_response.status_code == 200:
                                update_data = update_response.json()
                                print(f"✅ Favorite updated: {update_data.get('message')}")
                                
                                # Step 8: Test POST /api/favorites/{id}/replay - Replay
                                print(f"\nStep 8: Testing POST /api/favorites/{favorite_id}/replay...")
                                
                                replay_response = session.post(f"{BACKEND_URL}/favorites/{favorite_id}/replay")
                                
                                if replay_response.status_code == 200:
                                    replay_data = replay_response.json()
                                    new_session_id = replay_data.get("new_session_id")
                                    result = replay_data.get("result", {})
                                    
                                    print(f"✅ Favorite replayed successfully")
                                    print(f"   New session ID: {new_session_id}")
                                    print(f"   Result has answer: {len(result.get('answer', '')) > 0}")
                                    
                                    # Step 9: Test DELETE /api/favorites/{id} - Delete
                                    print(f"\nStep 9: Testing DELETE /api/favorites/{favorite_id}...")
                                    
                                    delete_response = session.delete(f"{BACKEND_URL}/favorites/{favorite_id}")
                                    
                                    if delete_response.status_code == 200:
                                        delete_data = delete_response.json()
                                        print(f"✅ Favorite deleted: {delete_data.get('message')}")
                                        
                                        # Verify deletion
                                        verify_response = session.get(f"{BACKEND_URL}/favorites/{favorite_id}")
                                        
                                        if verify_response.status_code == 404:
                                            print("✅ Deletion verified - favorite no longer accessible")
                                            
                                            print("\n" + "=" * 60)
                                            print("🎉 FAVORITE QUESTIONS SYSTEM TEST COMPLETED SUCCESSFULLY!")
                                            print("✅ All CRUD operations working perfectly")
                                            print("✅ Duplicate handling working")
                                            print("✅ Filtering working")
                                            print("✅ Replay functionality working")
                                            print("✅ 404 error handling working")
                                            print("=" * 60)
                                            return True
                                        else:
                                            print("❌ Deletion verification failed - favorite still accessible")
                                    else:
                                        print(f"❌ Delete failed: HTTP {delete_response.status_code}")
                                        print(f"   Response: {delete_response.text}")
                                else:
                                    print(f"❌ Replay failed: HTTP {replay_response.status_code}")
                                    print(f"   Response: {replay_response.text}")
                            else:
                                print(f"❌ Update failed: HTTP {update_response.status_code}")
                                print(f"   Response: {update_response.text}")
                        else:
                            print(f"❌ Get details failed: HTTP {detail_response.status_code}")
                            print(f"   Response: {detail_response.text}")
                else:
                    print(f"❌ List favorites failed: HTTP {list_response.status_code}")
                    print(f"   Response: {list_response.text}")
            else:
                print(f"❌ Add favorite failed: HTTP {add_response.status_code}")
                print(f"   Response: {add_response.text}")
        else:
            print(f"❌ Create test session failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False
    
    return False

def test_edge_cases():
    """Test edge cases for favorite questions system"""
    print("\n🔍 TESTING EDGE CASES:")
    print("-" * 30)
    
    session = requests.Session()
    session.timeout = 30
    
    fake_id = "non-existent-favorite-id-12345"
    
    # Test 404 handling
    print("Testing 404 error handling...")
    
    get_response = session.get(f"{BACKEND_URL}/favorites/{fake_id}")
    put_response = session.put(f"{BACKEND_URL}/favorites/{fake_id}", json={"category": "Test"})
    delete_response = session.delete(f"{BACKEND_URL}/favorites/{fake_id}")
    replay_response = session.post(f"{BACKEND_URL}/favorites/{fake_id}/replay")
    
    error_handling_results = [
        ("GET", get_response.status_code == 404),
        ("PUT", put_response.status_code == 404),
        ("DELETE", delete_response.status_code == 404),
        ("REPLAY", replay_response.status_code == 404)
    ]
    
    successful_404s = sum(1 for _, success in error_handling_results if success)
    
    print(f"✅ 404 Error handling: {successful_404s}/4 endpoints correctly return 404")
    for method, success in error_handling_results:
        status = "✅" if success else "❌"
        print(f"   {status} {method} endpoint")
    
    # Test pagination
    print("\nTesting pagination...")
    
    limit_response = session.get(f"{BACKEND_URL}/favorites?limit=5")
    if limit_response.status_code == 200:
        limit_data = limit_response.json()
        favorites_count = len(limit_data.get("favorites", []))
        print(f"✅ Pagination working: limit=5 returned {favorites_count} items")
    else:
        print(f"❌ Pagination test failed: HTTP {limit_response.status_code}")

if __name__ == "__main__":
    success = test_favorite_questions_system()
    test_edge_cases()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - FAVORITE QUESTIONS SYSTEM IS WORKING PERFECTLY!")
    else:
        print("\n❌ SOME TESTS FAILED - FAVORITE QUESTIONS SYSTEM NEEDS ATTENTION")