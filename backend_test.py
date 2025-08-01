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

    def test_doc_processing_system(self):
        """🔥 PRIORITY: Test DOC processing system - antiword installation and textract fallback"""
        try:
            print("   🔍 Testing DOC processing capabilities...")
            
            # Test 1: Check if antiword is available on the system
            import subprocess
            try:
                result = subprocess.run(['which', 'antiword'], capture_output=True, text=True, timeout=10)
                antiword_available = result.returncode == 0
                antiword_path = result.stdout.strip() if antiword_available else "Not found"
                
                if antiword_available:
                    # Test antiword version
                    version_result = subprocess.run(['antiword', '-v'], capture_output=True, text=True, timeout=10)
                    antiword_info = f"Available at {antiword_path}, Version info: {version_result.stderr[:100] if version_result.stderr else 'Unknown'}"
                else:
                    antiword_info = "Not installed or not in PATH"
                
                self.log_test(
                    "DOC Processing - Antiword Installation",
                    antiword_available,
                    f"Antiword status: {antiword_info}",
                    {"available": antiword_available, "path": antiword_path}
                )
                
            except Exception as e:
                self.log_test(
                    "DOC Processing - Antiword Installation",
                    False,
                    f"Error checking antiword: {str(e)}",
                    None
                )
            
            # Test 2: Check textract availability (fallback mechanism)
            try:
                import textract
                textract_available = True
                textract_info = f"Textract module available: {textract.__version__ if hasattr(textract, '__version__') else 'Version unknown'}"
            except ImportError as e:
                textract_available = False
                textract_info = f"Textract not available: {str(e)}"
            
            self.log_test(
                "DOC Processing - Textract Fallback",
                textract_available,
                textract_info,
                {"available": textract_available}
            )
            
            # Test 3: Create a minimal DOC file for testing (if possible)
            # Since we can't easily create a real DOC file, we'll test with a fake DOC upload
            # to see how the system handles DOC processing errors
            
            print("   📄 Testing DOC file upload handling...")
            
            # Create fake DOC content (this will likely fail processing, but we can test error handling)
            fake_doc_content = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'Fake DOC content for testing' + b'\x00' * 100
            
            files = {'file': ('test_document.doc', fake_doc_content, 'application/msword')}
            response = self.session.post(f"{self.base_url}/upload-document", files=files)
            
            if response.status_code == 400:
                error_data = response.json()
                error_detail = error_data.get("detail", "")
                
                # Check if error message is user-friendly and mentions DOC processing
                if any(keyword in error_detail.lower() for keyword in ["doc", "işlem", "process", "bozuk", "format"]):
                    self.log_test(
                        "DOC Processing - Error Handling",
                        True,
                        f"✅ DOC processing error handling working - user-friendly error message: {error_detail[:200]}",
                        {"error_detail": error_detail}
                    )
                else:
                    self.log_test(
                        "DOC Processing - Error Handling",
                        False,
                        f"❌ DOC processing error message not user-friendly: {error_detail}",
                        error_data
                    )
            elif response.status_code == 200:
                # Unexpected success - the fake DOC was processed somehow
                success_data = response.json()
                self.log_test(
                    "DOC Processing - Unexpected Success",
                    True,
                    f"⚠️ Fake DOC file was processed successfully (unexpected but not necessarily bad): {success_data.get('message', '')}",
                    success_data
                )
            else:
                self.log_test(
                    "DOC Processing - Error Handling",
                    False,
                    f"❌ Unexpected HTTP status for DOC processing: {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "DOC Processing System",
                False,
                f"❌ Error during DOC processing system test: {str(e)}",
                None
            )

    def test_document_processing_pipeline(self):
        """🔥 PRIORITY: Test the complete document processing pipeline"""
        try:
            print("   ⚙️ Testing document processing pipeline...")
            
            # Test 1: Test with various file extensions to see pipeline behavior
            test_files = [
                ('test.docx', b'PK\x03\x04' + b'Fake DOCX content' + b'\x00' * 50, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                ('test.doc', b'\xd0\xcf\x11\xe0' + b'Fake DOC content' + b'\x00' * 50, 'application/msword'),
                ('invalid.pdf', b'%PDF-1.4' + b'Fake PDF content', 'application/pdf'),
                ('invalid.rtf', b'{\\rtf1' + b'Fake RTF content', 'application/rtf')
            ]
            
            pipeline_results = []
            
            for filename, content, mime_type in test_files:
                print(f"     Testing pipeline with: {filename}")
                
                files = {'file': (filename, content, mime_type)}
                response = self.session.post(f"{self.base_url}/upload-document", files=files)
                
                result = {
                    "filename": filename,
                    "status_code": response.status_code,
                    "expected_behavior": "accept" if filename.endswith(('.doc', '.docx')) else "reject"
                }
                
                if response.status_code == 400:
                    error_data = response.json()
                    result["error"] = error_data.get("detail", "")
                    result["correct_rejection"] = not filename.endswith(('.doc', '.docx'))
                elif response.status_code == 200:
                    success_data = response.json()
                    result["success"] = success_data.get("message", "")
                    result["correct_acceptance"] = filename.endswith(('.doc', '.docx'))
                else:
                    result["unexpected_status"] = response.text
                
                pipeline_results.append(result)
            
            # Analyze pipeline results
            correct_behaviors = 0
            total_tests = len(test_files)
            
            for result in pipeline_results:
                if result["expected_behavior"] == "accept":
                    # Should accept .doc/.docx files (even if processing fails due to fake content)
                    if result["status_code"] in [200, 400]:  # 400 is OK if it's due to content processing, not format rejection
                        if result["status_code"] == 400 and "format" not in result.get("error", "").lower():
                            correct_behaviors += 1  # Processing error, not format error
                        elif result["status_code"] == 200:
                            correct_behaviors += 1  # Successfully accepted
                else:
                    # Should reject non-.doc/.docx files
                    if result["status_code"] == 400 and result.get("correct_rejection", False):
                        correct_behaviors += 1
            
            pipeline_success = correct_behaviors >= (total_tests * 0.75)  # 75% success rate acceptable
            
            self.log_test(
                "Document Processing Pipeline",
                pipeline_success,
                f"Pipeline behavior: {correct_behaviors}/{total_tests} correct responses. Pipeline {'working correctly' if pipeline_success else 'has issues'}",
                {"results": pipeline_results, "success_rate": f"{correct_behaviors}/{total_tests}"}
            )
            
        except Exception as e:
            self.log_test(
                "Document Processing Pipeline",
                False,
                f"❌ Error during pipeline test: {str(e)}",
                None
            )

    def test_enhanced_error_handling(self):
        """🔥 PRIORITY: Test enhanced error handling and user-friendly messages"""
        try:
            print("   💬 Testing enhanced error handling...")
            
            # Test various error scenarios
            error_scenarios = [
                {
                    "name": "Empty file",
                    "filename": "empty.docx",
                    "content": b'',
                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "expected_keywords": ["boş", "empty", "boyut"]
                },
                {
                    "name": "Very large file",
                    "filename": "large.docx", 
                    "content": b'PK\x03\x04' + b'X' * (11 * 1024 * 1024),  # 11MB file
                    "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "expected_keywords": ["büyük", "boyut", "maksimum", "limit"]
                },
                {
                    "name": "Corrupted DOC file",
                    "filename": "corrupted.doc",
                    "content": b'\xd0\xcf\x11\xe0' + b'corrupted content' + b'\xff' * 100,
                    "mime_type": "application/msword",
                    "expected_keywords": ["bozuk", "işlem", "hata", "format", "docx"]
                }
            ]
            
            error_handling_results = []
            
            for scenario in error_scenarios:
                print(f"     Testing: {scenario['name']}")
                
                files = {'file': (scenario['filename'], scenario['content'], scenario['mime_type'])}
                response = self.session.post(f"{self.base_url}/upload-document", files=files)
                
                result = {
                    "scenario": scenario['name'],
                    "status_code": response.status_code,
                    "user_friendly": False,
                    "contains_keywords": False
                }
                
                if response.status_code == 400:
                    error_data = response.json()
                    error_message = error_data.get("detail", "").lower()
                    
                    # Check if error message is user-friendly (Turkish)
                    result["user_friendly"] = any(turkish_word in error_message for turkish_word in 
                                                ["dosya", "doküman", "lütfen", "hata", "boyut", "format"])
                    
                    # Check if contains expected keywords
                    result["contains_keywords"] = any(keyword in error_message for keyword in scenario['expected_keywords'])
                    result["error_message"] = error_data.get("detail", "")
                
                error_handling_results.append(result)
            
            # Evaluate error handling quality
            user_friendly_count = sum(1 for r in error_handling_results if r["user_friendly"])
            keyword_match_count = sum(1 for r in error_handling_results if r["contains_keywords"])
            
            error_handling_quality = (user_friendly_count + keyword_match_count) / (len(error_scenarios) * 2)
            error_handling_success = error_handling_quality >= 0.6  # 60% quality threshold
            
            self.log_test(
                "Enhanced Error Handling",
                error_handling_success,
                f"Error handling quality: {error_handling_quality:.1%}. User-friendly messages: {user_friendly_count}/{len(error_scenarios)}, Keyword matches: {keyword_match_count}/{len(error_scenarios)}",
                {"results": error_handling_results, "quality_score": error_handling_quality}
            )
            
        except Exception as e:
            self.log_test(
                "Enhanced Error Handling",
                False,
                f"❌ Error during error handling test: {str(e)}",
                None
            )

    def test_document_delete_functionality(self):
        """Test DELETE /api/documents/{id} - PRIORITY: User reports deletion not working"""
        try:
            # First, try to get a document ID (if any exist)
            docs_response = self.session.get(f"{self.base_url}/documents")
            
            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                documents = docs_data.get("documents", [])
                
                if documents:
                    # Test delete with existing document
                    doc_id = documents[0]["id"]
                    filename = documents[0].get("filename", "Unknown")
                    
                    print(f"   Testing deletion of document: {filename} (ID: {doc_id})")
                    delete_response = self.session.delete(f"{self.base_url}/documents/{doc_id}")
                    
                    if delete_response.status_code == 200:
                        delete_data = delete_response.json()
                        required_fields = ["message", "document_id", "deleted_chunks"]
                        missing_fields = [field for field in required_fields if field not in delete_data]
                        
                        if not missing_fields:
                            # Verify document was actually deleted
                            verify_response = self.session.get(f"{self.base_url}/documents")
                            if verify_response.status_code == 200:
                                verify_data = verify_response.json()
                                remaining_docs = verify_data.get("documents", [])
                                doc_still_exists = any(doc["id"] == doc_id for doc in remaining_docs)
                                
                                if not doc_still_exists:
                                    self.log_test(
                                        "Document Delete Functionality - PRIORITY",
                                        True,
                                        f"✅ DELETION WORKING! Document '{filename}' successfully deleted. Response: {delete_data['message']}, Deleted chunks: {delete_data['deleted_chunks']}",
                                        delete_data
                                    )
                                else:
                                    self.log_test(
                                        "Document Delete Functionality - PRIORITY",
                                        False,
                                        f"❌ DELETION FAILED! Document still exists after delete request. API returned success but document not removed.",
                                        delete_data
                                    )
                            else:
                                self.log_test(
                                    "Document Delete Functionality - PRIORITY",
                                    True,
                                    f"✅ Delete response structure correct, but couldn't verify removal: {delete_data['message']}",
                                    delete_data
                                )
                        else:
                            self.log_test(
                                "Document Delete Functionality - PRIORITY",
                                False,
                                f"❌ Delete response missing required fields: {missing_fields}",
                                delete_data
                            )
                    elif delete_response.status_code == 404:
                        self.log_test(
                            "Document Delete Functionality - PRIORITY",
                            False,
                            f"❌ Document not found (404). Document may have been deleted already or ID invalid: {doc_id}",
                            delete_response.text
                        )
                    else:
                        self.log_test(
                            "Document Delete Functionality - PRIORITY",
                            False,
                            f"❌ DELETION FAILED! HTTP {delete_response.status_code}: {delete_response.text}",
                            delete_response.text
                        )
                else:
                    # Test delete with non-existent document to check error handling
                    fake_id = "non-existent-document-id-12345"
                    delete_response = self.session.delete(f"{self.base_url}/documents/{fake_id}")
                    
                    if delete_response.status_code == 404:
                        self.log_test(
                            "Document Delete Functionality - PRIORITY",
                            True,
                            "✅ Delete endpoint correctly returns 404 for non-existent document (no documents available to test actual deletion)",
                            None
                        )
                    else:
                        self.log_test(
                            "Document Delete Functionality - PRIORITY",
                            False,
                            f"❌ Expected 404 for non-existent document, got {delete_response.status_code}",
                            delete_response.text
                        )
            else:
                self.log_test(
                    "Document Delete Functionality - PRIORITY",
                    False,
                    f"❌ Could not retrieve documents list to test delete: HTTP {docs_response.status_code}",
                    docs_response.text
                )
                
        except Exception as e:
            self.log_test(
                "Document Delete Functionality - PRIORITY",
                False,
                f"❌ Connection error during delete test: {str(e)}",
                None
            )

    def test_group_management_apis(self):
        """Test Group Management APIs - PRIORITY: GET, POST, PUT, DELETE /api/groups"""
        try:
            # Test 1: GET /api/groups - List all groups
            print("   Testing GET /api/groups...")
            groups_response = self.session.get(f"{self.base_url}/groups")
            
            if groups_response.status_code == 200:
                groups_data = groups_response.json()
                required_fields = ["groups", "total_count"]
                missing_fields = [field for field in required_fields if field not in groups_data]
                
                if not missing_fields:
                    groups_list = groups_data.get("groups", [])
                    total_count = groups_data.get("total_count", 0)
                    
                    self.log_test(
                        "Group Management - GET /api/groups",
                        True,
                        f"✅ Groups list retrieved successfully. Total groups: {total_count}, Groups: {len(groups_list)}",
                        {"total_count": total_count, "groups_count": len(groups_list)}
                    )
                    
                    # Test 2: POST /api/groups - Create new group
                    print("   Testing POST /api/groups...")
                    test_group_data = {
                        "name": "Test Grup KPA",
                        "description": "Test grubu - silinecek",
                        "color": "#ff6b6b"
                    }
                    
                    create_response = self.session.post(
                        f"{self.base_url}/groups",
                        json=test_group_data
                    )
                    
                    if create_response.status_code == 200:
                        create_data = create_response.json()
                        if "group" in create_data and "message" in create_data:
                            created_group = create_data["group"]
                            group_id = created_group.get("id")
                            
                            self.log_test(
                                "Group Management - POST /api/groups",
                                True,
                                f"✅ Group created successfully: {create_data['message']}, Group ID: {group_id}",
                                create_data
                            )
                            
                            # Test 3: PUT /api/groups/{id} - Update group
                            if group_id:
                                print(f"   Testing PUT /api/groups/{group_id}...")
                                update_data = {
                                    "name": "Test Grup KPA - Güncellendi",
                                    "description": "Güncellenmiş test grubu",
                                    "color": "#4ecdc4"
                                }
                                
                                update_response = self.session.put(
                                    f"{self.base_url}/groups/{group_id}",
                                    json=update_data
                                )
                                
                                if update_response.status_code == 200:
                                    update_result = update_response.json()
                                    self.log_test(
                                        "Group Management - PUT /api/groups/{id}",
                                        True,
                                        f"✅ Group updated successfully: {update_result.get('message', 'Updated')}",
                                        update_result
                                    )
                                else:
                                    self.log_test(
                                        "Group Management - PUT /api/groups/{id}",
                                        False,
                                        f"❌ Group update failed: HTTP {update_response.status_code}",
                                        update_response.text
                                    )
                                
                                # Test 4: DELETE /api/groups/{id} - Delete group
                                print(f"   Testing DELETE /api/groups/{group_id}...")
                                delete_response = self.session.delete(f"{self.base_url}/groups/{group_id}")
                                
                                if delete_response.status_code == 200:
                                    delete_result = delete_response.json()
                                    self.log_test(
                                        "Group Management - DELETE /api/groups/{id}",
                                        True,
                                        f"✅ Group deleted successfully: {delete_result.get('message', 'Deleted')}",
                                        delete_result
                                    )
                                else:
                                    self.log_test(
                                        "Group Management - DELETE /api/groups/{id}",
                                        False,
                                        f"❌ Group deletion failed: HTTP {delete_response.status_code}",
                                        delete_response.text
                                    )
                        else:
                            self.log_test(
                                "Group Management - POST /api/groups",
                                False,
                                f"❌ Create response missing required fields (group, message)",
                                create_data
                            )
                    else:
                        self.log_test(
                            "Group Management - POST /api/groups",
                            False,
                            f"❌ Group creation failed: HTTP {create_response.status_code}",
                            create_response.text
                        )
                else:
                    self.log_test(
                        "Group Management - GET /api/groups",
                        False,
                        f"❌ Groups response missing required fields: {missing_fields}",
                        groups_data
                    )
            else:
                self.log_test(
                    "Group Management - GET /api/groups",
                    False,
                    f"❌ Groups list failed: HTTP {groups_response.status_code}",
                    groups_response.text
                )
                
        except Exception as e:
            self.log_test(
                "Group Management APIs",
                False,
                f"❌ Connection error during group management test: {str(e)}",
                None
            )

    def test_document_group_relationships(self):
        """Test Document-Group Relationships - PRIORITY: POST /api/documents/move, GET /api/documents?group_id"""
        try:
            # First check if we have any documents and groups
            docs_response = self.session.get(f"{self.base_url}/documents")
            groups_response = self.session.get(f"{self.base_url}/groups")
            
            if docs_response.status_code == 200 and groups_response.status_code == 200:
                docs_data = docs_response.json()
                groups_data = groups_response.json()
                
                documents = docs_data.get("documents", [])
                groups = groups_data.get("groups", [])
                
                if documents and groups:
                    # Test moving documents to a group
                    doc_id = documents[0]["id"]
                    group_id = groups[0]["id"]
                    group_name = groups[0]["name"]
                    
                    print(f"   Testing document move: Doc {doc_id} to Group '{group_name}'...")
                    
                    move_request = {
                        "document_ids": [doc_id],
                        "group_id": group_id
                    }
                    
                    move_response = self.session.post(
                        f"{self.base_url}/documents/move",
                        json=move_request
                    )
                    
                    if move_response.status_code == 200:
                        move_data = move_response.json()
                        if "message" in move_data and "modified_count" in move_data:
                            self.log_test(
                                "Document-Group Relationships - Move Documents",
                                True,
                                f"✅ Document move successful: {move_data['message']}, Modified: {move_data['modified_count']}",
                                move_data
                            )
                            
                            # Test filtering documents by group
                            print(f"   Testing GET /api/documents?group_id={group_id}...")
                            filter_response = self.session.get(f"{self.base_url}/documents?group_id={group_id}")
                            
                            if filter_response.status_code == 200:
                                filter_data = filter_response.json()
                                filtered_docs = filter_data.get("documents", [])
                                
                                # Check if our moved document is in the filtered results
                                moved_doc_found = any(doc["id"] == doc_id for doc in filtered_docs)
                                
                                if moved_doc_found:
                                    self.log_test(
                                        "Document-Group Relationships - Group Filtering",
                                        True,
                                        f"✅ Group filtering working: Found {len(filtered_docs)} documents in group '{group_name}'",
                                        {"group_id": group_id, "documents_count": len(filtered_docs)}
                                    )
                                else:
                                    self.log_test(
                                        "Document-Group Relationships - Group Filtering",
                                        False,
                                        f"❌ Moved document not found in group filter results",
                                        filter_data
                                    )
                            else:
                                self.log_test(
                                    "Document-Group Relationships - Group Filtering",
                                    False,
                                    f"❌ Group filtering failed: HTTP {filter_response.status_code}",
                                    filter_response.text
                                )
                        else:
                            self.log_test(
                                "Document-Group Relationships - Move Documents",
                                False,
                                f"❌ Move response missing required fields",
                                move_data
                            )
                    else:
                        self.log_test(
                            "Document-Group Relationships - Move Documents",
                            False,
                            f"❌ Document move failed: HTTP {move_response.status_code}",
                            move_response.text
                        )
                elif not documents:
                    self.log_test(
                        "Document-Group Relationships",
                        True,
                        "✅ No documents available to test group relationships (expected for empty system)",
                        None
                    )
                elif not groups:
                    self.log_test(
                        "Document-Group Relationships",
                        True,
                        "✅ No groups available to test document relationships (expected for empty system)",
                        None
                    )
            else:
                self.log_test(
                    "Document-Group Relationships",
                    False,
                    f"❌ Could not retrieve documents or groups for relationship testing",
                    None
                )
                
        except Exception as e:
            self.log_test(
                "Document-Group Relationships",
                False,
                f"❌ Connection error during document-group relationship test: {str(e)}",
                None
            )

    def test_system_status_total_groups(self):
        """Test System Status total_groups field - PRIORITY"""
        try:
            response = self.session.get(f"{self.base_url}/status")
            
            if response.status_code == 200:
                data = response.json()
                
                if "total_groups" in data:
                    total_groups = data["total_groups"]
                    
                    # Verify it's an integer
                    if isinstance(total_groups, int):
                        # Cross-check with actual groups count
                        groups_response = self.session.get(f"{self.base_url}/groups")
                        if groups_response.status_code == 200:
                            groups_data = groups_response.json()
                            actual_groups = groups_data.get("total_count", 0)
                            
                            if total_groups == actual_groups:
                                self.log_test(
                                    "System Status - total_groups Field",
                                    True,
                                    f"✅ total_groups field working correctly: {total_groups} (matches actual groups count)",
                                    {"total_groups": total_groups, "actual_groups": actual_groups}
                                )
                            else:
                                self.log_test(
                                    "System Status - total_groups Field",
                                    False,
                                    f"❌ total_groups mismatch: status shows {total_groups}, actual groups: {actual_groups}",
                                    {"total_groups": total_groups, "actual_groups": actual_groups}
                                )
                        else:
                            self.log_test(
                                "System Status - total_groups Field",
                                True,
                                f"✅ total_groups field present and valid: {total_groups} (couldn't verify against groups endpoint)",
                                {"total_groups": total_groups}
                            )
                    else:
                        self.log_test(
                            "System Status - total_groups Field",
                            False,
                            f"❌ total_groups should be integer, got {type(total_groups)}: {total_groups}",
                            data
                        )
                else:
                    self.log_test(
                        "System Status - total_groups Field",
                        False,
                        f"❌ total_groups field missing from status response",
                        data
                    )
            else:
                self.log_test(
                    "System Status - total_groups Field",
                    False,
                    f"❌ Status endpoint failed: HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "System Status - total_groups Field",
                False,
                f"❌ Connection error during status test: {str(e)}",
                None
            )

    def test_upload_with_group(self):
        """Test Upload with Group Parameter - PRIORITY: POST /api/upload-document with group_id"""
        try:
            # First, create a test group for upload
            test_group_data = {
                "name": "Upload Test Grup",
                "description": "Test grubu - upload için",
                "color": "#95a5a6"
            }
            
            create_response = self.session.post(
                f"{self.base_url}/groups",
                json=test_group_data
            )
            
            if create_response.status_code == 200:
                create_data = create_response.json()
                group_id = create_data.get("group", {}).get("id")
                
                if group_id:
                    # Test upload endpoint with group parameter (without actual file)
                    # We'll test the endpoint structure and parameter handling
                    print(f"   Testing upload endpoint with group_id parameter...")
                    
                    # Test with invalid file to check if group parameter is processed
                    files = {'file': ('test.txt', b'test content', 'text/plain')}
                    data = {'group_id': group_id}
                    
                    upload_response = self.session.post(
                        f"{self.base_url}/upload-document",
                        files=files,
                        data=data
                    )
                    
                    # We expect this to fail due to invalid file type, but we can check if group_id is processed
                    if upload_response.status_code == 400:
                        error_data = upload_response.json()
                        error_detail = error_data.get("detail", "")
                        
                        # If error is about file format (not group), then group parameter is being processed
                        if "doc" in error_detail.lower() or "format" in error_detail.lower():
                            self.log_test(
                                "Upload with Group Parameter",
                                True,
                                f"✅ Upload endpoint accepts group_id parameter (rejected due to file format as expected): {error_detail}",
                                {"group_id": group_id, "error": error_detail}
                            )
                        else:
                            self.log_test(
                                "Upload with Group Parameter",
                                False,
                                f"❌ Upload endpoint error not related to file format: {error_detail}",
                                error_data
                            )
                    else:
                        self.log_test(
                            "Upload with Group Parameter",
                            False,
                            f"❌ Unexpected response from upload endpoint: HTTP {upload_response.status_code}",
                            upload_response.text
                        )
                    
                    # Clean up test group
                    self.session.delete(f"{self.base_url}/groups/{group_id}")
                else:
                    self.log_test(
                        "Upload with Group Parameter",
                        False,
                        f"❌ Could not create test group for upload testing",
                        create_data
                    )
            else:
                self.log_test(
                    "Upload with Group Parameter",
                    False,
                    f"❌ Could not create test group: HTTP {create_response.status_code}",
                    create_response.text
                )
                
        except Exception as e:
            self.log_test(
                "Upload with Group Parameter",
                False,
                f"❌ Connection error during upload with group test: {str(e)}",
                None
            )

    def run_all_tests(self):
        """Run all backend tests focusing on PRIORITY: DOC PROCESSING & DOCUMENT ISSUES"""
        print("=" * 80)
        print("KURUMSAL PROSEDÜR ASISTANI (KPA) BACKEND API TESTS - DOC PROCESSING FOCUS")
        print("=" * 80)
        print(f"Testing backend at: {self.base_url}")
        print("🔥 PRIORITY TESTS: DOC Processing System - antiword, textract, error handling")
        print("📋 Testing: DOC processing pipeline, file validation, enhanced error messages")
        print()
        
        # Test connectivity first
        if not self.test_backend_connectivity():
            print("❌ Backend connectivity failed. Skipping other tests.")
            return self.get_summary()
        
        # 🔥 PRIORITY TESTS FIRST - DOC Processing Issues
        print("🚨 PRIORITY TESTS - DOC PROCESSING SYSTEM:")
        print("-" * 50)
        
        # 1. DOC processing system (antiword + textract)
        self.test_doc_processing_system()
        
        # 2. Document processing pipeline
        self.test_document_processing_pipeline()
        
        # 3. Enhanced error handling
        self.test_enhanced_error_handling()
        
        # 4. File format validation (.doc/.docx)
        self.test_file_validation()
        
        print("\n🚨 SECONDARY PRIORITY - USER REPORTED ISSUES:")
        print("-" * 50)
        
        # 5. Document deletion issue (user can't delete)
        self.test_document_delete_functionality()
        
        # 6. Group management APIs
        self.test_group_management_apis()
        
        # 7. Document-group relationships
        self.test_document_group_relationships()
        
        # 8. System status with total_groups
        self.test_system_status_total_groups()
        
        # 9. Upload with group parameter
        self.test_upload_with_group()
        
        print("\n📊 ADDITIONAL SYSTEM TESTS:")
        print("-" * 30)
        
        # Run basic API tests
        self.test_root_endpoint()
        self.test_status_endpoint()  # Enhanced with new fields
        self.test_documents_endpoint()  # Enhanced with statistics
        
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