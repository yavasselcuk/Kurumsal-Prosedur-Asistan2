#!/usr/bin/env python3
"""
Focused PDF Viewer Integration Testing
Tests only the PDF-related endpoints for the new PDF feature.
"""

import requests
import json
import sys
import time

# Backend URL from environment
BACKEND_URL = "https://f2ead008-c379-4406-a4b1-d910c3eaf61c.preview.emergentagent.com/api"

def test_pdf_functionality():
    """Test PDF viewer integration functionality"""
    session = requests.Session()
    session.timeout = 30
    
    print("🚀 Testing PDF Viewer Integration Feature")
    print("=" * 60)
    
    # Step 1: Check if we have any documents
    print("Step 1: Checking for existing documents...")
    docs_response = session.get(f"{BACKEND_URL}/documents")
    
    if docs_response.status_code != 200:
        print(f"❌ Could not retrieve documents: HTTP {docs_response.status_code}")
        return False
    
    docs_data = docs_response.json()
    documents = docs_data.get("documents", [])
    
    print(f"Found {len(documents)} documents in the system")
    
    # Find a DOCX/DOC document to test with
    test_document = None
    for doc in documents:
        if doc.get("file_type", "").lower() in ['.doc', '.docx']:
            test_document = doc
            break
    
    if not test_document:
        print("No DOCX/DOC documents found. Creating a test document...")
        
        # Create a test DOCX document
        test_docx_content = (
            b'PK\x03\x04\x14\x08'  # DOCX header
            b'Test PDF conversion document. '
            b'This document will be converted to PDF format. '
            b'The PDF conversion system should handle this content properly. '
            b'Testing various formatting and text content for PDF generation. '
            b'This is a comprehensive test of the PDF viewer integration feature.'
            + b'' * 500  # Padding to make it more realistic
        )
        
        files = {'file': ('pdf_test_document.docx', test_docx_content, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
        upload_response = session.post(f"{BACKEND_URL}/upload-document", files=files)
        
        if upload_response.status_code != 200:
            print(f"❌ Could not upload test document: HTTP {upload_response.status_code}")
            return False
        
        upload_data = upload_response.json()
        test_document = {
            "id": upload_data.get("document_id"),
            "filename": "pdf_test_document.docx"
        }
        
        print(f"✅ Created test document: {test_document['filename']}")
        
        # Wait for processing
        print("Waiting for document processing...")
        time.sleep(5)
    
    doc_id = test_document["id"]
    filename = test_document["filename"]
    
    print(f"\nTesting PDF functionality with document: {filename} (ID: {doc_id})")
    print("-" * 60)
    
    # Test 1: GET /api/documents/{document_id}/pdf - Serve document as PDF
    print("\n📄 Test 1: PDF Serving Endpoint")
    pdf_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/pdf")
    
    if pdf_response.status_code == 200:
        content_type = pdf_response.headers.get('content-type', '')
        content_disposition = pdf_response.headers.get('content-disposition', '')
        x_pdf_pages = pdf_response.headers.get('x-pdf-pages', '')
        x_original_filename = pdf_response.headers.get('x-original-filename', '')
        
        pdf_content = pdf_response.content
        
        # Validate PDF response
        pdf_valid = (
            content_type == 'application/pdf' and
            'inline' in content_disposition and
            '.pdf' in content_disposition and
            len(pdf_content) > 100 and
            pdf_content.startswith(b'%PDF')
        )
        
        if pdf_valid:
            print(f"✅ PDF serving working perfectly!")
            print(f"   Content-Type: {content_type}")
            print(f"   Size: {len(pdf_content)} bytes")
            print(f"   Pages: {x_pdf_pages}")
            print(f"   Original: {x_original_filename}")
        else:
            print(f"❌ PDF serving validation failed")
            print(f"   Content-Type: {content_type}")
            print(f"   Disposition: {content_disposition}")
            print(f"   Size: {len(pdf_content)}")
            print(f"   Starts with PDF: {pdf_content[:10] if pdf_content else 'No content'}")
    else:
        print(f"❌ PDF serving failed: HTTP {pdf_response.status_code}")
        print(f"   Response: {pdf_response.text}")
    
    # Test 2: GET /api/documents/{document_id}/pdf/metadata - Get PDF metadata
    print("\n📊 Test 2: PDF Metadata Endpoint")
    metadata_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/pdf/metadata")
    
    if metadata_response.status_code == 200:
        metadata_data = metadata_response.json()
        
        required_fields = ["page_count", "file_size", "file_size_human", "original_filename", "original_format", "document_id", "pdf_available"]
        missing_fields = [field for field in required_fields if field not in metadata_data]
        
        if not missing_fields:
            print(f"✅ PDF metadata working perfectly!")
            print(f"   Pages: {metadata_data['page_count']}")
            print(f"   Size: {metadata_data['file_size_human']}")
            print(f"   Format: {metadata_data['original_format']}")
            print(f"   Available: {metadata_data['pdf_available']}")
        else:
            print(f"❌ PDF metadata missing fields: {missing_fields}")
    else:
        print(f"❌ PDF metadata failed: HTTP {metadata_response.status_code}")
        print(f"   Response: {metadata_response.text}")
    
    # Test 3: GET /api/documents/{document_id}/download - Download document as PDF
    print("\n⬇️ Test 3: PDF Download Endpoint")
    download_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/download")
    
    if download_response.status_code == 200:
        content_type = download_response.headers.get('content-type', '')
        content_disposition = download_response.headers.get('content-disposition', '')
        
        download_content = download_response.content
        
        download_valid = (
            content_type == 'application/pdf' and
            'attachment' in content_disposition and
            '.pdf' in content_disposition and
            len(download_content) > 100 and
            download_content.startswith(b'%PDF')
        )
        
        if download_valid:
            print(f"✅ PDF download working perfectly!")
            print(f"   Content-Type: {content_type}")
            print(f"   Disposition: attachment")
            print(f"   Size: {len(download_content)} bytes")
        else:
            print(f"❌ PDF download validation failed")
            print(f"   Content-Type: {content_type}")
            print(f"   Disposition: {content_disposition}")
    else:
        print(f"❌ PDF download failed: HTTP {download_response.status_code}")
        print(f"   Response: {download_response.text}")
    
    # Test 4: Error handling with non-existent document
    print("\n🚫 Test 4: PDF Error Handling")
    fake_id = "non-existent-document-12345"
    error_response = session.get(f"{BACKEND_URL}/documents/{fake_id}/pdf")
    
    if error_response.status_code == 404:
        print(f"✅ PDF error handling working correctly - returns 404 for non-existent document")
    else:
        print(f"❌ PDF error handling failed - expected 404, got {error_response.status_code}")
    
    # Test 5: End-to-End Workflow Test
    print("\n🔄 Test 5: End-to-End PDF Workflow")
    workflow_steps = []
    
    # Step 1: Get PDF
    pdf_step = session.get(f"{BACKEND_URL}/documents/{doc_id}/pdf")
    workflow_steps.append(f"PDF Serve: HTTP {pdf_step.status_code}")
    
    # Step 2: Get Metadata
    meta_step = session.get(f"{BACKEND_URL}/documents/{doc_id}/pdf/metadata")
    workflow_steps.append(f"Metadata: HTTP {meta_step.status_code}")
    
    # Step 3: Download PDF
    download_step = session.get(f"{BACKEND_URL}/documents/{doc_id}/download")
    workflow_steps.append(f"Download: HTTP {download_step.status_code}")
    
    workflow_success = all(step.endswith("200") for step in workflow_steps)
    
    if workflow_success:
        print(f"✅ Complete PDF workflow working perfectly!")
        print(f"   Workflow: {' → '.join(workflow_steps)}")
    else:
        print(f"❌ PDF workflow has issues")
        print(f"   Workflow: {' → '.join(workflow_steps)}")
    
    print("\n" + "=" * 60)
    print("📊 PDF TESTING SUMMARY")
    print("=" * 60)
    
    # Count successful tests
    tests = [
        pdf_response.status_code == 200,
        metadata_response.status_code == 200,
        download_response.status_code == 200,
        error_response.status_code == 404,
        workflow_success
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL PDF TESTS PASSED! PDF Viewer Integration is working perfectly!")
        return True
    else:
        print(f"\n⚠️ {total - passed} PDF tests failed. Feature needs attention.")
        return False

if __name__ == "__main__":
    success = test_pdf_functionality()
    sys.exit(0 if success else 1)