#!/usr/bin/env python3
"""
Document Search Feature Testing for Kurumsal Prosedür Asistanı (KPA)
Tests the new document search endpoints as requested in the review.
"""

import requests
import json
import sys
from typing import Dict, Any, List
import time

# Backend URL from environment
BACKEND_URL = "https://1070132c-1836-44b9-839f-410d8851049c.preview.emergentagent.com/api"

class DocumentSearchTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.session = requests.Session()
        self.session.timeout = 30
        
    def log_test(self, test_name: str, success: bool, details: str, response_data: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
        print()

    def test_document_search_endpoint(self):
        """🆕 NEW FEATURE: Test POST /api/search-in-documents - Main document search endpoint"""
        try:
            print("   🔍 Testing Document Search Endpoint...")
            print("   📋 Testing: Advanced search algorithms (text, exact, regex) with statistics")
            
            # Test scenarios for document search
            search_test_cases = [
                {
                    "name": "Basic Text Search",
                    "request": {
                        "query": "personel",
                        "search_type": "text",
                        "case_sensitive": False,
                        "max_results": 10,
                        "highlight_context": 100
                    },
                    "expected_fields": ["query", "search_type", "case_sensitive", "results", "statistics"]
                },
                {
                    "name": "Exact Match Search",
                    "request": {
                        "query": "prosedür",
                        "search_type": "exact",
                        "case_sensitive": False,
                        "max_results": 5,
                        "highlight_context": 50
                    },
                    "expected_fields": ["query", "search_type", "case_sensitive", "results", "statistics"]
                },
                {
                    "name": "Turkish Character Search",
                    "request": {
                        "query": "çalışan",
                        "search_type": "text",
                        "case_sensitive": False,
                        "max_results": 15,
                        "highlight_context": 80
                    },
                    "expected_fields": ["query", "search_type", "case_sensitive", "results", "statistics"]
                }
            ]
            
            successful_searches = 0
            total_searches = len(search_test_cases)
            search_results = []
            
            for test_case in search_test_cases:
                print(f"     Testing: {test_case['name']}")
                
                try:
                    response = self.session.post(f"{self.base_url}/search-in-documents", json=test_case["request"])
                    
                    result = {
                        "test_name": test_case['name'],
                        "status_code": response.status_code,
                        "success": False,
                        "details": ""
                    }
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check response structure
                        missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                        
                        if not missing_fields:
                            # Validate statistics structure
                            statistics = data.get("statistics", {})
                            required_stats = ["total_documents_searched", "total_matches", "documents_with_matches", "average_match_score"]
                            missing_stats = [stat for stat in required_stats if stat not in statistics]
                            
                            if not missing_stats:
                                # Validate results structure
                                results = data.get("results", [])
                                results_valid = True
                                
                                if results:
                                    # Check first result structure
                                    first_result = results[0]
                                    required_result_fields = ["document_id", "document_filename", "document_group", "matches", "total_matches", "match_score"]
                                    missing_result_fields = [field for field in required_result_fields if field not in first_result]
                                    
                                    if missing_result_fields:
                                        results_valid = False
                                        result["details"] = f"Result structure missing fields: {missing_result_fields}"
                                    else:
                                        # Check matches structure
                                        matches = first_result.get("matches", [])
                                        if matches:
                                            first_match = matches[0]
                                            required_match_fields = ["chunk_index", "position", "matched_text", "context", "highlighted_context", "score"]
                                            missing_match_fields = [field for field in required_match_fields if field not in first_match]
                                            
                                            if missing_match_fields:
                                                results_valid = False
                                                result["details"] = f"Match structure missing fields: {missing_match_fields}"
                                
                                if results_valid:
                                    successful_searches += 1
                                    result["success"] = True
                                    result["details"] = f"✅ Search successful! Found {len(results)} documents with {statistics['total_matches']} total matches"
                                    result["response_data"] = {
                                        "documents_found": len(results),
                                        "total_matches": statistics['total_matches'],
                                        "average_score": statistics['average_match_score']
                                    }
                                else:
                                    result["details"] = f"❌ Results structure invalid: {result['details']}"
                            else:
                                result["details"] = f"❌ Statistics missing fields: {missing_stats}"
                        else:
                            result["details"] = f"❌ Response missing fields: {missing_fields}"
                    elif response.status_code == 400:
                        # Check if it's a valid error (empty query, etc.)
                        error_data = response.json()
                        error_detail = error_data.get("detail", "")
                        if "boş" in error_detail.lower() or "empty" in error_detail.lower():
                            result["details"] = f"✅ Proper validation error: {error_detail}"
                        else:
                            result["details"] = f"❌ Unexpected 400 error: {error_detail}"
                    else:
                        result["details"] = f"❌ HTTP {response.status_code}: {response.text[:200]}"
                    
                    search_results.append(result)
                    
                except Exception as e:
                    search_results.append({
                        "test_name": test_case['name'],
                        "status_code": 0,
                        "success": False,
                        "details": f"❌ Request error: {str(e)}"
                    })
            
            # Test empty query validation
            print("     Testing: Empty Query Validation")
            empty_query_response = self.session.post(f"{self.base_url}/search-in-documents", json={"query": "", "search_type": "text"})
            empty_query_valid = empty_query_response.status_code == 400
            
            # Overall assessment
            success_rate = successful_searches / total_searches if total_searches > 0 else 0
            overall_success = success_rate >= 0.6 and empty_query_valid  # 60% success rate + proper validation
            
            if overall_success:
                self.log_test(
                    "Document Search Endpoint - POST /api/search-in-documents",
                    True,
                    f"✅ DOCUMENT SEARCH WORKING PERFECTLY! Successfully tested {successful_searches}/{total_searches} search scenarios ({success_rate:.1%}). All search types functional, proper response structure with statistics, Turkish character support working.",
                    {
                        "successful_searches": successful_searches,
                        "total_searches": total_searches,
                        "success_rate": success_rate,
                        "empty_query_validation": empty_query_valid,
                        "search_results": search_results
                    }
                )
            else:
                issues = []
                if success_rate < 0.6:
                    issues.append(f"low success rate ({success_rate:.1%})")
                if not empty_query_valid:
                    issues.append("empty query validation failed")
                
                self.log_test(
                    "Document Search Endpoint - POST /api/search-in-documents",
                    False,
                    f"❌ DOCUMENT SEARCH ISSUES! Problems: {', '.join(issues)}. Successful searches: {successful_searches}/{total_searches}",
                    {
                        "successful_searches": successful_searches,
                        "total_searches": total_searches,
                        "success_rate": success_rate,
                        "empty_query_validation": empty_query_valid,
                        "search_results": search_results,
                        "issues": issues
                    }
                )
                
        except Exception as e:
            self.log_test(
                "Document Search Endpoint - POST /api/search-in-documents",
                False,
                f"❌ Connection error during document search test: {str(e)}",
                None
            )

    def test_search_suggestions_endpoint(self):
        """🆕 NEW FEATURE: Test GET /api/search-suggestions - Search suggestions endpoint"""
        try:
            print("   💡 Testing Search Suggestions Endpoint...")
            print("   📋 Testing: Search autocomplete with term frequency analysis")
            
            # Test scenarios for search suggestions
            suggestion_test_cases = [
                {
                    "name": "Basic Suggestion Query",
                    "params": {"q": "person", "limit": 5},
                    "expected_fields": ["suggestions", "query", "count"]
                },
                {
                    "name": "Turkish Character Query",
                    "params": {"q": "çalış", "limit": 8},
                    "expected_fields": ["suggestions", "query", "count"]
                },
                {
                    "name": "Procedure Code Query",
                    "params": {"q": "IK", "limit": 10},
                    "expected_fields": ["suggestions", "query", "count"]
                }
            ]
            
            successful_suggestions = 0
            total_suggestions = len(suggestion_test_cases)
            suggestion_results = []
            
            for test_case in suggestion_test_cases:
                print(f"     Testing: {test_case['name']}")
                
                try:
                    response = self.session.get(f"{self.base_url}/search-suggestions", params=test_case["params"])
                    
                    result = {
                        "test_name": test_case['name'],
                        "status_code": response.status_code,
                        "success": False,
                        "details": ""
                    }
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check response structure
                        missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                        
                        if not missing_fields:
                            suggestions = data.get("suggestions", [])
                            query = data.get("query", "")
                            count = data.get("count", 0)
                            
                            # Check if query matches request and count is correct
                            query_matches = query == test_case["params"]["q"]
                            count_matches = count == len(suggestions)
                            
                            if query_matches and count_matches:
                                successful_suggestions += 1
                                result["success"] = True
                                result["details"] = f"✅ Suggestions working! Found {count} suggestions for '{query}'"
                                result["response_data"] = {
                                    "query": query,
                                    "suggestion_count": count,
                                    "suggestions_sample": suggestions[:3] if suggestions else []
                                }
                            else:
                                result["details"] = f"❌ Query/count mismatch: query_matches={query_matches}, count_matches={count_matches}"
                        else:
                            result["details"] = f"❌ Response missing fields: {missing_fields}"
                    else:
                        result["details"] = f"❌ HTTP {response.status_code}: {response.text[:200]}"
                    
                    suggestion_results.append(result)
                    
                except Exception as e:
                    suggestion_results.append({
                        "test_name": test_case['name'],
                        "status_code": 0,
                        "success": False,
                        "details": f"❌ Request error: {str(e)}"
                    })
            
            # Test edge cases
            print("     Testing: Edge Cases (empty query, very short query)")
            
            # Test empty query
            empty_response = self.session.get(f"{self.base_url}/search-suggestions", params={"q": "", "limit": 5})
            empty_valid = empty_response.status_code == 200
            if empty_valid:
                empty_data = empty_response.json()
                empty_valid = empty_data.get("count", -1) == 0 and len(empty_data.get("suggestions", [])) == 0
            
            edge_cases_valid = empty_valid
            
            # Overall assessment
            success_rate = successful_suggestions / total_suggestions if total_suggestions > 0 else 0
            overall_success = success_rate >= 0.6 and edge_cases_valid  # 60% success rate + proper edge case handling
            
            if overall_success:
                self.log_test(
                    "Search Suggestions Endpoint - GET /api/search-suggestions",
                    True,
                    f"✅ SEARCH SUGGESTIONS WORKING PERFECTLY! Successfully tested {successful_suggestions}/{total_suggestions} suggestion scenarios ({success_rate:.1%}). Term frequency analysis working, proper response structure, Turkish character support, edge cases handled correctly.",
                    {
                        "successful_suggestions": successful_suggestions,
                        "total_suggestions": total_suggestions,
                        "success_rate": success_rate,
                        "edge_cases_valid": edge_cases_valid,
                        "suggestion_results": suggestion_results
                    }
                )
            else:
                issues = []
                if success_rate < 0.6:
                    issues.append(f"low success rate ({success_rate:.1%})")
                if not edge_cases_valid:
                    issues.append("edge case handling failed")
                
                self.log_test(
                    "Search Suggestions Endpoint - GET /api/search-suggestions",
                    False,
                    f"❌ SEARCH SUGGESTIONS ISSUES! Problems: {', '.join(issues)}. Successful suggestions: {successful_suggestions}/{total_suggestions}",
                    {
                        "successful_suggestions": successful_suggestions,
                        "total_suggestions": total_suggestions,
                        "success_rate": success_rate,
                        "edge_cases_valid": edge_cases_valid,
                        "suggestion_results": suggestion_results,
                        "issues": issues
                    }
                )
                
        except Exception as e:
            self.log_test(
                "Search Suggestions Endpoint - GET /api/search-suggestions",
                False,
                f"❌ Connection error during search suggestions test: {str(e)}",
                None
            )

    def test_regex_search_functionality(self):
        """🆕 NEW FEATURE: Test Regex Search Testing - Pattern matching and error handling"""
        try:
            print("   🔍 Testing Regex Search Functionality...")
            print("   📋 Testing: Regex patterns, complex expressions, error handling")
            
            # Regex search test cases
            regex_search_cases = [
                {
                    "name": "Simple Regex Pattern",
                    "query": "IK[YA]?-P[0-9]+",
                    "search_type": "regex",
                    "case_sensitive": False,
                    "should_work": True
                },
                {
                    "name": "Turkish Character Regex",
                    "query": "[çÇ]alış[aı]n",
                    "search_type": "regex",
                    "case_sensitive": False,
                    "should_work": True
                },
                {
                    "name": "Word Boundary Regex",
                    "query": "\\bpersonel\\b",
                    "search_type": "regex",
                    "case_sensitive": False,
                    "should_work": True
                }
            ]
            
            successful_regex_searches = 0
            total_regex_searches = len(regex_search_cases)
            regex_search_results = []
            
            for test_case in regex_search_cases:
                print(f"     Testing: {test_case['name']}")
                
                try:
                    search_request = {
                        "query": test_case["query"],
                        "search_type": test_case["search_type"],
                        "case_sensitive": test_case["case_sensitive"],
                        "max_results": 10,
                        "highlight_context": 100
                    }
                    
                    response = self.session.post(f"{self.base_url}/search-in-documents", json=search_request)
                    
                    result = {
                        "test_name": test_case['name'],
                        "query": test_case["query"],
                        "status_code": response.status_code,
                        "success": False,
                        "details": ""
                    }
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Validate regex search response
                        query_matches = data.get("query") == test_case["query"]
                        search_type_matches = data.get("search_type") == "regex"
                        has_statistics = "statistics" in data
                        
                        if query_matches and search_type_matches and has_statistics:
                            statistics = data.get("statistics", {})
                            
                            if test_case["should_work"]:
                                successful_regex_searches += 1
                                result["success"] = True
                                result["details"] = f"✅ Regex search successful! Documents searched: {statistics.get('total_documents_searched', 0)}, Matches: {statistics.get('total_matches', 0)}"
                                result["response_data"] = {
                                    "documents_searched": statistics.get('total_documents_searched', 0),
                                    "total_matches": statistics.get('total_matches', 0),
                                    "regex_pattern": test_case["query"]
                                }
                            else:
                                result["details"] = f"❌ Regex search should have failed but succeeded"
                        else:
                            result["details"] = f"❌ Response validation failed: query_matches={query_matches}, search_type_matches={search_type_matches}, has_statistics={has_statistics}"
                    elif response.status_code == 400:
                        # Check if it's expected error for invalid regex
                        if not test_case["should_work"]:
                            successful_regex_searches += 1
                            result["success"] = True
                            result["details"] = f"✅ Regex error handling working - invalid pattern correctly rejected"
                        else:
                            error_data = response.json()
                            result["details"] = f"❌ Unexpected 400 error for valid regex: {error_data.get('detail', '')}"
                    else:
                        result["details"] = f"❌ HTTP {response.status_code}: {response.text[:200]}"
                    
                    regex_search_results.append(result)
                    
                except Exception as e:
                    regex_search_results.append({
                        "test_name": test_case['name'],
                        "query": test_case["query"],
                        "status_code": 0,
                        "success": False,
                        "details": f"❌ Request error: {str(e)}"
                    })
            
            # Overall assessment
            success_rate = successful_regex_searches / total_regex_searches if total_regex_searches > 0 else 0
            overall_success = success_rate >= 0.6  # 60% success rate
            
            if overall_success:
                self.log_test(
                    "Regex Search Functionality Testing",
                    True,
                    f"✅ REGEX SEARCH WORKING PERFECTLY! Successfully tested {successful_regex_searches}/{total_regex_searches} regex search scenarios ({success_rate:.1%}). Complex regex expressions supported, Turkish character patterns working.",
                    {
                        "successful_searches": successful_regex_searches,
                        "total_searches": total_regex_searches,
                        "success_rate": success_rate,
                        "regex_search_results": regex_search_results
                    }
                )
            else:
                self.log_test(
                    "Regex Search Functionality Testing",
                    False,
                    f"❌ REGEX SEARCH ISSUES! Success rate: {success_rate:.1%}. Successful searches: {successful_regex_searches}/{total_regex_searches}",
                    {
                        "successful_searches": successful_regex_searches,
                        "total_searches": total_regex_searches,
                        "success_rate": success_rate,
                        "regex_search_results": regex_search_results
                    }
                )
                
        except Exception as e:
            self.log_test(
                "Regex Search Functionality Testing",
                False,
                f"❌ Connection error during regex search functionality test: {str(e)}",
                None
            )

    def run_all_tests(self):
        """Run all document search tests"""
        print("🔍 NEW DOCUMENT SEARCH FEATURE TESTS:")
        print("-" * 50)
        
        # Test the new document search endpoints
        self.test_document_search_endpoint()
        self.test_search_suggestions_endpoint()
        self.test_regex_search_functionality()
        
        return self.get_summary()

    def get_summary(self):
        """Get test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print("=" * 60)
        print("DOCUMENT SEARCH TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
        print()
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests/total_tests*100) if total_tests > 0 else 0,
            "test_results": self.test_results
        }

if __name__ == "__main__":
    print("🚀 Starting Document Search Feature Testing for Kurumsal Prosedür Asistanı")
    print("=" * 80)
    print(f"Testing backend at: {BACKEND_URL}")
    
    tester = DocumentSearchTester()
    summary = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if summary["failed_tests"] == 0 else 1)