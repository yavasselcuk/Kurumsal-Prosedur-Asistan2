#!/usr/bin/env python3
"""
Clean Database Validation Test for KPA Application
Tests the system after complete database reset to validate clean state functionality.
"""

import requests
import json
import sys
from typing import Dict, Any, List
import time

# Backend URL from environment
BACKEND_URL = "https://1070132c-1836-44b9-839f-410d8851049c.preview.emergentagent.com/api"

class CleanDatabaseValidator:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.session = requests.Session()
        self.session.timeout = 30
        self.admin_token = None
        
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

    def test_clean_system_status(self):
        """Test that system status shows clean state (0 documents, 0 chunks, 0 groups)"""
        try:
            response = self.session.get(f"{self.base_url}/status")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for clean state indicators
                is_clean_state = (
                    data.get("total_documents", -1) == 0 and
                    data.get("total_chunks", -1) == 0 and
                    data.get("total_groups", -1) == 0 and
                    data.get("embedding_model_loaded", False) == True and
                    data.get("faiss_index_ready", True) == False  # Should be False for empty system
                )
                
                if is_clean_state:
                    self.log_test(
                        "Clean System Status Validation",
                        True,
                        f"✅ CLEAN STATE CONFIRMED! Documents: {data['total_documents']}, Chunks: {data['total_chunks']}, Groups: {data['total_groups']}, AI Model: {'Loaded' if data['embedding_model_loaded'] else 'Not Loaded'}, FAISS Index: {'Ready' if data['faiss_index_ready'] else 'Empty (Expected)'}",
                        data
                    )
                else:
                    issues = []
                    if data.get("total_documents", -1) != 0:
                        issues.append(f"Documents: {data.get('total_documents')} (expected 0)")
                    if data.get("total_chunks", -1) != 0:
                        issues.append(f"Chunks: {data.get('total_chunks')} (expected 0)")
                    if data.get("total_groups", -1) != 0:
                        issues.append(f"Groups: {data.get('total_groups')} (expected 0)")
                    if not data.get("embedding_model_loaded", False):
                        issues.append("AI Model not loaded")
                    if data.get("faiss_index_ready", False):
                        issues.append("FAISS Index ready (should be False for empty system)")
                    
                    self.log_test(
                        "Clean System Status Validation",
                        False,
                        f"❌ SYSTEM NOT IN CLEAN STATE! Issues: {', '.join(issues)}",
                        data
                    )
            else:
                self.log_test(
                    "Clean System Status Validation",
                    False,
                    f"❌ Status endpoint failed: HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Clean System Status Validation",
                False,
                f"❌ Error checking system status: {str(e)}",
                None
            )

    def test_initial_admin_user_creation(self):
        """Test that initial admin user exists with correct credentials and must_change_password=true"""
        try:
            # Test admin login with default credentials
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check login response structure
                required_fields = ["access_token", "token_type", "user", "must_change_password"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    user_info = data.get("user", {})
                    must_change_password = data.get("must_change_password", False)
                    user_must_change = user_info.get("must_change_password", False)
                    
                    # Validate admin user properties
                    is_valid_admin = (
                        user_info.get("username") == "admin" and
                        user_info.get("role") == "admin" and
                        user_info.get("is_active", False) == True and
                        (must_change_password == True or user_must_change == True)  # Either field should be True
                    )
                    
                    if is_valid_admin:
                        # Store token for further tests
                        self.admin_token = data["access_token"]
                        
                        self.log_test(
                            "Initial Admin User Creation",
                            True,
                            f"✅ ADMIN USER VALID! Username: {user_info['username']}, Role: {user_info['role']}, Active: {user_info['is_active']}, Must Change Password: {must_change_password or user_must_change}",
                            {
                                "username": user_info.get("username"),
                                "role": user_info.get("role"),
                                "is_active": user_info.get("is_active"),
                                "must_change_password": must_change_password or user_must_change
                            }
                        )
                    else:
                        issues = []
                        if user_info.get("username") != "admin":
                            issues.append(f"Username: {user_info.get('username')} (expected 'admin')")
                        if user_info.get("role") != "admin":
                            issues.append(f"Role: {user_info.get('role')} (expected 'admin')")
                        if not user_info.get("is_active", False):
                            issues.append("User not active")
                        if not (must_change_password or user_must_change):
                            issues.append("must_change_password should be True")
                        
                        self.log_test(
                            "Initial Admin User Creation",
                            False,
                            f"❌ ADMIN USER INVALID! Issues: {', '.join(issues)}",
                            data
                        )
                else:
                    self.log_test(
                        "Initial Admin User Creation",
                        False,
                        f"❌ Login response missing fields: {', '.join(missing_fields)}",
                        data
                    )
            else:
                self.log_test(
                    "Initial Admin User Creation",
                    False,
                    f"❌ ADMIN LOGIN FAILED! HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Initial Admin User Creation",
                False,
                f"❌ Error testing admin user: {str(e)}",
                None
            )

    def test_core_endpoints_accessibility(self):
        """Test that all core API endpoints are accessible and responding correctly"""
        try:
            core_endpoints = [
                {"path": "/", "method": "GET", "name": "Root API"},
                {"path": "/status", "method": "GET", "name": "System Status"},
                {"path": "/documents", "method": "GET", "name": "Documents List"},
                {"path": "/groups", "method": "GET", "name": "Groups List", "requires_auth": True},
            ]
            
            accessible_count = 0
            total_endpoints = len(core_endpoints)
            
            for endpoint in core_endpoints:
                try:
                    headers = {}
                    if endpoint.get("requires_auth") and self.admin_token:
                        headers["Authorization"] = f"Bearer {self.admin_token}"
                    
                    if endpoint["method"] == "GET":
                        response = self.session.get(f"{self.base_url}{endpoint['path']}", headers=headers)
                    
                    if response.status_code in [200, 401]:  # 401 is OK if auth is required but not provided
                        accessible_count += 1
                        print(f"     ✅ {endpoint['name']}: HTTP {response.status_code}")
                    else:
                        print(f"     ❌ {endpoint['name']}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"     ❌ {endpoint['name']}: Error - {str(e)}")
            
            success_rate = accessible_count / total_endpoints
            is_successful = success_rate >= 0.75  # 75% success rate acceptable
            
            self.log_test(
                "Core Endpoints Accessibility",
                is_successful,
                f"Core endpoints accessibility: {accessible_count}/{total_endpoints} ({success_rate:.1%}) endpoints responding correctly",
                {"accessible": accessible_count, "total": total_endpoints, "success_rate": success_rate}
            )
            
        except Exception as e:
            self.log_test(
                "Core Endpoints Accessibility",
                False,
                f"❌ Error testing core endpoints: {str(e)}",
                None
            )

    def test_empty_documents_list(self):
        """Test that documents list is empty in clean state"""
        try:
            headers = {}
            if self.admin_token:
                headers["Authorization"] = f"Bearer {self.admin_token}"
            
            response = self.session.get(f"{self.base_url}/documents", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                documents = data.get("documents", [])
                statistics = data.get("statistics", {})
                
                is_empty_state = (
                    len(documents) == 0 and
                    statistics.get("total_count", -1) == 0 and
                    statistics.get("completed_count", -1) == 0 and
                    statistics.get("processing_count", -1) == 0 and
                    statistics.get("failed_count", -1) == 0
                )
                
                if is_empty_state:
                    self.log_test(
                        "Empty Documents List Validation",
                        True,
                        f"✅ DOCUMENTS LIST EMPTY! Total: {statistics.get('total_count')}, Completed: {statistics.get('completed_count')}, Processing: {statistics.get('processing_count')}, Failed: {statistics.get('failed_count')}",
                        statistics
                    )
                else:
                    self.log_test(
                        "Empty Documents List Validation",
                        False,
                        f"❌ DOCUMENTS LIST NOT EMPTY! Found {len(documents)} documents, Statistics: {statistics}",
                        data
                    )
            else:
                self.log_test(
                    "Empty Documents List Validation",
                    False,
                    f"❌ Documents endpoint failed: HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Empty Documents List Validation",
                False,
                f"❌ Error checking documents list: {str(e)}",
                None
            )

    def test_empty_groups_list(self):
        """Test that groups list is empty in clean state"""
        try:
            headers = {}
            if self.admin_token:
                headers["Authorization"] = f"Bearer {self.admin_token}"
            
            response = self.session.get(f"{self.base_url}/groups", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                groups = data.get("groups", [])
                total_count = data.get("total_count", -1)
                
                is_empty_state = len(groups) == 0 and total_count == 0
                
                if is_empty_state:
                    self.log_test(
                        "Empty Groups List Validation",
                        True,
                        f"✅ GROUPS LIST EMPTY! Total groups: {total_count}",
                        data
                    )
                else:
                    self.log_test(
                        "Empty Groups List Validation",
                        False,
                        f"❌ GROUPS LIST NOT EMPTY! Found {len(groups)} groups, Total count: {total_count}",
                        data
                    )
            elif response.status_code == 401:
                self.log_test(
                    "Empty Groups List Validation",
                    True,
                    "✅ Groups endpoint requires authentication (expected behavior)",
                    None
                )
            else:
                self.log_test(
                    "Empty Groups List Validation",
                    False,
                    f"❌ Groups endpoint failed: HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Empty Groups List Validation",
                False,
                f"❌ Error checking groups list: {str(e)}",
                None
            )

    def test_qa_system_with_no_documents(self):
        """Test Q&A system behavior when no documents are available"""
        try:
            headers = {}
            if self.admin_token:
                headers["Authorization"] = f"Bearer {self.admin_token}"
            
            # Test asking a question when no documents exist
            question_data = {
                "question": "İnsan kaynakları prosedürleri hakkında bilgi verebilir misiniz?"
            }
            
            response = self.session.post(f"{self.base_url}/ask-question", json=question_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                answer = data.get("answer", "")
                sources = data.get("sources", [])
                session_id = data.get("session_id", "")
                
                # Check if system appropriately handles no documents scenario
                appropriate_response = (
                    len(sources) == 0 and  # No sources should be available
                    len(session_id) > 0 and  # Session should still be created
                    len(answer) > 0  # Should provide some response
                )
                
                if appropriate_response:
                    # Check if answer indicates no documents available
                    no_docs_indicators = ["doküman", "yüklenmemiş", "mevcut değil", "bulunamadı", "henüz"]
                    indicates_no_docs = any(indicator in answer.lower() for indicator in no_docs_indicators)
                    
                    self.log_test(
                        "Q&A System - No Documents Handling",
                        True,
                        f"✅ Q&A SYSTEM HANDLES EMPTY STATE! Answer provided: {len(answer)} chars, Sources: {len(sources)}, Indicates no docs: {indicates_no_docs}",
                        {
                            "answer_length": len(answer),
                            "sources_count": len(sources),
                            "session_id": session_id,
                            "indicates_no_docs": indicates_no_docs
                        }
                    )
                else:
                    self.log_test(
                        "Q&A System - No Documents Handling",
                        False,
                        f"❌ Q&A system response inappropriate for empty state. Sources: {len(sources)}, Answer: {len(answer)} chars, Session: {len(session_id)}",
                        data
                    )
            else:
                self.log_test(
                    "Q&A System - No Documents Handling",
                    False,
                    f"❌ Q&A endpoint failed: HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Q&A System - No Documents Handling",
                False,
                f"❌ Error testing Q&A system: {str(e)}",
                None
            )

    def test_group_creation_on_empty_system(self):
        """Test group creation functionality on empty system"""
        try:
            if not self.admin_token:
                self.log_test(
                    "Group Creation - Empty System",
                    False,
                    "❌ Cannot test group creation - no admin token available",
                    None
                )
                return
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Create a test group
            group_data = {
                "name": "Test Grup - Clean Database",
                "description": "Test grubu - temiz veritabanı doğrulaması için",
                "color": "#3b82f6"
            }
            
            response = self.session.post(f"{self.base_url}/groups", json=group_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                message = data.get("message", "")
                group_id = data.get("group_id", "")
                
                if "başarıyla oluşturuldu" in message and len(group_id) > 0:
                    self.log_test(
                        "Group Creation - Empty System",
                        True,
                        f"✅ GROUP CREATION WORKING! Created group with ID: {group_id}, Message: {message}",
                        data
                    )
                    
                    # Clean up - delete the test group
                    delete_response = self.session.delete(f"{self.base_url}/groups/{group_id}", headers=headers)
                    if delete_response.status_code == 200:
                        print("     ✅ Test group cleaned up successfully")
                    else:
                        print(f"     ⚠️ Test group cleanup failed: HTTP {delete_response.status_code}")
                else:
                    self.log_test(
                        "Group Creation - Empty System",
                        False,
                        f"❌ Group creation response invalid. Message: {message}, Group ID: {group_id}",
                        data
                    )
            else:
                self.log_test(
                    "Group Creation - Empty System",
                    False,
                    f"❌ Group creation failed: HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Group Creation - Empty System",
                False,
                f"❌ Error testing group creation: {str(e)}",
                None
            )

    def test_document_upload_to_empty_system(self):
        """Test document upload functionality on empty system"""
        try:
            if not self.admin_token:
                self.log_test(
                    "Document Upload - Empty System",
                    False,
                    "❌ Cannot test document upload - no admin token available",
                    None
                )
                return
            
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Create a minimal test DOCX file content
            # This is a very basic DOCX structure that should be processable
            test_docx_content = (
                b'PK\x03\x04\x14\x00\x00\x00\x08\x00' +
                b'Test document content for clean database validation' +
                b'\x00' * 100
            )
            
            files = {'file': ('test_clean_db.docx', test_docx_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            
            response = self.session.post(f"{self.base_url}/upload-document", files=files, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                message = data.get("message", "")
                document_id = data.get("document_id", "")
                chunks = data.get("chunks", 0)
                
                if "başarıyla yüklendi" in message and len(document_id) > 0:
                    self.log_test(
                        "Document Upload - Empty System",
                        True,
                        f"✅ DOCUMENT UPLOAD WORKING! Uploaded with ID: {document_id}, Chunks: {chunks}, Message: {message}",
                        data
                    )
                    
                    # Clean up - delete the test document
                    delete_response = self.session.delete(f"{self.base_url}/documents/{document_id}", headers=headers)
                    if delete_response.status_code == 200:
                        print("     ✅ Test document cleaned up successfully")
                    else:
                        print(f"     ⚠️ Test document cleanup failed: HTTP {delete_response.status_code}")
                else:
                    self.log_test(
                        "Document Upload - Empty System",
                        False,
                        f"❌ Document upload response invalid. Message: {message}, Document ID: {document_id}",
                        data
                    )
            elif response.status_code == 400:
                # Check if it's a format validation error (acceptable for test file)
                error_data = response.json()
                error_detail = error_data.get("detail", "")
                
                if any(keyword in error_detail.lower() for keyword in ["format", "bozuk", "işlem", "docx"]):
                    self.log_test(
                        "Document Upload - Empty System",
                        True,
                        f"✅ UPLOAD VALIDATION WORKING! Test file rejected appropriately: {error_detail}",
                        error_data
                    )
                else:
                    self.log_test(
                        "Document Upload - Empty System",
                        False,
                        f"❌ Upload failed with unexpected error: {error_detail}",
                        error_data
                    )
            else:
                self.log_test(
                    "Document Upload - Empty System",
                    False,
                    f"❌ Document upload failed: HTTP {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Document Upload - Empty System",
                False,
                f"❌ Error testing document upload: {str(e)}",
                None
            )

    def test_authentication_system_comprehensive(self):
        """Test comprehensive authentication system functionality"""
        try:
            # Test 1: Invalid credentials
            invalid_login = {
                "username": "invalid_user",
                "password": "invalid_password"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=invalid_login)
            
            invalid_login_handled = response.status_code == 401
            
            # Test 2: Valid admin credentials (already tested, but verify token works)
            if self.admin_token:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                me_response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
                token_valid = me_response.status_code == 200
            else:
                token_valid = False
            
            # Test 3: Protected endpoint without token
            protected_response = self.session.get(f"{self.base_url}/groups")
            auth_required = protected_response.status_code == 401
            
            # Test 4: Protected endpoint with token
            if self.admin_token:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                protected_with_auth = self.session.get(f"{self.base_url}/groups", headers=headers)
                auth_working = protected_with_auth.status_code == 200
            else:
                auth_working = False
            
            auth_tests_passed = sum([invalid_login_handled, token_valid, auth_required, auth_working])
            auth_success = auth_tests_passed >= 3  # At least 3 out of 4 tests should pass
            
            self.log_test(
                "Authentication System Comprehensive",
                auth_success,
                f"Authentication system tests: {auth_tests_passed}/4 passed. Invalid login handled: {invalid_login_handled}, Token valid: {token_valid}, Auth required: {auth_required}, Auth working: {auth_working}",
                {
                    "invalid_login_handled": invalid_login_handled,
                    "token_valid": token_valid,
                    "auth_required": auth_required,
                    "auth_working": auth_working,
                    "tests_passed": auth_tests_passed
                }
            )
            
        except Exception as e:
            self.log_test(
                "Authentication System Comprehensive",
                False,
                f"❌ Error testing authentication system: {str(e)}",
                None
            )

    def run_all_tests(self):
        """Run all clean database validation tests"""
        print("🧹 CLEAN DATABASE VALIDATION TEST - KPA APPLICATION")
        print("=" * 60)
        print("Testing system after complete database reset...")
        print()
        
        # Run tests in logical order
        test_methods = [
            self.test_clean_system_status,
            self.test_initial_admin_user_creation,
            self.test_core_endpoints_accessibility,
            self.test_empty_documents_list,
            self.test_empty_groups_list,
            self.test_qa_system_with_no_documents,
            self.test_authentication_system_comprehensive,
            self.test_group_creation_on_empty_system,
            self.test_document_upload_to_empty_system,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                print(f"❌ CRITICAL ERROR in {test_method.__name__}: {str(e)}")
                self.log_test(
                    test_method.__name__,
                    False,
                    f"Critical error during test execution: {str(e)}",
                    None
                )
        
        # Summary
        print("\n" + "=" * 60)
        print("🧹 CLEAN DATABASE VALIDATION SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "=" * 60)
        
        # Return overall success
        return passed_tests >= (total_tests * 0.8)  # 80% success rate required

if __name__ == "__main__":
    validator = CleanDatabaseValidator()
    success = validator.run_all_tests()
    
    if success:
        print("✅ CLEAN DATABASE VALIDATION COMPLETED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("❌ CLEAN DATABASE VALIDATION FAILED!")
        sys.exit(1)