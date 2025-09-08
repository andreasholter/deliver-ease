


# src/app/apis/postal_checker/__init__.py
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Dict
import requests
import databutton as db
from datetime import datetime
import pytz
import csv
import io
import httpx
import logging

# Set the logging level for the httpx library to WARNING to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)


# Import the new firebase helper
from app.libs.firebase_admin import get_firestore_client

router = APIRouter(prefix="/postalcode", tags=["PostalCode Serviceability"])


# --- Pydantic Models ---
class PostalCodeEntry(BaseModel):
    postal_code: str = Field(pattern=r"^\d{4}$")
    carrier_no: str
    carrier_en: str
    carrier_sv: str
    carrier_da: str
    delivery_info: str

class BulkUploadValidationResult(BaseModel):
    success: bool
    message: str
    errors: Optional[List[str]] = None
    data: Optional[List[PostalCodeEntry]] = None

class PostalCodeAvailabilityRequest(BaseModel):
    postal_code: str = Field(
        ...,
        description="The postal code to check for serviceability.",
        min_length=4,
        max_length=4,
        pattern="^\\d{4}$",
    )
    language: str = Field(
        default="no",
        description="The language for the response (e.g., 'en', 'no'). Defaults to 'no'.",
        pattern="^(no|en|sv|da)$"
    )

# The response will now be a simple list of human-readable strings
class PostalCodeAvailabilityResponse(BaseModel):
    serviceable: bool
    delivery_options: List[str] = []
    message: Optional[str] = None

# --- Helper Functions ---
def format_delivery_window(start_str: str, end_str: str, language: str = "no") -> str:
    """Formats a delivery window into a human-readable string like 'Today between 17:30 and 19:30'.
    
    Args:
        start_str: ISO formatted start time string
        end_str: ISO formatted end time string
        language: Language code ('no', 'en', 'sv', 'da')
    """
    # Hardcoded translation dictionaries to avoid file system access
    translations = {
        "no": {
            "today": "I dag",
            "tomorrow": "I morgen",
            "between": "mellom",
            "and": "og",
            "monday": "mandag",
            "tuesday": "tirsdag",
            "wednesday": "onsdag",
            "thursday": "torsdag",
            "friday": "fredag",
            "saturday": "lørdag",
            "sunday": "søndag"
        },
        "en": {
            "today": "Today",
            "tomorrow": "Tomorrow",
            "between": "between",
            "and": "and",
            "monday": "Monday",
            "tuesday": "Tuesday",
            "wednesday": "Wednesday",
            "thursday": "Thursday",
            "friday": "Friday",
            "saturday": "Saturday",
            "sunday": "Sunday"
        },
        "sv": {
            "today": "Idag",
            "tomorrow": "Imorgon",
            "between": "mellan",
            "and": "och",
            "monday": "måndag",
            "tuesday": "tisdag",
            "wednesday": "onsdag",
            "thursday": "torsdag",
            "friday": "fredag",
            "saturday": "lördag",
            "sunday": "söndag"
        },
        "da": {
            "today": "I dag",
            "tomorrow": "I morgen",
            "between": "mellem",
            "and": "og",
            "monday": "mandag",
            "tuesday": "tirsdag",
            "wednesday": "onsdag",
            "thursday": "torsdag",
            "friday": "fredag",
            "saturday": "lørdag",
            "sunday": "søndag"
        }
    }
    
    # Fallback to English if language not supported
    lang_dict = translations.get(language, translations["en"])
    
    oslo_tz = pytz.timezone("Europe/Oslo")
    now_oslo = datetime.now(oslo_tz)
    
    try:
        start_dt = datetime.fromisoformat(start_str).astimezone(oslo_tz)
        end_dt = datetime.fromisoformat(end_str).astimezone(oslo_tz)
    except (ValueError, TypeError):
        return "Invalid date format"

    start_time = start_dt.strftime("%H:%M")
    end_time = end_dt.strftime("%H:%M")

    if start_dt.date() == now_oslo.date():
        day_str = lang_dict["today"]
    elif (start_dt.date() - now_oslo.date()).days == 1:
        day_str = lang_dict["tomorrow"]
    else:
        # Map English day names to translated versions
        english_day = start_dt.strftime("%A").lower()  # e.g., "sunday"
        day_str = lang_dict.get(english_day, start_dt.strftime("%A"))  # fallback to English

    between_word = lang_dict["between"]
    and_word = lang_dict["and"]
    return f"{day_str} {between_word} {start_time} {and_word} {end_time}"


