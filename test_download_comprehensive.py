#!/usr/bin/env python3
"""
Comprehensive test of the simplified document download system
"""

import requests
import json
import sys
from typing import Dict, Any, List
import time

# Backend URL from environment
BACKEND_URL = "https://f2ead008-c379-4406-a4b1-d910c3eaf61c.preview.emergentagent.com/api"

def test_comprehensive_download_system():
    """Comprehensive test of simplified document download system"""
    session = requests.Session()
    session.timeout = 30
    
    print("📥 COMPREHENSIVE SIMPLIFIED DOCUMENT DOWNLOAD SYSTEM TEST...")
    print("=" * 70)
    
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
    print()
    
    # Separate documents by type
    doc_files = [doc for doc in documents if doc.get("file_type") == ".doc"]
    docx_files = [doc for doc in documents if doc.get("file_type") == ".docx"]
    
    print(f"DOC files: {len(doc_files)}")
    print(f"DOCX files: {len(docx_files)}")
    print()
    
    test_results = {
        "total_tested": 0,
        "successful_downloads": 0,
        "correct_mime_types": 0,
        "correct_headers": 0,
        "doc_files_tested": 0,
        "docx_files_tested": 0,
        "errors": []
    }
    
    # Test DOC files
    print("Testing DOC files:")
    print("-" * 20)
    
    for i, doc in enumerate(doc_files[:5], 1):  # Test up to 5 DOC files
        test_results["total_tested"] += 1
        test_results["doc_files_tested"] += 1
        
        doc_id = doc["id"]
        filename = doc["filename"]
        
        print(f"{i}. Testing: {filename}")
        
        download_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/download-original")
        
        if download_response.status_code == 200:
            content_type = download_response.headers.get('content-type', '')
            content_disposition = download_response.headers.get('content-disposition', '')
            content_size = len(download_response.content)
            
            # Check MIME type for DOC files
            correct_mime = content_type == "application/msword"
            if correct_mime:
                test_results["correct_mime_types"] += 1
            
            # Check attachment headers
            correct_header = 'attachment' in content_disposition and filename in content_disposition
            if correct_header:
                test_results["correct_headers"] += 1
            
            # Check content
            has_content = content_size > 0
            if has_content:
                test_results["successful_downloads"] += 1
            
            print(f"   ✅ Downloaded: {content_size} bytes")
            print(f"   MIME: {content_type} {'✅' if correct_mime else '❌'}")
            print(f"   Header: {'✅' if correct_header else '❌'}")
            
        else:
            error_msg = f"HTTP {download_response.status_code}"
            try:
                error_data = download_response.json()
                error_msg += f": {error_data.get('detail', 'Unknown error')}"
            except:
                error_msg += f": {download_response.text[:100]}"
            
            test_results["errors"].append(f"{filename}: {error_msg}")
            print(f"   ❌ Failed: {error_msg}")
        
        print()
    
    # Test DOCX files
    print("Testing DOCX files:")
    print("-" * 20)
    
    for i, doc in enumerate(docx_files[:5], 1):  # Test up to 5 DOCX files
        test_results["total_tested"] += 1
        test_results["docx_files_tested"] += 1
        
        doc_id = doc["id"]
        filename = doc["filename"]
        
        print(f"{i}. Testing: {filename}")
        
        download_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/download-original")
        
        if download_response.status_code == 200:
            content_type = download_response.headers.get('content-type', '')
            content_disposition = download_response.headers.get('content-disposition', '')
            content_size = len(download_response.content)
            
            # Check MIME type for DOCX files
            correct_mime = content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if correct_mime:
                test_results["correct_mime_types"] += 1
            
            # Check attachment headers
            correct_header = 'attachment' in content_disposition and filename in content_disposition
            if correct_header:
                test_results["correct_headers"] += 1
            
            # Check content
            has_content = content_size > 0
            if has_content:
                test_results["successful_downloads"] += 1
            
            print(f"   ✅ Downloaded: {content_size} bytes")
            print(f"   MIME: {content_type} {'✅' if correct_mime else '❌'}")
            print(f"   Header: {'✅' if correct_header else '❌'}")
            
        else:
            error_msg = f"HTTP {download_response.status_code}"
            try:
                error_data = download_response.json()
                error_msg += f": {error_data.get('detail', 'Unknown error')}"
            except:
                error_msg += f": {download_response.text[:100]}"
            
            test_results["errors"].append(f"{filename}: {error_msg}")
            print(f"   ❌ Failed: {error_msg}")
        
        print()
    
    # Test error handling
    print("Testing error handling:")
    print("-" * 20)
    
    fake_doc_id = "non-existent-document-12345"
    error_response = session.get(f"{BACKEND_URL}/documents/{fake_doc_id}/download-original")
    
    if error_response.status_code == 404:
        try:
            error_data = error_response.json()
            error_message = error_data.get("detail", "")
            
            # Check if error message is in Turkish and user-friendly
            is_turkish = any(word in error_message.lower() for word in ["doküman", "bulunamadı", "mevcut"])
            
            print(f"✅ Error handling working: {error_message}")
            print(f"   Turkish message: {'✅' if is_turkish else '❌'}")
        except:
            print("✅ Error handling working (404 returned for non-existent document)")
    else:
        print(f"❌ Expected 404 for non-existent document, got {error_response.status_code}")
        test_results["errors"].append(f"Error handling: Expected 404, got {error_response.status_code}")
    
    print()
    
    # Calculate success rates
    if test_results["total_tested"] > 0:
        download_success_rate = test_results["successful_downloads"] / test_results["total_tested"]
        mime_accuracy = test_results["correct_mime_types"] / test_results["total_tested"]
        header_accuracy = test_results["correct_headers"] / test_results["total_tested"]
        
        print("=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        print(f"Total documents tested: {test_results['total_tested']}")
        print(f"DOC files tested: {test_results['doc_files_tested']}")
        print(f"DOCX files tested: {test_results['docx_files_tested']}")
        print(f"Successful downloads: {test_results['successful_downloads']}/{test_results['total_tested']} ({download_success_rate:.1%})")
        print(f"Correct MIME types: {test_results['correct_mime_types']}/{test_results['total_tested']} ({mime_accuracy:.1%})")
        print(f"Correct headers: {test_results['correct_headers']}/{test_results['total_tested']} ({header_accuracy:.1%})")
        
        if test_results["errors"]:
            print(f"\nErrors encountered: {len(test_results['errors'])}")
            for error in test_results["errors"]:
                print(f"  - {error}")
        
        # Overall success criteria
        overall_success = (
            download_success_rate >= 0.8 and
            mime_accuracy >= 0.8 and
            header_accuracy >= 0.8 and
            len(test_results["errors"]) <= test_results["total_tested"] * 0.2
        )
        
        print(f"\nOverall success: {'✅ PASS' if overall_success else '❌ FAIL'}")
        
        return overall_success
    else:
        print("No documents were tested")
        return False

if __name__ == "__main__":
    success = test_comprehensive_download_system()
    if success:
        print("\n🎉 COMPREHENSIVE SIMPLIFIED DOCUMENT DOWNLOAD SYSTEM TEST PASSED!")
        sys.exit(0)
    else:
        print("\n❌ COMPREHENSIVE SIMPLIFIED DOCUMENT DOWNLOAD SYSTEM TEST FAILED!")
        sys.exit(1)