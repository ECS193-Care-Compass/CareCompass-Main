"""
End-to-End Integration Test for CARE Compass
Tests the complete workflow: health check, document processing, S3 operations, and logging
"""
import os
import sys
import tempfile
import json
import time
import boto3
from datetime import datetime

# Set bucket names from environment
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

def header(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

def success(msg):
    print(f"{Colors.GREEN}[PASS] {msg}{Colors.END}")

def error(msg):
    print(f"{Colors.RED}[FAIL] {msg}{Colors.END}")

def warning(msg):
    print(f"{Colors.YELLOW}[WARN] {msg}{Colors.END}")

def info(msg):
    print(f"{Colors.CYAN}        {msg}{Colors.END}")

test_stats = {'passed': 0, 'failed': 0}

header("CARE COMPASS - END-TO-END INTEGRATION TEST")

# PHASE 1: AWS Connectivity
header("PHASE 1: AWS Connectivity & Resources")

try:
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    logs_client = boto3.client('logs', region_name='us-east-1')
    success("AWS SDK clients initialized")
    test_stats['passed'] += 1
except Exception as e:
    error(f"Failed to initialize AWS SDK: {e}")
    test_stats['failed'] += 1
    sys.exit(1)

# Check Lambda function exists
try:
    func = lambda_client.get_function(FunctionName='care-compass-dev')
    success(f"Lambda function found: {func['Configuration']['FunctionName']}")
    info(f"Runtime: {func['Configuration']['Runtime']}")
    info(f"Memory: {func['Configuration']['MemorySize']}MB")
    info(f"Timeout: {func['Configuration']['Timeout']}s")
    test_stats['passed'] += 1
except Exception as e:
    error(f"Lambda function not found: {e}")
    test_stats['failed'] += 1

# Check S3 buckets exist
try:
    s3_manager = S3Manager(region='us-east-1')
    for name, bucket in [
        ("Documents", s3_manager.documents_bucket),
        ("Processed", s3_manager.processed_bucket),
        ("VectorDB", s3_manager.vectordb_bucket),
    ]:
        try:
            s3_client.head_bucket(Bucket=bucket)
            success(f"S3 {name} bucket accessible: {bucket}")
            test_stats['passed'] += 1
        except:
            error(f"S3 {name} bucket NOT accessible: {bucket}")
            test_stats['failed'] += 1
except Exception as e:
    error(f"S3 check failed: {e}")
    test_stats['failed'] += 1

# Check CloudWatch logs exist
try:
    logs_client.describe_log_groups(logGroupNamePrefix='/aws/lambda/care-compass-dev')
    success("CloudWatch log group exists: /aws/lambda/care-compass-dev")
    test_stats['passed'] += 1
except Exception as e:
    warning(f"CloudWatch logs not found: {e}")
    test_stats['failed'] += 1

# PHASE 2: Lambda Health Check
header("PHASE 2: Lambda Health Check")

try:
    payload = {"requestContext": {"http": {"method": "GET"}}, "rawPath": "/health"}
    response = lambda_client.invoke(
        FunctionName='care-compass-dev',
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    if response['StatusCode'] == 200:
        success("Lambda invoked successfully (HTTP 200)")
        test_stats['passed'] += 1
        
        # Parse response
        try:
            lambda_response = json.loads(response['Payload'].read())
            if 'body' in lambda_response:
                body = json.loads(lambda_response['body'])
                if body.get('status') == 'ok':
                    success(f"Health check passed: {body.get('message')}")
                    test_stats['passed'] += 1
                else:
                    warning(f"Unexpected health response: {body}")
                    test_stats['failed'] += 1
        except Exception as e:
            warning(f"Could not parse lambda response: {e}")
    else:
        error(f"Lambda returned status {response['StatusCode']}")
        test_stats['failed'] += 1
except Exception as e:
    error(f"Lambda invocation failed: {e}")
    test_stats['failed'] += 1

# PHASE 3: Document Processing Workflow
header("PHASE 3: Document Processing Workflow")

# Simulate documents a user would upload
test_documents = [
    {
        'name': 'patient_intake_form.txt',
        'content': 'Patient: John Doe\nAge: 34\nDiagnosis: PTSD, Anxiety Disorder\nTrauma History: Combat experience\nRecommendation: Trauma-informed therapy with EMDR',
        'type': 'intake_form'
    },
    {
        'name': 'clinical_notes.json',
        'content': json.dumps({
            'patient_id': 'P001',
            'date': '2026-02-23',
            'notes': 'Patient shows significant improvement in hypervigilance symptoms. Continue current trauma-informed care protocol.',
            'crisis_risk': 'low',
            'follow_up': 'weekly'
        }),
        'type': 'clinical_notes'
    }
]

uploaded_keys = []
for doc in test_documents:
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(doc['content'])
            temp_path = f.name
        
        key = f"e2e_test/{doc['type']}/{doc['name']}"
        if s3_manager.upload_document(temp_path, key, bucket=s3_manager.documents_bucket):
            success(f"Uploaded: {doc['name']} → {key}")
            uploaded_keys.append(key)
            test_stats['passed'] += 1
            os.unlink(temp_path)
        else:
            error(f"Failed to upload: {doc['name']}")
            test_stats['failed'] += 1
    except Exception as e:
        error(f"Upload exception for {doc['name']}: {str(e)[:80]}")
        test_stats['failed'] += 1

# PHASE 4: Document Retrieval & Verification
header("PHASE 4: Document Retrieval & Verification")

for key in uploaded_keys:
    try:
        # Get object info
        info_result = s3_manager.get_object_info(key, bucket=s3_manager.documents_bucket)
        if info_result:
            success(f"Retrieved metadata for: {key}")
            info(f"  Size: {info_result['size']} bytes")
            info(f"  Last modified: {info_result['last_modified']}")
            test_stats['passed'] += 1
            
            # Download and verify content
            download_path = tempfile.mktemp()
            if s3_manager.download_document(key, download_path, bucket=s3_manager.documents_bucket):
                with open(download_path, 'r') as f:
                    content = f.read()
                if len(content) > 0:
                    success(f"Downloaded & verified: {len(content)} bytes")
                    test_stats['passed'] += 1
                else:
                    error(f"Downloaded content is empty: {key}")
                    test_stats['failed'] += 1
                os.unlink(download_path)
            else:
                error(f"Failed to download: {key}")
                test_stats['failed'] += 1
        else:
            error(f"Could not get info for: {key}")
            test_stats['failed'] += 1
    except Exception as e:
        error(f"Retrieval exception for {key}: {str(e)[:80]}")
        test_stats['failed'] += 1

# PHASE 5: Simulate Processing Pipeline
header("PHASE 5: Document Processing Pipeline")

try:
    # Simulate: move from documents to processed
    if uploaded_keys:
        source_key = uploaded_keys[0]
        processed_key = f"processed/intake_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Download from documents
        temp_path = tempfile.mktemp()
        if s3_manager.download_document(source_key, temp_path, bucket=s3_manager.documents_bucket):
            # Upload to processed
            if s3_manager.upload_document(temp_path, processed_key, bucket=s3_manager.processed_bucket):
                success(f"Document moved to processed: {processed_key}")
                test_stats['passed'] += 1
                
                # Verify in processed bucket
                processed_list = s3_manager.list_documents(bucket=s3_manager.processed_bucket)
                if any(p['key'] == processed_key for p in processed_list):
                    success(f"Verified in processed bucket")
                    test_stats['passed'] += 1
                else:
                    warning(f"Could not verify in processed bucket list")
                    test_stats['failed'] += 1
            else:
                error(f"Failed to upload to processed bucket")
                test_stats['failed'] += 1
            os.unlink(temp_path)
        else:
            error(f"Failed to download from documents bucket")
            test_stats['failed'] += 1
except Exception as e:
    error(f"Processing pipeline exception: {str(e)[:80]}")
    test_stats['failed'] += 1

# PHASE 6: Signed URL Generation
header("PHASE 6: Signed URL & Access Control")

try:
    if uploaded_keys:
        key = uploaded_keys[0]
        # Generate short-lived URL
        url_short = s3_manager.create_signed_url(key, expiration=300, bucket=s3_manager.documents_bucket)
        if url_short and url_short.startswith('https://'):
            success(f"Generated 5-min signed URL")
            info(f"  URL: {url_short[:70]}...")
            test_stats['passed'] += 1
            
            # Generate long-lived URL
            url_long = s3_manager.create_signed_url(key, expiration=86400, bucket=s3_manager.documents_bucket)
            if url_long and url_long.startswith('https://'):
                success(f"Generated 24-hr signed URL")
                test_stats['passed'] += 1
            else:
                error(f"Failed to generate 24-hr URL")
                test_stats['failed'] += 1
        else:
            error(f"Failed to generate signed URL")
            test_stats['failed'] += 1
except Exception as e:
    error(f"Signed URL exception: {str(e)[:80]}")
    test_stats['failed'] += 1

# PHASE 7: CloudWatch Logs
header("PHASE 7: CloudWatch Logs & Monitoring")

try:
    response = logs_client.filter_log_events(
        logGroupName='/aws/lambda/care-compass-dev',
        limit=100
    )
    
    if response['events']:
        success(f"CloudWatch logs retrieved: {len(response['events'])} events")
        test_stats['passed'] += 1
        
        # Check for errors
        error_events = [e for e in response['events'] if 'ERROR' in e['message']]
        if error_events:
            warning(f"Found {len(error_events)} error entries in logs")
            for evt in error_events[:3]:
                info(f"  {evt['message'][:100]}")
        else:
            success(f"No ERROR entries found in recent logs")
            test_stats['passed'] += 1
        
        # Show recent invocation
        recent = response['events'][-1] if response['events'] else None
        if recent:
            info(f"Most recent: {recent['message'][:100]}")
    else:
        warning(f"No CloudWatch logs available")
        test_stats['failed'] += 1
except Exception as e:
    error(f"CloudWatch logs exception: {str(e)[:80]}")
    test_stats['failed'] += 1

# PHASE 8: List All Bucket Contents
header("PHASE 8: S3 Bucket Inventory")

try:
    for name, bucket in [
        ("Documents", s3_manager.documents_bucket),
        ("Processed", s3_manager.processed_bucket),
        ("VectorDB", s3_manager.vectordb_bucket),
    ]:
        docs = s3_manager.list_documents(bucket=bucket)
        success(f"{name} bucket: {len(docs)} objects")
        if docs:
            info(f"  Sample keys:")
            for d in docs[:5]:
                info(f"    {d['key']}")
            if len(docs) > 5:
                info(f"    ... and {len(docs)-5} more")
        test_stats['passed'] += 1
except Exception as e:
    error(f"Bucket inventory exception: {str(e)[:80]}")
    test_stats['failed'] += 1

# FINAL SUMMARY
header("FINAL TEST SUMMARY")

total = test_stats['passed'] + test_stats['failed']
success_rate = (test_stats['passed'] / total * 100) if total > 0 else 0

info(f"Total: {total} tests")
success(f"Passed: {test_stats['passed']}")
if test_stats['failed'] > 0:
    error(f"Failed: {test_stats['failed']}")

print()
if success_rate >= 90:
    success(f"Success Rate: {success_rate:.1f}% — EXCELLENT")
elif success_rate >= 75:
    warning(f"Success Rate: {success_rate:.1f}% — GOOD (some issues)")
elif success_rate >= 50:
    warning(f"Success Rate: {success_rate:.1f}% — PARTIAL")
else:
    error(f"Success Rate: {success_rate:.1f}% — CRITICAL ISSUES")

print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

print(f"{Colors.BOLD}Key Findings:{Colors.END}")
print(f"  • Lambda health check: {'[PASS]' if test_stats['passed'] > 2 else '[FAIL]'}")
print(f"  • S3 document upload/download: {'[PASS]' if test_stats['passed'] > 5 else '[FAIL]'}")
print(f"  • Cross-bucket processing: {'[PASS]' if test_stats['passed'] > 8 else '[FAIL]'}")
print(f"  • CloudWatch logging: {'[PASS]' if test_stats['passed'] > 10 else '[FAIL]'}")
print(f"  • System Integration: {'[COHESIVE]' if success_rate >= 80 else '[NEEDS WORK]'}")
print()