# --- Porterbuddy API Configuration ---
PORTERBUDDY_API_URL = "https://api.porterbuddy.com/availability"
PORTERBUDDY_ORIGIN_STREET_NAME = "Haraldrudveien 11"
PORTERBUDDY_ORIGIN_POSTAL_CODE = "0581"
PORTERBUDDY_ORIGIN_CITY = "Oslo"
PORTERBUDDY_ORIGIN_COUNTRY_CODE = "NO"
PORTERBUDDY_DESTINATION_STATIC_STREET_NAME = "Haraldrudveien 11"
PORTERBUDDY_DESTINATION_STATIC_CITY = "Oslo"
PORTERBUDDY_DESTINATION_COUNTRY_CODE = "NO"
PORTERBUDDY_STATIC_EMAIL = "hello@kosibox.no"
PORTERBUDDY_STATIC_PARCEL_DESCRIPTION = "Kosibox gavelevering"


# --- Bulk Upload Endpoint ---
def validate_csv_data(file: UploadFile) -> BulkUploadValidationResult:
    """
    Reads a CSV file, validates its structure and content, and formats the data.
    This function is designed to be run as a dependency.
    """
    errors = []
    validated_data = []
    
    # Read file content into memory
    content = file.file.read()
    
    # Check for empty file
    if not content.strip():
        return BulkUploadValidationResult(success=False, message="The uploaded file is empty.")

    try:
        # Use TextIOWrapper to handle decoding, specifically using 'utf-8-sig'
        # to automatically handle the Byte Order Mark (BOM) if present.
        decoded_content = content.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(decoded_content))
        
        # --- Header Validation ---
        header = next(reader)
        expected_headers = ["postal_code", "carrier_no", "carrier_en", "carrier_sv", "carrier_da", "delivery_info"]
        if header != expected_headers:
            return BulkUploadValidationResult(
                success=False,
                message=f"Invalid CSV headers. Expected '{', '.join(expected_headers)}' but got '{', '.join(header)}'."
            )

        # --- Row-by-Row Validation ---
        for i, row in enumerate(reader, start=2): # Start from line 2
            if len(row) != 6:
                errors.append(f"Row {i}: Expected 6 columns, but found {len(row)}.")
                continue

            postal_code, carrier_no, carrier_en, carrier_sv, carrier_da, delivery_info = row
            
            # Intelligent Formatting for postal code
            postal_code = postal_code.strip().lstrip("'") # Remove whitespace and leading apostrophe
            if postal_code.isdigit() and len(postal_code) < 4:
                postal_code = postal_code.zfill(4) # Pad with leading zeros

            # Validation using Pydantic model
            try:
                entry = PostalCodeEntry(
                    postal_code=postal_code,
                    carrier_no=carrier_no.strip(),
                    carrier_en=carrier_en.strip(),
                    carrier_sv=carrier_sv.strip(),
                    carrier_da=carrier_da.strip(),
                    delivery_info=delivery_info.strip()
                )
                if not entry.carrier_no or not entry.carrier_en or not entry.carrier_sv or not entry.carrier_da or not entry.delivery_info:
                    errors.append(f"Row {i}: All carrier and delivery_info fields are required and cannot be empty.")
                else:
                    validated_data.append(entry)
            except ValidationError as e:
                # Format Pydantic errors to be more user-friendly
                for error in e.errors():
                    field = error['loc'][0]
                    msg = error['msg']
                    errors.append(f"Row {i}: Invalid value for '{field}'. {msg}.")

    except UnicodeDecodeError:
        return BulkUploadValidationResult(success=False, message="Failed to decode file. Please ensure it is saved with UTF-8 encoding.")
    except Exception as e:
        # Catch-all for other parsing errors
        return BulkUploadValidationResult(success=False, message=f"An unexpected error occurred during parsing: {str(e)}")


    if errors:
        return BulkUploadValidationResult(success=False, message="Validation failed with errors.", errors=errors)
    
    if not validated_data:
        return BulkUploadValidationResult(success=False, message="The file contains no valid data rows.")

    return BulkUploadValidationResult(success=True, message="Validation successful", data=validated_data)


