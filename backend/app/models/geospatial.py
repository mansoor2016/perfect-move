from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class Location(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None


class AmenityCategory(str, Enum):
    TRANSPORT = "transport"
    EDUCATION = "education"
    HEALTHCARE = "healthcare"
    SHOPPING = "shopping"
    RECREATION = "recreation"
    DINING = "dining"
    FITNESS = "fitness"


class Amenity(BaseModel):
    id: str
    name: str
    category: AmenityCategory
    location: Location
    rating: Optional[float] = Field(None, ge=0, le=5)
    opening_hours: Optional[Dict[str, str]] = None
    contact_info: Optional[Dict[str, str]] = None


class EnvironmentalData(BaseModel):
    location: Location
    air_quality_index: Optional[int] = Field(None, ge=0, le=500)
    noise_level_db: Optional[float] = Field(None, ge=0, le=120)
    flood_risk_level: Optional[str] = None  # "low", "medium", "high"
    crime_rate: Optional[float] = None  # crimes per 1000 residents
    green_space_percentage: Optional[float] = Field(None, ge=0, le=100)


class TransportLink(BaseModel):
    id: str
    name: str
    transport_type: str  # "bus", "train", "tube", "tram"
    location: Location
    lines: List[str] = []
    zones: List[str] = []  # For London transport zones


class CommuteInfo(BaseModel):
    origin: Location
    destination: Location
    duration_minutes: int
    distance_km: float
    transport_mode: str
    route_details: Optional[Dict[str, Any]] = None