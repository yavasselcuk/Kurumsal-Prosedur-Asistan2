#!/usr/bin/env python3
"""
Focused Backend Testing for Review Request Features
Tests the three specific features mentioned in the review request:
1. Group Creation Authentication Fix
2. Bulk Document Upload
3. Mandatory Password Change System
"""

import requests
import json
import base64
import time

BACKEND_URL = "https://1070132c-1836-44b9-839f-410d8851049c.preview.emergentagent.com/api"

def test_mandatory_password_change_system():
    """Test Mandatory Password Change System"""
    print("🔐 Testing Mandatory Password Change System...")
    
    # Test 1: Admin login should show must_change_password=true
    login_data = {"username": "admin", "password": "admin123"}
    response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if response.status_code == 200:
        result = response.json()
        must_change = result.get("must_change_password", False)
        user_must_change = result.get("user", {}).get("must_change_password", False)
        
        print(f"✅ Admin login successful")
        print(f"   must_change_password (response): {must_change}")
        print(f"   must_change_password (user): {user_must_change}")
        
        if must_change or user_must_change:
            print("✅ PASS: Mandatory password change system working - admin requires password change")
            
            # Test password change endpoint
            access_token = result.get("access_token")
            headers = {"Authorization": f"Bearer {access_token}"}
            
            password_change_data = {
                "current_password": "admin123",
                "new_password": "newadmin123"
            }
            
            change_response = requests.post(
                f"{BACKEND_URL}/auth/change-password",
                json=password_change_data,
                headers=headers
            )
            
            if change_response.status_code == 200:
                print("✅ PASS: Password change endpoint working")
                
                # Test login with new password
                new_login = {"username": "admin", "password": "newadmin123"}
                new_response = requests.post(f"{BACKEND_URL}/auth/login", json=new_login)
                
                if new_response.status_code == 200:
                    new_result = new_response.json()
                    new_must_change = new_result.get("must_change_password", True)
                    new_user_must_change = new_result.get("user", {}).get("must_change_password", True)
                    
                    if not new_must_change and not new_user_must_change:
                        print("✅ PASS: Password change flag cleared after successful change")
                    else:
                        print("❌ FAIL: Password change flag not cleared")
                    
                    # Restore original password
                    restore_headers = {"Authorization": f"Bearer {new_result.get('access_token')}"}
                    restore_data = {
                        "current_password": "newadmin123",
                        "new_password": "admin123"
                    }
                    requests.post(f"{BACKEND_URL}/auth/change-password", json=restore_data, headers=restore_headers)
                    
                else:
                    print("❌ FAIL: Cannot login with new password")
            else:
                print(f"❌ FAIL: Password change failed: {change_response.status_code}")
        else:
            print("❌ FAIL: Admin user does not require password change")
    else:
        print(f"❌ FAIL: Admin login failed: {response.status_code}")
    
    print()

def test_group_creation_authentication_fix():
    """Test Group Creation Authentication Fix"""
    print("🔐 Testing Group Creation Authentication Fix...")
    
    # Login first
    login_data = {"username": "admin", "password": "admin123"}
    login_response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if login_response.status_code == 200:
        access_token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test group creation
        group_data = {
            "name": "Test Group Auth Fix",
            "description": "Testing authentication header fix",
            "color": "#ff5722"
        }
        
        response = requests.post(f"{BACKEND_URL}/groups", json=group_data, headers=headers)
        
        if response.status_code == 200:
            print("✅ PASS: Group creation with authentication working - no 'No authenticated' error")
        elif response.status_code == 401:
            error_detail = response.json().get("detail", "")
            if "No authenticated" in error_detail:
                print("❌ FAIL: 'No authenticated' error still occurring")
            else:
                print(f"❌ FAIL: Authentication failed with different error: {error_detail}")
        elif response.status_code == 404:
            print("❌ FAIL: Groups endpoint not found (404) - endpoint may not be implemented")
        else:
            print(f"❌ FAIL: Group creation failed with HTTP {response.status_code}")
    else:
        print("❌ FAIL: Cannot test group creation - admin login failed")
    
    print()

def test_bulk_document_upload():
    """Test Bulk Document Upload"""
    print("📁 Testing Bulk Document Upload...")
    
    # Login first
    login_data = {"username": "admin", "password": "admin123"}
    login_response = requests.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if login_response.status_code == 200:
        access_token = login_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Create test files
        test_files = [
            {
                "filename": "bulk_test_1.docx",
                "content": base64.b64encode(b'PK\x03\x04' + b'Test DOCX content 1' + b'\x00' * 100).decode('utf-8')
            },
            {
                "filename": "bulk_test_2.doc",
                "content": base64.b64encode(b'\xd0\xcf\x11\xe0' + b'Test DOC content 2' + b'\x00' * 100).decode('utf-8')
            }
        ]
        
        bulk_request = {"files": test_files}
        
        response = requests.post(f"{BACKEND_URL}/bulk-upload-documents", json=bulk_request, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            required_fields = ["total_files", "successful_uploads", "failed_uploads", "results", "processing_time"]
            
            if all(field in result for field in required_fields):
                total = result["total_files"]
                successful = result["successful_uploads"]
                processing_time = result["processing_time"]
                
                print(f"✅ PASS: Bulk upload working - {successful}/{total} files processed in {processing_time:.2f}s")
                
                # Test validation with invalid files
                invalid_files = [{
                    "filename": "invalid.txt",
                    "content": base64.b64encode(b'Invalid text content').decode('utf-8')
                }]
                
                validation_request = {"files": invalid_files}
                validation_response = requests.post(f"{BACKEND_URL}/bulk-upload-documents", json=validation_request, headers=headers)
                
                if validation_response.status_code == 200:
                    validation_result = validation_response.json()
                    failed = validation_result.get("failed_uploads", 0)
                    if failed > 0:
                        print("✅ PASS: File format validation working")
                    else:
                        print("❌ FAIL: File format validation not working")
                else:
                    print("❌ FAIL: Validation test failed")
                    
            else:
                print("❌ FAIL: Bulk upload response missing required fields")
        elif response.status_code == 404:
            print("❌ FAIL: Bulk upload endpoint not found (404) - endpoint may not be implemented")
        else:
            print(f"❌ FAIL: Bulk upload failed with HTTP {response.status_code}")
    else:
        print("❌ FAIL: Cannot test bulk upload - admin login failed")
    
    print()

def main():
    print("🚀 Focused Backend Testing for Review Request Features")
    print("=" * 70)
    print("Testing the three specific features mentioned in the review request:")
    print("1. Group Creation Authentication Fix")
    print("2. Bulk Document Upload")
    print("3. Mandatory Password Change System")
    print()
    
    # Test the three specific features
    test_mandatory_password_change_system()
    test_group_creation_authentication_fix()
    test_bulk_document_upload()
    
    print("=" * 70)
    print("Focused testing completed!")

if __name__ == "__main__":
    main()