@router.post("/bulk-upload-replace", summary="Upload and replace postal code data from a CSV")
async def bulk_upload_replace(
    validation_result: BulkUploadValidationResult = Depends(validate_csv_data),
):
    """
    This endpoint safely replaces the entire postal code dataset in Firestore.
    1. It relies on a dependency (`validate_csv_data`) to upload and validate the CSV.
    2. If validation fails, this function won't even be called, and the dependency will return a 422 error with details.
    3. If validation is successful, it proceeds to replace the data.
    """
    # --- Fail-safe Check ---
    # This is a critical check to ensure that we don't proceed if the
    # dependency function found validation errors.
    if not validation_result.success:
        raise HTTPException(
            status_code=422, # Unprocessable Entity
            detail=validation_result.message or "CSV validation failed.",
        )
    if not validation_result.data:
         raise HTTPException(
            status_code=422, # Unprocessable Entity
            detail="Validation was successful but no data was returned.",
        )

    firestore_db = get_firestore_client()
    if not firestore_db:
        raise HTTPException(status_code=500, detail="Firestore client could not be initialized.")
        
    try:
        # --- Group data by postal code ---
        data_by_postal_code: Dict[str, List[Dict]] = {}
        for entry in validation_result.data:
            if entry.postal_code not in data_by_postal_code:
                data_by_postal_code[entry.postal_code] = []
            
            data_by_postal_code[entry.postal_code].append({
                "carrierName": {
                    "no": entry.carrier_no,
                    "en": entry.carrier_en,
                    "sv": entry.carrier_sv,
                    "da": entry.carrier_da,
                },
                "deliveryInfo": entry.delivery_info,
                "serviceable": True # All entries from the file are considered serviceable
            })

        # --- Firestore Transaction ---
        # First, we'll delete all existing documents in the collection
        collection_ref = firestore_db.collection("postalCodeData")
        docs = collection_ref.stream()
        for doc in docs:
            doc.reference.delete()
        
        print(f"Successfully deleted all existing documents in 'postalCodeData'.")

        # Then, we'll add the new documents in a batch
        batch = firestore_db.batch()
        for postal_code, carriers in data_by_postal_code.items():
            doc_ref = collection_ref.document(postal_code)
            batch.set(doc_ref, {"carriers": carriers})
        
        batch.commit()
        
        print(f"Successfully uploaded {len(data_by_postal_code)} new postal code documents.")

        return {
            "message": f"Successfully uploaded and replaced data for {len(data_by_postal_code)} postal codes.",
            "postal_codes_updated": list(data_by_postal_code.keys()),
        }

    except Exception as e:
        print(f"ERROR: An unexpected error occurred during Firestore operation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during the database update. Your data may be in an inconsistent state. Please contact support. Error: {e}",
        )

# --- Main Endpoint ---
@router.post("/check-availability", response_model=PostalCodeAvailabilityResponse)
async def check_postal_code_serviceability(request_body: PostalCodeAvailabilityRequest):
    """
    Checks serviceability of a given postal code.
    First, it tries Porterbuddy API. If Porterbuddy doesn't service the area,
    it falls back to a manually managed list in Firestore.
    Returns a formatted list of delivery options.
    """
    porterbuddy_options = await get_porterbuddy_options(request_body.postal_code, request_body.language)

    if porterbuddy_options:
        return PostalCodeAvailabilityResponse(
            serviceable=True,
            delivery_options=porterbuddy_options,
            message="Delivery options retrieved successfully.",
        )

    # Fallback to Firestore if Porterbuddy has no options
    print(f"Porterbuddy has no options for {request_body.postal_code}. Falling back to Firestore.")
    firestore_options = await get_firestore_options(request_body.postal_code, request_body.language)

    if firestore_options:
        return PostalCodeAvailabilityResponse(
            serviceable=True,
            delivery_options=firestore_options,
            message="Delivery options retrieved from local providers.",
        )

    return PostalCodeAvailabilityResponse(
        serviceable=False,
        delivery_options=[],
        message="This postal code is not currently serviceable.",
    )


