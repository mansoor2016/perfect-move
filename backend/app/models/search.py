from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from datetime import datetime, time
from app.models.property import PropertyType, PropertyStatus, Property


class DistanceUnit(str, Enum):
    METERS = "meters"
    KILOMETERS = "kilometers"
    MILES = "miles"


class AmenityType(str, Enum):
    PARK = "park"
    GREEN_SPACE = "green_space"
    TRAIN_STATION = "train_station"
    BUS_STOP = "bus_stop"
    UNDERGROUND_STATION = "underground_station"
    GYM = "gym"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    SHOPPING_CENTER = "shopping_center"
    RESTAURANT = "restaurant"
    PHARMACY = "pharmacy"
    SUPERMARKET = "supermarket"
    LIBRARY = "library"
    POST_OFFICE = "post_office"


class NoiseSource(str, Enum):
    AIRPORT = "airport"
    MAJOR_ROAD = "major_road"
    RAILWAY = "railway"
    INDUSTRIAL_AREA = "industrial_area"
    NIGHTLIFE = "nightlife"


class PollutionType(str, Enum):
    AIR_QUALITY = "air_quality"
    NOISE = "noise"
    WATER_QUALITY = "water_quality"


class AmenityFilter(BaseModel):
    """Filter for amenities with proximity and avoidance options"""
    amenity_type: AmenityType
    max_distance: Optional[float] = None  # Maximum distance to amenity
    min_distance: Optional[float] = None  # Minimum distance (for avoidance)
    distance_unit: DistanceUnit = DistanceUnit.KILOMETERS
    walking_distance: bool = False  # If True, use walking distance instead of straight-line
    required: bool = True  # If True, property must have this amenity nearby
    
    @field_validator('max_distance', 'min_distance')
    @classmethod
    def validate_distances(cls, v):
        if v is not None and v < 0:
            raise ValueError('Distance must be non-negative')
        return v
    
    @model_validator(mode='after')
    def validate_distance_logic(self):
        if self.max_distance is None and self.min_distance is None:
            raise ValueError('Either max_distance or min_distance must be specified')
        
        if (self.max_distance is not None and self.min_distance is not None and 
            self.min_distance >= self.max_distance):
            raise ValueError('min_distance must be less than max_distance')
        
        return self


class ProximityFilter(BaseModel):
    """Legacy model - use AmenityFilter instead"""
    amenity_type: AmenityType
    max_distance: float
    distance_unit: DistanceUnit = DistanceUnit.KILOMETERS
    walking_distance: bool = False  # If True, use walking distance instead of straight-line
    
    @field_validator('max_distance')
    @classmethod
    def validate_max_distance(cls, v):
        if v <= 0:
            raise ValueError('max_distance must be positive')
        return v


class AvoidanceFilter(BaseModel):
    """Filter for avoiding specific noise sources or pollution areas"""
    noise_sources: List[NoiseSource] = []
    min_distance_from_noise: Optional[float] = None  # km
    max_pollution_levels: Dict[PollutionType, int] = {}  # 1-10 scale
    avoid_flood_risk_areas: bool = False
    
    @field_validator('min_distance_from_noise')
    @classmethod
    def validate_noise_distance(cls, v):
        if v is not None and v < 0:
            raise ValueError('min_distance_from_noise must be non-negative')
        return v
    
    @field_validator('max_pollution_levels')
    @classmethod
    def validate_pollution_levels(cls, v):
        for pollution_type, level in v.items():
            if not 1 <= level <= 10:
                raise ValueError(f'Pollution level for {pollution_type} must be between 1 and 10')
        return v


class EnvironmentalFilter(BaseModel):
    max_air_pollution_level: Optional[int] = Field(None, ge=1, le=10)  # 1-10 scale
    max_noise_level: Optional[int] = Field(None, ge=1, le=10)  # 1-10 scale
    avoid_flood_risk: bool = False
    min_green_space_proximity: Optional[float] = Field(None, gt=0)  # km
    avoidance_filters: Optional[AvoidanceFilter] = None
    
    @field_validator('min_green_space_proximity')
    @classmethod
    def validate_green_space_proximity(cls, v):
        if v is not None and v <= 0:
            raise ValueError('min_green_space_proximity must be positive')
        return v


class TransportMode(str, Enum):
    PUBLIC_TRANSPORT = "public_transport"
    WALKING = "walking"
    CYCLING = "cycling"
    DRIVING = "driving"


class CommuteFilter(BaseModel):
    destination_address: str = Field(..., min_length=1)
    max_commute_minutes: int = Field(..., gt=0, le=300)  # Max 5 hours
    transport_modes: List[TransportMode] = [TransportMode.PUBLIC_TRANSPORT]
    arrival_time: Optional[time] = None
    departure_time: Optional[time] = None
    
    @field_validator('transport_modes')
    @classmethod
    def validate_transport_modes(cls, v):
        if not v:
            raise ValueError('At least one transport mode must be specified')
        return v
    
    @model_validator(mode='after')
    def validate_time_logic(self):
        if self.arrival_time and self.departure_time:
            raise ValueError('Cannot specify both arrival_time and departure_time - choose one')
        
        return self


class SortOption(str, Enum):
    RELEVANCE = "relevance"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    DISTANCE = "distance"
    NEWEST = "newest"
    OLDEST = "oldest"


