from fastapi import APIRouter
from pydantic import BaseModel
import databutton as db
import os

router = APIRouter()

class MapConfigResponse(BaseModel):
    api_key: str

@router.get("/map-config", response_model=MapConfigResponse)
def get_map_config():
    """
    Provides the necessary configuration for the frontend map component.
    """
    # Use os.environ.get for development flexibility, fallback to db.secrets
    api_key = db.secrets.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY is not set in secrets.")
    return MapConfigResponse(api_key=api_key)