async def get_porterbuddy_options(postal_code: str, language: str) -> List[str]:
    """Helper function to get and process options from Porterbuddy."""
    porterbuddy_api_key = db.secrets.get("PORTERBUDDY_API_KEY")
    if not porterbuddy_api_key:
        print("ERROR: PORTERBUDDY_API_KEY secret not found.")
        return []

    # Translations for "Porterbuddy"
    porterbuddy_translations = {
        "no": "Porterbuddy",
        "en": "Porterbuddy",
        "sv": "Porterbuddy",
        "da": "Porterbuddy"
    }
    carrier_name = porterbuddy_translations.get(language, "Porterbuddy")

    headers = {"Content-Type": "application/json", "x-api-key": porterbuddy_api_key}
    payload = {
        "originAddress": {
            "streetName": PORTERBUDDY_ORIGIN_STREET_NAME,
            "postalCode": PORTERBUDDY_ORIGIN_POSTAL_CODE,
            "city": PORTERBUDDY_ORIGIN_CITY,
            "country": PORTERBUDDY_ORIGIN_COUNTRY_CODE
        },
        "destinationAddress": {
            "postalCode": postal_code,
            "country": PORTERBUDDY_DESTINATION_COUNTRY_CODE
        },
        "email": PORTERBUDDY_STATIC_EMAIL,
        "parcelDescription": PORTERBUDDY_STATIC_PARCEL_DESCRIPTION,
        "pickupWindows": None,
        "deliveryWindows": [],
        "parcels": [{"weight": 1000, "items": [{"sku": "DEFAULT_SKU", "quantity": 1, "weight": 500}]}]
    }

    try:
        # Use a separate httpx client for this request to control logging
        async with httpx.AsyncClient() as client:
            response = await client.post(PORTERBUDDY_API_URL, json=payload, headers=headers, timeout=10)

        # Don't raise for status on 404-like errors, as it can mean non-serviceable
        if response.status_code >= 500:
            response.raise_for_status()
        if response.status_code >= 400: # e.g. 400, 422 for non-serviceable
            print(f"Porterbuddy returned status {response.status_code}. Assuming not serviceable. Response: {response.text}")
            return []

        porterbuddy_data = response.json()
        returned_windows = porterbuddy_data.get("deliveryWindows", [])
        
        if not returned_windows:
            return []

        # -- Business Logic: Cut-off time and formatting --
        oslo_tz = pytz.timezone("Europe/Oslo")
        now_oslo = datetime.now(oslo_tz)
        
        formatted_options = []
        for window in returned_windows:
            start_dt = datetime.fromisoformat(window["start"]).astimezone(oslo_tz)
            
            # Skip same-day delivery if it's past 12:00 PM
            if start_dt.date() == now_oslo.date() and now_oslo.hour >= 12:
                continue
                
            delivery_window_str = format_delivery_window(window["start"], window["end"], language)
            formatted_options.append(f"{carrier_name}: {delivery_window_str}")

        # Return only the first two available options
        return formatted_options[:2]

    except httpx.RequestError as e:
        print(f"ERROR: Network request to Porterbuddy failed: {e}")
        return [] # Return empty on network error, allowing fallback
    except Exception as e:
        print(f"ERROR: Unexpected error processing Porterbuddy response: {e}")
        return []


async def get_firestore_options(postal_code: str, language: str) -> List[str]:
    """Helper function to get and process options from Firestore."""
    try:
        firestore_db = get_firestore_client()
        if not firestore_db:
            print("ERROR: Firestore client could not be initialized.")
            return []

        doc_ref = firestore_db.collection("postalCodeData").document(postal_code)
        doc = doc_ref.get()

        if not doc.exists:
            print(f"Firestore: No document found for postal code {postal_code}.")
            return []

        data = doc.to_dict()
        
        # Correctly look for the 'carriers' field produced by the frontend
        carrier_list = data.get("carriers", [])
        if not carrier_list:
            print(f"Firestore: Document for {postal_code} has no 'carriers' list.")
            return []
            
        # Format the delivery info from each serviceable carrier
        options = []
        for carrier in carrier_list:
            # Check if the individual carrier is marked as serviceable
            if carrier.get("serviceable"):
                carrier_name_obj = carrier.get('carrierName', {})
                # Get the translation for the requested language, fallback to 'no', then a default string
                carrier_name = carrier_name_obj.get(language, carrier_name_obj.get('no', 'Unknown Carrier'))
                
                delivery_info = carrier.get('deliveryInfo', 'No delivery info')
                options.append(f"{carrier_name}: {delivery_info}")
        
        return options

    except Exception as e:
        print(f"ERROR: An unexpected error occurred while fetching from Firestore: {e}")
        return []
