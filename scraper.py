import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

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

def scrape_bh_cameras():
    """Scrape B&H Photo using ScraperAPI"""
    bh_url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
    
    # Get ScraperAPI key
    api_key = os.environ.get('SCRAPER_API_KEY')
    
    if not api_key:
        print("ERROR: SCRAPER_API_KEY not found!")
        return []
    
    print(f"✓ Using ScraperAPI (key: {api_key[:10]}...)")
    
    # ScraperAPI endpoint - this is what we call, NOT B&H directly
    params = {
        'api_key': api_key,
        'url': bh_url,
        'render': 'true',
        'country_code': 'us'
    }
    
    try:
        print("Fetching page via ScraperAPI...")
        response = requests.get('http://api.scraperapi.com', params=params, timeout=60)
        
        print(f"Response status: {response.status_code}")
        print(f"Response size: {len(response.text)} characters")
        
        if response.status_code != 200:
            print(f"Error: ScraperAPI returned status {response.status_code}")
            return []
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        cameras_found = []
        
        # Method 1: Find all h3 tags (product titles on B&H)
        h3_count = 0
        for h3 in soup.find_all('h3'):
            h3_count += 1
            text = h3.get_text(strip=True)
            
            # Check if it's a camera product
            camera_brands = ['Sony', 'Canon', 'Nikon', 'FUJIFILM', 'Panasonic', 'OM SYSTEM', 
                           'Leica', 'Hasselblad', 'Pentax', 'Ricoh', 'Sigma', 'Olympus',
                           'GoPro', 'DJI', 'Insta360', 'Kodak', 'Polaroid']
            
            # Check if text contains a camera brand
            has_brand = any(brand.lower() in text.lower() for brand in camera_brands)
            
            # Check for camera-related keywords
            camera_keywords = ['camera', 'mirrorless', 'dslr', 'digital', 'body', 'lens', 'kit']
            has_keyword = any(keyword in text.lower() for keyword in camera_keywords)
            
            # If it looks like a camera product name
            if has_brand and (has_keyword or 'mm' in text.lower()):
                # Clean up the text
                clean_text = text.replace('Key Features', '').strip()
                clean_text = clean_text.replace('Show More', '').strip()
                
                # Avoid duplicates and ensure it's substantial
                if clean_text and len(clean_text) > 15 and clean_text not in cameras_found:
                    cameras_found.append(clean_text)
                    print(f"  Found: {clean_text[:60]}...")
        
        print(f"Scanned {h3_count} h3 tags")
        
        # Method 2: Also check data-selenium attributes
        selenium_items = soup.find_all(attrs={'data-selenium': 'miniProductPageProductName'})
        for item in selenium_items:
            text = item.get_text(strip=True)
            if text and len(text) > 15 and text not in cameras_found:
                # Apply same brand/keyword checks
                has_brand = any(brand.lower() in text.lower() for brand in camera_brands)
                if has_brand:
                    cameras_found.append(text)
        
        print(f"✓ Found {len(cameras_found)} unique cameras")
        return cameras_found
        
    except requests.exceptions.Timeout:
        print("Error: Request timed out (60 seconds)")
        return []
    except Exception as e:
        print(f"Error: {e}")
        return []

def find_new_cameras(current_cameras, existing_data):
    """Identify cameras that are truly new (never seen before)"""
    all_previous_cameras = set(existing_data.get('cameras', []))
    current_set = set(current_cameras)
    
    # Find cameras that have never been seen before
    new_cameras = current_set - all_previous_cameras
    
    # Update the master list with ALL cameras we've ever seen
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
        # Don't update database if scraping failed
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
            for camera in new_cameras:
                f.write(f"{camera}\n")
                print(f"  • {camera}")
    else:
        print("\n✓ No new cameras since last check")
        open('new_cameras.txt', 'w').close()
    
    print("\n" + "=" * 60)
    print("Check complete!")

if __name__ == "__main__":
    main()
