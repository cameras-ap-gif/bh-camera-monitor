import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time

def load_existing_cameras():
    """Load previously seen cameras from JSON file"""
    if os.path.exists('data/cameras.json'):
        with open('data/cameras.json', 'r') as f:
            return json.load(f)
    return {"cameras": [], "last_updated": None}

def save_cameras(camera_data):
    """Save camera data to JSON file"""
    os.makedirs('data', exist_ok=True)
    with open('data/cameras.json', 'w') as f:
        json.dump(camera_data, f, indent=2)

def scrape_with_scraperapi(url, api_key, attempt=1):
    """Try to scrape using ScraperAPI with retry logic"""
    print(f"\nAttempt {attempt}: Fetching via ScraperAPI...")
    
    # Try different parameter combinations
    param_sets = [
        # Attempt 1: With JavaScript rendering
        {
            'api_key': api_key,
            'url': url,
            'render': 'true',
            'country_code': 'us'
        },
        # Attempt 2: Without rendering (faster, might work)
        {
            'api_key': api_key,
            'url': url,
            'country_code': 'us'
        },
        # Attempt 3: Minimal parameters
        {
            'api_key': api_key,
            'url': url
        }
    ]
    
    if attempt <= len(param_sets):
        params = param_sets[attempt - 1]
        print(f"  Parameters: render={params.get('render', 'false')}, country={params.get('country_code', 'default')}")
    else:
        return None
    
    try:
        response = requests.get('http://api.scraperapi.com', params=params, timeout=60)
        print(f"  Response status: {response.status_code}")
        print(f"  Response size: {len(response.text)} characters")
        
        if response.status_code == 200 and len(response.text) > 10000:
            print("  ✓ Success!")
            return response.text
        elif response.status_code == 500:
            print("  ✗ Server error from ScraperAPI")
            if attempt < 3:
                print(f"  Waiting 5 seconds before retry...")
                time.sleep(5)
                return scrape_with_scraperapi(url, api_key, attempt + 1)
        else:
            print(f"  ✗ Unexpected response: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("  ✗ Request timed out")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    return None

def scrape_bh_cameras():
    """Scrape B&H Photo using ScraperAPI with multiple attempts"""
    bh_url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
    
    # Get ScraperAPI key
    api_key = os.environ.get('SCRAPER_API_KEY')
    
    if not api_key:
        print("ERROR: SCRAPER_API_KEY not found!")
        return []
    
    print(f"✓ Using ScraperAPI (key: {api_key[:10]}...)")
    
    # Try to scrape with retries
    html_content = scrape_with_scraperapi(bh_url, api_key)
    
    if not html_content:
        print("\n⚠️  All ScraperAPI attempts failed")
        
        # Try alternative: Use ScraperAPI's dedicated endpoint for difficult sites
        print("\nTrying ScraperAPI with premium parameters...")
        premium_params = {
            'api_key': api_key,
            'url': bh_url,
            'premium': 'true',  # Use premium proxies
            'render': 'true',
            'wait_for_selector': 'h3'  # Wait for product titles to load
        }
        
        try:
            response = requests.get('http://api.scraperapi.com', params=premium_params, timeout=90)
            if response.status_code == 200:
                print("✓ Premium scraping successful!")
                html_content = response.text
            else:
                print(f"✗ Premium attempt failed: {response.status_code}")
        except Exception as e:
            print(f"✗ Premium attempt error: {e}")
    
    if not html_content:
        return []
    
    # Parse the HTML
    print("\nParsing HTML content...")
    soup = BeautifulSoup(html_content, 'html.parser')
    cameras_found = []
    
    # Camera brands to look for
    camera_brands = ['Sony', 'Canon', 'Nikon', 'FUJIFILM', 'Fujifilm', 'Panasonic', 'OM SYSTEM', 
                    'Leica', 'Hasselblad', 'Pentax', 'Ricoh', 'Sigma', 'Olympus',
                    'GoPro', 'DJI', 'Insta360', 'Kodak', 'Polaroid', 'Blackmagic']
    
    # Method 1: Find all h3 tags
    h3_tags = soup.find_all('h3')
    print(f"Found {len(h3_tags)} h3 tags")
    
    for h3 in h3_tags:
        text = h3.get_text(strip=True)
        
        # Check if it contains a camera brand
        for brand in camera_brands:
            if brand.lower() in text.lower():
                # Clean up the text
                clean_text = text.replace('Key Features', '').strip()
                clean_text = clean_text.replace('Show More', '').strip()
                
                # Make sure it's a product name
                if len(clean_text) > 15 and clean_text not in cameras_found:
                    if any(word in clean_text.lower() for word in ['camera', 'mirrorless', 'dslr', 'body', 'kit', 'lens']):
                        cameras_found.append(clean_text)
                        break
    
    # Method 2: Look for specific product containers
    product_containers = soup.find_all('div', {'data-selenium': 'miniProductPage'})
    print(f"Found {len(product_containers)} product containers")
    
    for container in product_containers:
        title = container.find('h3')
        if title:
            text = title.get_text(strip=True)
            if text and text not in cameras_found:
                for brand in camera_brands:
                    if brand.lower() in text.lower():
                        cameras_found.append(text)
                        break
    
    # Method 3: Links with product info
    product_links = soup.find_all('a', {'data-selenium': 'miniProductPageProductNameLink'})
    for link in product_links:
        text = link.get_text(strip=True)
        if text and text not in cameras_found:
            for brand in camera_brands:
                if brand.lower() in text.lower():
                    cameras_found.append(text)
                    break
    
    print(f"✓ Found {len(cameras_found)} unique cameras")
    
    # Show first few cameras found for verification
    if cameras_found:
        print("\nSample of cameras found:")
        for camera in cameras_found[:5]:
            print(f"  • {camera[:80]}...")
    
    return cameras_found

def find_new_cameras(current_cameras, existing_data):
    """Identify cameras that are truly new (never seen before)"""
    all_previous_cameras = set(existing_data.get('cameras', []))
    current_set = set(current_cameras)
    
    new_cameras = current_set - all_previous_cameras
    all_cameras = list(all_previous_cameras | current_set)
    
    return list(new_cameras), all_cameras

def main():
    print("=" * 60)
    print(f"B&H Camera Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Verify environment
    if os.environ.get('SCRAPER_API_KEY'):
        print("✓ SCRAPER_API_KEY is configured")
    else:
        print("✗ SCRAPER_API_KEY is missing!")
        return
    
    # Load existing data
    existing_data = load_existing_cameras()
    previous_count = len(existing_data.get('cameras', []))
    print(f"Previously tracked cameras: {previous_count}")
    
    # Scrape current cameras
    print("\nScraping B&H Photo...")
    current_cameras = scrape_bh_cameras()
    
    if not current_cameras:
        print("\n⚠️  No cameras found - scraping may have failed")
        
        # Initialize with empty database if first run
        if previous_count == 0:
            print("Initializing empty database for first run...")
            camera_data = {
                "cameras": [],
                "last_updated": datetime.now().isoformat(),
                "total_cameras_tracked": 0,
                "note": "Awaiting successful scrape"
            }
            save_cameras(camera_data)
        
        open('new_cameras.txt', 'w').close()
        return
    
    print(f"\n📊 Summary:")
    print(f"  - Cameras found on page: {len(current_cameras)}")
    
    # Find new cameras
    new_cameras, all_cameras = find_new_cameras(current_cameras, existing_data)
    
    # Save updated data
    camera_data = {
        "cameras": all_cameras,
        "last_updated": datetime.now().isoformat(),
        "total_cameras_tracked": len(all_cameras)
    }
    save_cameras(camera_data)
    
    print(f"  - Total cameras in database: {len(all_cameras)}")
    print(f"  - New cameras detected: {len(new_cameras)}")
    
    # Save new cameras for email notification
    if new_cameras:
        print(f"\n🎉 NEW CAMERAS FOUND:")
        with open('new_cameras.txt', 'w') as f:
            for camera in new_cameras[:10]:  # Show first 10 in logs
                f.write(f"{camera}\n")
                print(f"  • {camera}")
            if len(new_cameras) > 10:
                print(f"  ... and {len(new_cameras) - 10} more")
                for camera in new_cameras[10:]:
                    f.write(f"{camera}\n")
    else:
        print("\n✓ No new cameras since last check")
        open('new_cameras.txt', 'w').close()
    
    print("\n" + "=" * 60)
    print("Check complete!")

if __name__ == "__main__":
    main()
