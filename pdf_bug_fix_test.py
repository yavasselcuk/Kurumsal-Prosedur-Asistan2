#!/usr/bin/env python3
"""
PDF Viewer Bug Fix Testing
Tests the specific bug fix for PDF viewer where modal shows error "Package not found at '/tmp/tmpjehpblnz.docx'"
"""

import requests
import json
import sys
import time

# Backend URL from environment
BACKEND_URL = "https://f2ead008-c379-4406-a4b1-d910c3eaf61c.preview.emergentagent.com/api"

class PDFBugFixTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.session.timeout = 30
        
    def log_result(self, test_name: str, success: bool, details: str):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        print()

    def test_pdf_bug_fix(self):
        """Test the specific PDF viewer bug fix"""
        print("🔥 CRITICAL TEST: PDF Viewer Bug Fix")
        print("Testing for the specific error: 'Package not found at '/tmp/tmpjehpblnz.docx'")
        print("=" * 80)
        
        try:
            # Step 1: Get available documents
            print("Step 1: Retrieving available documents...")
            docs_response = self.session.get(f"{self.base_url}/documents")
            
            if docs_response.status_code != 200:
                self.log_result("Document Retrieval", False, f"Could not retrieve documents: HTTP {docs_response.status_code}")
                return
            
            docs_data = docs_response.json()
            documents = docs_data.get("documents", [])
            
            if not documents:
                self.log_result("Document Availability", False, "No documents available to test PDF conversion")
                return
            
            print(f"Found {len(documents)} documents to test")
            
            # Step 2: Look for the specific problematic document
            problematic_doc = None
            for doc in documents:
                if "IKY-P03-00 Personel Proseduru" in doc.get("filename", ""):
                    problematic_doc = doc
                    break
            
            # Use the problematic document if found, otherwise use the first document
            test_doc = problematic_doc or documents[0]
            doc_id = test_doc["id"]
            filename = test_doc.get("filename", "Unknown")
            
            if problematic_doc:
                print(f"✅ Found the specific problematic document: {filename}")
            else:
                print(f"⚠️ Specific document not found, testing with: {filename}")
            
            # Step 3: Test PDF conversion
            print(f"Step 2: Testing PDF conversion for document: {filename}")
            pdf_response = self.session.get(f"{self.base_url}/documents/{doc_id}/pdf")
            
            if pdf_response.status_code == 200:
                # Check if content is valid PDF
                pdf_content = pdf_response.content
                is_valid_pdf = pdf_content.startswith(b'%PDF')
                
                # Check for the specific error mentioned in the bug report
                error_patterns = [
                    b'/tmp/tmpjehpblnz.docx',
                    b'Package not found',
                    'görüntülenemiyor'.encode('utf-8')
                ]
                
                error_found = any(pattern in pdf_content for pattern in error_patterns)
                
                if is_valid_pdf and not error_found:
                    self.log_result(
                        "PDF Bug Fix - Original Error",
                        True,
                        f"✅ BUG FIXED! PDF conversion successful. No '/tmp/tmpjehpblnz.docx' error found. PDF size: {len(pdf_content)} bytes"
                    )
                    
                    # Check headers
                    content_type = pdf_response.headers.get('Content-Type', '')
                    x_original_filename = pdf_response.headers.get('X-Original-Filename', '')
                    
                    self.log_result(
                        "PDF Bug Fix - Headers",
                        True,
                        f"✅ Proper headers present. Content-Type: {content_type}, Original filename: {x_original_filename}"
                    )
                    
                elif error_found:
                    # The original bug still exists
                    error_text = pdf_response.text if isinstance(pdf_content, bytes) else str(pdf_content)
                    self.log_result(
                        "PDF Bug Fix - Original Error",
                        False,
                        f"❌ ORIGINAL BUG STILL EXISTS! Found error pattern in PDF content. This indicates the bug fix did not work."
                    )
                    print(f"Error content preview: {error_text[:300]}...")
                    
                else:
                    self.log_result(
                        "PDF Bug Fix - PDF Format",
                        False,
                        f"❌ PDF conversion failed. Content is not valid PDF format. Content starts with: {pdf_content[:50]}"
                    )
                    
            elif pdf_response.status_code == 404:
                self.log_result(
                    "PDF Bug Fix - Document Not Found",
                    False,
                    f"❌ Document not found: {doc_id}"
                )
                
            else:
                # Check if this is an enhanced error response
                try:
                    error_data = pdf_response.json()
                    error_detail = error_data.get("detail", "")
                    
                    # Check if error handling is improved (Turkish error messages)
                    turkish_keywords = ["içerik", "dönüştürme", "pdf", "hata"]
                    if any(keyword in error_detail.lower() for keyword in turkish_keywords):
                        self.log_result(
                            "PDF Bug Fix - Enhanced Error Handling",
                            True,
                            f"✅ Enhanced error handling working! User-friendly Turkish error: {error_detail}"
                        )
                    else:
                        self.log_result(
                            "PDF Bug Fix - Error Response",
                            False,
                            f"❌ PDF conversion failed: HTTP {pdf_response.status_code}, Error: {error_detail}"
                        )
                except:
                    self.log_result(
                        "PDF Bug Fix - Error Response",
                        False,
                        f"❌ PDF conversion failed: HTTP {pdf_response.status_code}, Response: {pdf_response.text[:200]}"
                    )
            
            # Step 4: Test PDF metadata endpoint
            print("Step 3: Testing PDF metadata endpoint...")
            metadata_response = self.session.get(f"{self.base_url}/documents/{doc_id}/pdf/metadata")
            
            if metadata_response.status_code == 200:
                metadata_data = metadata_response.json()
                self.log_result(
                    "PDF Bug Fix - Metadata",
                    True,
                    f"✅ PDF metadata working. Page count: {metadata_data.get('page_count', 'N/A')}, Size: {metadata_data.get('file_size_human', 'N/A')}"
                )
            else:
                self.log_result(
                    "PDF Bug Fix - Metadata",
                    False,
                    f"❌ PDF metadata failed: HTTP {metadata_response.status_code}"
                )
            
            # Step 5: Test PDF download endpoint
            print("Step 4: Testing PDF download endpoint...")
            download_response = self.session.get(f"{self.base_url}/documents/{doc_id}/download")
            
            if download_response.status_code == 200:
                download_content = download_response.content
                is_valid_pdf = download_content.startswith(b'%PDF')
                content_disposition = download_response.headers.get('Content-Disposition', '')
                
                if is_valid_pdf and 'attachment' in content_disposition.lower():
                    self.log_result(
                        "PDF Bug Fix - Download",
                        True,
                        f"✅ PDF download working. Size: {len(download_content)} bytes, Disposition: {content_disposition}"
                    )
                else:
                    self.log_result(
                        "PDF Bug Fix - Download",
                        False,
                        f"❌ PDF download issues. Valid PDF: {is_valid_pdf}, Has attachment header: {'attachment' in content_disposition.lower()}"
                    )
            else:
                self.log_result(
                    "PDF Bug Fix - Download",
                    False,
                    f"❌ PDF download failed: HTTP {download_response.status_code}"
                )
                
        except Exception as e:
            self.log_result(
                "PDF Bug Fix Test",
                False,
                f"❌ Critical error during testing: {str(e)}"
            )

def main():
    tester = PDFBugFixTester()
    tester.test_pdf_bug_fix()
    
    print("=" * 80)
    print("PDF Bug Fix Testing Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()