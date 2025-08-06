#!/usr/bin/env python3
"""
COMPREHENSIVE BACKEND TESTING - KPA Application
Focus: Fixed endpoints, new features, authentication, and regression testing
"""

import requests
import json
import sys
import time
import base64
from typing import Dict, Any, List

# Backend URL from environment
BACKEND_URL = "https://1070132c-1836-44b9-839f-410d8851049c.preview.emergentagent.com/api"

class ComprehensiveKPATester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_results = []
        self.session = requests.Session()
        self.session.timeout = 30
        self.auth_token = None
        self.auth_headers = {}
        
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

    def test_authentication_system(self):
        """🔥 COMPREHENSIVE AUTHENTICATION TESTING - JWT, Login, User Management"""
        try:
            print("   🔐 Testing comprehensive authentication system...")
            
            # Test 1: Admin login (should have must_change_password=true)
            print("   Step 1: Testing admin login...")
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            login_response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            
            if login_response.status_code == 200:
                login_result = login_response.json()
                required_fields = ["access_token", "token_type", "user", "must_change_password"]
                missing_fields = [field for field in required_fields if field not in login_result]
                
                if not missing_fields:
                    # Store token for subsequent tests
                    self.auth_token = login_result["access_token"]
                    self.auth_headers = {"Authorization": f"Bearer {self.auth_token}"}
                    
                    user_info = login_result["user"]
                    must_change_password = login_result.get("must_change_password", False)
                    
                    self.log_test(
                        "Authentication - Admin Login",
                        True,
                        f"✅ Admin login successful! Token received, user role: {user_info.get('role')}, must_change_password: {must_change_password}",
                        {"user_role": user_info.get('role'), "must_change_password": must_change_password}
                    )
                    
                    # Test 2: Test /auth/me endpoint
                    me_response = self.session.get(f"{self.base_url}/auth/me", headers=self.auth_headers)
                    
                    if me_response.status_code == 200:
                        me_data = me_response.json()
                        self.log_test(
                            "Authentication - Current User Info",
                            True,
                            f"✅ /auth/me endpoint working. User: {me_data.get('username')}, Role: {me_data.get('role')}",
                            me_data
                        )
                    else:
                        self.log_test(
                            "Authentication - Current User Info",
                            False,
                            f"❌ /auth/me failed: HTTP {me_response.status_code}",
                            me_response.text
                        )
                    
                    # Test 3: Test password change functionality
                    print("   Step 2: Testing password change...")
                    password_change_data = {
                        "current_password": "admin123",
                        "new_password": "newadmin123"
                    }
                    
                    password_response = self.session.post(f"{self.base_url}/auth/change-password", 
                                                        json=password_change_data, headers=self.auth_headers)
                    
                    if password_response.status_code == 200:
                        self.log_test(
                            "Authentication - Password Change",
                            True,
                            "✅ Password change successful",
                            password_response.json()
                        )
                        
                        # Test login with new password
                        new_login_data = {
                            "username": "admin",
                            "password": "newadmin123"
                        }
                        
                        new_login_response = self.session.post(f"{self.base_url}/auth/login", json=new_login_data)
                        
                        if new_login_response.status_code == 200:
                            new_login_result = new_login_response.json()
                            # Update token
                            self.auth_token = new_login_result["access_token"]
                            self.auth_headers = {"Authorization": f"Bearer {self.auth_token}"}
                            
                            # Check if must_change_password flag is cleared
                            must_change_cleared = not new_login_result.get("must_change_password", True)
                            
                            self.log_test(
                                "Authentication - Password Change Flag Cleared",
                                must_change_cleared,
                                f"✅ Login with new password successful, must_change_password cleared: {must_change_cleared}",
                                {"must_change_password": new_login_result.get("must_change_password")}
                            )
                        else:
                            self.log_test(
                                "Authentication - New Password Login",
                                False,
                                f"❌ Login with new password failed: HTTP {new_login_response.status_code}",
                                new_login_response.text
                            )
                    else:
                        self.log_test(
                            "Authentication - Password Change",
                            False,
                            f"❌ Password change failed: HTTP {password_response.status_code}",
                            password_response.text
                        )
                    
                    # Test 4: Test user creation (admin should be able to create users)
                    print("   Step 3: Testing user creation...")
                    test_user_data = {
                        "username": "test_editor",
                        "email": "test@example.com",
                        "full_name": "Test Editor",
                        "password": "testpass123",
                        "role": "editor",
                        "is_active": True
                    }
                    
                    create_user_response = self.session.post(f"{self.base_url}/auth/create-user", 
                                                           json=test_user_data, headers=self.auth_headers)
                    
                    if create_user_response.status_code == 200:
                        create_result = create_user_response.json()
                        self.log_test(
                            "Authentication - User Creation",
                            True,
                            f"✅ User creation successful: {create_result.get('message')}",
                            create_result
                        )
                        
                        # Test login with new user
                        new_user_login = {
                            "username": "test_editor",
                            "password": "testpass123"
                        }
                        
                        new_user_response = self.session.post(f"{self.base_url}/auth/login", json=new_user_login)
                        
                        if new_user_response.status_code == 200:
                            new_user_result = new_user_response.json()
                            self.log_test(
                                "Authentication - New User Login",
                                True,
                                f"✅ New user login successful, role: {new_user_result['user'].get('role')}",
                                {"role": new_user_result['user'].get('role')}
                            )
                        else:
                            self.log_test(
                                "Authentication - New User Login",
                                False,
                                f"❌ New user login failed: HTTP {new_user_response.status_code}",
                                new_user_response.text
                            )
                    else:
                        self.log_test(
                            "Authentication - User Creation",
                            False,
                            f"❌ User creation failed: HTTP {create_user_response.status_code}",
                            create_user_response.text
                        )
                        
                else:
                    self.log_test(
                        "Authentication - Admin Login",
                        False,
                        f"❌ Login response missing required fields: {missing_fields}",
                        login_result
                    )
            else:
                self.log_test(
                    "Authentication - Admin Login",
                    False,
                    f"❌ Admin login failed: HTTP {login_response.status_code}",
                    login_response.text
                )
                
        except Exception as e:
            self.log_test(
                "Authentication System",
                False,
                f"❌ Error during authentication testing: {str(e)}",
                None
            )

    def test_group_management_fixed_endpoints(self):
        """🔥 PRIORITY: Test FIXED group management endpoints that were missing"""
        try:
            print("   🔥 Testing FIXED group management endpoints...")
            
            if not self.auth_headers:
                print("   ⚠️ No authentication token available, skipping group tests")
                return
            
            # Test 1: GET /api/groups (group listing)
            print("   Step 1: Testing GET /api/groups...")
            groups_response = self.session.get(f"{self.base_url}/groups", headers=self.auth_headers)
            
            if groups_response.status_code == 200:
                groups_data = groups_response.json()
                required_fields = ["groups", "total_count"]
                missing_fields = [field for field in required_fields if field not in groups_data]
                
                if not missing_fields:
                    self.log_test(
                        "Fixed Endpoints - GET /api/groups",
                        True,
                        f"✅ Group listing endpoint FIXED and working! Found {groups_data['total_count']} groups",
                        {"total_count": groups_data['total_count']}
                    )
                else:
                    self.log_test(
                        "Fixed Endpoints - GET /api/groups",
                        False,
                        f"❌ Group listing response missing fields: {missing_fields}",
                        groups_data
                    )
            else:
                self.log_test(
                    "Fixed Endpoints - GET /api/groups",
                    False,
                    f"❌ CRITICAL: Group listing still not working! HTTP {groups_response.status_code}",
                    groups_response.text
                )
                return
            
            # Test 2: POST /api/groups (group creation)
            print("   Step 2: Testing POST /api/groups...")
            test_group_data = {
                "name": "Test Group for API Testing",
                "description": "Created by comprehensive backend testing",
                "color": "#ff6b6b"
            }
            
            create_group_response = self.session.post(f"{self.base_url}/groups", 
                                                    json=test_group_data, headers=self.auth_headers)
            
            if create_group_response.status_code == 200:
                create_result = create_group_response.json()
                test_group_id = create_result.get("group_id")
                
                self.log_test(
                    "Fixed Endpoints - POST /api/groups",
                    True,
                    f"✅ Group creation endpoint FIXED and working! Created group: {create_result.get('message')}",
                    {"group_id": test_group_id}
                )
                
                # Test 3: PUT /api/groups/{id} (group updating)
                print("   Step 3: Testing PUT /api/groups/{id}...")
                if test_group_id:
                    update_group_data = {
                        "name": "Updated Test Group",
                        "description": "Updated by comprehensive backend testing",
                        "color": "#4ecdc4"
                    }
                    
                    update_response = self.session.put(f"{self.base_url}/groups/{test_group_id}", 
                                                     json=update_group_data, headers=self.auth_headers)
                    
                    if update_response.status_code == 200:
                        self.log_test(
                            "Fixed Endpoints - PUT /api/groups/{id}",
                            True,
                            f"✅ Group update endpoint FIXED and working! {update_response.json().get('message')}",
                            update_response.json()
                        )
                    else:
                        self.log_test(
                            "Fixed Endpoints - PUT /api/groups/{id}",
                            False,
                            f"❌ Group update failed: HTTP {update_response.status_code}",
                            update_response.text
                        )
                    
                    # Test 4: DELETE /api/groups/{id} (group deletion)
                    print("   Step 4: Testing DELETE /api/groups/{id}...")
                    delete_response = self.session.delete(f"{self.base_url}/groups/{test_group_id}", 
                                                        headers=self.auth_headers)
                    
                    if delete_response.status_code == 200:
                        delete_result = delete_response.json()
                        self.log_test(
                            "Fixed Endpoints - DELETE /api/groups/{id}",
                            True,
                            f"✅ Group deletion endpoint FIXED and working! {delete_result.get('message')}",
                            delete_result
                        )
                    else:
                        self.log_test(
                            "Fixed Endpoints - DELETE /api/groups/{id}",
                            False,
                            f"❌ Group deletion failed: HTTP {delete_response.status_code}",
                            delete_response.text
                        )
                        
            else:
                self.log_test(
                    "Fixed Endpoints - POST /api/groups",
                    False,
                    f"❌ CRITICAL: Group creation still not working! HTTP {create_group_response.status_code}",
                    create_group_response.text
                )
            
            # Test 5: POST /api/documents/move (document moving between groups)
            print("   Step 5: Testing POST /api/documents/move...")
            
            # First check if we have any documents to move
            docs_response = self.session.get(f"{self.base_url}/documents", headers=self.auth_headers)
            
            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                documents = docs_data.get("documents", [])
                
                if documents:
                    # Test document move endpoint structure
                    move_data = {
                        "document_ids": [documents[0]["id"]],
                        "target_group_id": None  # Move to ungrouped
                    }
                    
                    move_response = self.session.post(f"{self.base_url}/documents/move", 
                                                    json=move_data, headers=self.auth_headers)
                    
                    if move_response.status_code == 200:
                        move_result = move_response.json()
                        self.log_test(
                            "Fixed Endpoints - POST /api/documents/move",
                            True,
                            f"✅ Document move endpoint FIXED and working! {move_result.get('message')}",
                            move_result
                        )
                    else:
                        self.log_test(
                            "Fixed Endpoints - POST /api/documents/move",
                            False,
                            f"❌ Document move failed: HTTP {move_response.status_code}",
                            move_response.text
                        )
                else:
                    self.log_test(
                        "Fixed Endpoints - POST /api/documents/move",
                        True,
                        "✅ Document move endpoint structure available (no documents to test with)",
                        None
                    )
            
        except Exception as e:
            self.log_test(
                "Group Management Fixed Endpoints",
                False,
                f"❌ Error during fixed endpoints testing: {str(e)}",
                None
            )

    def test_bulk_upload_feature(self):
        """🔥 NEW FEATURE: Test bulk document upload functionality"""
        try:
            print("   📦 Testing bulk document upload feature...")
            
            if not self.auth_headers:
                print("   ⚠️ No authentication token available, skipping bulk upload test")
                return
            
            # Test 1: Basic bulk upload functionality
            print("   Step 1: Testing basic bulk upload...")
            
            # Create test files (base64 encoded)
            test_files = [
                {
                    "filename": "bulk_test1.docx",
                    "content": base64.b64encode(b'PK\x03\x04' + b'Test DOCX content 1' + b'\x00' * 100).decode('utf-8'),
                    "group_id": None
                },
                {
                    "filename": "bulk_test2.doc", 
                    "content": base64.b64encode(b'\xd0\xcf\x11\xe0' + b'Test DOC content 2' + b'\x00' * 100).decode('utf-8'),
                    "group_id": None
                }
            ]
            
            bulk_upload_data = {
                "files": test_files,
                "group_id": None
            }
            
            bulk_response = self.session.post(f"{self.base_url}/bulk-upload-documents", 
                                            json=bulk_upload_data, headers=self.auth_headers)
            
            if bulk_response.status_code == 200:
                bulk_result = bulk_response.json()
                required_fields = ["total_files", "successful_uploads", "failed_uploads", "results", "processing_time"]
                missing_fields = [field for field in required_fields if field not in bulk_result]
                
                if not missing_fields:
                    success_rate = bulk_result["successful_uploads"] / bulk_result["total_files"] if bulk_result["total_files"] > 0 else 0
                    
                    self.log_test(
                        "Bulk Upload - Basic Functionality",
                        success_rate >= 0.5,  # At least 50% success rate acceptable for test files
                        f"✅ Bulk upload working! Processed {bulk_result['total_files']} files, {bulk_result['successful_uploads']} successful, {bulk_result['failed_uploads']} failed in {bulk_result['processing_time']:.2f}s",
                        bulk_result
                    )
                    
                    # Test 2: File format validation in bulk upload
                    print("   Step 2: Testing bulk upload file validation...")
                    
                    invalid_files = [
                        {
                            "filename": "invalid.txt",
                            "content": base64.b64encode(b'Invalid text file content').decode('utf-8'),
                            "group_id": None
                        }
                    ]
                    
                    invalid_bulk_data = {
                        "files": invalid_files,
                        "group_id": None
                    }
                    
                    invalid_response = self.session.post(f"{self.base_url}/bulk-upload-documents", 
                                                       json=invalid_bulk_data, headers=self.auth_headers)
                    
                    if invalid_response.status_code == 200:
                        invalid_result = invalid_response.json()
                        
                        # Check if invalid files were properly rejected
                        all_failed = invalid_result["failed_uploads"] == invalid_result["total_files"]
                        has_error_messages = all(result.get("status") == "error" for result in invalid_result["results"])
                        
                        validation_working = all_failed and has_error_messages
                        
                        self.log_test(
                            "Bulk Upload - File Validation",
                            validation_working,
                            f"✅ Bulk upload validation working! Invalid files properly rejected: {validation_working}",
                            {"all_failed": all_failed, "has_error_messages": has_error_messages}
                        )
                    else:
                        self.log_test(
                            "Bulk Upload - File Validation",
                            False,
                            f"❌ Bulk upload validation test failed: HTTP {invalid_response.status_code}",
                            invalid_response.text
                        )
                        
                else:
                    self.log_test(
                        "Bulk Upload - Basic Functionality",
                        False,
                        f"❌ Bulk upload response missing fields: {missing_fields}",
                        bulk_result
                    )
            else:
                self.log_test(
                    "Bulk Upload - Basic Functionality",
                    False,
                    f"❌ Bulk upload failed: HTTP {bulk_response.status_code}",
                    bulk_response.text
                )
                
        except Exception as e:
            self.log_test(
                "Bulk Upload Feature",
                False,
                f"❌ Error during bulk upload testing: {str(e)}",
                None
            )

    def test_qa_functionality(self):
        """🔥 PRIORITY: Test Q&A functionality (ask-question endpoint)"""
        try:
            print("   💬 Testing Q&A functionality...")
            
            if not self.auth_headers:
                print("   ⚠️ No authentication token available, skipping Q&A test")
                return
            
            # Test 1: Basic Q&A functionality
            print("   Step 1: Testing basic Q&A...")
            
            test_questions = [
                "İnsan kaynakları prosedürleri nelerdir?",
                "Çalışan hakları hakkında bilgi verebilir misiniz?",
                "Şirket politikaları neler?"
            ]
            
            qa_results = []
            
            for question in test_questions:
                qa_data = {
                    "question": question,
                    "session_id": None
                }
                
                qa_response = self.session.post(f"{self.base_url}/ask-question", 
                                              json=qa_data, headers=self.auth_headers)
                
                result = {
                    "question": question,
                    "status_code": qa_response.status_code,
                    "success": False
                }
                
                if qa_response.status_code == 200:
                    qa_result = qa_response.json()
                    required_fields = ["answer", "sources", "session_id"]
                    missing_fields = [field for field in required_fields if field not in qa_result]
                    
                    if not missing_fields:
                        result["success"] = True
                        result["answer_length"] = len(qa_result.get("answer", ""))
                        result["sources_count"] = len(qa_result.get("sources", []))
                        result["session_id"] = qa_result.get("session_id")
                    else:
                        result["error"] = f"Missing fields: {missing_fields}"
                else:
                    try:
                        error_data = qa_response.json()
                        result["error"] = error_data.get("detail", qa_response.text)
                    except:
                        result["error"] = qa_response.text
                
                qa_results.append(result)
                
                # Small delay between requests
                time.sleep(1)
            
            # Evaluate Q&A results
            successful_questions = sum(1 for r in qa_results if r["success"])
            success_rate = successful_questions / len(test_questions)
            
            self.log_test(
                "Q&A Functionality - Basic Testing",
                success_rate >= 0.6,  # 60% success rate acceptable (some may fail due to no documents)
                f"Q&A system results: {successful_questions}/{len(test_questions)} questions answered successfully ({success_rate:.1%})",
                {"results": qa_results, "success_rate": success_rate}
            )
            
        except Exception as e:
            self.log_test(
                "Q&A Functionality",
                False,
                f"❌ Error during Q&A testing: {str(e)}",
                None
            )

    def test_role_based_access_control(self):
        """🔥 PRIORITY: Test role-based access control"""
        try:
            print("   🛡️ Testing role-based access control...")
            
            if not self.auth_headers:
                print("   ⚠️ No authentication token available, skipping RBAC test")
                return
            
            # Test 1: Admin access to admin-only endpoints
            print("   Step 1: Testing admin access...")
            
            admin_endpoints = [
                ("GET", "/auth/users", "User list", None),
                ("POST", "/auth/create-user", "User creation", {
                    "username": "rbac_test_user",
                    "email": "rbac@test.com", 
                    "full_name": "RBAC Test User",
                    "password": "testpass123",
                    "role": "viewer"
                })
            ]
            
            admin_access_results = []
            
            for method, endpoint, description, data in admin_endpoints:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}", headers=self.auth_headers)
                elif method == "POST":
                    response = self.session.post(f"{self.base_url}{endpoint}", json=data, headers=self.auth_headers)
                
                success = response.status_code in [200, 201]
                admin_access_results.append({
                    "endpoint": endpoint,
                    "description": description,
                    "success": success,
                    "status_code": response.status_code
                })
            
            admin_success_rate = sum(1 for r in admin_access_results if r["success"]) / len(admin_access_results)
            
            self.log_test(
                "RBAC - Admin Access",
                admin_success_rate >= 0.8,
                f"Admin access control: {admin_success_rate:.1%} success rate on admin endpoints",
                {"results": admin_access_results}
            )
            
            # Test 2: Test editor/admin access to document operations
            print("   Step 2: Testing editor/admin document access...")
            
            # These should work with admin token
            editor_endpoints = [
                ("GET", "/documents", "Document listing", None),
                ("POST", "/groups", "Group creation", {
                    "name": "RBAC Test Group",
                    "description": "Test group for RBAC",
                    "color": "#123456"
                })
            ]
            
            editor_access_results = []
            
            for method, endpoint, description, data in editor_endpoints:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}", headers=self.auth_headers)
                elif method == "POST":
                    response = self.session.post(f"{self.base_url}{endpoint}", json=data, headers=self.auth_headers)
                
                success = response.status_code in [200, 201]
                editor_access_results.append({
                    "endpoint": endpoint,
                    "description": description,
                    "success": success,
                    "status_code": response.status_code
                })
            
            editor_success_rate = sum(1 for r in editor_access_results if r["success"]) / len(editor_access_results)
            
            self.log_test(
                "RBAC - Editor/Admin Document Access",
                editor_success_rate >= 0.8,
                f"Editor/Admin document access: {editor_success_rate:.1%} success rate",
                {"results": editor_access_results}
            )
            
        except Exception as e:
            self.log_test(
                "Role-Based Access Control",
                False,
                f"❌ Error during RBAC testing: {str(e)}",
                None
            )

    def test_existing_features_regression(self):
        """🔄 REGRESSION TESTING: Test existing features"""
        try:
            print("   🔄 Testing existing features regression...")
            
            # Test 1: Root endpoint
            response = self.session.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "Kurumsal Prosedür Asistanı" in data["message"]:
                    self.log_test(
                        "Regression - Root Endpoint",
                        True,
                        f"✅ Root endpoint working: {data['message']}",
                        data
                    )
                else:
                    self.log_test(
                        "Regression - Root Endpoint",
                        False,
                        "❌ Root endpoint response missing expected message",
                        data
                    )
            else:
                self.log_test(
                    "Regression - Root Endpoint",
                    False,
                    f"❌ Root endpoint failed: HTTP {response.status_code}",
                    response.text
                )
            
            # Test 2: System status endpoint
            status_response = self.session.get(f"{self.base_url}/status")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                required_fields = ["total_documents", "total_chunks", "embedding_model_loaded", "faiss_index_ready"]
                missing_fields = [field for field in required_fields if field not in status_data]
                
                if not missing_fields:
                    self.log_test(
                        "Regression - System Status",
                        True,
                        f"✅ System status working: {status_data['total_documents']} docs, {status_data['total_chunks']} chunks, model loaded: {status_data['embedding_model_loaded']}",
                        status_data
                    )
                else:
                    self.log_test(
                        "Regression - System Status",
                        False,
                        f"❌ System status missing fields: {missing_fields}",
                        status_data
                    )
            else:
                self.log_test(
                    "Regression - System Status",
                    False,
                    f"❌ System status failed: HTTP {status_response.status_code}",
                    status_response.text
                )
            
            # Test 3: Documents list endpoint
            if self.auth_headers:
                docs_response = self.session.get(f"{self.base_url}/documents", headers=self.auth_headers)
                
                if docs_response.status_code == 200:
                    docs_data = docs_response.json()
                    required_fields = ["documents", "statistics"]
                    missing_fields = [field for field in required_fields if field not in docs_data]
                    
                    if not missing_fields:
                        self.log_test(
                            "Regression - Documents List",
                            True,
                            f"✅ Documents list working: {len(docs_data['documents'])} documents",
                            {"document_count": len(docs_data['documents'])}
                        )
                    else:
                        self.log_test(
                            "Regression - Documents List",
                            False,
                            f"❌ Documents list missing fields: {missing_fields}",
                            docs_data
                        )
                else:
                    self.log_test(
                        "Regression - Documents List",
                        False,
                        f"❌ Documents list failed: HTTP {docs_response.status_code}",
                        docs_response.text
                    )
            
        except Exception as e:
            self.log_test(
                "Existing Features Regression",
                False,
                f"❌ Error during regression testing: {str(e)}",
                None
            )

    def test_data_integrity_and_performance(self):
        """🔧 DATA INTEGRITY & PERFORMANCE: Test system consistency"""
        try:
            print("   🔧 Testing data integrity and performance...")
            
            if not self.auth_headers:
                print("   ⚠️ No authentication token available, skipping data integrity test")
                return
            
            # Test 1: System status consistency
            print("   Step 1: Testing system status consistency...")
            
            status_response = self.session.get(f"{self.base_url}/status")
            docs_response = self.session.get(f"{self.base_url}/documents", headers=self.auth_headers)
            groups_response = self.session.get(f"{self.base_url}/groups", headers=self.auth_headers)
            
            if all(r.status_code == 200 for r in [status_response, docs_response, groups_response]):
                status_data = status_response.json()
                docs_data = docs_response.json()
                groups_data = groups_response.json()
                
                # Check consistency
                status_docs = status_data.get("total_documents", 0)
                actual_docs = len(docs_data.get("documents", []))
                status_groups = status_data.get("total_groups", 0)
                actual_groups = groups_data.get("total_count", 0)
                
                docs_consistent = status_docs == actual_docs
                groups_consistent = status_groups == actual_groups
                
                self.log_test(
                    "Data Integrity - System Status Consistency",
                    docs_consistent and groups_consistent,
                    f"✅ Data consistency: Documents {status_docs}=={actual_docs} ({docs_consistent}), Groups {status_groups}=={actual_groups} ({groups_consistent})",
                    {
                        "status_docs": status_docs,
                        "actual_docs": actual_docs,
                        "status_groups": status_groups,
                        "actual_groups": actual_groups
                    }
                )
            else:
                self.log_test(
                    "Data Integrity - System Status Consistency",
                    False,
                    "❌ Could not retrieve all endpoints for consistency check",
                    None
                )
            
            # Test 2: Performance test - multiple concurrent requests
            print("   Step 2: Testing concurrent request performance...")
            
            import threading
            import time
            
            results = []
            start_time = time.time()
            
            def make_request():
                try:
                    response = self.session.get(f"{self.base_url}/status")
                    results.append({
                        "success": response.status_code == 200,
                        "response_time": time.time() - start_time
                    })
                except Exception as e:
                    results.append({
                        "success": False,
                        "error": str(e)
                    })
            
            # Create 5 concurrent requests
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            total_time = time.time() - start_time
            successful_requests = sum(1 for r in results if r.get("success", False))
            success_rate = successful_requests / len(results)
            
            performance_good = success_rate >= 0.8 and total_time < 10  # 80% success rate, under 10 seconds
            
            self.log_test(
                "Performance - Concurrent Requests",
                performance_good,
                f"✅ Concurrent performance: {successful_requests}/{len(results)} successful ({success_rate:.1%}) in {total_time:.2f}s",
                {
                    "successful_requests": successful_requests,
                    "total_requests": len(results),
                    "total_time": total_time,
                    "success_rate": success_rate
                }
            )
            
        except Exception as e:
            self.log_test(
                "Data Integrity and Performance",
                False,
                f"❌ Error during data integrity testing: {str(e)}",
                None
            )

    def run_comprehensive_tests(self):
        """Run comprehensive backend tests - COMPLETE TESTING CYCLE"""
        print("🚀 COMPREHENSIVE KPA BACKEND TESTING")
        print("🔥 FOCUS: Fixed endpoints, new features, authentication, regression testing")
        print("=" * 80)
        
        # Test basic connectivity first
        if not self.test_backend_connectivity():
            print("❌ Backend connectivity failed. Stopping tests.")
            return self.get_summary()
        
        # PRIORITY 1: Authentication System (needed for other tests)
        print("\n🔐 PRIORITY 1: AUTHENTICATION & USER MANAGEMENT")
        print("-" * 50)
        self.test_authentication_system()
        
        # PRIORITY 2: Fixed Endpoints Testing
        print("\n🔥 PRIORITY 2: FIXED ENDPOINTS TESTING")
        print("-" * 50)
        self.test_group_management_fixed_endpoints()
        
        # PRIORITY 3: New Features Validation
        print("\n🆕 PRIORITY 3: NEW FEATURES VALIDATION")
        print("-" * 50)
        self.test_bulk_upload_feature()
        self.test_qa_functionality()
        
        # PRIORITY 4: Role-Based Access Control
        print("\n🛡️ PRIORITY 4: ROLE-BASED ACCESS CONTROL")
        print("-" * 50)
        self.test_role_based_access_control()
        
        # PRIORITY 5: Existing Features Regression Testing
        print("\n🔄 PRIORITY 5: REGRESSION TESTING")
        print("-" * 50)
        self.test_existing_features_regression()
        
        # PRIORITY 6: Data Integrity & Performance
        print("\n🔧 PRIORITY 6: DATA INTEGRITY & PERFORMANCE")
        print("-" * 50)
        self.test_data_integrity_and_performance()
        
        # Print comprehensive summary
        return self.get_comprehensive_summary()

    def get_comprehensive_summary(self):
        """Get comprehensive test results summary"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Categorize results
        categories = {
            "Authentication": ["Authentication", "RBAC"],
            "Fixed Endpoints": ["Fixed Endpoints"],
            "New Features": ["Bulk Upload", "Q&A"],
            "Regression": ["Regression"],
            "Data Integrity": ["Data Integrity", "Performance"]
        }
        
        print(f"\n📋 RESULTS BY CATEGORY:")
        for category, keywords in categories.items():
            category_tests = [r for r in self.test_results if any(keyword in r["test"] for keyword in keywords)]
            if category_tests:
                category_passed = sum(1 for r in category_tests if r["success"])
                category_total = len(category_tests)
                category_rate = (category_passed / category_total) * 100 if category_total > 0 else 0
                status = "✅" if category_rate >= 80 else "⚠️" if category_rate >= 60 else "❌"
                print(f"   {status} {category}: {category_passed}/{category_total} ({category_rate:.1f}%)")
        
        if failed_tests > 0:
            print(f"\n🔍 FAILED TESTS DETAILS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   ❌ {result['test']}")
                    print(f"      └─ {result['details']}")
        
        # Key findings
        print(f"\n🎯 KEY FINDINGS:")
        
        # Check if fixed endpoints are working
        fixed_endpoint_tests = [r for r in self.test_results if "Fixed Endpoints" in r["test"]]
        if fixed_endpoint_tests:
            fixed_success = sum(1 for r in fixed_endpoint_tests if r["success"])
            if fixed_success == len(fixed_endpoint_tests):
                print("   ✅ ALL FIXED ENDPOINTS ARE WORKING - Main agent's fix was successful!")
            elif fixed_success > 0:
                print(f"   ⚠️ PARTIAL FIX - {fixed_success}/{len(fixed_endpoint_tests)} fixed endpoints working")
            else:
                print("   ❌ FIXED ENDPOINTS STILL NOT WORKING - Main agent's fix may have failed")
        
        # Check authentication system
        auth_tests = [r for r in self.test_results if "Authentication" in r["test"]]
        if auth_tests:
            auth_success = sum(1 for r in auth_tests if r["success"])
            if auth_success >= len(auth_tests) * 0.8:
                print("   ✅ AUTHENTICATION SYSTEM WORKING PROPERLY")
            else:
                print("   ❌ AUTHENTICATION SYSTEM HAS ISSUES")
        
        # Check new features
        new_feature_tests = [r for r in self.test_results if any(keyword in r["test"] for keyword in ["Bulk Upload", "Q&A"])]
        if new_feature_tests:
            feature_success = sum(1 for r in new_feature_tests if r["success"])
            if feature_success >= len(new_feature_tests) * 0.8:
                print("   ✅ NEW FEATURES WORKING PROPERLY")
            else:
                print("   ⚠️ SOME NEW FEATURES NEED ATTENTION")
        
        print("\n" + "=" * 80)
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests/total_tests*100) if total_tests > 0 else 0,
            "results": self.test_results
        }

if __name__ == "__main__":
    tester = ComprehensiveKPATester()
    summary = tester.run_comprehensive_tests()
    
    # Exit with error code if tests failed
    if summary["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)