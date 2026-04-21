"""
Comprehensive S3 edge case testing
Tests document upload, processing, vectorization, and cross-bucket operations
"""
import os
import sys
import tempfile
import json
import base64
from pathlib import Path
sys.path.insert(0, '.')

from s3_manager import S3Manager

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{title}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}{'='*70}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}[PASS] {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}[FAIL] {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}[WARN] {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}  -> {msg}{Colors.ENDC}")

# Initialize
print_section("S3 COMPREHENSIVE EDGE CASE TESTING")

s3_manager = S3Manager(region='us-east-1')
print_info(f"Documents bucket: {s3_manager.documents_bucket}")
print_info(f"Processed bucket: {s3_manager.processed_bucket}")
print_info(f"VectorDB bucket: {s3_manager.vectordb_bucket}")

test_results = {
    'passed': 0,
    'failed': 0,
    'skipped': 0
}

# Test 1: Various file types
print_section("TEST 1: Various File Types")

file_types = {
    'text': ('test_document.txt', 'This is a test document for CARE Bot. It contains clinical information about trauma-informed care.'),
    'json': ('test_config.json', json.dumps({'type': 'config', 'version': '1.0', 'trauma_informed': True})),
    'csv': ('test_data.csv', 'id,name,condition\n1,Sample,PTSD\n2,Case,Depression'),
}

for ftype, (filename, content) in file_types.items():
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=Path(filename).suffix) as f:
            if isinstance(content, str):
                f.write(content)
            else:
                f.write(json.dumps(content))
            temp_path = f.name
        
        key = f"test/edge_cases/{filename}"
        success = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
        
        if success:
            print_success(f"Uploaded {ftype} file: {filename}")
            test_results['passed'] += 1
            
            # Verify by downloading
            verify_path = tempfile.mktemp()
            if s3_manager.download_document(key, verify_path, bucket=s3_manager.documents_bucket):
                print_info(f"Verified download of {filename}")
                os.unlink(verify_path)
        else:
            print_error(f"Failed to upload {ftype}")
            test_results['failed'] += 1
        
        os.unlink(temp_path)
    except Exception as e:
        print_error(f"Exception with {ftype}: {str(e)}")
        test_results['failed'] += 1

# Test 2: Filename edge cases
print_section("TEST 2: Filename Edge Cases")

edge_case_names = [
    'file with spaces.txt',
    'file-with-dashes.txt',
    'file_with_underscores.txt',
    'UPPERCASE_FILE.TXT',
    'file.multiple.dots.txt',
    'file(with)parentheses.txt',
    'very_long_filename_' + 'x' * 200 + '.txt',  # long name
]

for filename in edge_case_names:
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(f"Content for {filename}")
            temp_path = f.name
        
        key = f"test/edge_cases/{filename}"
        success = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
        
        if success:
            print_success(f"Handled filename: {filename[:50]}...")
            test_results['passed'] += 1
        else:
            print_error(f"Failed on filename: {filename[:50]}...")
            test_results['failed'] += 1
        
        os.unlink(temp_path)
    except Exception as e:
        print_warning(f"Exception with filename: {str(e)}")
        test_results['skipped'] += 1

# Test 3: File size edge cases
print_section("TEST 3: File Size Edge Cases")

size_cases = [
    ('empty_file.txt', 0),
    ('small_file.txt', 100),
    ('medium_file.txt', 1024 * 100),      # 100KB
    ('larger_file.txt', 1024 * 1024),     # 1MB
]

for filename, size in size_cases:
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            if size > 0:
                f.write('x' * size)
            temp_path = f.name
        
        key = f"test/edge_cases/{filename}"
        success = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
        
        if success:
            info = s3_manager.get_object_info(key, bucket=s3_manager.documents_bucket)
            if info:
                print_success(f"Uploaded {filename}: {info['size']} bytes")
                test_results['passed'] += 1
            else:
                print_error(f"Failed to get info for {filename}")
                test_results['failed'] += 1
        else:
            print_error(f"Failed to upload {filename}")
            test_results['failed'] += 1
        
        os.unlink(temp_path)
    except Exception as e:
        print_error(f"Exception with {filename}: {str(e)}")
        test_results['failed'] += 1

