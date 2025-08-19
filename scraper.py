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
    """Scrape B&H Photo for camera names using proxy service"""
    url = "https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST"
    
    # Try multiple approaches
    cameras_found = []
    
    # Method 1: Try ScraperAPI if available
    scraper_api_key = os.environ.get('SCRAPER_API_KEY', '')
    if scraper_api_key:
        print("Using ScraperAPI...")
        scraper_url = f"http://api.scraperapi.com?api_key={scraper_api_key}&url={url}&render=true"
        try:
            response = requests.get(scraper_url, timeout=60)
            if response.status_code == 200:
                cameras_found = parse_bh_html(response.text)
                if cameras_found:
                    return cameras_found
        except Exception as e:
            print(f"ScraperAPI failed: {e}")
    
    # Method 2: Try ProxyScrape free proxy
    print("Trying with proxy...")
    proxies = {
        'http': 'http://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=us',
        'https': 'http://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=us'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers, proxies=proxies, timeout=30)
        if response.status_code == 200:
            cameras_found = parse_bh_html(response.text)
            if cameras_found:
                return cameras_found
    except:
        pass
    
    # Method 3: Direct request (last resort)
    print("Trying direct request...")
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            cameras_found = parse_bh_html(response.text)
    except Exception as e:
        print(f"Direct request failed with: {e}")
    
    # If all methods fail, use a fallback list for testing
    if not cameras_found:
        print("All methods failed. Using test data for initial setup.")
        # Return empty list so the system initializes properly
        return []
    
    return cameras_found

def parse_bh_html(html_content):
    """Parse B&H HTML to extract camera names"""
    soup = BeautifulSoup(html_content, 'html.parser')
    cameras_found = []
    
    # Based on your HTML sample, look for product names in various locations
    
    # Method 1: Look for data-selenium attributes
    product_elements = soup.find_all(attrs={"data-selenium": True})
    for elem in product_elements:
        if 'product' in elem.get('data-selenium', '').lower():
            text = elem.get_text(strip=True)
            if is_camera_name(text):
                cameras_found.append(clean_camera_name(text))
    
    # Method 2: Look for specific heading tags with camera info
    for heading in soup.find_all(['h3', 'h2', 'h4']):
        text = heading.get_text(strip=True)
        if is_camera_name(text):
            cameras_found.append(clean_camera_name(text))
    
    # Method 3: Look for links with camera names
    for link in soup.find_all('a'):
        text = link.get_text(strip=True)
        if is_camera_name(text):
            cameras_found.append(clean_camera_name(text))
    
    # Remove duplicates and return
    cameras_found = list(set(cameras_found))
    
    # Filter out obvious non-camera items
    cameras_found = [c for c in cameras_found if len(c) > 10 and not c.startswith('$')]
    
    return cameras_found

def is_camera_name(text):
    """Check if text is likely a camera name"""
    if not text or len(text) < 10:
        return False
    
    # Camera brands to look for
    camera_brands = ['Sony', 'Canon', 'Nikon', 'FUJIFILM', 'Fujifilm', 'Panasonic', 
                    'OM SYSTEM', 'Olympus', 'Leica', 'Hasselblad', 'Pentax', 
                    'Ricoh', 'Sigma', 'GoPro', 'DJI', 'Insta360']
    
    # Check if any brand is in the text
    has_brand = any(brand.lower() in text.lower() for brand in camera_brands)
    
    # Check for camera-related keywords
    camera_keywords = ['camera', 'mirrorless', 'dslr', 'digital', 'lens', 'kit']
    has_keyword = any(keyword in text.lower() for keyword in camera_keywords)
    
    return has_brand or has_keyword

def clean_camera_name(text):
    """Clean up camera name text"""
    # Remove common suffixes
    text = text.replace('Key Features', '').strip()
    text = text.replace('Show More', '').strip()
    text = text.replace('Add to Cart', '').strip()
    text = text.replace('Add to Wish List', '').strip()
    
    # Remove multiple spaces
    text = ' '.join(text.split())
    
    return text

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
    
    # If this is the first run and we couldn't scrape, initialize with empty data
    if not current_cameras and not existing_data.get('cameras'):
        print("Initializing camera database...")
        camera_data = {
            "cameras": [],
            "last_updated": datetime.now().isoformat(),
            "total_cameras_tracked": 0,
            "note": "Initialized - waiting for successful scrape"
        }
        save_cameras(camera_data)
        # Create empty new_cameras.txt
        open('new_cameras.txt', 'w').close()
        return
    
    # If we couldn't scrape but have existing data, skip update
    if not current_cameras:
        print("Scraping failed, skipping update to preserve data integrity")
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
