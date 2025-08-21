# Pydantic models for API contracts

from .property import Property, PropertyType, PropertyStatus, Location, PropertyLineage
from .search import (
    # Enums
    AmenityType, DistanceUnit, NoiseSource, PollutionType, TransportMode, SortOption,
    
    # Filter models
    AmenityFilter, ProximityFilter, AvoidanceFilter, EnvironmentalFilter, CommuteFilter,
    SearchCriteria,
    
    # Response models
    MatchedFilter, SearchResultProperty, SearchSummary, FilterValidationError,
    SearchResult, PropertyDetailsResponse
)
from .user import User, SavedSearch, FavoriteProperty, UserPreferences

__all__ = [
    # Property models
    "Property", "PropertyType", "PropertyStatus", "Location", "PropertyLineage",
    
    # Search enums
    "AmenityType", "DistanceUnit", "NoiseSource", "PollutionType", "TransportMode", "SortOption",
    
    # Filter models
    "AmenityFilter", "ProximityFilter", "AvoidanceFilter", "EnvironmentalFilter", 
    "CommuteFilter", "SearchCriteria",
    
    # Response models
    "MatchedFilter", "SearchResultProperty", "SearchSummary", "FilterValidationError",
    "SearchResult", "PropertyDetailsResponse",
    
    # User models
    "User", "SavedSearch", "FavoriteProperty", "UserPreferences"
]