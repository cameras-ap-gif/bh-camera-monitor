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
                print(f"✗ Failed to send to {recipient}: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"✗ Error sending to {recipient}: {e}")
            return False
    
    return True

def main():
    # Read new cameras from file
    new_cameras = []
    if os.path.exists('new_cameras.txt'):
        with open('new_cameras.txt', 'r') as f:
            new_cameras = [line.strip() for line in f if line.strip()]
    
    if not new_cameras:
        print("No new cameras to report")
        return
    
    # Get recipients from environment variable
    recipients_str = os.environ.get('EMAIL_RECIPIENTS', '')
    if not recipients_str:
        print("Error: EMAIL_RECIPIENTS not found")
        return
    
    recipients = [r.strip() for r in recipients_str.split(',')]
    
    # Send emails
    print(f"Sending notification for {len(new_cameras)} new cameras to {len(recipients)} recipient(s)")
    send_courier_email(new_cameras, recipients)

if __name__ == "__main__":
    main()
