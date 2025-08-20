from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PropertyType(str, Enum):
    HOUSE = "house"
    FLAT = "flat"
    BUNGALOW = "bungalow"
    MAISONETTE = "maisonette"
    LAND = "land"


class PropertyStatus(str, Enum):
    FOR_SALE = "for_sale"
    FOR_RENT = "for_rent"
    SOLD = "sold"
    LET = "let"


class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str
    postcode: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None


class PropertyLineage(BaseModel):
    source: str  # "rightmove", "zoopla", etc.
    source_id: str
    last_updated: datetime
    reliability_score: float = Field(..., ge=0, le=1)


class Property(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    price: int
    property_type: PropertyType
    status: PropertyStatus
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    location: Location
    images: List[str] = []
    features: List[str] = []
    energy_rating: Optional[str] = None
    council_tax_band: Optional[str] = None
    tenure: Optional[str] = None  # "freehold", "leasehold"
    floor_area_sqft: Optional[int] = None
    garden: Optional[bool] = None
    parking: Optional[bool] = None
    lineage: PropertyLineage
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }