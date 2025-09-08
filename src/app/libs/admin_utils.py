import databutton as db

ADMIN_EMAIL_LIST_KEY = "admin_email_list"

def get_admin_emails() -> list[str]:
    """Retrieves the list of admin emails from storage."""
    # The default value is a fallback for when no list is configured yet.
    return db.storage.json.get(ADMIN_EMAIL_LIST_KEY, default=["hello@kosibox.no"])
