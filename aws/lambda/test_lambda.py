"""Test Lambda handler locally"""
import json
import sys
sys.path.insert(0, '.')

from lambda_handler import lambda_handler

# Test Lambda Function URL format event
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

print("Testing /health endpoint...")
response = lambda_handler(event, None)
print(f"Status: {response['statusCode']}")
print(f"Body: {response['body']}")

# Test categories
event["rawPath"] = "/categories"
event["requestContext"]["http"]["path"] = "/categories"

print("\nTesting /categories endpoint...")
response = lambda_handler(event, None)
print(f"Status: {response['statusCode']}")
print(f"Body: {response['body']}")
