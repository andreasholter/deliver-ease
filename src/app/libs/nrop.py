

# src/app/libs/nrop.py
import databutton as db
import requests
from fastapi import HTTPException
from requests.auth import HTTPBasicAuth
from typing import Dict, Any

def get_address_from_nrop(phone_number: str) -> Dict[str, Any]:
    """
    Looks up an address using the nrop.no API.

    Args:
        phone_number: The phone number to look up.

    Returns:
        A dictionary containing the address information, or an empty dictionary if not found.
    """
    api_key = db.secrets.get("NROP_API_KEY")
    api_password = db.secrets.get("NROP_API_PASSWORD")

    if not api_key or not api_password:
        print("NROP API key or password not found in secrets.")
        print(f"API Key exists: {bool(api_key)}, Password exists: {bool(api_password)}")
        return {}

    # Ensure the phone number starts with the Norwegian country code (47)
    phone_number = phone_number.lstrip('+')
    if not phone_number.startswith('47'):
        phone_number = f"47{phone_number}"

    # The nrop.no API expects the phone number to be in E164 format, with the '+' URL-encoded.
    encoded_phone_number = f"%2B{phone_number}"
    url = f"https://api.nrop.no/nrop/{encoded_phone_number}"

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(api_key, api_password),
            headers={"Accept-Version": "1.2.*"}
        )

        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        data = response.json()

        # If the number was found and not hidden, normalize the keys to snake_case
        if data.get("phoneBook"):
            return {
                "first_name": data.get("firstName", ""),
                "last_name": data.get("lastName", ""),
                "address": data.get("address", ""),
                "postal_code": data.get("postalCode", ""),
                "city": data.get("city", ""),
                "customer_type": data.get("customerType", ""),
            }
        else:
            return {}

    except requests.exceptions.HTTPError as e:
        # If the error is a 404, we re-raise it as a specific HTTPException
        # so the main API can handle it as a "Not Found" case.
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Phone number not found in nrop.no") from e
        # For rate limiting (429), pass it through so frontend can trigger manual entry
        elif e.response.status_code == 429:
            raise HTTPException(status_code=429, detail="API quota exceeded. Please try again later or enter postal code manually.") from e
        # For any other HTTP error (403, 5xx), we raise a generic 503 error.
        raise HTTPException(status_code=503, detail=f"NROP API Error: {e.response.status_code}") from e
    except requests.exceptions.RequestException as e:
        # For non-HTTP errors like timeouts or connection problems
        print(f"Error calling nrop.no API: {e}")
        raise HTTPException(status_code=503, detail="Error communicating with the address lookup service.") from e
