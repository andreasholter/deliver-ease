# src/app/libs/firebase_admin.py
import firebase_admin
from firebase_admin import credentials, firestore
import databutton as db
import json

# A flag to ensure we don't try to initialize the app more than once.
_app_initialized = False

def get_firestore_client():
    """
    Initializes the Firebase Admin SDK if it hasn't been already and
    returns a Firestore client instance.

    This function is safe to call multiple times.
    """
    global _app_initialized

    if _app_initialized:
        return firestore.client()

    try:
        # Get the service account key from secrets
        service_account_str = db.secrets.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if not service_account_str:
            print("ERROR: FIREBASE_SERVICE_ACCOUNT_JSON secret not found.")
            return None

        # Parse the JSON string into a dictionary
        service_account_info = json.loads(service_account_str)

        # Initialize the app
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
        _app_initialized = True
        print("Firebase Admin SDK initialized successfully.")
        return firestore.client()

    except json.JSONDecodeError:
        print("ERROR: Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON. Make sure it's a valid JSON string.")
        return None
    except Exception as e:
        # Catch other potential errors during initialization (e.g., invalid credentials)
        print(f"ERROR: An unexpected error occurred during Firebase initialization: {e}")
        return None
