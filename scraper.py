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
    # IMPORTANT: This should NOT be the B&H URL directly!
    bh_url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
    
    # Get ScraperAPI key
    api_key = os.environ.get('SCRAPER_API_KEY')
    
    if not api_key:
        print("ERROR: SCRAPER_API_KEY not found!")
        print("Attempting direct request (will likely fail)...")
        # This is what's happening - it's falling back to direct request
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(bh_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            print(f"Error scraping: {e}")
            return []
    else:
        print(f"✓ ScraperAPI key found: {api_key[:10]}...")
        
        # Use ScraperAPI endpoint - NOT the B&H URL directly!
        SCRAPER_API_ENDPOINT = 'http://api.scraperapi.com'
        
        params = {
            'api_key': api_key,
            'url': bh_url,
            'render': 'true',  # Enable JavaScript rendering
            'country_code': 'us'
        }
        
        print(f"Calling ScraperAPI endpoint: {SCRAPER_API_ENDPOINT}")
        print(f"Target URL: {bh_url}")
        
        try:
            response = requests.get(SCRAPER_API_ENDPOINT, params=params, timeout=60)
            print(f"ScraperAPI Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✓ Successfully retrieved page via ScraperAPI")
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                cameras_found = []
                
                # Look for camera names in h3 tags
                for h3 in soup.find_all('h3'):
                    text = h3.get_text(strip=True)
                    if any(brand in text for brand in ['Sony', 'Canon', 'Nikon', 'FUJIFILM', 'Panasonic', 'Leica']):
                        if 'Camera' in text or 'Mirrorless' in text or 'DSLR' in text:
                            # Clean the text
                            text = text.replace('Key Features', '').strip()
                            if text and len(text) > 10:
                                cameras_found.append(text)
                
                # Remove duplicates
                cameras_found = list(set(cameras_found))
                print(f"Found {len(cameras_found)} unique cameras")
                return cameras_found
            else:
                print(f"ScraperAPI error: Status {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []
                
        except Exception as e:
            print(f"Exception calling ScraperAPI: {e}")
            return []
    
    return []

def find_new_cameras(current_cameras, existing_data):
    """Identify cameras that are truly new (never seen before)"""
    all_previous_cameras = set(existing_data.get('cameras', []))
    current_set = set(current_cameras)
    
    new_cameras = current_set - all_previous_cameras
    all_cameras = list(all_previous_cameras | current_set)
    
    return list(new_cameras), all_cameras

def main():
    print(f"Starting camera check at {datetime.now()}")
    print("-" * 50)
    
    # Check environment
    api_key = os.environ.get('SCRAPER_API_KEY')
    if api_key:
        print(f"✓ SCRAPER_API_KEY is set (starts with: {api_key[:10]}...)")
    else:
        print("✗ SCRAPER_API_KEY is NOT set")
    
    # Load existing data
    existing_data = load_existing_cameras()
    
    # Scrape current cameras
    current_cameras = scrape_bh_cameras()
    print(f"Found {len(current_cameras)} cameras currently listed")
    
    if not current_cameras:
        print("Warning: No cameras found. Site structure might have changed.")
        open('new_cameras.txt', 'w').close()
        return
    
    # Find new cameras
    new_cameras, all_cameras = find_new_cameras(current_cameras, existing_data)
    
    # Save updated data
    camera_data = {
        "cameras": all_cameras,
        "last_updated": datetime.now().isoformat(),
        "total_cameras_tracked": len(all_cameras)
    }
    save_cameras(camera_data)
    
    # Save new cameras for email notification
    if new_cameras:
        print(f"Found {len(new_cameras)} NEW cameras!")
        with open('new_cameras.txt', 'w') as f:
            for camera in new_cameras:
                f.write(f"{camera}\n")
                print(f"  - {camera}")
    else:
        print("No new cameras found since last check")
        open('new_cameras.txt', 'w').close()

if __name__ == "__main__":
    main()
