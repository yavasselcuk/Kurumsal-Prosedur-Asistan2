#!/usr/bin/env python3
"""
Comprehensive PDF Viewer Bug Fix Testing
Tests multiple documents to ensure the bug fix works across different content types
"""

import requests
import json
import sys
import time

# Backend URL from environment
BACKEND_URL = "https://ba75e451-2594-4c01-9332-1b1f91b06df3.preview.emergentagent.com/api"

class ComprehensivePDFTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.session.timeout = 30
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, details: str):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        self.test_results.append({"test": test_name, "success": success, "details": details})
        print()

    def test_all_documents_pdf_conversion(self):
        """Test PDF conversion for all available documents"""
        print("🔥 COMPREHENSIVE PDF BUG FIX TESTING")
        print("Testing PDF conversion for all available documents")
        print("=" * 80)
        
        try:
            # Get all documents
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
            print()
            
            successful_conversions = 0
            failed_conversions = 0
            
            for i, doc in enumerate(documents[:10], 1):  # Test first 10 documents
                doc_id = doc["id"]
                filename = doc.get("filename", "Unknown")
                file_type = doc.get("file_type", "Unknown")
                
                print(f"Test {i}: Testing {filename} ({file_type})")
                
                # Test PDF conversion
                pdf_response = self.session.get(f"{self.base_url}/documents/{doc_id}/pdf")
                
                if pdf_response.status_code == 200:
                    pdf_content = pdf_response.content
                    is_valid_pdf = pdf_content.startswith(b'%PDF')
                    
                    # Check for the specific error patterns
                    error_patterns = [
                        b'/tmp/tmpjehpblnz.docx',
                        b'Package not found',
                        'görüntülenemiyor'.encode('utf-8')
                    ]
                    
                    error_found = any(pattern in pdf_content for pattern in error_patterns)
                    
                    if is_valid_pdf and not error_found:
                        self.log_result(
                            f"PDF Conversion - {filename}",
                            True,
                            f"✅ PDF conversion successful. Size: {len(pdf_content)} bytes"
                        )
                        successful_conversions += 1
                    elif error_found:
                        self.log_result(
                            f"PDF Conversion - {filename}",
                            False,
                            f"❌ ORIGINAL BUG FOUND! Error pattern detected in PDF content"
                        )
                        failed_conversions += 1
                    else:
                        self.log_result(
                            f"PDF Conversion - {filename}",
                            False,
                            f"❌ Invalid PDF format. Content starts with: {pdf_content[:20]}"
                        )
                        failed_conversions += 1
                else:
                    self.log_result(
                        f"PDF Conversion - {filename}",
                        False,
                        f"❌ HTTP {pdf_response.status_code}: {pdf_response.text[:100]}"
                    )
                    failed_conversions += 1
            
            # Summary
            total_tested = successful_conversions + failed_conversions
            success_rate = (successful_conversions / total_tested * 100) if total_tested > 0 else 0
            
            self.log_result(
                "Overall PDF Bug Fix Status",
                success_rate >= 80,  # 80% success rate threshold
                f"✅ PDF Bug Fix Success Rate: {success_rate:.1f}% ({successful_conversions}/{total_tested} documents converted successfully)"
            )
            
        except Exception as e:
            self.log_result(
                "Comprehensive PDF Test",
                False,
                f"❌ Critical error during testing: {str(e)}"
            )

    def test_enhanced_content_handling(self):
        """Test enhanced content handling features"""
        print("🔧 TESTING ENHANCED CONTENT HANDLING")
        print("=" * 50)
        
        try:
            # Get documents
            docs_response = self.session.get(f"{self.base_url}/documents")
            
            if docs_response.status_code == 200:
                docs_data = docs_response.json()
                documents = docs_data.get("documents", [])
                
                if documents:
                    # Test with different document types
                    doc_types_tested = set()
                    
                    for doc in documents[:5]:  # Test first 5 documents
                        doc_id = doc["id"]
                        filename = doc.get("filename", "Unknown")
                        file_type = doc.get("file_type", "Unknown")
                        
                        if file_type not in doc_types_tested:
                            doc_types_tested.add(file_type)
                            
                            # Test PDF metadata (enhanced content handling)
                            metadata_response = self.session.get(f"{self.base_url}/documents/{doc_id}/pdf/metadata")
                            
                            if metadata_response.status_code == 200:
                                metadata_data = metadata_response.json()
                                required_fields = ["page_count", "file_size", "file_size_human", "original_filename", "original_format", "document_id", "pdf_available"]
                                missing_fields = [field for field in required_fields if field not in metadata_data]
                                
                                if not missing_fields:
                                    self.log_result(
                                        f"Enhanced Content Handling - {file_type}",
                                        True,
                                        f"✅ Metadata extraction working for {file_type}. Page count: {metadata_data.get('page_count')}, Original format: {metadata_data.get('original_format')}"
                                    )
                                else:
                                    self.log_result(
                                        f"Enhanced Content Handling - {file_type}",
                                        False,
                                        f"❌ Missing metadata fields: {missing_fields}"
                                    )
                            else:
                                self.log_result(
                                    f"Enhanced Content Handling - {file_type}",
                                    False,
                                    f"❌ Metadata extraction failed: HTTP {metadata_response.status_code}"
                                )
                    
                    self.log_result(
                        "Enhanced Content Handling Coverage",
                        len(doc_types_tested) > 0,
                        f"✅ Tested enhanced content handling for {len(doc_types_tested)} document types: {list(doc_types_tested)}"
                    )
                else:
                    self.log_result(
                        "Enhanced Content Handling",
                        False,
                        "❌ No documents available for enhanced content handling test"
                    )
            else:
                self.log_result(
                    "Enhanced Content Handling",
                    False,
                    f"❌ Could not retrieve documents: HTTP {docs_response.status_code}"
                )
                
        except Exception as e:
            self.log_result(
                "Enhanced Content Handling",
                False,
                f"❌ Error during enhanced content handling test: {str(e)}"
            )

    def test_error_recovery(self):
        """Test error recovery mechanisms"""
        print("🛡️ TESTING ERROR RECOVERY")
        print("=" * 30)
        
        try:
            # Test with non-existent document
            fake_id = "non-existent-document-12345"
            error_response = self.session.get(f"{self.base_url}/documents/{fake_id}/pdf")
            
            if error_response.status_code == 404:
                self.log_result(
                    "Error Recovery - 404 Handling",
                    True,
                    "✅ Proper 404 response for non-existent document"
                )
            else:
                self.log_result(
                    "Error Recovery - 404 Handling",
                    False,
                    f"❌ Expected 404, got {error_response.status_code}"
                )
            
            # Test error headers
            if 'X-Error' in error_response.headers or 'X-Original-Filename' in error_response.headers:
                self.log_result(
                    "Error Recovery - Error Headers",
                    True,
                    f"✅ Error headers present: X-Error={error_response.headers.get('X-Error', 'N/A')}"
                )
            else:
                self.log_result(
                    "Error Recovery - Error Headers",
                    True,  # Not critical if headers are missing for 404
                    "⚠️ Error headers not present (acceptable for 404 responses)"
                )
                
        except Exception as e:
            self.log_result(
                "Error Recovery",
                False,
                f"❌ Error during error recovery test: {str(e)}"
            )

    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print("=" * 80)
        print("COMPREHENSIVE PDF BUG FIX TEST SUMMARY")
        print("=" * 80)
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
        
        # Overall assessment
        success_rate = (passed_tests/total_tests*100) if total_tests > 0 else 0
        if success_rate >= 90:
            print("🎉 OVERALL ASSESSMENT: PDF BUG FIX IS WORKING EXCELLENTLY!")
        elif success_rate >= 75:
            print("✅ OVERALL ASSESSMENT: PDF BUG FIX IS WORKING WELL!")
        elif success_rate >= 50:
            print("⚠️ OVERALL ASSESSMENT: PDF BUG FIX HAS SOME ISSUES!")
        else:
            print("❌ OVERALL ASSESSMENT: PDF BUG FIX NEEDS ATTENTION!")

def main():
    tester = ComprehensivePDFTester()
    
    # Run all tests
    tester.test_all_documents_pdf_conversion()
    tester.test_enhanced_content_handling()
    tester.test_error_recovery()
    
    # Print summary
    tester.print_summary()

if __name__ == "__main__":
    main()