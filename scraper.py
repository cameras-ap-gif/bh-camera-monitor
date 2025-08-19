import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import re

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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 403:
            print("B&H is blocking GitHub Actions. This is expected.")
            print("The scraper will work when run from your local machine.")
            print("For GitHub Actions, consider using:")
            print("1. A proxy service like ScraperAPI")
            print("2. Running the scraper locally and pushing results")
            print("3. Using a self-hosted GitHub Actions runner")
            
            # Return empty list for now - won't send false alerts
            return []
        
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        cameras_found = []
        
        # Method 1: Look for product names using data-selenium attributes
        product_names = soup.find_all(attrs={"data-selenium": "miniProductPageProductName"})
        for element in product_names:
            camera_name = element.get_text(strip=True)
            if camera_name and len(camera_name) > 5:
                # Clean up the name - remove "Key Features" if present
                camera_name = camera_name.replace('Key Features', '').strip()
                cameras_found.append(camera_name)
        
        # Method 2: If no products found with first method, try alternative selectors
        if not cameras_found:
            # Look for h3 tags that contain camera names
            for h3 in soup.find_all('h3'):
                text = h3.get_text(strip=True)
                # Check if it looks like a camera name (contains brand names)
                camera_brands = ['Sony', 'Canon', 'Nikon', 'FUJIFILM', 'Panasonic', 
                               'OM SYSTEM', 'Leica', 'Hasselblad', 'Pentax', 'Ricoh', 
                               'Sigma', 'Olympus', 'GoPro', 'DJI', 'Insta360']
                
                if any(brand in text for brand in camera_brands):
                    # Clean up common suffixes
                    text = text.replace('Key Features', '').strip()
                    if text and len(text) > 10 and text not in cameras_found:
                        cameras_found.append(text)
        
        # Method 3: Look for product links
        if not cameras_found:
            product_links = soup.find_all('a', attrs={"data-selenium": "miniProductPageProductNameLink"})
            for link in product_links:
                camera_name = link.get_text(strip=True)
                if camera_name and len(camera_name) > 5:
                    cameras_found.append(camera_name)
        
        # Remove duplicates while preserving order
        seen = set()
        cameras_found = [x for x in cameras_found if not (x in seen or seen.add(x))]
        
        print(f"Successfully scraped {len(cameras_found)} cameras")
        
        # Print first 5 cameras as examples
        if cameras_found:
            print("Sample cameras found:")
            for camera in cameras_found[:5]:
                print(f"  - {camera}")
        
        return cameras_found
        
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
    print("=" * 50)
    
    # Load existing data
    existing_data = load_existing_cameras()
    print(f"Previously tracked cameras: {len(existing_data.get('cameras', []))}")
    
    # Scrape current cameras
    current_cameras = scrape_bh_cameras()
    print(f"Found {len(current_cameras)} cameras currently listed")
    
    if not current_cameras:
        print("\nNo cameras found. This could mean:")
        print("1. The site is blocking automated requests (common in GitHub Actions)")
        print("2. The site structure has changed")
        print("3. There's a network issue")
        print("\nThe scraper should work when run locally on your machine.")
        
        # Don't update the database if we couldn't scrape
        # This prevents losing our history
        return
    
    # Find new cameras
    new_cameras, all_cameras = find_new_cameras(current_cameras, existing_data)
    
    # Save updated data
    camera_data = {
        "cameras": all_cameras,
        "last_updated": datetime.now().isoformat(),
        "total_cameras_tracked": len(all_cameras),
        "current_listing_count": len(current_cameras)
    }
    save_cameras(camera_data)
    
    print("=" * 50)
    print(f"Database updated: {len(all_cameras)} total cameras tracked")
    
    # Save new cameras for email notification
    if new_cameras:
        print(f"\n🎉 Found {len(new_cameras)} NEW cameras!")
        with open('new_cameras.txt', 'w') as f:
            for camera in new_cameras:
                f.write(f"{camera}\n")
                print(f"  NEW: {camera}")
    else:
        print("\n✓ No new cameras found since last check")
        # Create empty file to signal no new cameras
        open('new_cameras.txt', 'w').close()

if __name__ == "__main__":
    main()
