#!/usr/bin/env python3
import requests
import json

print("Testing Real RAG Backend...")
print("=" * 70)

r = requests.post('http://localhost:8000/chat', json={
    'query': 'I am experiencing anxiety after a traumatic event'
})
resp = r.json()

print("\n[OK] Response from RAG Backend:")
print("-" * 70)
print(resp['response'][:500])
print("...")
print("-" * 70)
print(f"\nIs Crisis: {resp.get('is_crisis')}")
print(f"Docs Retrieved: {resp.get('num_docs_retrieved')}")
print(f"Scenario: {resp.get('scenario')}")
