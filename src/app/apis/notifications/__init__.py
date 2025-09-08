import databutton as db
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, EmailStr
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"]
)

# --- Pydantic Models ---
class FailureNotificationRequest(BaseModel):
    """Defines the structure for a failure notification request."""
    api_name: str
    error_details: str
    timestamp_utc: str

class AdminEmailRequest(BaseModel):
    """Defines the structure for adding/removing an admin email."""
    email: EmailStr

from app.libs.admin_utils import get_admin_emails, ADMIN_EMAIL_LIST_KEY

def send_failure_email(email_list: list[str], subject: str, content_html: str, content_text: str):
    """Sends notification emails to the admin list."""
    try:
        db.notify.email(
            to=email_list,
            subject=subject,
            content_html=content_html,
            content_text=content_text
        )
        logger.info(f"Successfully sent failure notification to: {email_list}")
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")

# --- API Endpoints ---
@router.post(
    "/notify-failure",
    summary="Notify administrators about an API failure",
    status_code=status.HTTP_202_ACCEPTED
)
def notify_failure(
    request: FailureNotificationRequest,
    background_tasks: BackgroundTasks
):
    """Handles an API failure notification and sends an email to admins."""
    admin_emails = get_admin_emails()

    if not admin_emails:
        logger.warning("No admin emails configured. Skipping notification.")
        return {"message": "Notification skipped; no admin emails configured."}

    subject = f"🚨 API Failure Alert: {request.api_name}"
    content_html = f"""
    <html><body>
        <h2>API Failure Alert</h2>
        <p>A critical third-party API has failed. Details are below:</p>
        <ul>
            <li><strong>API/Service:</strong> {request.api_name}</li>
            <li><strong>Error Details:</strong> {request.error_details}</li>
            <li><strong>Timestamp (UTC):</strong> {request.timestamp_utc}</li>
        </ul>
        <p>Please investigate this issue to ensure service stability.</p>
    </body></html>
    """
    content_text = (
        f"API Failure Alert\n\nA critical third-party API has failed. Details are below:\n"
        f"- API/Service: {request.api_name}\n"
        f"- Error Details: {request.error_details}\n"
        f"- Timestamp (UTC): {request.timestamp_utc}\n\n"
        f"Please investigate this issue to ensure service stability."
    )

    background_tasks.add_task(send_failure_email, admin_emails, subject, content_html, content_text)
    return {"message": "Failure notification has been queued."}

@router.get(
    "/admin/emails",
    summary="Get the list of admin email addresses for notifications",
    response_model=list[EmailStr]
)
def get_admin_email_list():
    """Retrieves the list of emails configured for admin notifications."""
    return get_admin_emails()

@router.post(
    "/admin/emails",
    summary="Add an email to the admin notification list",
    status_code=status.HTTP_201_CREATED
)
def add_admin_email(request: AdminEmailRequest):
    """
    Adds a new, validated email address to the persistent admin list in storage.
    """
    admin_emails = get_admin_emails()
    email_to_add = request.email

    if email_to_add in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address already exists in the notification list."
        )

    admin_emails.append(email_to_add)
    db.storage.json.put(ADMIN_EMAIL_LIST_KEY, admin_emails)
    logger.info(f"Added '{email_to_add}' to admin email list.")
    return {"message": "Email address added successfully.", "email_list": admin_emails}

@router.delete(
    "/admin/emails",
    summary="Remove an email from the admin notification list",
    status_code=status.HTTP_200_OK
)
def delete_admin_email(request: AdminEmailRequest):
    """Deletes an email address from the persistent admin list."""
    admin_emails = get_admin_emails()
    email_to_delete = request.email

    if email_to_delete not in admin_emails:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email address not found in the notification list."
        )

    admin_emails.remove(email_to_delete)
    db.storage.json.put(ADMIN_EMAIL_LIST_KEY, admin_emails)
    logger.info(f"Removed '{email_to_delete}' from admin email list.")
    return {"message": "Email address removed successfully.", "email_list": admin_emails}