class SearchCriteria(BaseModel):
    # Basic filters
    min_price: Optional[int] = Field(None, ge=0)
    max_price: Optional[int] = Field(None, ge=0)
    property_types: List[PropertyType] = []
    status: List[PropertyStatus] = [PropertyStatus.FOR_SALE]
    min_bedrooms: Optional[int] = Field(None, ge=0)
    max_bedrooms: Optional[int] = Field(None, ge=0)
    min_bathrooms: Optional[int] = Field(None, ge=0)
    
    # Location filters
    center_latitude: Optional[float] = Field(None, ge=-90, le=90)
    center_longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_km: Optional[float] = Field(None, gt=0, le=100)  # Max 100km radius
    areas: List[str] = []  # Specific areas/postcodes
    
    # Lifestyle filters
    proximity_filters: List[ProximityFilter] = []
    amenity_filters: List[AmenityFilter] = []
    environmental_filters: Optional[EnvironmentalFilter] = None
    commute_filters: List[CommuteFilter] = []
    
    # Property features
    must_have_garden: Optional[bool] = None
    must_have_parking: Optional[bool] = None
    min_floor_area_sqft: Optional[int] = Field(None, gt=0)
    
    # Search options
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    sort_by: SortOption = SortOption.RELEVANCE
    
    @model_validator(mode='after')
    def validate_price_range(self):
        if (self.max_price is not None and self.min_price is not None and 
            self.max_price <= self.min_price):
            raise ValueError('max_price must be greater than min_price')
        return self
    
    @model_validator(mode='after')
    def validate_bedroom_range(self):
        if (self.max_bedrooms is not None and self.min_bedrooms is not None and 
            self.max_bedrooms < self.min_bedrooms):
            raise ValueError('max_bedrooms must be greater than or equal to min_bedrooms')
        return self
    
    @model_validator(mode='after')
    def validate_location_criteria(self):
        # Check if both coordinate-based and area-based location filters are provided
        has_coordinates = self.center_latitude is not None and self.center_longitude is not None
        
        if has_coordinates and not self.radius_km:
            raise ValueError('radius_km is required when center coordinates are provided')
        
        if self.radius_km and not has_coordinates:
            raise ValueError('center_latitude and center_longitude are required when radius_km is provided')
        
        return self
    
    @model_validator(mode='after')
    def validate_filter_conflicts(self):
        """Detect and report conflicts between different filter combinations"""
        conflicts = []
        
        # Check for conflicting amenity filters
        amenity_types_required = set()
        amenity_types_avoided = set()
        
        for filter_item in self.amenity_filters:
            if filter_item.required and filter_item.max_distance:
                amenity_types_required.add(filter_item.amenity_type)
            elif filter_item.min_distance and not filter_item.max_distance:
                amenity_types_avoided.add(filter_item.amenity_type)
        
        conflicting_amenities = amenity_types_required.intersection(amenity_types_avoided)
        if conflicting_amenities:
            conflicts.append(f"Conflicting amenity filters: {', '.join(conflicting_amenities)} are both required and avoided")
        
        # Check for conflicting environmental filters
        if self.environmental_filters and self.environmental_filters.avoidance_filters:
            avoidance = self.environmental_filters.avoidance_filters
            if (self.environmental_filters.min_green_space_proximity and 
                avoidance.noise_sources and 
                NoiseSource.MAJOR_ROAD in avoidance.noise_sources):
                # This might not be a true conflict, but worth noting
                pass
        
        # Check for unrealistic commute + location combinations
        if self.commute_filters and self.radius_km:
            for commute in self.commute_filters:
                if commute.max_commute_minutes < 10 and self.radius_km > 20:
                    conflicts.append(f"Short commute time ({commute.max_commute_minutes} min) with large search radius ({self.radius_km} km) may be unrealistic")
        
        if conflicts:
            raise ValueError(f"Filter conflicts detected: {'; '.join(conflicts)}")
        
        return self


class MatchedFilter(BaseModel):
    """Details about which filter criteria a property matched"""
    filter_type: str  # "amenity", "commute", "environmental", etc.
    filter_name: str
    match_value: Optional[Union[float, str, bool]] = None
    match_details: Optional[Dict[str, Any]] = None


class SearchResultProperty(Property):
    match_score: float = Field(..., ge=0, le=1)
    distance_km: Optional[float] = None
    matched_filters: List[MatchedFilter] = []  # Detailed filter matches
    amenity_distances: Dict[str, float] = {}  # Distance to each amenity type
    commute_times: Dict[str, int] = {}  # Commute times to specified destinations
    environmental_scores: Dict[str, Union[int, float]] = {}  # Environmental quality scores


class SearchSummary(BaseModel):
    """Summary statistics about the search results"""
    total_properties_found: int
    properties_returned: int
    avg_price: Optional[float] = None
    price_range: Optional[Dict[str, int]] = None  # {"min": 100000, "max": 500000}
    avg_match_score: Optional[float] = None
    common_areas: List[str] = []  # Most common areas in results


class FilterValidationError(BaseModel):
    """Details about filter validation errors or conflicts"""
    field: str
    message: str
    suggested_fix: Optional[str] = None


class SearchResult(BaseModel):
    properties: List[SearchResultProperty]
    total_count: int
    search_time_ms: int
    filters_applied: SearchCriteria
    summary: SearchSummary
    validation_warnings: List[FilterValidationError] = []
    
    class Config:
        json_encoders = {
            # Add any custom encoders if needed
        }


class PropertyDetailsResponse(BaseModel):
    """Enhanced response model for individual property details"""
    property: Property
    nearby_amenities: Dict[AmenityType, List[Dict[str, Any]]] = {}
    commute_analysis: Dict[str, Dict[str, Any]] = {}  # Commute times to major areas
    environmental_data: Dict[str, Union[int, float]] = {}
    similar_properties: List[Property] = []
    price_history: List[Dict[str, Any]] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }