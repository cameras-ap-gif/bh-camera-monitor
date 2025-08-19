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
    
    # Get ScraperAPI key from environment
    api_key = os.environ.get('SCRAPER_API_KEY')
    
    if not api_key:
        print("ERROR: SCRAPER_API_KEY not found in environment variables!")
        print("Please add SCRAPER_API_KEY to GitHub Secrets")
        return []
    
    print(f"Using ScraperAPI (key starts with: {api_key[:10]}...)")
    
    # ScraperAPI endpoint with JavaScript rendering enabled
    params = {
        'api_key': api_key,
        'url': url,
        'render': 'true',  # Enable JavaScript rendering
        'country_code': 'us'
    }
    
    try:
        print("Sending request to ScraperAPI...")
        response = requests.get('http://api.scraperapi.com', params=params, timeout=60)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("Successfully retrieved page via ScraperAPI")
            return parse_bh_html(response.text)
        else:
            print(f"ScraperAPI returned status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return []
            
    except requests.exceptions.Timeout:
        print("ScraperAPI request timed out (this can happen with JavaScript rendering)")
        return []
    except Exception as e:
        print(f"Error with ScraperAPI: {e}")
        return []

def parse_bh_html(html_content):
    """Parse B&H HTML to extract camera names"""
    soup = BeautifulSoup(html_content, 'html.parser')
    cameras_found = []
    
    print("Parsing HTML content...")
    
    # Method 1: Look for h3 tags (most common for product names on B&H)
    h3_tags = soup.find_all('h3')
    print(f"Found {len(h3_tags)} h3 tags")
    
    for h3 in h3_tags:
        text = h3.get_text(strip=True)
        if is_camera_name(text):
            clean_name = clean_camera_name(text)
            if clean_name and clean_name not in cameras_found:
                cameras_found.append(clean_name)
                print(f"  Found camera: {clean_name}")
    
    # Method 2: Look for data-selenium attributes
    selenium_elements = soup.find_all(attrs={"data-selenium": True})
    print(f"Found {len(selenium_elements)} elements with data-selenium")
    
    for elem in selenium_elements:
        selenium_value = elem.get('data-selenium', '')
        if 'product' in selenium_value.lower() or 'name' in selenium_value.lower():
            text = elem.get_text(strip=True)
            if is_camera_name(text):
                clean_name = clean_camera_name(text)
                if clean_name and clean_name not in cameras_found:
                    cameras_found.append(clean_name)
    
    # Method 3: Look for links containing camera names
    for link in soup.find_all('a', href=True):
        if '/c/product/' in link.get('href', ''):
            text = link.get_text(strip=True)
            if is_camera_name(text):
                clean_name = clean_camera_name(text)
                if clean_name and clean_name not in cameras_found:
                    cameras_found.append(clean_name)
    
    print(f"Total unique cameras found: {len(cameras_found)}")
    return cameras_found

def is_camera_name(text):
    """Check if text is likely a camera name"""
    if not text or len(text) < 10 or len(text) > 200:
        return False
    
    # Skip common non-product text
    skip_phrases = ['Key Features', 'Show More', 'Add to Cart', 'Special Offers', 
                   'Calculate Shipping', 'Add to Wish List', 'In Stock', 'Preorder',
                   'Request', 'Available', 'B&H #', 'MFR #', '$']
    
    for phrase in skip_phrases:
        if phrase in text:
            return False
    
    # Camera brands to look for
    camera_brands = ['Sony', 'Canon', 'Nikon', 'FUJIFILM', 'Fujifilm', 'Panasonic', 
                    'OM SYSTEM', 'Olympus', 'Leica', 'Hasselblad', 'Pentax', 
                    'Ricoh', 'Sigma', 'GoPro', 'DJI', 'Insta360', 'Kodak', 'Polaroid']
    
    # Check if any brand is in the text
    has_brand = any(brand.lower() in text.lower() for brand in camera_brands)
    
    # Camera-related keywords
    camera_keywords = ['camera', 'mirrorless', 'dslr', 'lens', 'kit', 'body']
    has_keyword = any(keyword in text.lower() for keyword in camera_keywords)
    
    return has_brand and (has_keyword or 'mm' in text)

def clean_camera_name(text):
    """Clean up camera name text"""
    # Remove line breaks and extra spaces
    text = ' '.join(text.split())
    
    # Remove common suffixes that aren't part of the product name
    remove_phrases = ['Key Features', 'Show More', 'Add to Cart', 'Add to Wish List',
                     'Special Offers', 'Calculate Shipping', 'In Stock', 'Preorder']
    
    for phrase in remove_phrases:
        text = text.replace(phrase, '')
    
    # Trim and return
    return text.strip()

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
    print("-" * 50)
    
    # Load existing data
    existing_data = load_existing_cameras()
    print(f"Previously tracked cameras: {len(existing_data.get('cameras', []))}")
    
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
        print(f"\n🎉 Found {len(new_cameras)} NEW cameras!")
        with open('new_cameras.txt', 'w') as f:
            for camera in new_cameras:
                f.write(f"{camera}\n")
                print(f"  - {camera}")
    else:
        print("\n✓ No new cameras found since last check")
        open('new_cameras.txt', 'w').close()

if __name__ == "__main__":
    main()
