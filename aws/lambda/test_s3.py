"""
Test S3 Manager with actual AWS S3 buckets
Requires AWS credentials configured
"""
import os
import sys
import tempfile
sys.path.insert(0, '.')

from s3_manager import S3Manager

print("=" * 60)
print("TESTING S3 MANAGER WITH AWS")
print("=" * 60)

# Initialize S3 Manager
print("\n1. Initializing S3 Manager...")
try:
    s3_manager = S3Manager(region='us-east-1')
    print(f"[PASS] Documents bucket: {s3_manager.documents_bucket}")
    print(f"[PASS] Processed bucket: {s3_manager.processed_bucket}")
    print(f"[PASS] VectorDB bucket: {s3_manager.vectordb_bucket}")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")
    sys.exit(1)

# Test listing documents
print("\n2. Testing list_documents...")
try:
    docs = s3_manager.list_documents(bucket=s3_manager.documents_bucket)
    print(f"[PASS] Found {len(docs)} documents")
    if docs:
        print(f"  First document: {docs[0]['key']}")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

# Test upload and download
print("\n3. Testing upload_document...")
try:
    # Create a test file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test content for CARE Bot S3 integration")
        test_file = f.name
    
    # Upload
    success = s3_manager.upload_document(
        test_file, 
        "test/test_file.txt",
        bucket=s3_manager.documents_bucket
    )
    
    if success:
        print("[PASS] Upload successful")
    else:
        print("[FAIL] Upload failed")
    
    # Clean up local file
    os.unlink(test_file)
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

# Test download
print("\n4. Testing download_document...")
try:
    download_path = tempfile.mktemp(suffix='.txt')
    success = s3_manager.download_document(
        "test/test_file.txt",
        download_path,
        bucket=s3_manager.documents_bucket
    )
    
    if success:
        with open(download_path, 'r') as f:
            content = f.read()
        print(f"[PASS] Download successful")
        print(f"  Content: {content[:50]}...")
        os.unlink(download_path)
    else:
        print("[FAIL] Download failed")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

# Test get object info
print("\n5. Testing get_object_info...")
try:
    info = s3_manager.get_object_info(
        "test/test_file.txt",
        bucket=s3_manager.documents_bucket
    )
    
    if info:
        print(f"[PASS] Object info retrieved")
        print(f"  Size: {info['size']} bytes")
        print(f"  Last modified: {info['last_modified']}")
    else:
        print("[FAIL] Object not found")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

# Test signed URL
print("\n6. Testing create_signed_url...")
try:
    url = s3_manager.create_signed_url(
        "test/test_file.txt",
        expiration=3600,
        bucket=s3_manager.documents_bucket
    )
    
    if url:
        print(f"[PASS] Signed URL created")
        print(f"  URL: {url[:80]}...")
    else:
        print("[FAIL] Failed to create signed URL")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

print("\n" + "=" * 60)
print("S3 TESTS COMPLETED")
print("=" * 60)
print("\nNote: Test file 'test/test_file.txt' was created in your S3 bucket")
print("You can delete it manually if needed")
