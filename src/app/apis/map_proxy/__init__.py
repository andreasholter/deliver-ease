import databutton as db
import requests
import datetime
from fastapi import APIRouter, Query, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.libs.admin_utils import get_admin_emails

router = APIRouter(prefix="/map_proxy")

def send_failure_notification(api_name: str, error_details: str):
    """
    Sends a failure notification email to the configured admin list.
    """
    admin_emails = get_admin_emails()
    if not admin_emails:
        print("No admin emails configured. Skipping failure notification.")
        return

    subject = f"🚨 API Failure Alert: {api_name}"
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    content_text = f"""
    An API failure was detected.
    
    API/Service: {api_name}
    Timestamp (UTC): {timestamp}
    Error Details: {error_details}
    """
    
    content_html = f"""
    <html>
        <body>
            <h2>API Failure Alert</h2>
            <p>A critical service call has failed. Details are below:</p>
            <ul>
                <li><strong>API/Service:</strong> {api_name}</li>
                <li><strong>Timestamp (UTC):</strong> {timestamp}</li>
                <li><strong>Error Details:</strong> <pre>{error_details}</pre></li>
            </ul>
        </body>
    </html>
    """
    
    try:
        db.notify.email(
            to=admin_emails,
            subject=subject,
            content_html=content_html,
            content_text=content_text
        )
        print(f"Sent failure notification to: {', '.join(admin_emails)}")
    except Exception as e:
        print(f"CRITICAL: Failed to send admin failure notification via db.notify.email: {e}")


@router.get("/image", tags=["stream"])
def get_map_image(
    background_tasks: BackgroundTasks,
    address: str = Query(..., description="The full address to generate a map for."),
    width: int = Query(400, description="The width of the map in pixels."),
    height: int = Query(300, description="The height of the map in pixels."),
    zoom: int = Query(15, description="The zoom level of the map.")
):
    """
    Acts as a secure proxy to the Google Maps Static API.
    It fetches the map image on the backend to protect the API key.
    If it fails, it notifies an admin via email.
    """
    api_key = db.secrets.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        error_message = "Google Maps API key is not configured in Databutton secrets."
        background_tasks.add_task(send_failure_notification, "map_proxy (Google Maps)", error_message)
        return Response(status_code=500, content=error_message)

    base_url = "https://maps.googleapis.com/maps/api/staticmap"
    
    params = {
        "center": address,
        "zoom": zoom,
        "size": f"{width}x{height}",
        "maptype": "roadmap",
        "markers": f"color:red|label:A|{address}",
        "key": api_key,
    }

    try:
        # Use a timeout to prevent hanging requests
        response = requests.get(base_url, params=params, stream=True, timeout=5)
        response.raise_for_status()
        
        return StreamingResponse(response.iter_content(chunk_size=8192), media_type=response.headers['Content-Type'])

    except requests.exceptions.Timeout:
        error_message = "Request to Google Maps Static API timed out after 5 seconds."
        background_tasks.add_task(send_failure_notification, "map_proxy (Google Maps)", error_message)
        print(error_message)
        return Response(status_code=504, content="The map service is currently unavailable.")
        
    except requests.exceptions.RequestException as e:
        error_body = "No response body"
        if e.response is not None:
            error_body = e.response.text
        
        error_message = f"Failed to fetch map from Google. Status: {e.response.status_code if e.response is not None else 'N/A'}. Body: {error_body}"
        background_tasks.add_task(send_failure_notification, "map_proxy (Google Maps)", error_message)
        print(f"Error fetching map from Google: {e}")
        return Response(status_code=502, content="The map service is currently unavailable.")
