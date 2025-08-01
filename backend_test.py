#!/usr/bin/env python3
"""
Backend API Testing for Kurumsal Prosedür Asistanı (KPA)
Tests the core API endpoints as requested in the review.
"""

import requests
import json
import sys
from typing import Dict, Any, List
import time

# Backend URL from environment
BACKEND_URL = "https://60a0fa58-5a2e-4151-bb1b-8b3af8226ea9.preview.emergentagent.com/api"

class KPABackendTester:
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

    def test_root_endpoint(self):
        """Test GET /api/ - should return welcome message"""
        try:
            response = self.session.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "Kurumsal Prosedür Asistanı" in data["message"]:
                    self.log_test(
                        "Root Endpoint (/api/)",
                        True,
                        f"Welcome message received: {data['message']}",
                        data
                    )
                else:
                    self.log_test(
                        "Root Endpoint (/api/)",
                        False,
                        "Response missing expected welcome message",
                        data
                    )
            else:
                self.log_test(
                    "Root Endpoint (/api/)",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Root Endpoint (/api/)",
                False,
                f"Connection error: {str(e)}",
                None
            )

    def test_status_endpoint(self):
        """Test GET /api/status - should return system status"""
        try:
            response = self.session.get(f"{self.base_url}/status")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["total_documents", "total_chunks", "embedding_model_loaded", "faiss_index_ready"]
                
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Check field types
                    type_errors = []
                    if not isinstance(data["total_documents"], int):
                        type_errors.append("total_documents should be int")
                    if not isinstance(data["total_chunks"], int):
                        type_errors.append("total_chunks should be int")
                    if not isinstance(data["embedding_model_loaded"], bool):
                        type_errors.append("embedding_model_loaded should be bool")
                    if not isinstance(data["faiss_index_ready"], bool):
                        type_errors.append("faiss_index_ready should be bool")
                    
                    if not type_errors:
                        self.log_test(
                            "Status Endpoint (/api/status)",
                            True,
                            f"All required fields present with correct types. Documents: {data['total_documents']}, Chunks: {data['total_chunks']}, Model loaded: {data['embedding_model_loaded']}, FAISS ready: {data['faiss_index_ready']}",
                            data
                        )
                    else:
                        self.log_test(
                            "Status Endpoint (/api/status)",
                            False,
                            f"Type errors: {', '.join(type_errors)}",
                            data
                        )
                else:
                    self.log_test(
                        "Status Endpoint (/api/status)",
                        False,
                        f"Missing required fields: {', '.join(missing_fields)}",
                        data
                    )
            else:
                self.log_test(
                    "Status Endpoint (/api/status)",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Status Endpoint (/api/status)",
                False,
                f"Connection error: {str(e)}",
                None
            )

    def test_documents_endpoint(self):
        """Test GET /api/documents - should list uploaded documents"""
        try:
            response = self.session.get(f"{self.base_url}/documents")
            
            if response.status_code == 200:
                data = response.json()
                
                if "documents" in data and "total_count" in data:
                    if isinstance(data["documents"], list) and isinstance(data["total_count"], int):
                        self.log_test(
                            "Documents Endpoint (/api/documents)",
                            True,
                            f"Documents list retrieved successfully. Total count: {data['total_count']}, Documents in response: {len(data['documents'])}",
                            {"total_count": data["total_count"], "documents_length": len(data["documents"])}
                        )
                    else:
                        self.log_test(
                            "Documents Endpoint (/api/documents)",
                            False,
                            "Response fields have incorrect types (documents should be list, total_count should be int)",
                            data
                        )
                else:
                    self.log_test(
                        "Documents Endpoint (/api/documents)",
                        False,
                        "Response missing required fields: documents and/or total_count",
                        data
                    )
            else:
                self.log_test(
                    "Documents Endpoint (/api/documents)",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Documents Endpoint (/api/documents)",
                False,
                f"Connection error: {str(e)}",
                None
            )

    def test_backend_connectivity(self):
        """Test basic backend connectivity"""
        try:
            response = self.session.get(self.base_url, timeout=10)
            if response.status_code in [200, 404, 405]:  # Any response means server is up
                self.log_test(
                    "Backend Connectivity",
                    True,
                    f"Backend server is responding (HTTP {response.status_code})",
                    None
                )
                return True
            else:
                self.log_test(
                    "Backend Connectivity",
                    False,
                    f"Unexpected HTTP status: {response.status_code}",
                    response.text
                )
                return False
        except Exception as e:
            self.log_test(
                "Backend Connectivity",
                False,
                f"Cannot connect to backend: {str(e)}",
                None
            )
            return False

    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 60)
        print("KURUMSAL PROSEDÜR ASISTANI (KPA) BACKEND API TESTS")
        print("=" * 60)
        print(f"Testing backend at: {self.base_url}")
        print()
        
        # Test connectivity first
        if not self.test_backend_connectivity():
            print("❌ Backend connectivity failed. Skipping other tests.")
            return self.get_summary()
        
        # Run specific API tests
        self.test_root_endpoint()
        self.test_status_endpoint()
        self.test_documents_endpoint()
        
        return self.get_summary()

    def get_summary(self):
        """Get test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
        print()
        
        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['details']}")
            print()
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests/total_tests*100) if total_tests > 0 else 0,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = KPABackendTester()
    summary = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if summary["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)