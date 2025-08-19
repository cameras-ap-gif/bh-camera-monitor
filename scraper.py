import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time
import random

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
    """Scrape B&H Photo for camera names with enhanced anti-bot measures"""
    url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
    
    # Enhanced headers to appear more like a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    # Create a session to maintain cookies
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # Add random delay to appear more human
        time.sleep(random.uniform(1, 3))
        
        # First visit the main site to get cookies
        session.get("https://www.bhphotovideo.com", headers=headers)
        time.sleep(random.uniform(2, 4))
        
        # Now visit the cameras page
        response = session.get(url, headers=headers)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 403:
            print("Still getting 403. Trying alternative approach...")
            # Try with different user agent
            headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
            response = session.get(url, headers=headers)
        
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find camera names - B&H specific selectors
        cameras_found = []
        
        # Updated selectors based on B&H's current structure
        selectors = [
            'h3[data-selenium="miniProductPageProductName"]',
            'a[data-selenium="miniProductPageProductNameLink"]',
            '[data-selenium*="product"]',
            '.sku-title',
            'h3.bold',
            'a.link_24fL8',
            '[class*="title"]',
            'h3'
        ]
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                for item in items:
                    camera_name = item.get_text(strip=True)
                    # Filter to ensure we're getting product names
                    if camera_name and len(camera_name) > 10 and not camera_name.startswith('$'):
                        cameras_found.append(camera_name)
                if cameras_found:
                    break
        
        # Remove duplicates and return
        cameras_found = list(set(cameras_found))
        
        # If still no cameras, save page for debugging
        if not cameras_found:
            print("No cameras found with selectors. Page might be using JavaScript.")
            # Save first 500 chars of HTML for debugging
            print(f"Page HTML preview: {response.text[:500]}")
        
        return cameras_found
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}")
        print(f"Response Headers: {response.headers}")
        return []
    except Exception as e:
        print(f"Error scraping: {e}")
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
    
    # Load existing data
    existing_data = load_existing_cameras()
    
    # Scrape current cameras
    current_cameras = scrape_bh_cameras()
    print(f"Found {len(current_cameras)} cameras currently listed")
    
    if not current_cameras:
        print("Warning: No cameras found. Site might be blocking scrapers or using JavaScript.")
        # For testing, let's use mock data on first run
        if not existing_data.get('cameras'):
            print("First run detected - initializing with empty database")
            camera_data = {
                "cameras": [],
                "last_updated": datetime.now().isoformat(),
                "total_cameras_tracked": 0,
                "note": "B&H blocking detected - may need Selenium approach"
            }
            save_cameras(camera_data)
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
        # Create empty file to signal no new cameras
        open('new_cameras.txt', 'w').close()

if __name__ == "__main__":
    main()
