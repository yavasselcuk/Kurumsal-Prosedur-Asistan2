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
        """Test GET /api/status - should return system status with NEW FEATURES"""
        try:
            response = self.session.get(f"{self.base_url}/status")
            
            if response.status_code == 200:
                data = response.json()
                # Updated required fields including NEW FEATURES
                required_fields = ["total_documents", "total_chunks", "embedding_model_loaded", "faiss_index_ready", "supported_formats", "processing_queue"]
                
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
                    if not isinstance(data["supported_formats"], list):
                        type_errors.append("supported_formats should be list")
                    if not isinstance(data["processing_queue"], int):
                        type_errors.append("processing_queue should be int")
                    
                    # NEW FEATURES validation
                    format_errors = []
                    if data["supported_formats"] != ['.doc', '.docx']:
                        format_errors.append(f"supported_formats should be ['.doc', '.docx'], got {data['supported_formats']}")
                    if data["processing_queue"] != 0:
                        format_errors.append(f"processing_queue should be 0, got {data['processing_queue']}")
                    
                    if not type_errors and not format_errors:
                        self.log_test(
                            "Status Endpoint (/api/status) - Enhanced",
                            True,
                            f"All required fields present with correct types and values. Documents: {data['total_documents']}, Chunks: {data['total_chunks']}, Model loaded: {data['embedding_model_loaded']}, FAISS ready: {data['faiss_index_ready']}, Supported formats: {data['supported_formats']}, Processing queue: {data['processing_queue']}",
                            data
                        )
                    else:
                        all_errors = type_errors + format_errors
                        self.log_test(
                            "Status Endpoint (/api/status) - Enhanced",
                            False,
                            f"Validation errors: {', '.join(all_errors)}",
                            data
                        )
                else:
                    self.log_test(
                        "Status Endpoint (/api/status) - Enhanced",
                        False,
                        f"Missing required fields: {', '.join(missing_fields)}",
                        data
                    )
            else:
                self.log_test(
                    "Status Endpoint (/api/status) - Enhanced",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Status Endpoint (/api/status) - Enhanced",
                False,
                f"Connection error: {str(e)}",
                None
            )

    def test_documents_endpoint(self):
        """Test GET /api/documents - should list uploaded documents with ENHANCED FEATURES"""
        try:
            response = self.session.get(f"{self.base_url}/documents")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for enhanced structure
                required_fields = ["documents", "statistics"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Validate documents structure
                    documents_valid = isinstance(data["documents"], list)
                    
                    # Validate statistics structure
                    statistics = data.get("statistics", {})
                    required_stats = ["total_count", "completed_count", "processing_count", "failed_count", "total_size", "total_size_human"]
                    missing_stats = [stat for stat in required_stats if stat not in statistics]
                    
                    # Check document structure if any documents exist
                    document_structure_valid = True
                    document_errors = []
                    
                    if data["documents"]:
                        for i, doc in enumerate(data["documents"][:3]):  # Check first 3 documents
                            required_doc_fields = ["id", "filename", "file_type", "file_size", "chunk_count"]
                            missing_doc_fields = [field for field in required_doc_fields if field not in doc]
                            if missing_doc_fields:
                                document_errors.append(f"Document {i}: missing {missing_doc_fields}")
                                document_structure_valid = False
                    
                    if documents_valid and not missing_stats and document_structure_valid:
                        self.log_test(
                            "Documents Endpoint (/api/documents) - Enhanced",
                            True,
                            f"Enhanced documents list retrieved successfully. Statistics: {statistics}, Documents count: {len(data['documents'])}, Document structure validated",
                            {"statistics": statistics, "documents_count": len(data["documents"])}
                        )
                    else:
                        errors = []
                        if not documents_valid:
                            errors.append("documents field should be list")
                        if missing_stats:
                            errors.append(f"missing statistics fields: {missing_stats}")
                        if document_errors:
                            errors.extend(document_errors)
                        
                        self.log_test(
                            "Documents Endpoint (/api/documents) - Enhanced",
                            False,
                            f"Structure validation errors: {', '.join(errors)}",
                            data
                        )
                else:
                    self.log_test(
                        "Documents Endpoint (/api/documents) - Enhanced",
                        False,
                        f"Response missing required fields: {', '.join(missing_fields)}",
                        data
                    )
            else:
                self.log_test(
                    "Documents Endpoint (/api/documents) - Enhanced",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Documents Endpoint (/api/documents) - Enhanced",
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

    def test_file_validation(self):
        """Test file format validation for .doc and .docx support"""
        try:
            # Test with a mock file upload to check validation
            # We'll test the upload endpoint with invalid file types to see if validation works
            
            # Test 1: Invalid file type (should be rejected)
            files = {'file': ('test.txt', b'test content', 'text/plain')}
            response = self.session.post(f"{self.base_url}/upload-document", files=files)
            
            if response.status_code == 400:
                error_data = response.json()
                if "doc" in error_data.get("detail", "").lower() and "docx" in error_data.get("detail", "").lower():
                    self.log_test(
                        "File Format Validation",
                        True,
                        f"File validation working correctly - rejected .txt file with appropriate error: {error_data.get('detail', '')}",
                        error_data
                    )
                else:
                    self.log_test(
                        "File Format Validation",
                        False,
                        f"File validation error message doesn't mention supported formats: {error_data.get('detail', '')}",
                        error_data
                    )
            else:
                self.log_test(
                    "File Format Validation",
                    False,
                    f"Expected HTTP 400 for invalid file type, got {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "File Format Validation",
                False,
                f"Connection error during file validation test: {str(e)}",
                None
            )

    def test_document_delete_response_structure(self):
        """Test DELETE /api/documents/{id} enhanced response structure"""
        try:
            # First, try to get a document ID (if any exist)
            docs_response = self.session.get(f"{self.base_url}/documents")
            
            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                documents = docs_data.get("documents", [])
                
                if documents:
                    # Test delete with existing document
                    doc_id = documents[0]["id"]
                    delete_response = self.session.delete(f"{self.base_url}/documents/{doc_id}")
                    
                    if delete_response.status_code == 200:
                        delete_data = delete_response.json()
                        required_fields = ["message", "document_id", "deleted_chunks"]
                        missing_fields = [field for field in required_fields if field not in delete_data]
                        
                        if not missing_fields:
                            self.log_test(
                                "Document Delete Response Structure",
                                True,
                                f"Enhanced delete response structure validated. Fields: {list(delete_data.keys())}",
                                delete_data
                            )
                        else:
                            self.log_test(
                                "Document Delete Response Structure",
                                False,
                                f"Delete response missing required fields: {missing_fields}",
                                delete_data
                            )
                    else:
                        self.log_test(
                            "Document Delete Response Structure",
                            False,
                            f"Delete request failed with HTTP {delete_response.status_code}",
                            delete_response.text
                        )
                else:
                    # Test delete with non-existent document to check error structure
                    fake_id = "non-existent-id"
                    delete_response = self.session.delete(f"{self.base_url}/documents/{fake_id}")
                    
                    if delete_response.status_code == 404:
                        self.log_test(
                            "Document Delete Response Structure",
                            True,
                            "Delete endpoint correctly returns 404 for non-existent document (no documents to test actual delete)",
                            None
                        )
                    else:
                        self.log_test(
                            "Document Delete Response Structure",
                            False,
                            f"Expected 404 for non-existent document, got {delete_response.status_code}",
                            delete_response.text
                        )
            else:
                self.log_test(
                    "Document Delete Response Structure",
                    False,
                    f"Could not retrieve documents list to test delete: HTTP {docs_response.status_code}",
                    docs_response.text
                )
                
        except Exception as e:
            self.log_test(
                "Document Delete Response Structure",
                False,
                f"Connection error during delete test: {str(e)}",
                None
            )

    def test_new_format_support_active(self):
        """Test that .doc and .docx format support is active in the API"""
        try:
            # Check status endpoint for supported formats
            status_response = self.session.get(f"{self.base_url}/status")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                supported_formats = status_data.get("supported_formats", [])
                
                expected_formats = ['.doc', '.docx']
                formats_match = set(supported_formats) == set(expected_formats)
                
                if formats_match:
                    self.log_test(
                        "New Format Support Active",
                        True,
                        f"Both .doc and .docx formats are active and supported: {supported_formats}",
                        {"supported_formats": supported_formats}
                    )
                else:
                    self.log_test(
                        "New Format Support Active",
                        False,
                        f"Supported formats don't match expected. Expected: {expected_formats}, Got: {supported_formats}",
                        {"expected": expected_formats, "actual": supported_formats}
                    )
            else:
                self.log_test(
                    "New Format Support Active",
                    False,
                    f"Could not retrieve status to check supported formats: HTTP {status_response.status_code}",
                    status_response.text
                )
                
        except Exception as e:
            self.log_test(
                "New Format Support Active",
                False,
                f"Connection error during format support test: {str(e)}",
                None
            )

    def run_all_tests(self):
        """Run all backend tests including NEW FEATURES"""
        print("=" * 70)
        print("KURUMSAL PROSEDÜR ASISTANI (KPA) BACKEND API TESTS - ENHANCED")
        print("=" * 70)
        print(f"Testing backend at: {self.base_url}")
        print("Testing NEW FEATURES: Enhanced status, document management, format support")
        print()
        
        # Test connectivity first
        if not self.test_backend_connectivity():
            print("❌ Backend connectivity failed. Skipping other tests.")
            return self.get_summary()
        
        # Run specific API tests (original)
        self.test_root_endpoint()
        
        # Run enhanced tests for NEW FEATURES
        self.test_status_endpoint()  # Enhanced with new fields
        self.test_documents_endpoint()  # Enhanced with statistics
        
        # Run NEW FEATURE tests
        self.test_new_format_support_active()
        self.test_file_validation()
        self.test_document_delete_response_structure()
        
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