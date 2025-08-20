from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from app.models.property import PropertyType, PropertyStatus, Property


class DistanceUnit(str, Enum):
    METERS = "meters"
    KILOMETERS = "kilometers"
    MILES = "miles"


class AmenityType(str, Enum):
    PARK = "park"
    TRAIN_STATION = "train_station"
    GYM = "gym"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    SHOPPING_CENTER = "shopping_center"
    RESTAURANT = "restaurant"
    PHARMACY = "pharmacy"


class ProximityFilter(BaseModel):
    amenity_type: AmenityType
    max_distance: float
    distance_unit: DistanceUnit = DistanceUnit.KILOMETERS
    walking_distance: bool = False  # If True, use walking distance instead of straight-line


class EnvironmentalFilter(BaseModel):
    max_air_pollution_level: Optional[int] = None  # 1-10 scale
    max_noise_level: Optional[int] = None  # 1-10 scale
    avoid_flood_risk: bool = False
    min_green_space_proximity: Optional[float] = None  # km


class CommuteFilter(BaseModel):
    destination_address: str
    max_commute_minutes: int
    transport_modes: List[str] = ["public_transport", "walking", "cycling"]


class SearchCriteria(BaseModel):
    # Basic filters
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    property_types: List[PropertyType] = []
    status: List[PropertyStatus] = [PropertyStatus.FOR_SALE]
    min_bedrooms: Optional[int] = None
    max_bedrooms: Optional[int] = None
    min_bathrooms: Optional[int] = None
    
    # Location filters
    center_latitude: Optional[float] = Field(None, ge=-90, le=90)
    center_longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = None
    areas: List[str] = []  # Specific areas/postcodes
    
    # Lifestyle filters
    proximity_filters: List[ProximityFilter] = []
    environmental_filters: Optional[EnvironmentalFilter] = None
    commute_filters: List[CommuteFilter] = []
    
    # Property features
    must_have_garden: Optional[bool] = None
    must_have_parking: Optional[bool] = None
    min_floor_area_sqft: Optional[int] = None
    
    # Search options
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    sort_by: str = "relevance"  # "price_asc", "price_desc", "distance", "relevance"


class SearchResultProperty(Property):
    match_score: float = Field(..., ge=0, le=1)
    distance_km: Optional[float] = None
    matched_filters: List[str] = []  # Which filters this property satisfied


class SearchResult(BaseModel):
    properties: List[SearchResultProperty]
    total_count: int
    search_time_ms: int
    filters_applied: Dict[str, Any]
    
    class Config:
        json_encoders = {
            # Add any custom encoders if needed
        }