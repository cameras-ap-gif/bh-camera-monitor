import os
import requests

# Test if ScraperAPI works
api_key = os.environ.get('SCRAPER_API_KEY', 'YOUR_API_KEY_HERE')  # Replace with your actual key for local testing

print(f"Testing ScraperAPI...")
print(f"API Key present: {'Yes' if api_key else 'No'}")
print(f"Key starts with: {api_key[:10]}..." if api_key else "No key found")

# Test with a simple website first
test_url = "https://httpbin.org/html"
params = {
    'api_key': api_key,
    'url': test_url
}

print(f"\n1. Testing with httpbin.org...")
response = requests.get('http://api.scraperapi.com', params=params)
print(f"Status: {response.status_code}")

# Now test with B&H
bh_url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
params = {
    'api_key': api_key,
    'url': bh_url,
    'render': 'true'
}

print(f"\n2. Testing with B&H Photo...")
try:
    response = requests.get('http://api.scraperapi.com', params=params, timeout=60)
    print(f"Status: {response.status_code}")
    print(f"Response length: {len(response.text)} characters")
    
    # Check if we got real content
    if 'Sony' in response.text or 'Canon' in response.text:
        print("✓ Successfully found camera content!")
    else:
        print("✗ No camera brands found in response")
        print(f"First 500 chars: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
