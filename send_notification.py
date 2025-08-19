import os
import requests
from datetime import datetime

def send_courier_email(new_cameras, recipients):
    """Send email via Courier API"""
    
    api_key = os.environ.get('COURIER_API_KEY')
    
    if not api_key:
        print("Error: COURIER_API_KEY not found")
        return False
    
    # Format the camera list
    if new_cameras:
        camera_list_html = "<ul>" + "".join([f"<li>{camera}</li>" for camera in new_cameras]) + "</ul>"
        subject = f"🎥 {len(new_cameras)} New Camera(s) Found on B&H Photo!"
        title = f"New Camera Alert - {datetime.now().strftime('%B %d, %Y')}"
    else:
        return True  # No new cameras, no email needed
    
    # Prepare email for each recipient
    for recipient in recipients:
        recipient = recipient.strip()
        
        payload = {
            "message": {
                "to": {
                    "email": recipient
                },
                "content": {
                    "title": subject,
                    "body": f"""
                    <h2>{title}</h2>
                    <p>The following new camera models have been detected on B&H Photo:</p>
                    {camera_list_html}
                    <p><a href="https://www.bhphotovideo.com/c/products/Digital-Cameras/ci/9811/N/4288586282?sort=NEWEST">View on B&H Photo</a></p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">This is an automated notification from your B&H Camera Monitor</p>
                    """
                },
                "routing": {
                    "method": "single",
                    "channels": ["email"]
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                "https://api.courier.com/send",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 202:
                print(f"✓ Email queued successfully for {recipient}")
            else:
                print(f"✗ Failed to sen
