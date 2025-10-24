#!/usr/bin/env python3
"""
Test script to verify httping works with requests module
"""

import sys
import requests

def test_requests():
    try:
        response = requests.get('https://httpbin.org/get', timeout=5)
        print(f"✓ requests module working - Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"✗ requests module failed: {e}")
        return False

if __name__ == '__main__':
    print("Testing httping dependencies...")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.executable}")
    
    success = test_requests()
    sys.exit(0 if success else 1)