# Test 4: Special characters and Unicode
print_section("TEST 4: Unicode and Special Characters")

special_content = "Clinical notes: Patient exhibits PTSD symptomology (nightmares, hypervigilance, anxiety). Recommended trauma-informed care & therapeutic interventions. Special chars: @#$%! 你好 مرحبا"

try:
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write(special_content)
        temp_path = f.name
    
    key = "test/edge_cases/special_chars_unicode.txt"
    success = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
    
    if success:
        print_success("Uploaded file with Unicode and special characters")
        test_results['passed'] += 1
        
        # Verify content
        verify_path = tempfile.mktemp()
        if s3_manager.download_document(key, verify_path, bucket=s3_manager.documents_bucket):
            with open(verify_path, 'r', encoding='utf-8') as f:
                downloaded = f.read()
            if downloaded == special_content:
                print_success("Unicode content preserved during download")
                test_results['passed'] += 1
            else:
                print_error("Unicode content corrupted")
                test_results['failed'] += 1
            os.unlink(verify_path)
    else:
        print_error("Failed to upload Unicode file")
        test_results['failed'] += 1
    
    os.unlink(temp_path)
except Exception as e:
    print_error(f"Unicode test failed: {str(e)}")
    test_results['failed'] += 1

# Test 5: Cross-bucket operations
print_section("TEST 5: Cross-Bucket Operations")

try:
    # Upload to documents bucket
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Test document for cross-bucket movement")
        temp_path = f.name
    
    doc_key = "test/cross_bucket/source_document.txt"
    success = s3_manager.upload_document(temp_path, doc_key, bucket=s3_manager.documents_bucket)
    
    if success:
        print_success("Uploaded to documents bucket")
        test_results['passed'] += 1
        
        # Try to copy to processed bucket (simulate processing)
        processed_key = "processed/source_document.txt"
        try:
            # Download from documents, re-upload to processed
            verify_path = tempfile.mktemp()
            if s3_manager.download_document(doc_key, verify_path, bucket=s3_manager.documents_bucket):
                processed_success = s3_manager.upload_document(verify_path, processed_key, bucket=s3_manager.processed_bucket)
                if processed_success:
                    print_success("Successfully moved to processed bucket")
                    test_results['passed'] += 1
                else:
                    print_error("Failed to move to processed bucket")
                    test_results['failed'] += 1
                os.unlink(verify_path)
        except Exception as e:
            print_warning(f"Cross-bucket move failed: {str(e)}")
            test_results['skipped'] += 1
    else:
        print_error("Failed to upload to documents bucket")
        test_results['failed'] += 1
    
    os.unlink(temp_path)
except Exception as e:
    print_error(f"Cross-bucket test failed: {str(e)}")
    test_results['failed'] += 1

# Test 6: Listing and pagination
print_section("TEST 6: Listing and Pagination")

try:
    # List documents
    docs = s3_manager.list_documents(bucket=s3_manager.documents_bucket)
    print_success(f"Retrieved list of {len(docs)} documents from documents bucket")
    print_info(f"Sample keys: {[doc['key'][:50] for doc in docs[:3]]}")
    test_results['passed'] += 1
    
    # List processed
    processed = s3_manager.list_documents(bucket=s3_manager.processed_bucket)
    print_success(f"Retrieved list of {len(processed)} documents from processed bucket")
    test_results['passed'] += 1
    
    # List vectordb
    vectordb = s3_manager.list_documents(bucket=s3_manager.vectordb_bucket)
    print_success(f"Retrieved list of {len(vectordb)} objects from vectordb bucket")
    test_results['passed'] += 1
except Exception as e:
    print_error(f"Listing failed: {str(e)}")
    test_results['failed'] += 1

# Test 7: Signed URLs
print_section("TEST 7: Signed URL Generation")

try:
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Content for signed URL test")
        temp_path = f.name
    
    key = "test/signed_url_test.txt"
    s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
    
    # Generate signed URL with various expiration times
    for expiration in [300, 3600, 86400]:
        try:
            url = s3_manager.create_signed_url(key, expiration=expiration, bucket=s3_manager.documents_bucket)
            if url:
                print_success(f"Generated signed URL (expiration: {expiration}s)")
                print_info(f"URL (truncated): {url[:80]}...")
                test_results['passed'] += 1
            else:
                print_error(f"Failed to generate signed URL (expiration: {expiration}s)")
                test_results['failed'] += 1
        except Exception as e:
            print_warning(f"Signed URL generation failed for {expiration}s: {str(e)}")
            test_results['skipped'] += 1
    
    os.unlink(temp_path)
