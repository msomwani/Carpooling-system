from fastapi import APIRouter

from app.config.settings import settings

router = APIRouter(prefix="/maps", tags=["Maps"])


@router.get("/api-key")
def get_maps_api_key():
    """Return the Google Maps API key for frontend use."""
    return {"api_key": settings.google_maps_api_key}
