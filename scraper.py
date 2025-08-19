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
    """Scrape B&H Photo using ScraperAPI to bypass blocks"""
    url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
    
    # Use ScraperAPI to handle JavaScript and anti-bot measures
    api_key = os.environ.get('SCRAPER_API_KEY', '')
    
    if api_key:
        # Using ScraperAPI
        scraper_url = f"http://api.scraperapi.com?api_key={api_key}&url={url}&render=true"
        response = requests.get(scraper_url)
    else:
        # Fallback to direct request (might get blocked)
        print("Warning: No SCRAPER_API_KEY found, trying direct request...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Got status code {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    cameras_found = []
    
    # Based on the actual B&H page structure from our successful scrape
    # Look for product titles in h3 tags
    for h3 in soup.find_all('h3'):
        text = h3.get_text(strip=True)
        # Filter for actual camera names (they usually contain brand names)
        camera_brands = ['Sony', 'Canon', 'Nikon', 'FUJIFILM', 'Panasonic', 'OM SYSTEM', 
                        'Leica', 'Hasselblad', 'Pentax', 'Ricoh', 'Sigma', 'Olympus']
        if any(brand in text for brand in camera_brands) and 'Camera' in text:
            # Clean up the name
            camera_name = text.replace('Key Features', '').strip()
            if camera_name and len(camera_name) > 10:
                cameras_found.append(camera_name)
    
    # Remove duplicates
    cameras_found = list(set(cameras_found))
    print(f"Successfully found {len(cameras_found)} cameras")
    
    return cameras_found

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
        print("Warning: No cameras found. Site might be blocking or changed structure.")
        # Don't update anything if we couldn't scrape
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
