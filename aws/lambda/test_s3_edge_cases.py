"""
S3 Edge Case Testing with Actual Deployed Buckets
Tests using the real bucket names from dev environment
"""
import os
import sys
import tempfile
import json
from pathlib import Path

# Set actual bucket names
os.environ['S3_DOCUMENTS_BUCKET'] = 'care-compass-documents-432732422396-dev'
os.environ['S3_PROCESSED_BUCKET'] = 'care-compass-processed-432732422396-dev'
os.environ['S3_VECTORDB_BUCKET'] = 'care-compass-vectordb-432732422396-dev'

sys.path.insert(0, '.')
from s3_manager import S3Manager

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_section(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")

def success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def info(msg):
    print(f"{Colors.CYAN}  → {msg}{Colors.END}")

# Test tracking
passed = 0
failed = 0

print_section("S3 EDGE CASE TESTING - ACTUAL DEPLOYED BUCKETS")

# Initialize
try:
    s3_manager = S3Manager(region='us-east-1')
    success("S3Manager initialized")
    info(f"Documents: {s3_manager.documents_bucket}")
    info(f"Processed: {s3_manager.processed_bucket}")
    info(f"VectorDB: {s3_manager.vectordb_bucket}")
except Exception as e:
    error(f"Failed to initialize: {e}")
    sys.exit(1)

# TEST 1: Various file types
print_section("TEST 1: Various File Types")

file_types = {
    'text': ('document.txt', 'Clinical notes for trauma-informed care assessment.'),
    'json': ('config.json', json.dumps({'type': 'config', 'trauma_informed': True})),
    'csv': ('data.csv', 'id,name,condition\n1,Patient1,PTSD\n2,Patient2,Anxiety'),
}

for ftype, (filename, content) in file_types.items():
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=Path(filename).suffix) as f:
            f.write(content)
            temp_path = f.name
        
        key = f"edge_case_tests/{filename}"
        upload_ok = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
        
        if upload_ok:
            success(f"Uploaded {ftype}: {filename}")
            passed += 1
            os.unlink(temp_path)
        else:
            error(f"Failed to upload {ftype}")
            failed += 1
    except Exception as e:
        error(f"Exception with {ftype}: {str(e)[:100]}")
        failed += 1

# TEST 2: Filename edge cases (safe subset)
print_section("TEST 2: Filename Edge Cases")

edge_case_names = [
    'spaces in name.txt',
    'dashes-in-name.txt',
    'underscores_in_name.txt',
    'multiple.dots.here.txt',
]

for filename in edge_case_names:
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(f"Test: {filename}")
            temp_path = f.name
        
        key = f"edge_case_tests/{filename}"
        upload_ok = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
        
        if upload_ok:
            success(f"Handled: {filename}")
            passed += 1
            os.unlink(temp_path)
        else:
            error(f"Failed: {filename}")
            failed += 1
    except Exception as e:
        error(f"Exception: {str(e)[:100]}")
        failed += 1

# TEST 3: File sizes
print_section("TEST 3: File Size Variations")

size_cases = [
    ('small.txt', 100),
    ('medium.txt', 50 * 1024),      # 50KB
    ('larger.txt', 500 * 1024),     # 500KB
]

for filename, size in size_cases:
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write('x' * size)
            temp_path = f.name
        
        key = f"edge_case_tests/{filename}"
        upload_ok = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
        
        if upload_ok:
            info_result = s3_manager.get_object_info(key, bucket=s3_manager.documents_bucket)
            if info_result:
                success(f"{filename}: {info_result['size']} bytes uploaded")
                passed += 1
            else:
                error(f"Failed to get info for {filename}")
                failed += 1
        else:
            error(f"Failed to upload {filename}")
            failed += 1
        
        os.unlink(temp_path)
    except Exception as e:
        error(f"Exception: {str(e)[:100]}")
        failed += 1

# TEST 4: Unicode content
print_section("TEST 4: Unicode & Special Characters")

try:
    content = "Notes: PTSD Symptoms (nightmares, hypervigilance) • Trauma-informed care & therapeutic support 你好 مرحبا"
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    key = "edge_case_tests/unicode_content.txt"
    upload_ok = s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
    
    if upload_ok:
        success("Uploaded Unicode content")
        passed += 1
        
        # Verify roundtrip
        verify_path = tempfile.mktemp()
        if s3_manager.download_document(key, verify_path, bucket=s3_manager.documents_bucket):
            with open(verify_path, 'r', encoding='utf-8') as f:
                downloaded = f.read()
            if downloaded == content:
                success("Unicode preserved in roundtrip")
                passed += 1
            else:
                error("Unicode corrupted")
                failed += 1
            os.unlink(verify_path)
    else:
        error("Failed to upload Unicode")
        failed += 1
    
    os.unlink(temp_path)
