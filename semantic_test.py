#!/usr/bin/env python3
"""
Focused test for NEW Semantic Question Suggestions Feature
Tests the new semantic endpoints specifically
"""

import requests
import json
import time

# Backend URL
BACKEND_URL = "https://f2ead008-c379-4406-a4b1-d910c3eaf61c.preview.emergentagent.com/api"

def test_semantic_question_suggestions():
    """Test GET /api/suggest-questions endpoint"""
    print("🧠 Testing Semantic Question Suggestions...")
    
    test_cases = [
        {"query": "insan kaynakları", "expected_min": 0},
        {"query": "çalışan hakları", "expected_min": 0},
        {"query": "prosedür", "expected_min": 0},
        {"query": "", "expected_min": 0},  # Empty query
        {"query": "pr", "expected_min": 0},  # Short query
    ]
    
    results = []
    
    for case in test_cases:
        print(f"  Testing query: '{case['query']}'")
        
        try:
            response = requests.get(f"{BACKEND_URL}/suggest-questions", 
                                  params={"q": case["query"], "limit": 5},
                                  timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["suggestions", "query", "count"]
                has_all_fields = all(field in data for field in required_fields)
                
                suggestions = data.get("suggestions", [])
                suggestion_types = set()
                similarity_scores_valid = True
                
                # Validate each suggestion
                for suggestion in suggestions:
                    if all(field in suggestion for field in ["type", "text", "similarity", "icon"]):
                        suggestion_types.add(suggestion["type"])
                        similarity = suggestion["similarity"]
                        if not (0.0 <= similarity <= 1.0):
                            similarity_scores_valid = False
                    else:
                        similarity_scores_valid = False
                
                results.append({
                    "query": case["query"],
                    "success": True,
                    "count": data.get("count", 0),
                    "structure_valid": has_all_fields,
                    "similarity_scores_valid": similarity_scores_valid,
                    "suggestion_types": list(suggestion_types)
                })
                
                print(f"    ✅ Success: {data.get('count', 0)} suggestions, types: {list(suggestion_types)}")
                
            else:
                results.append({
                    "query": case["query"],
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
                print(f"    ❌ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            results.append({
                "query": case["query"],
                "success": False,
                "error": str(e)
            })
            print(f"    ❌ Error: {str(e)}")
    
    return results

def test_similar_questions_search():
    """Test GET /api/similar-questions endpoint"""
    print("\n🔍 Testing Similar Questions Search...")
    
    test_cases = [
        {"query": "personel yönetimi", "similarity": 0.6},
        {"query": "çalışan hakları", "similarity": 0.4},
        {"query": "prosedür adımları", "similarity": 0.8},
        {"query": "", "similarity": 0.6},  # Empty query
        {"query": "ik", "similarity": 0.6},  # Short query
    ]
    
    results = []
    
    for case in test_cases:
        print(f"  Testing query: '{case['query']}' (similarity: {case['similarity']})")
        
        try:
            response = requests.get(f"{BACKEND_URL}/similar-questions", 
                                  params={"q": case["query"], 
                                         "similarity": case["similarity"],
                                         "limit": 5},
                                  timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                required_fields = ["similar_questions", "query", "min_similarity", "count"]
                has_all_fields = all(field in data for field in required_fields)
                
                similar_questions = data.get("similar_questions", [])
                similarity_scores_valid = True
                threshold_respected = True
                
                # Validate each similar question
                for similar_q in similar_questions:
                    if all(field in similar_q for field in ["question", "similarity", "session_id", "created_at"]):
                        similarity_score = similar_q["similarity"]
                        if not (0.0 <= similarity_score <= 1.0):
                            similarity_scores_valid = False
                        if similarity_score < case["similarity"]:
                            threshold_respected = False
                    else:
                        similarity_scores_valid = False
                
                results.append({
                    "query": case["query"],
                    "similarity_threshold": case["similarity"],
                    "success": True,
                    "count": data.get("count", 0),
                    "structure_valid": has_all_fields,
                    "similarity_scores_valid": similarity_scores_valid,
                    "threshold_respected": threshold_respected,
                    "min_similarity": data.get("min_similarity", 0)
                })
                
                print(f"    ✅ Success: {data.get('count', 0)} similar questions, min_similarity: {data.get('min_similarity', 0)}")
                
            else:
                results.append({
                    "query": case["query"],
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                })
                print(f"    ❌ Failed: HTTP {response.status_code}")
                
        except Exception as e:
            results.append({
                "query": case["query"],
                "success": False,
                "error": str(e)
            })
            print(f"    ❌ Error: {str(e)}")
    
    return results

def test_performance():
    """Test performance of semantic endpoints"""
    print("\n⚡ Testing Performance...")
    
    test_queries = ["prosedür", "insan kaynakları", "çalışan hakları"]
    performance_results = []
    
    for query in test_queries:
        print(f"  Testing performance for: '{query}'")
        
        # Test suggest-questions performance
        start_time = time.time()
        try:
            response1 = requests.get(f"{BACKEND_URL}/suggest-questions", 
                                   params={"q": query, "limit": 5},
                                   timeout=5)
            suggest_time = time.time() - start_time
            suggest_success = response1.status_code == 200
        except:
            suggest_time = 5.0  # Timeout
            suggest_success = False
        
        # Test similar-questions performance
        start_time = time.time()
        try:
            response2 = requests.get(f"{BACKEND_URL}/similar-questions", 
                                   params={"q": query, "similarity": 0.6},
                                   timeout=5)
            similar_time = time.time() - start_time
            similar_success = response2.status_code == 200
        except:
            similar_time = 5.0  # Timeout
            similar_success = False
        
        performance_results.append({
            "query": query,
            "suggest_time": suggest_time,
            "similar_time": similar_time,
            "suggest_success": suggest_success,
            "similar_success": similar_success
        })
        
        print(f"    Suggest: {suggest_time:.2f}s ({'✅' if suggest_success else '❌'}), Similar: {similar_time:.2f}s ({'✅' if similar_success else '❌'})")
    
    return performance_results

def main():
    print("🚀 SEMANTIC QUESTION SUGGESTIONS FEATURE TEST")
    print("=" * 60)
    print(f"Testing backend at: {BACKEND_URL}")
    print()
    
    # Test 1: Semantic Question Suggestions
    suggest_results = test_semantic_question_suggestions()
    
    # Test 2: Similar Questions Search
    similar_results = test_similar_questions_search()
    
    # Test 3: Performance
    performance_results = test_performance()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    # Suggestions summary
    suggest_success = sum(1 for r in suggest_results if r.get("success", False))
    print(f"Semantic Suggestions: {suggest_success}/{len(suggest_results)} successful")
    
    # Similar questions summary
    similar_success = sum(1 for r in similar_results if r.get("success", False))
    print(f"Similar Questions: {similar_success}/{len(similar_results)} successful")
    
    # Performance summary
    avg_suggest_time = sum(r["suggest_time"] for r in performance_results) / len(performance_results)
    avg_similar_time = sum(r["similar_time"] for r in performance_results) / len(performance_results)
    print(f"Average Response Times: Suggest={avg_suggest_time:.2f}s, Similar={avg_similar_time:.2f}s")
    
    # Overall assessment
    total_tests = len(suggest_results) + len(similar_results)
    total_success = suggest_success + similar_success
    success_rate = (total_success / total_tests) * 100 if total_tests > 0 else 0
    
    performance_acceptable = avg_suggest_time < 2.0 and avg_similar_time < 2.0
    
    print(f"\nOverall Success Rate: {success_rate:.1f}%")
    print(f"Performance: {'✅ Acceptable' if performance_acceptable else '❌ Slow'} (<2s threshold)")
    
    if success_rate >= 80 and performance_acceptable:
        print("\n🎉 SEMANTIC QUESTION SUGGESTIONS FEATURE: ✅ WORKING PERFECTLY!")
        return True
    elif success_rate >= 60:
        print("\n⚠️ SEMANTIC QUESTION SUGGESTIONS FEATURE: 🔶 WORKING WITH ISSUES")
        return True
    else:
        print("\n❌ SEMANTIC QUESTION SUGGESTIONS FEATURE: ❌ MAJOR ISSUES DETECTED")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)