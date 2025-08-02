#!/usr/bin/env python3
"""
Test script for voice authentication microservice deployment.
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, Any


async def test_endpoint(client: httpx.AsyncClient, url: str, method: str = "GET", data: Dict[Any, Any] = None) -> Dict[str, Any]:
    """Test a single endpoint."""
    try:
        if method == "GET":
            response = await client.get(url)
        elif method == "POST":
            response = await client.post(url, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        return {
            "url": url,
            "method": method,
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            "error": None
        }
    except Exception as e:
        return {
            "url": url,
            "method": method,
            "status_code": None,
            "success": False,
            "response": None,
            "error": str(e)
        }


async def test_deployment(base_url: str):
    """Test the deployed voice authentication microservice."""
    print(f"Testing deployment at: {base_url}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        tests = [
            # Health check
            {
                "name": "Health Check",
                "url": f"{base_url}/healthz",
                "method": "GET"
            },
            
            # Audio processing tests
            {
                "name": "Audio Processing Test",
                "url": f"{base_url}/api/audio/test",
                "method": "GET"
            },
            {
                "name": "Audio Formats Info",
                "url": f"{base_url}/api/audio/formats",
                "method": "GET"
            },
            
            # VAPI tests
            {
                "name": "VAPI Client Test",
                "url": f"{base_url}/api/vapi/test",
                "method": "GET"
            },
            {
                "name": "VAPI Config Info",
                "url": f"{base_url}/api/vapi/config",
                "method": "GET"
            },
        ]
        
        results = []
        for test in tests:
            print(f"Testing: {test['name']}")
            result = await test_endpoint(
                client, 
                test["url"], 
                test["method"], 
                test.get("data")
            )
            results.append({**test, **result})
            
            if result["success"]:
                print(f"  ✅ SUCCESS - Status: {result['status_code']}")
            else:
                print(f"  ❌ FAILED - Status: {result.get('status_code', 'N/A')}, Error: {result['error']}")
            
            print()
        
        # Summary
        print("=" * 60)
        print("DEPLOYMENT TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in results if r["success"])
        total = len(results)
        
        print(f"Tests Passed: {passed}/{total}")
        print(f"Success Rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("🎉 All tests passed! Deployment is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the deployment.")
            
            # Show failed tests
            failed_tests = [r for r in results if not r["success"]]
            for test in failed_tests:
                print(f"  - {test['name']}: {test['error'] or f'HTTP {test['status_code']}'}")
            
            return False


async def main():
    """Main test function."""
    if len(sys.argv) != 2:
        print("Usage: python test_deployment.py <base_url>")
        print("Example: python test_deployment.py https://voice-auth-microservice.onrender.com")
        sys.exit(1)
    
    base_url = sys.argv[1].rstrip('/')
    success = await test_deployment(base_url)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())