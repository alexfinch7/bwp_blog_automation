#!/usr/bin/env python3
"""
Local test script for the blog automation API.
Run this to test the /generate endpoint locally.
"""
import os
import requests
import json

# Check environment variables
print("🔍 Checking environment variables...")
required_vars = [
    "OPENAI_API_KEY",
    "WEBFLOW_API_TOKEN", 
    "WEBFLOW_SITE_ID",
    "WEBFLOW_COLLECTION_ID"
]

missing = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        # Show first/last 4 chars only
        masked = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
        print(f"  ✅ {var}: {masked}")
    else:
        print(f"  ❌ {var}: NOT SET")
        missing.append(var)

if missing:
    print(f"\n⚠️  Missing environment variables: {', '.join(missing)}")
    print("\nTo fix this, export them in your shell:")
    print("  export OPENAI_API_KEY='your-key-here'")
    print("  export WEBFLOW_API_TOKEN='6becb991e6ec8f7d49688237e13c3e38dc8ddf818ea08ea54e6db1f751687215'")
    print("  export WEBFLOW_SITE_ID='666990319136648fdc377552'")
    print("  export WEBFLOW_COLLECTION_ID='66ba3e1671702de92f5a9ee1'")
    print("\nOr create a .env file and use python-dotenv")
    exit(1)

print("\n✅ All required environment variables are set!\n")

# Test the API
BASE_URL = "http://localhost:5000"

print("🏥 Testing health endpoint...")
try:
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    if resp.ok:
        print(f"  ✅ Health check passed: {resp.json()}")
    else:
        print(f"  ❌ Health check failed: {resp.status_code}")
        exit(1)
except requests.exceptions.ConnectionError:
    print("  ❌ Cannot connect to server. Is it running?")
    print("     Start it with: python api/index.py")
    exit(1)

print("\n📝 Testing /generate endpoint...")
test_payload = {
    "prompt": "Write a 700-word blog post about the best theaters in downtown Houston",
    "publish": False,
    "author_id": "671fcf925e3bc8b2761baaa2",
    "category_id": "66ba3e3134ef3aa9b21a2fa1"
}

print(f"  Request: {json.dumps(test_payload, indent=2)}")
print("\n  🤖 Generating content (this may take 30-60 seconds)...\n")

try:
    resp = requests.post(
        f"{BASE_URL}/generate",
        json=test_payload,
        timeout=120
    )
    
    if resp.ok:
        result = resp.json()
        print("  ✅ Success!")
        if result.get("item"):
            item = result["item"]
            field_data = item.get("fieldData", {})
            print(f"\n  📄 Created item:")
            print(f"     ID: {item.get('id')}")
            print(f"     Title: {field_data.get('name')}")
            print(f"     Slug: {field_data.get('slug')}")
            print(f"     Reading time: {field_data.get('reading-time-in-minutes')} min")
            print(f"     Draft: {item.get('isDraft')}")
            print(f"\n  🔗 View in Webflow editor:")
            print(f"     (Check your Webflow CMS collection)")
    else:
        print(f"  ❌ Failed: {resp.status_code}")
        print(f"  Response: {resp.text}")
except Exception as e:
    print(f"  ❌ Error: {e}")