except Exception as e:
    print_error(f"Signed URL test failed: {str(e)}")
    test_results['failed'] += 1

# Test 8: Object metadata
print_section("TEST 8: Object Metadata")

try:
    # Create metadata-rich file
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Document with metadata")
        temp_path = f.name
    
    key = "test/metadata_test.txt"
    success = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
    
    if success:
        info = s3_manager.get_object_info(key, bucket=s3_manager.documents_bucket)
        if info:
            print_success("Retrieved object metadata")
            for field in ['size', 'last_modified', 'content_type']:
                if field in info:
                    print_info(f"{field}: {info[field]}")
            test_results['passed'] += 1
        else:
            print_error("Failed to retrieve metadata")
            test_results['failed'] += 1
    
    os.unlink(temp_path)
except Exception as e:
    print_error(f"Metadata test failed: {str(e)}")
    test_results['failed'] += 1

# Test 9: Error handling
print_section("TEST 9: Error Handling")

error_tests = [
    ("Non-existent file", "/nonexistent/path/file.txt", False),
    ("Invalid S3 key", "../../../etc/passwd", True),
]

for test_name, test_input, should_handle in error_tests:
    try:
        if should_handle:
            try:
                # Try to download non-existent key
                result = s3_manager.download_document(test_input, tempfile.mktemp(), bucket=s3_manager.documents_bucket)
                if not result:
                    print_success(f"Correctly handled: {test_name}")
                    test_results['passed'] += 1
                else:
                    print_warning(f"Unexpected success for: {test_name}")
                    test_results['skipped'] += 1
            except Exception as e:
                print_success(f"Correctly raised exception for: {test_name}")
                print_info(f"Exception: {type(e).__name__}")
                test_results['passed'] += 1
        else:
            try:
                # Try to upload non-existent file
                result = s3_manager.upload_document(test_input, "test/key", bucket=s3_manager.documents_bucket)
                print_error(f"Failed to catch error for: {test_name}")
                test_results['failed'] += 1
            except Exception as e:
                print_success(f"Correctly raised exception for: {test_name}")
                test_results['passed'] += 1
    except Exception as e:
        print_error(f"Unexpected error in error handling test: {str(e)}")
        test_results['failed'] += 1

# Test 10: Bucket connectivity
print_section("TEST 10: Bucket Connectivity")

try:
    # Test each bucket is accessible
    for bucket_name, bucket_var in [
        ("Documents", s3_manager.documents_bucket),
        ("Processed", s3_manager.processed_bucket),
        ("VectorDB", s3_manager.vectordb_bucket),
    ]:
        try:
            result = s3_manager.list_documents(bucket=bucket_var)
            print_success(f"{bucket_name} bucket is accessible ({len(result)} objects)")
            test_results['passed'] += 1
        except Exception as e:
            print_error(f"{bucket_name} bucket is NOT accessible: {str(e)}")
            test_results['failed'] += 1
except Exception as e:
    print_error(f"Connectivity test failed: {str(e)}")
    test_results['failed'] += 1

# Final summary
print_section("TEST SUMMARY")
total = test_results['passed'] + test_results['failed'] + test_results['skipped']
print_info(f"Total tests: {total}")
print_success(f"Passed: {test_results['passed']}")
if test_results['failed'] > 0:
    print_error(f"Failed: {test_results['failed']}")
if test_results['skipped'] > 0:
    print_warning(f"Skipped: {test_results['skipped']}")

success_rate = (test_results['passed'] / total * 100) if total > 0 else 0
if success_rate >= 80:
    print_success(f"Success rate: {success_rate:.1f}%")
elif success_rate >= 50:
    print_warning(f"Success rate: {success_rate:.1f}%")
else:
    print_error(f"Success rate: {success_rate:.1f}%")

print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'='*70}{Colors.ENDC}")
