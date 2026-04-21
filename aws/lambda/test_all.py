"""
Test Lambda Handler and S3 Manager
Run this to verify functionality before deploying to AWS
"""
import json
import sys
import os
sys.path.insert(0, '.')

print("=" * 60)
print("TESTING LAMBDA HANDLER")
print("=" * 60)

from lambda_handler import lambda_handler

# Test 1: Health endpoint
print("\n1. Testing /health endpoint...")
event = {
    "version": "2.0",
    "routeKey": "$default",
    "rawPath": "/health",
    "requestContext": {
        "http": {
            "method": "GET",
            "path": "/health"
        }
    }
}

try:
    response = lambda_handler(event, None)
    print(f"[PASS] Status: {response['statusCode']}")
    print(f"[PASS] Body: {response['body']}")
    assert response['statusCode'] == 200
    print("[PASS] PASSED")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

# Test 2: Categories endpoint
print("\n2. Testing /categories endpoint...")
event["rawPath"] = "/categories"
event["requestContext"]["http"]["path"] = "/categories"

try:
    response = lambda_handler(event, None)
    print(f"[PASS] Status: {response['statusCode']}")
    body = json.loads(response['body'])
    print(f"[PASS] Categories count: {len(body['categories'])}")
    assert response['statusCode'] == 200
    assert len(body['categories']) == 5
    print("[PASS] PASSED")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

# Test 3: CORS preflight
print("\n3. Testing CORS preflight...")
event["requestContext"]["http"]["method"] = "OPTIONS"
event["rawPath"] = "/health"

try:
    response = lambda_handler(event, None)
    print(f"[PASS] Status: {response['statusCode']}")
    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
    print("[PASS] PASSED")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

# Test 4: 404 for unknown route
print("\n4. Testing 404 for unknown route...")
event["requestContext"]["http"]["method"] = "GET"
event["rawPath"] = "/unknown"

try:
    response = lambda_handler(event, None)
    print(f"[PASS] Status: {response['statusCode']}")
    assert response['statusCode'] == 404
    print("[PASS] PASSED")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

# Test 5: API Gateway format (legacy)
print("\n5. Testing API Gateway event format...")
api_gateway_event = {
    "httpMethod": "GET",
    "path": "/health"
}

try:
    response = lambda_handler(api_gateway_event, None)
    print(f"[PASS] Status: {response['statusCode']}")
    assert response['statusCode'] == 200
    print("[PASS] PASSED")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

print("\n" + "=" * 60)
print("TESTING S3 MANAGER")
print("=" * 60)

from s3_manager import S3Manager

# Test S3 Manager initialization
print("\n6. Testing S3Manager initialization...")
try:
    # Set test environment variables
    os.environ['S3_DOCUMENTS_BUCKET'] = 'test-documents-bucket'
    os.environ['S3_PROCESSED_BUCKET'] = 'test-processed-bucket'
    os.environ['S3_VECTORDB_BUCKET'] = 'test-vectordb-bucket'
    
    s3_manager = S3Manager(region='us-east-1')
    print(f"[PASS] Documents bucket: {s3_manager.documents_bucket}")
    print(f"[PASS] Processed bucket: {s3_manager.processed_bucket}")
    print(f"[PASS] VectorDB bucket: {s3_manager.vectordb_bucket}")
    assert s3_manager.documents_bucket == 'test-documents-bucket'
    print("[PASS] PASSED")
except Exception as e:
    print(f"[FAIL] FAILED: {e}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED")
print("=" * 60)
print("\nNext steps:")
print("1. Deploy to AWS Lambda")
print("2. Test with actual Lambda URL")
print("3. Check CloudWatch logs for any errors")
