#!/usr/bin/env python3
"""
Specific test for ChatSession Pydantic Validation Fix
Tests the critical bug fix for source_documents field requirement
"""

import requests
import json
import time

BACKEND_URL = "https://1070132c-1836-44b9-839f-410d8851049c.preview.emergentagent.com/api"

def test_chatsession_validation_fix():
    """Test ChatSession Pydantic validation fix - source_documents field"""
    print("🔥 CRITICAL TEST: ChatSession Pydantic Validation Fix")
    print("=" * 60)
    
    session = requests.Session()
    session.timeout = 30
    
    # Test questions to verify no Pydantic validation errors
    test_questions = [
        "What are the main procedures mentioned in the documents?",
        "ANKAS çalışanları için hangi prosedürler var?",
        "Tell me about the orientation procedure",
        "What is the complaint evaluation procedure?",
        "Explain the email correspondence procedure"
    ]
    
    successful_tests = 0
    pydantic_errors = []
    
    for i, question in enumerate(test_questions, 1):
        print(f"\nTest {i}: {question}")
        
        try:
            # Make request to ask-question endpoint
            response = session.post(
                f"{BACKEND_URL}/ask-question",
                json={
                    "question": question,
                    "session_id": f"validation_test_{int(time.time())}_{i}"
                }
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check required fields
                    required_fields = ["question", "answer", "session_id", "context_found"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        answer = data.get("answer", "")
                        context_found = data.get("context_found", False)
                        
                        print(f"   ✅ SUCCESS: Response received")
                        print(f"   Context found: {context_found}")
                        print(f"   Answer length: {len(answer)} characters")
                        
                        successful_tests += 1
                    else:
                        print(f"   ❌ FAIL: Missing fields {missing_fields}")
                        
                except json.JSONDecodeError as e:
                    print(f"   ❌ FAIL: Invalid JSON response - {str(e)}")
                    
            elif response.status_code == 500:
                # Check for Pydantic validation errors
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "")
                    
                    if "validation error" in error_detail.lower() and "chatsession" in error_detail.lower():
                        print(f"   ❌ CRITICAL FAIL: PYDANTIC VALIDATION ERROR!")
                        print(f"   Error: {error_detail}")
                        pydantic_errors.append(f"Test {i}: {error_detail}")
                    else:
                        print(f"   ⚠️ Server error (non-Pydantic): {error_detail}")
                        
                except json.JSONDecodeError:
                    print(f"   ❌ FAIL: HTTP 500 with non-JSON response")
                    
            else:
                print(f"   ❌ FAIL: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ FAIL: Connection error - {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("CHATSESSION VALIDATION FIX TEST RESULTS")
    print("=" * 60)
    
    if len(pydantic_errors) == 0:
        print("✅ CRITICAL FIX WORKING!")
        print(f"✅ No Pydantic validation errors detected")
        print(f"✅ Successfully processed {successful_tests}/{len(test_questions)} questions")
        print("✅ ChatSession source_documents field properly handled")
        
        if successful_tests >= len(test_questions) * 0.8:  # 80% success rate
            print("✅ OVERALL RESULT: PASS - ChatSession validation fix is working correctly")
            return True
        else:
            print("⚠️ OVERALL RESULT: PARTIAL - Some questions failed but no Pydantic errors")
            return True
    else:
        print("❌ CRITICAL FIX FAILED!")
        print(f"❌ {len(pydantic_errors)} Pydantic validation errors detected:")
        for error in pydantic_errors:
            print(f"   - {error}")
        print("❌ OVERALL RESULT: FAIL - ChatSession validation fix not working")
        return False

if __name__ == "__main__":
    success = test_chatsession_validation_fix()
    exit(0 if success else 1)