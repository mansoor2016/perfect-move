from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from app.models.property import Property
from app.models.search import PropertyDetailsResponse, SearchCriteria
from app.modules.search.service import SearchService
from app.modules.geospatial.service import GeospatialService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_search_service() -> SearchService:
    return SearchService()

def get_geospatial_service() -> GeospatialService:
    from app.modules.geospatial.service import GeospatialService
    return GeospatialService()

@router.get("/", response_model=List[Property])
async def get_properties(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of properties to return"),
    offset: int = Query(0, ge=0, description="Number of properties to skip"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    min_price: Optional[int] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[int] = Query(None, ge=0, description="Maximum price filter"),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Get properties with basic filtering and pagination.
    
    For advanced filtering, use the /search endpoint instead.
    """
    try:
        # Build basic search criteria
        from app.models.property import PropertyType, PropertyStatus
        
        criteria = SearchCriteria(
            limit=limit,
            offset=offset,
            min_price=min_price,
            max_price=max_price,
            property_types=[PropertyType(property_type)] if property_type else [],
            status=[PropertyStatus.FOR_SALE, PropertyStatus.FOR_RENT]
        )
        
        result = await search_service.search_properties(criteria)
        
        # Return just the properties without search metadata
        return [prop for prop in result.properties]
        
    except Exception as e:
        logger.error(f"Failed to get properties: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve properties"
        )

@router.get("/{property_id}", response_model=PropertyDetailsResponse)
async def get_property_details(
    property_id: str,
    include_similar: bool = Query(True, description="Include similar properties"),
    include_amenities: bool = Query(True, description="Include nearby amenities"),
    include_commute: bool = Query(True, description="Include commute analysis"),
    search_service: SearchService = Depends(get_search_service),
    geospatial_service: GeospatialService = Depends(get_geospatial_service)
):
    """
    Get detailed information about a specific property.
    
    Includes:
    - Basic property details
    - Nearby amenities (if requested)
    - Commute analysis to major areas (if requested)
    - Environmental data
    - Similar properties (if requested)
    - Price history
    """
    try:
        # First get the basic property
        # For now, we'll search for it using the search service
        # In a real implementation, this would be a direct database lookup
        
        criteria = SearchCriteria(
            limit=1,
            offset=0
        )
        
        # TODO: Implement proper property lookup by ID
        # This is a placeholder implementation
        
        # For now, return a mock response structure
        from app.models.property import Property, PropertyType, PropertyStatus, Location, PropertyLineage
        from datetime import datetime
        
        # This would be replaced with actual database lookup
        mock_property = Property(
            id=property_id,
            title="Sample Property",
            description="A beautiful property",
            price=350000,
            property_type=PropertyType.FLAT,
            status=PropertyStatus.FOR_SALE,
            bedrooms=2,
            bathrooms=1,
            location=Location(
                latitude=51.5074,
                longitude=-0.1278,
                address="123 Sample Street, London",
                postcode="SW1A 1AA",
                area="Westminster",
                city="London"
            ),
            features=["Modern kitchen", "Double glazing"],
            energy_rating="C",
            council_tax_band="D",
            tenure="Leasehold",
            floor_area_sqft=800,
            garden=False,
            parking=True,
            lineage=PropertyLineage(
                source="rightmove",
                source_id="12345",
                last_updated=datetime.now(),
                reliability_score=0.9
            ),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        response = PropertyDetailsResponse(
            property=mock_property,
            nearby_amenities={},
            commute_analysis={},
            environmental_data={},
            similar_properties=[],
            price_history=[]
        )
        
        # Add nearby amenities if requested
        if include_amenities:
            try:
                amenities = await geospatial_service.get_nearby_amenities(
                    mock_property.location.latitude,
                    mock_property.location.longitude,
                    radius_km=2.0
                )
                response.nearby_amenities = amenities
            except Exception as e:
                logger.warning(f"Failed to get amenities for property {property_id}: {e}")
        
        # Add commute analysis if requested
        if include_commute:
            try:
                # Mock commute data - in real implementation, this would call transport APIs
                response.commute_analysis = {
                    "London Bridge": {
                        "public_transport": {"time_minutes": 25, "changes": 1},
                        "driving": {"time_minutes": 35, "distance_km": 8.5}
                    },
                    "Canary Wharf": {
                        "public_transport": {"time_minutes": 30, "changes": 2},
                        "driving": {"time_minutes": 40, "distance_km": 12.0}
                    }
                }
            except Exception as e:
                logger.warning(f"Failed to get commute analysis for property {property_id}: {e}")
        
        # Add similar properties if requested
        if include_similar:
            try:
                # Find similar properties based on location, price, and type
                similar_criteria = SearchCriteria(
                    center_latitude=mock_property.location.latitude,
                    center_longitude=mock_property.location.longitude,
                    radius_km=2.0,
                    property_types=[mock_property.property_type],
                    min_price=int(mock_property.price * 0.8),
                    max_price=int(mock_property.price * 1.2),
                    limit=5
                )
                
                similar_result = await search_service.search_properties(similar_criteria)
                # Filter out the current property
                response.similar_properties = [
                    prop for prop in similar_result.properties 
                    if prop.id != property_id
                ][:4]  # Limit to 4 similar properties
                
            except Exception as e:
                logger.warning(f"Failed to get similar properties for {property_id}: {e}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get property details for {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve property details"
        )

@router.get("/{property_id}/amenities")
async def get_property_amenities(
    property_id: str,
    radius_km: float = Query(2.0, ge=0.1, le=10.0, description="Search radius in kilometers"),
    amenity_types: Optional[List[str]] = Query(None, description="Filter by amenity types"),
    geospatial_service: GeospatialService = Depends(get_geospatial_service)
):
    """
    Get nearby amenities for a specific property.
    
    Returns amenities within the specified radius, optionally filtered by type.
    """
    try:
        # TODO: Get property coordinates from database
        # For now, using mock coordinates
        latitude, longitude = 51.5074, -0.1278
        
        amenities = await geospatial_service.get_nearby_amenities(
            latitude, longitude, radius_km, amenity_types
        )
        
        return {
            "property_id": property_id,
            "radius_km": radius_km,
            "amenities": amenities
        }
        
    except Exception as e:
        logger.error(f"Failed to get amenities for property {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve property amenities"
        )

@router.get("/{property_id}/commute")
async def get_property_commute_analysis(
    property_id: str,
    destinations: List[str] = Query(..., description="Destination addresses or postcodes"),
    transport_modes: List[str] = Query(["public_transport"], description="Transport modes to analyze"),
    geospatial_service: GeospatialService = Depends(get_geospatial_service)
):
    """
    Get commute analysis from a property to specified destinations.
    
    Calculates travel times using different transport modes.
    """
    try:
        # TODO: Get property coordinates from database
        # For now, using mock coordinates
        latitude, longitude = 51.5074, -0.1278
        
        commute_analysis = {}
        
        for destination in destinations:
            try:
                analysis = await geospatial_service.calculate_commute_times(
                    latitude, longitude, destination, transport_modes
                )
                commute_analysis[destination] = analysis
            except Exception as e:
                logger.warning(f"Failed to calculate commute to {destination}: {e}")
                commute_analysis[destination] = {"error": "Unable to calculate commute"}
        
        return {
            "property_id": property_id,
            "commute_analysis": commute_analysis
        }
        
    except Exception as e:
        logger.error(f"Failed to get commute analysis for property {property_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve commute analysis"
        )