except Exception as e:
    error(f"Unicode test failed: {str(e)[:100]}")
    failed += 1

# TEST 5: Cross-bucket operations
print_section("TEST 5: Cross-Bucket Document Movement")

try:
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Document to be processed")
        temp_path = f.name
    
    source_key = "edge_case_tests/source_doc.txt"
    target_key = "processed/source_doc.txt"
    
    # Upload to documents
    upload_ok = s3_manager.upload_document(temp_path, source_key, bucket=s3_manager.documents_bucket)
    if upload_ok:
        success("Uploaded to documents bucket")
        passed += 1
        
        # Download and re-upload to processed (simulating processing)
        temp_verify = tempfile.mktemp()
        download_ok = s3_manager.download_document(source_key, temp_verify, bucket=s3_manager.documents_bucket)
        if download_ok:
            upload_ok2 = s3_manager.upload_document(temp_verify, target_key, bucket=s3_manager.processed_bucket)
            if upload_ok2:
                success("Cross-bucket document movement successful")
                passed += 1
            else:
                error("Failed to upload to processed bucket")
                failed += 1
            os.unlink(temp_verify)
    else:
        error("Failed to upload to documents")
        failed += 1
    
    os.unlink(temp_path)
except Exception as e:
    error(f"Cross-bucket test failed: {str(e)[:100]}")
    failed += 1

# TEST 6: Listing documents
print_section("TEST 6: Listing & Pagination")

try:
    docs = s3_manager.list_documents(bucket=s3_manager.documents_bucket)
    success(f"Listed {len(docs)} documents from documents bucket")
    if docs:
        info(f"Sample: {docs[0]['key']}")
    passed += 1
    
    processed = s3_manager.list_documents(bucket=s3_manager.processed_bucket)
    success(f"Listed {len(processed)} documents from processed bucket")
    passed += 1
except Exception as e:
    error(f"Listing failed: {str(e)[:100]}")
    failed += 1

# TEST 7: Signed URLs
print_section("TEST 7: Signed URL Generation")

try:
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("Content for signed URL")
        temp_path = f.name
    
    key = "edge_case_tests/signed_url_test.txt"
    s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket)
    
    for expiration in [300, 3600]:
        try:
            url = s3_manager.create_signed_url(key, expiration=expiration, bucket=s3_manager.documents_bucket)
            if url and url.startswith('https://'):
                success(f"Generated signed URL ({expiration}s expiry)")
                passed += 1
            else:
                error(f"Invalid URL generated")
                failed += 1
        except Exception as e:
            error(f"Signed URL generation failed: {str(e)[:50]}")
            failed += 1
    
    os.unlink(temp_path)
except Exception as e:
    error(f"Signed URL test failed: {str(e)[:100]}")
    failed += 1

# TEST 8: Error handling
print_section("TEST 8: Error Handling")

try:
    # Try to download non-existent file
    result = s3_manager.download_document("nonexistent/file.txt", tempfile.mktemp(), bucket=s3_manager.documents_bucket)
    if not result:
        success("Correctly failed to download non-existent file")
        passed += 1
    else:
        error("Should have failed on non-existent file")
        failed += 1
except Exception as e:
    success(f"Correctly raised exception for non-existent file")
    passed += 1

# TEST 9: Bucket connectivity
print_section("TEST 9: Bucket Connectivity Verification")

try:
    for bucket_name, bucket_var in [
        ("Documents", s3_manager.documents_bucket),
        ("Processed", s3_manager.processed_bucket),
        ("VectorDB", s3_manager.vectordb_bucket),
    ]:
        try:
            result = s3_manager.list_documents(bucket=bucket_var)
            success(f"{bucket_name} bucket accessible")
            passed += 1
        except Exception as e:
            error(f"{bucket_name} bucket NOT accessible")
            failed += 1
except Exception as e:
    error(f"Connectivity test failed: {str(e)}")
    failed += 1

# Summary
print_section("TEST SUMMARY")
total = passed + failed
success_rate = (passed / total * 100) if total > 0 else 0

info(f"Total: {total} tests")
success(f"Passed: {passed}")
if failed > 0:
    error(f"Failed: {failed}")

if success_rate >= 80:
    success(f"Success rate: {success_rate:.1f}%")
elif success_rate >= 50:
    print(f"{Colors.YELLOW}⚠ Success rate: {success_rate:.1f}%{Colors.END}")
else:
    error(f"Success rate: {success_rate:.1f}%")

print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")
