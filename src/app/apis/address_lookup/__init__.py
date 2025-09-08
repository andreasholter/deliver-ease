


# src/app/apis/address_lookup/__init__.py
import databutton as db
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

# Import the new nrop library
from app.libs.nrop import get_address_from_nrop

router = APIRouter(prefix="/addresslookup")

# --- Pydantic Models ---
class PhoneNumberRequest(BaseModel):
    phone_number: str = Field(..., description="Norwegian phone number to look up.")

class AddressInfoResponse(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    customer_type: Optional[str] = None

# --- Configuration for Address Provider ---
PROVIDER_CONFIG_KEY = "address_provider_config"

def get_provider():
    return db.storage.json.get(PROVIDER_CONFIG_KEY, default={"provider": "1881"})

def set_provider(provider_name: str):
    db.storage.json.put(PROVIDER_CONFIG_KEY, {"provider": provider_name})

# --- 1881.no API Logic ---
def get_address_from_1881(phone_number: str):
    api_key = db.secrets.get("API_1881_KEY")
    if not api_key:
        print("Error: API_1881_KEY secret not found.")
        raise HTTPException(status_code=500, detail="API key for 1881.no is not configured.")

    headers = {"Ocp-Apim-Subscription-Key": api_key, "Content-Type": "application/json"}
    url = f"https://services.api1881.no/lookup/phonenumber/{phone_number}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Check if response has content before parsing JSON
        if not response.content:
            print(f"Empty response from 1881 API for phone {phone_number}")
            return {}
            
        data = response.json()
        
        # Check if data is None or not a dict
        if not data or not isinstance(data, dict):
            print(f"Invalid JSON response from 1881 API for phone {phone_number}: {data}")
            return {}
        
        if data.get("found") and data.get("name"):
            return {
                "first_name": data.get("firstname", ""),
                "last_name": data.get("lastname", ""),
                "address": data.get("address", {}).get("street", ""),
                "postal_code": data.get("address", {}).get("zipcode", ""),
                "city": data.get("address", {}).get("city", ""),
            }
        return {}
    except requests.exceptions.RequestException as e:
        print(f"Error calling 1881 API: {e}")
        
        # Check for specific HTTP status codes
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            if status_code == 403:
                # Check if it's a quota exceeded error
                error_text = e.response.text.lower()
                if 'quota' in error_text or 'exceeded' in error_text:
                    raise HTTPException(status_code=429, detail="API quota exceeded. Please try again later or contact support.")
                else:
                    raise HTTPException(status_code=403, detail="API access denied. Please check API configuration.")
            elif status_code == 401:
                raise HTTPException(status_code=401, detail="API authentication failed. Please check API key configuration.")
        
        # Generic fallback for other request errors
        raise HTTPException(status_code=503, detail="Error communicating with the address lookup service.")
    except ValueError as e:
        print(f"Error parsing JSON response from 1881 API: {e}")
        raise HTTPException(status_code=503, detail="Invalid response from address lookup service.")

# --- API Endpoints ---
@router.post("/address", response_model=AddressInfoResponse)
def get_address_by_phone(request: PhoneNumberRequest):
    """
    Retrieves address information based on a Norwegian phone number,
    using the configured provider (1881 or nrop).
    """
    config = get_provider()
    provider = config.get("provider", "1881")
    phone_number = request.phone_number

    address_data = {}
    if provider == "nrop":
        address_data = get_address_from_nrop(phone_number)
    elif provider == "1881":
        address_data = get_address_from_1881(phone_number)
    else:
        raise HTTPException(status_code=500, detail="Invalid address provider configured.")

    if not address_data:
        raise HTTPException(status_code=404, detail="Phone number not found or is unlisted.")

    # Since both nrop and 1881 functions now return snake_case keys, we can unpack directly.
    return AddressInfoResponse(**address_data)

@router.post("/set-provider/nrop", summary="Set nrop.no as the address provider")
def set_provider_nrop():
    set_provider("nrop")
    return {"message": "Address provider set to nrop.no"}

@router.post("/set-provider/1881", summary="Set 1881.no as the address provider")
def set_provider_1881():
    set_provider("1881")
    return {"message": "Address provider set to 1881.no"}

@router.get("/get-provider", summary="Get the current address provider")
def get_current_provider():
    return get_provider()
