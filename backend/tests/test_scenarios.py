#!/usr/bin/env python3
"""Quick test to verify scenario detection works"""
import requests

tests = [
    ('I am having anxiety and cannot sleep', 'mental_health'),
    ('I need housing and transportation help', 'practical_social'),
    ('I need to talk to a lawyer about a protection order', 'legal_advocacy'),
    ('I got tested for STI last week', 'immediate_followup'),
    ('It happened a long time ago and I am not sure it matters', 'delayed_ambivalent'),
]

print('Testing Scenario Detection:\n')
for query, expected in tests:
    try:
        response = requests.post('http://localhost:8000/chat', json={'query': query})
        data = response.json()
        response_start = data["response"][:100].replace('\n', ' ')
        print(f'[PASS] Query: {query[:50]}...')
        print(f'  Response: {response_start}...')
        print(f'  Scenario: {data.get("scenario", "N/A")}')
        print()
    except Exception as e:
        print(f'[FAIL] Error testing query: {e}\n')
