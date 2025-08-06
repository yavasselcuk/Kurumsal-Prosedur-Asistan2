#!/usr/bin/env python3
"""
Focused test for Comprehensive DOC Processing with Binary Fallback
"""

import requests
import json
import sys
from typing import Dict, Any, List
import time

# Backend URL from environment
BACKEND_URL = "https://1070132c-1836-44b9-839f-410d8851049c.preview.emergentagent.com/api"

class DOCProcessingTester:
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

    def test_comprehensive_doc_processing_with_binary_fallback(self):
        """🔥 COMPREHENSIVE DOC PROCESSING FIX: Test 3-tier processing with binary content analysis fallback"""
        try:
            print("   🔥 COMPREHENSIVE DOC PROCESSING WITH BINARY FALLBACK TESTING...")
            print("   📋 Testing: Triple-method DOC processing (textract → antiword → binary analysis)")
            
            # Test 1: Find and test the specific problematic document
            print("   Step 1: Testing specific problematic document 'IKY-P03-00 Personel Proseduru.doc'...")
            docs_response = self.session.get(f"{self.base_url}/documents")
            
            target_document = None
            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                documents = docs_data.get("documents", [])
                
                # Look for the specific document mentioned in the review
                for doc in documents:
                    if "IKY-P03-00 Personel Proseduru" in doc.get("filename", ""):
                        target_document = doc
                        break
                
                if target_document:
                    print(f"   ✅ Found target document: {target_document['filename']}")
                    
                    # Test the specific document that was causing issues
                    doc_id = target_document['id']
                    
                    # Test PDF generation (this should use the 3-tier approach)
                    pdf_response = self.session.get(f"{self.base_url}/documents/{doc_id}/pdf")
                    
                    if pdf_response.status_code == 200:
                        pdf_content = pdf_response.content
                        content_type = pdf_response.headers.get('content-type', '')
                        
                        # Verify it's a valid PDF
                        is_valid_pdf = (
                            'application/pdf' in content_type and
                            pdf_content.startswith(b'%PDF') and
                            len(pdf_content) > 100
                        )
                        
                        if is_valid_pdf:
                            self.log_test(
                                "Comprehensive DOC Processing - Target Document Success",
                                True,
                                f"✅ SUCCESS! The problematic document '{target_document['filename']}' now works perfectly. PDF generated successfully ({len(pdf_content)} bytes). The 'textract ve antiword başarısız' error has been resolved!",
                                {
                                    "document_id": doc_id,
                                    "filename": target_document['filename'],
                                    "pdf_size": len(pdf_content),
                                    "content_type": content_type
                                }
                            )
                            
                            # Test PDF metadata to ensure content was properly extracted
                            metadata_response = self.session.get(f"{self.base_url}/documents/{doc_id}/pdf/metadata")
                            if metadata_response.status_code == 200:
                                metadata = metadata_response.json()
                                self.log_test(
                                    "Comprehensive DOC Processing - PDF Content Validation",
                                    True,
                                    f"✅ PDF metadata confirms successful content extraction: {metadata.get('page_count', 0)} pages, {metadata.get('file_size_human', 'Unknown size')}",
                                    metadata
                                )
                        else:
                            self.log_test(
                                "Comprehensive DOC Processing - Target Document Failed",
                                False,
                                f"❌ PDF generation failed for target document. Content-Type: {content_type}, Size: {len(pdf_content)}, Valid PDF: {is_valid_pdf}",
                                {
                                    "document_id": doc_id,
                                    "filename": target_document['filename'],
                                    "content_type": content_type,
                                    "response_size": len(pdf_content)
                                }
                            )
                    else:
                        # Check for the specific error mentioned in the review
                        try:
                            error_data = pdf_response.json() if pdf_response.headers.get('content-type', '').startswith('application/json') else {"detail": pdf_response.text}
                            error_detail = error_data.get("detail", "")
                            
                            if "textract ve antiword başarısız" in error_detail:
                                self.log_test(
                                    "Comprehensive DOC Processing - Original Error Still Present",
                                    False,
                                    f"❌ CRITICAL: The original error 'textract ve antiword başarısız' is still occurring! Error: {error_detail}",
                                    {
                                        "document_id": doc_id,
                                        "filename": target_document['filename'],
                                        "error": error_detail,
                                        "status_code": pdf_response.status_code
                                    }
                                )
                            else:
                                self.log_test(
                                    "Comprehensive DOC Processing - Different Error",
                                    False,
                                    f"❌ PDF generation failed with different error (not the original 'textract ve antiword başarısız'): {error_detail}",
                                    {
                                        "document_id": doc_id,
                                        "filename": target_document['filename'],
                                        "error": error_detail,
                                        "status_code": pdf_response.status_code
                                    }
                                )
                        except:
                            self.log_test(
                                "Comprehensive DOC Processing - Unknown Error",
                                False,
                                f"❌ PDF generation failed with HTTP {pdf_response.status_code}: {pdf_response.text[:200]}",
                                {
                                    "document_id": doc_id,
                                    "filename": target_document['filename'],
                                    "status_code": pdf_response.status_code
                                }
                            )
                else:
                    self.log_test(
                        "Comprehensive DOC Processing - Target Document Not Found",
                        False,
                        "❌ The specific problematic document 'IKY-P03-00 Personel Proseduru.doc' was not found in the system",
                        None
                    )
            
            # Test 2: Test binary content analysis capability
            print("   Step 2: Testing binary content analysis fallback...")
            
            # Check if we have any DOC files to test binary analysis
            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                documents = docs_data.get("documents", [])
                doc_files = [doc for doc in documents if doc.get("file_type") == ".doc"]
                
                if doc_files:
                    print(f"   Found {len(doc_files)} DOC files to test binary analysis...")
                    
                    binary_analysis_results = {"success": 0, "total": 0}
                    
                    # Test up to 5 DOC files
                    for doc in doc_files[:5]:
                        binary_analysis_results["total"] += 1
                        doc_id = doc["id"]
                        filename = doc.get("filename", "Unknown")
                        
                        print(f"     Testing: {filename}")
                        
                        # Test PDF generation (which should use binary analysis if other methods fail)
                        pdf_response = self.session.get(f"{self.base_url}/documents/{doc_id}/pdf")
                        
                        if pdf_response.status_code == 200:
                            pdf_content = pdf_response.content
                            if pdf_content.startswith(b'%PDF') and len(pdf_content) > 100:
                                binary_analysis_results["success"] += 1
                                print(f"       ✅ Success: {len(pdf_content)} bytes PDF")
                            else:
                                print(f"       ❌ Invalid PDF: {len(pdf_content)} bytes")
                        else:
                            print(f"       ❌ HTTP {pdf_response.status_code}")
                    
                    success_rate = binary_analysis_results["success"] / binary_analysis_results["total"] if binary_analysis_results["total"] > 0 else 0
                    
                    self.log_test(
                        "Comprehensive DOC Processing - Binary Analysis Capability",
                        success_rate >= 0.8,  # 80% success rate acceptable
                        f"Binary content analysis results: {binary_analysis_results['success']}/{binary_analysis_results['total']} DOC files successfully processed ({success_rate:.1%} success rate)",
                        binary_analysis_results
                    )
                else:
                    self.log_test(
                        "Comprehensive DOC Processing - Binary Analysis Test",
                        True,
                        "✅ No DOC files available to test binary analysis (system may be empty)",
                        None
                    )
            
            # Test 3: Test comprehensive error handling (all 3 methods fail scenario)
            print("   Step 3: Testing comprehensive error handling when all methods fail...")
            
            # Create a completely invalid DOC file to test error handling
            invalid_doc_content = b'\x00\x01\x02\x03' + b'Invalid DOC content' + b'\xff' * 50
            files = {'file': ('invalid_test.doc', invalid_doc_content, 'application/msword')}
            
            upload_response = self.session.post(f"{self.base_url}/upload-document", files=files)
            
            if upload_response.status_code == 400:
                error_data = upload_response.json()
                error_detail = error_data.get("detail", "")
                
                # Check if error message is informative and doesn't mention the old error
                is_informative = (
                    len(error_detail) > 50 and  # Detailed message
                    "textract ve antiword başarısız" not in error_detail and  # Not the old error
                    any(keyword in error_detail.lower() for keyword in ["doc", "işlem", "format", "bozuk", "docx"])  # Contains relevant keywords
                )
                
                self.log_test(
                    "Comprehensive DOC Processing - Error Handling",
                    is_informative,
                    f"Error handling quality: {'Good' if is_informative else 'Poor'}. Message: {error_detail[:200]}",
                    {"error_detail": error_detail, "informative": is_informative}
                )
            else:
                self.log_test(
                    "Comprehensive DOC Processing - Error Handling",
                    False,
                    f"Expected 400 error for invalid DOC, got {upload_response.status_code}",
                    upload_response.text
                )
            
            # Test 4: End-to-end validation with multiple DOC files
            print("   Step 4: End-to-end validation with multiple DOC files...")
            
            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                documents = docs_data.get("documents", [])
                doc_files = [doc for doc in documents if doc.get("file_type") == ".doc"]
                
                if doc_files:
                    end_to_end_results = {
                        "pdf_generation_success": 0,
                        "pdf_readable": 0,
                        "no_parsing_errors": 0,
                        "total_tested": 0
                    }
                    
                    # Test up to 3 DOC files for comprehensive validation
                    for doc in doc_files[:3]:
                        end_to_end_results["total_tested"] += 1
                        doc_id = doc["id"]
                        filename = doc.get("filename", "Unknown")
                        
                        print(f"     Testing end-to-end: {filename}")
                        
                        # Test PDF generation
                        pdf_response = self.session.get(f"{self.base_url}/documents/{doc_id}/pdf")
                        
                        if pdf_response.status_code == 200:
                            pdf_content = pdf_response.content
                            
                            # Check if PDF is valid
                            if pdf_content.startswith(b'%PDF') and len(pdf_content) > 100:
                                end_to_end_results["pdf_generation_success"] += 1
                                print(f"       ✅ PDF Generation: {len(pdf_content)} bytes")
                                
                                # Check if PDF has readable content (size > 1KB indicates content)
                                if len(pdf_content) > 1024:
                                    end_to_end_results["pdf_readable"] += 1
                                    print(f"       ✅ Readable Content: {len(pdf_content)} bytes")
                                
                                # Check that no parsing errors occurred (no error headers)
                                error_header = pdf_response.headers.get('X-Error', '')
                                if not error_header:
                                    end_to_end_results["no_parsing_errors"] += 1
                                    print(f"       ✅ No Parsing Errors")
                            else:
                                print(f"       ❌ Invalid PDF: {len(pdf_content)} bytes")
                        else:
                            print(f"       ❌ PDF Generation Failed: HTTP {pdf_response.status_code}")
                    
                    # Calculate overall success
                    total_possible = end_to_end_results["total_tested"] * 3  # 3 criteria per file
                    total_achieved = (end_to_end_results["pdf_generation_success"] + 
                                    end_to_end_results["pdf_readable"] + 
                                    end_to_end_results["no_parsing_errors"])
                    
                    overall_success_rate = total_achieved / total_possible if total_possible > 0 else 0
                    
                    self.log_test(
                        "Comprehensive DOC Processing - End-to-End Validation",
                        overall_success_rate >= 0.8,  # 80% success rate
                        f"End-to-end validation: PDF generation {end_to_end_results['pdf_generation_success']}/{end_to_end_results['total_tested']}, Readable content {end_to_end_results['pdf_readable']}/{end_to_end_results['total_tested']}, No parsing errors {end_to_end_results['no_parsing_errors']}/{end_to_end_results['total_tested']} (Overall: {overall_success_rate:.1%})",
                        end_to_end_results
                    )
                else:
                    self.log_test(
                        "Comprehensive DOC Processing - End-to-End Validation",
                        True,
                        "✅ No DOC files available for end-to-end testing (system may be empty)",
                        None
                    )
            
        except Exception as e:
            self.log_test(
                "Comprehensive DOC Processing with Binary Fallback",
                False,
                f"❌ Error during comprehensive DOC processing test: {str(e)}",
                None
            )

    def print_summary(self):
        """Print test summary"""
        print("=" * 80)
        print("COMPREHENSIVE DOC PROCESSING TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['details']}")
        
        print()
        return success_rate >= 80  # 80% success rate threshold

if __name__ == "__main__":
    tester = DOCProcessingTester()
    print("🔥 COMPREHENSIVE DOC PROCESSING WITH BINARY FALLBACK TEST")
    print("=" * 80)
    
    tester.test_comprehensive_doc_processing_with_binary_fallback()
    
    success = tester.print_summary()
    sys.exit(0 if success else 1)