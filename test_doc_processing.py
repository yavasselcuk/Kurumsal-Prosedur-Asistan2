#!/usr/bin/env python3
"""
Focused test for Enhanced DOC Processing Fix
"""

import requests
import json
import sys
import time

# Backend URL from environment
BACKEND_URL = "https://f2ead008-c379-4406-a4b1-d910c3eaf61c.preview.emergentagent.com/api"

def test_enhanced_doc_processing_fix():
    """🔥 ENHANCED DOC PROCESSING FIX: Test specific DOC file processing improvements for PDF viewer"""
    session = requests.Session()
    session.timeout = 30
    
    print("🔥 ENHANCED DOC PROCESSING FIX TESTING...")
    print("📋 Testing: DOC vs DOCX handling, textract integration, antiword fallback, PDF generation")
    
    # Test 1: Check if the specific problematic document exists
    print("\nStep 1: Checking for existing documents...")
    docs_response = session.get(f"{BACKEND_URL}/documents")
    
    target_document = None
    if docs_response.status_code == 200:
        docs_data = docs_response.json()
        documents = docs_data.get("documents", [])
        
        print(f"Found {len(documents)} total documents")
        
        # Look for the specific document mentioned in the review
        for doc in documents:
            filename = doc.get("filename", "")
            print(f"  - {filename} ({doc.get('file_type', 'unknown')})")
            if "IKY-P03-00 Personel Proseduru" in filename:
                target_document = doc
                break
        
        if target_document:
            print(f"✅ Found target document: {target_document['filename']}")
        else:
            print("⚠️ Target document 'IKY-P03-00 Personel Proseduru.doc' not found")
            # Let's try to find any .doc file for testing
            doc_files = [doc for doc in documents if doc.get("file_type") == ".doc"]
            if doc_files:
                target_document = doc_files[0]
                print(f"Using alternative DOC file for testing: {target_document['filename']}")
    else:
        print(f"❌ Failed to get documents: HTTP {docs_response.status_code}")
        return
    
    # Test 2: Test DOC file processing capabilities
    print("\nStep 2: Testing DOC processing capabilities...")
    
    # Check antiword availability
    import subprocess
    try:
        antiword_result = subprocess.run(['which', 'antiword'], capture_output=True, text=True, timeout=10)
        antiword_available = antiword_result.returncode == 0
        antiword_path = antiword_result.stdout.strip() if antiword_available else "Not found"
        
        if antiword_available:
            print(f"✅ Antiword available at: {antiword_path}")
            # Test antiword functionality
            version_result = subprocess.run(['antiword', '-v'], capture_output=True, text=True, timeout=10)
            if version_result.returncode == 0 or "antiword" in version_result.stderr.lower():
                print("✅ Antiword is working correctly")
            else:
                print("⚠️ Antiword may have issues")
        else:
            print("❌ Antiword not available - DOC processing may fail")
            
    except Exception as e:
        print(f"❌ Error checking antiword: {str(e)}")
    
    # Check textract availability
    try:
        import textract
        print("✅ Textract module is available")
        
        # Test textract with a simple file
        test_content = b"Simple test content"
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(test_content)
            tmp.flush()
            
            try:
                extracted = textract.process(tmp.name)
                if b"test content" in extracted.lower():
                    print("✅ Textract is working correctly")
                else:
                    print("⚠️ Textract may have issues")
            except Exception as e:
                print(f"⚠️ Textract test failed: {str(e)}")
            
            os.unlink(tmp.name)
            
    except ImportError:
        print("❌ Textract not available - fallback processing may be limited")
    
    # Test 3: Test PDF generation for existing DOC documents
    if target_document:
        print(f"\nStep 3: Testing PDF generation for {target_document['filename']}...")
        
        doc_id = target_document['id']
        
        # Test PDF serving endpoint
        print(f"Testing PDF endpoint: /api/documents/{doc_id}/pdf")
        pdf_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/pdf")
        
        print(f"PDF Response Status: {pdf_response.status_code}")
        print(f"Content-Type: {pdf_response.headers.get('content-type', 'Not set')}")
        
        if pdf_response.status_code == 200:
            # Check if response is actually a PDF
            content_type = pdf_response.headers.get('content-type', '')
            pdf_content = pdf_response.content
            
            is_valid_pdf = (
                'application/pdf' in content_type and
                pdf_content.startswith(b'%PDF') and
                len(pdf_content) > 100
            )
            
            if is_valid_pdf:
                print(f"✅ PDF generation SUCCESS! Successfully converted {target_document['filename']} to PDF ({len(pdf_content)} bytes)")
                
                # Test PDF metadata endpoint
                metadata_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/pdf/metadata")
                
                if metadata_response.status_code == 200:
                    metadata = metadata_response.json()
                    print(f"✅ PDF metadata: {metadata.get('page_count', 'unknown')} pages, {metadata.get('file_size_human', 'unknown size')}")
                else:
                    print(f"⚠️ PDF metadata failed: HTTP {metadata_response.status_code}")
                
                # Test PDF download endpoint
                download_response = session.get(f"{BACKEND_URL}/documents/{doc_id}/download")
                
                if download_response.status_code == 200:
                    print("✅ PDF download working correctly")
                else:
                    print(f"⚠️ PDF download failed: HTTP {download_response.status_code}")
                    
            else:
                print(f"❌ PDF generation FAILED! Response not a valid PDF.")
                print(f"   Content-Type: {content_type}")
                print(f"   Size: {len(pdf_content)} bytes")
                print(f"   Starts with PDF header: {pdf_content[:10] if pdf_content else 'Empty'}")
                
        elif pdf_response.status_code == 404:
            print(f"❌ PDF generation returned 404 - document may not exist or PDF generation failed")
            
        else:
            # Check if it's the specific error mentioned in the review
            try:
                if pdf_response.headers.get('content-type', '').startswith('application/json'):
                    error_data = pdf_response.json()
                else:
                    error_data = {"detail": pdf_response.text}
                    
                error_detail = error_data.get("detail", "")
                
                if "Package not found" in error_detail and ".docx" in error_detail:
                    print(f"❌ FOUND THE REPORTED BUG! 'Package not found at '/tmp/tmpXXXXXX.docx'' error still occurring:")
                    print(f"   Error: {error_detail}")
                else:
                    print(f"❌ PDF generation failed with HTTP {pdf_response.status_code}:")
                    print(f"   Error: {error_detail}")
                    
            except Exception as e:
                print(f"❌ PDF generation failed with HTTP {pdf_response.status_code}:")
                print(f"   Response: {pdf_response.text[:200]}")
    
    # Test 4: Test with multiple document types to verify DOC vs DOCX handling
    print("\nStep 4: Testing DOC vs DOCX processing differentiation...")
    
    if docs_response.status_code == 200:
        docs_data = docs_response.json()
        documents = docs_data.get("documents", [])
        
        doc_files = [doc for doc in documents if doc.get("file_type") == ".doc"]
        docx_files = [doc for doc in documents if doc.get("file_type") == ".docx"]
        
        print(f"Found {len(doc_files)} .doc files and {len(docx_files)} .docx files")
        
        # Test PDF generation for both types
        test_results = {"doc_success": 0, "doc_total": 0, "docx_success": 0, "docx_total": 0}
        
        # Test up to 3 DOC files
        print("\nTesting DOC files:")
        for doc in doc_files[:3]:
            test_results["doc_total"] += 1
            print(f"  Testing: {doc['filename']}")
            pdf_response = session.get(f"{BACKEND_URL}/documents/{doc['id']}/pdf")
            if pdf_response.status_code == 200 and pdf_response.content.startswith(b'%PDF'):
                test_results["doc_success"] += 1
                print(f"    ✅ Success")
            else:
                print(f"    ❌ Failed (HTTP {pdf_response.status_code})")
        
        # Test up to 3 DOCX files
        print("\nTesting DOCX files:")
        for doc in docx_files[:3]:
            test_results["docx_total"] += 1
            print(f"  Testing: {doc['filename']}")
            pdf_response = session.get(f"{BACKEND_URL}/documents/{doc['id']}/pdf")
            if pdf_response.status_code == 200 and pdf_response.content.startswith(b'%PDF'):
                test_results["docx_success"] += 1
                print(f"    ✅ Success")
            else:
                print(f"    ❌ Failed (HTTP {pdf_response.status_code})")
        
        # Calculate success rates
        doc_success_rate = test_results["doc_success"] / test_results["doc_total"] if test_results["doc_total"] > 0 else 0
        docx_success_rate = test_results["docx_success"] / test_results["docx_total"] if test_results["docx_total"] > 0 else 0
        
        print(f"\nResults:")
        print(f"DOC files: {test_results['doc_success']}/{test_results['doc_total']} ({doc_success_rate:.1%})")
        print(f"DOCX files: {test_results['docx_success']}/{test_results['docx_total']} ({docx_success_rate:.1%})")
        
        overall_success = (test_results["doc_success"] + test_results["docx_success"]) >= (test_results["doc_total"] + test_results["docx_total"]) * 0.8
        
        if overall_success:
            print("✅ Overall DOC/DOCX processing working well")
        else:
            print("❌ DOC/DOCX processing has issues")

if __name__ == "__main__":
    test_enhanced_doc_processing_fix()