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
    url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
    
    # Get API key from environment
    api_key = os.environ.get('SCRAPER_API_KEY', '')
    
    if not api_key:
        print("ERROR: SCRAPER_API_KEY not found in environment variables!")
        print("Please add SCRAPER_API_KEY to your GitHub Secrets")
        return []
    
    print(f"Using ScraperAPI (key starts with: {api_key[:10]}...)")
    
    # ScraperAPI endpoint
    scraper_url = "http://api.scraperapi.com"
    
    # Parameters for ScraperAPI
    params = {
        'api_key': api_key,
        'url': url,
        'render': 'true',  # Enable JavaScript rendering
        'country_code': 'us'
    }
    
    try:
        print("Sending request to ScraperAPI...")
        response = requests.get(scraper_url, params=params, timeout=60)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ScraperAPI error: {response.text}")
            return []
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        cameras_found = []
        
        # Look for camera names in h3 tags (based on B&H structure)
        camera_brands = ['Sony', 'Canon', 'Nikon', 'FUJIFILM', 'Panasonic', 'OM SYSTEM', 
                        'Leica', 'Hasselblad', 'Pentax', 'Ricoh', 'Sigma', 'Olympus']
        
        # Find all h3 elements
        for h3 in soup.find_all('h3'):
            text = h3.get_text(strip=True)
            # Check if it's a camera name
            if any(brand in text for brand in camera_brands):
                # Clean up the text
                camera_name = text.replace('Key Features', '').strip()
                if camera_name and len(camera_name) > 10:
                    cameras_found.append(camera_name)
        
        # Also look in data-selenium attributes
        for elem in soup.find_all(attrs={"data-selenium": "miniProductPageProductName"}):
            text = elem.get_text(strip=True)
            if text and len(text) > 10:
                cameras_found.append(text)
        
        # Remove duplicates
        cameras_found = list(set(cameras_found))
        
        print(f"Successfully parsed {len(cameras_found)} cameras")
        return cameras_found
        
    except requests.exceptions.Timeout:
        print("Request timed out. B&H might be slow to respond.")
        return []
    except Exception as e:
        print(f"Error with ScraperAPI: {e}")
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
    print(f"Starting camera check at {datetime.now()}")
    
    # Check for API key
    if not os.environ.get('SCRAPER_API_KEY'):
        print("\n⚠️  SCRAPER_API_KEY not found!")
        print("To fix this:")
        print("1. Sign up at https://www.scraperapi.com/ (free)")
        print("2. Get your API key from the dashboard")
        print("3. Add it to GitHub Secrets as SCRAPER_API_KEY")
        print("4. For local testing, set: export SCRAPER_API_KEY='your_key_here'")
        return
    
    # Load existing data
    existing_data = load_existing_cameras()
    
    # Scrape current cameras
    current_cameras = scrape_bh_cameras()
    print(f"Found {len(current_cameras)} cameras currently listed")
    
    if not current_cameras:
        print("\n⚠️  No cameras found. Possible issues:")
        print("1. ScraperAPI key might be invalid")
        print("2. You might have exceeded the free tier limit")
        print("3. B&H page structure might have changed")
        
        # Initialize empty database if first run
        if not existing_data.get('cameras'):
            camera_data = {
                "cameras": [],
                "last_updated": datetime.now().isoformat(),
                "total_cameras_tracked": 0,
                "note": "Waiting for successful scrape"
            }
            save_cameras(camera_data)
        
        # Create empty new_cameras file
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
        print(f"\n✅ Found {len(new_cameras)} NEW cameras!")
        with open('new_cameras.txt', 'w') as f:
            for camera in new_cameras:
                f.write(f"{camera}\n")
                print(f"  - {camera}")
    else:
        print("\n✅ No new cameras found since last check")
        open('new_cameras.txt', 'w').close()

if __name__ == "__main__":
    main()
