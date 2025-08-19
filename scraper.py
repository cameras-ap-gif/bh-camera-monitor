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
    """Scrape B&H Photo for camera names"""
    url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find camera names - B&H specific selectors
        cameras_found = []
        
        # Try multiple possible selectors (B&H might use different ones)
        selectors = [
            'h3[data-selenium="miniProductPageProductName"]',
            'a[data-selenium="miniProductPageProductNameLink"]',
            '.sku-title h3',
            'h3.bold_class'
        ]
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                for item in items:
                    camera_name = item.get_text(strip=True)
                    if camera_name:
                        cameras_found.append(camera_name)
                break
        
        # If no cameras found with CSS selectors, try a broader approach
        if not cameras_found:
            # Look for product containers
            products = soup.find_all(['div', 'article'], class_=lambda x: x and 'product' in x.lower() if x else False)
            for product in products[:50]:  # Limit to first 50 to avoid noise
                title = product.find(['h3', 'h2', 'a'], class_=lambda x: x and any(word in x.lower() for word in ['title', 'name', 'product']) if x else False)
                if title:
                    camera_name = title.get_text(strip=True)
                    if camera_name and len(camera_name) > 5:  # Basic validation
                        cameras_found.append(camera_name)
        
        return list(set(cameras_found))  # Remove duplicates
        
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
        print("Warning: No cameras found. Site structure might have changed.")
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
