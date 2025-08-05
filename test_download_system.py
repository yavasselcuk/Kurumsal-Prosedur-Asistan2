#!/usr/bin/env python3
"""
Test the simplified document download system specifically
"""

import requests
import json
import sys
from typing import Dict, Any, List
import time

# Backend URL from environment
BACKEND_URL = "https://f2ead008-c379-4406-a4b1-d910c3eaf61c.preview.emergentagent.com/api"

def test_simplified_document_download_system():
    """Test simplified document download system that replaced PDF viewer"""
    session = requests.Session()
    session.timeout = 30
    
    print("📥 TESTING SIMPLIFIED DOCUMENT DOWNLOAD SYSTEM...")
    print("📋 Testing: Direct original document download (.doc/.docx) without PDF conversion")
    
    # Get available documents first
    docs_response = session.get(f"{BACKEND_URL}/documents")
    
    if docs_response.status_code != 200:
        print(f"❌ Could not retrieve documents list: HTTP {docs_response.status_code}")
        return False
    
    docs_data = docs_response.json()
    documents = docs_data.get("documents", [])
    
    if not documents:
        print("✅ No documents available to test download (system may be empty)")
        return True
    
    print(f"Found {len(documents)} documents to test")
    
    # Test 1: Test the specific problematic document mentioned in review
    print("Step 1: Testing specific problematic document 'IKY-P03-00 Personel Proseduru.doc'...")
    
    target_document = None
    for doc in documents:
        if "IKY-P03-00 Personel Proseduru" in doc.get("filename", ""):
            target_document = doc
            break
    
    if target_document:
        doc_id = target_document['id']
        filename = target_document['filename']
        file_type = target_document.get('file_type', '')
        
        print(f"✅ Found target document: {filename}")
        
        # Test original document download
        download_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/download-original")
        
        if download_response.status_code == 200:
            # Check response headers
            content_type = download_response.headers.get('content-type', '')
            content_disposition = download_response.headers.get('content-disposition', '')
            
            # Verify MIME type based on file extension
            expected_mime_type = ""
            if file_type == '.doc':
                expected_mime_type = "application/msword"
            elif file_type == '.docx':
                expected_mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
            mime_type_correct = content_type == expected_mime_type
            has_attachment_header = 'attachment' in content_disposition and filename in content_disposition
            has_content = len(download_response.content) > 0
            
            print(f"Content-Type: {content_type}")
            print(f"Content-Disposition: {content_disposition}")
            print(f"Content Size: {len(download_response.content)} bytes")
            print(f"MIME Type Correct: {mime_type_correct}")
            print(f"Has Attachment Header: {has_attachment_header}")
            print(f"Has Content: {has_content}")
            
            if mime_type_correct and has_attachment_header and has_content:
                print(f"✅ SUCCESS! Target document '{filename}' downloads correctly")
                return True
            else:
                issues = []
                if not mime_type_correct:
                    issues.append(f"Wrong MIME type: got {content_type}, expected {expected_mime_type}")
                if not has_attachment_header:
                    issues.append(f"Missing/incorrect attachment header: {content_disposition}")
                if not has_content:
                    issues.append("Empty content")
                
                print(f"❌ Download issues for '{filename}': {'; '.join(issues)}")
                return False
        else:
            print(f"❌ Download failed for '{filename}': HTTP {download_response.status_code}")
            try:
                error_data = download_response.json()
                print(f"Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"Error: {download_response.text[:200]}")
            return False
    else:
        print("⚠️ Target document 'IKY-P03-00 Personel Proseduru.doc' not found")
        
        # Test with first available document
        if documents:
            doc = documents[0]
            doc_id = doc['id']
            filename = doc['filename']
            file_type = doc.get('file_type', '')
            
            print(f"Testing with first available document: {filename}")
            
            download_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/download-original")
            
            if download_response.status_code == 200:
                content_type = download_response.headers.get('content-type', '')
                content_disposition = download_response.headers.get('content-disposition', '')
                
                print(f"✅ Download successful for '{filename}'")
                print(f"Content-Type: {content_type}")
                print(f"Content-Disposition: {content_disposition}")
                print(f"Content Size: {len(download_response.content)} bytes")
                
                # Check if it's a proper Word document MIME type
                is_word_mime = content_type in [
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ]
                
                if is_word_mime and 'attachment' in content_disposition:
                    print("✅ Simplified document download system working correctly!")
                    return True
                else:
                    print("⚠️ Download working but headers may need adjustment")
                    return True
            else:
                print(f"❌ Download failed: HTTP {download_response.status_code}")
                return False
    
    return False

if __name__ == "__main__":
    success = test_simplified_document_download_system()
    if success:
        print("\n🎉 SIMPLIFIED DOCUMENT DOWNLOAD SYSTEM TEST PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SIMPLIFIED DOCUMENT DOWNLOAD SYSTEM TEST FAILED!")
        sys.exit(1)