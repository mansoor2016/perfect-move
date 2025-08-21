import pytest
from datetime import datetime, time
from pydantic import ValidationError
from app.models.search import (
    AmenityFilter, AmenityType, DistanceUnit, AvoidanceFilter, NoiseSource, 
    PollutionType, EnvironmentalFilter, CommuteFilter, TransportMode,
    SearchCriteria, SortOption, SearchResult, SearchResultProperty,
    MatchedFilter, SearchSummary, FilterValidationError, PropertyDetailsResponse
)
from app.models.property import PropertyType, PropertyStatus, Property, Location, PropertyLineage


class TestAmenityFilter:
    """Test AmenityFilter validation and logic"""
    
    def test_valid_amenity_filter_max_distance(self):
        """Test valid amenity filter with max distance"""
        filter_data = {
            "amenity_type": AmenityType.PARK,
            "max_distance": 1.5,
            "distance_unit": DistanceUnit.KILOMETERS,
            "required": True
        }
        amenity_filter = AmenityFilter(**filter_data)
        assert amenity_filter.amenity_type == AmenityType.PARK
        assert amenity_filter.max_distance == 1.5
        assert amenity_filter.required is True
    
    def test_valid_amenity_filter_min_distance(self):
        """Test valid amenity filter with min distance (avoidance)"""
        filter_data = {
            "amenity_type": AmenityType.TRAIN_STATION,
            "min_distance": 2.0,
            "required": False
        }
        amenity_filter = AmenityFilter(**filter_data)
        assert amenity_filter.min_distance == 2.0
        assert amenity_filter.required is False
    
    def test_negative_distance_validation(self):
        """Test that negative distances are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            AmenityFilter(
                amenity_type=AmenityType.PARK,
                max_distance=-1.0
            )
        assert "Distance must be non-negative" in str(exc_info.value)
    
    def test_missing_distance_validation(self):
        """Test that at least one distance must be specified"""
        with pytest.raises(ValidationError) as exc_info:
            AmenityFilter(amenity_type=AmenityType.PARK)
        assert "Either max_distance or min_distance must be specified" in str(exc_info.value)
    
    def test_invalid_distance_range(self):
        """Test that min_distance must be less than max_distance"""
        with pytest.raises(ValidationError) as exc_info:
            AmenityFilter(
                amenity_type=AmenityType.PARK,
                min_distance=2.0,
                max_distance=1.0
            )
        assert "min_distance must be less than max_distance" in str(exc_info.value)


class TestAvoidanceFilter:
    """Test AvoidanceFilter validation"""
    
    def test_valid_avoidance_filter(self):
        """Test valid avoidance filter"""
        filter_data = {
            "noise_sources": [NoiseSource.AIRPORT, NoiseSource.MAJOR_ROAD],
            "min_distance_from_noise": 1.0,
            "max_pollution_levels": {
                PollutionType.AIR_QUALITY: 5,
                PollutionType.NOISE: 3
            },
            "avoid_flood_risk_areas": True
        }
        avoidance_filter = AvoidanceFilter(**filter_data)
        assert len(avoidance_filter.noise_sources) == 2
        assert avoidance_filter.max_pollution_levels[PollutionType.AIR_QUALITY] == 5
    
    def test_invalid_pollution_levels(self):
        """Test that pollution levels must be between 1-10"""
        with pytest.raises(ValidationError) as exc_info:
            AvoidanceFilter(
                max_pollution_levels={PollutionType.AIR_QUALITY: 15}
            )
        assert "must be between 1 and 10" in str(exc_info.value)
    
    def test_negative_noise_distance(self):
        """Test that negative noise distance is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            AvoidanceFilter(min_distance_from_noise=-0.5)
        assert "min_distance_from_noise must be non-negative" in str(exc_info.value)


class TestCommuteFilter:
    """Test CommuteFilter validation"""
    
    def test_valid_commute_filter_with_arrival(self):
        """Test valid commute filter with arrival time"""
        filter_data = {
            "destination_address": "London Bridge Station",
            "max_commute_minutes": 45,
            "transport_modes": [TransportMode.PUBLIC_TRANSPORT],
            "arrival_time": time(9, 0)
        }
        commute_filter = CommuteFilter(**filter_data)
        assert commute_filter.arrival_time == time(9, 0)
        assert commute_filter.departure_time is None
    
    def test_valid_commute_filter_with_departure(self):
        """Test valid commute filter with departure time"""
        filter_data = {
            "destination_address": "Canary Wharf",
            "max_commute_minutes": 30,
            "transport_modes": [TransportMode.CYCLING, TransportMode.PUBLIC_TRANSPORT],
            "departure_time": time(8, 30)
        }
        commute_filter = CommuteFilter(**filter_data)
        assert commute_filter.departure_time == time(8, 30)
        assert commute_filter.arrival_time is None
    
    def test_both_arrival_and_departure_rejected(self):
        """Test that both arrival and departure times cannot be specified"""
        with pytest.raises(ValidationError) as exc_info:
            CommuteFilter(
                destination_address="Test Address",
                max_commute_minutes=30,
                arrival_time=time(9, 0),
                departure_time=time(8, 0)
            )
        assert "Cannot specify both arrival_time and departure_time" in str(exc_info.value)
    
    def test_empty_transport_modes_rejected(self):
        """Test that empty transport modes list is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CommuteFilter(
                destination_address="Test Address",
                max_commute_minutes=30,
                transport_modes=[]
            )
        assert "At least one transport mode must be specified" in str(exc_info.value)
    
    def test_invalid_commute_time_bounds(self):
        """Test commute time validation bounds"""
        # Test zero commute time
        with pytest.raises(ValidationError):
            CommuteFilter(
                destination_address="Test Address",
                max_commute_minutes=0
            )
        
        # Test excessive commute time
        with pytest.raises(ValidationError):
            CommuteFilter(
                destination_address="Test Address",
                max_commute_minutes=400  # Over 5 hours
            )


class TestSearchCriteria:
    """Test SearchCriteria validation and conflict detection"""
    
    def test_valid_basic_search_criteria(self):
        """Test valid basic search criteria"""
        criteria_data = {
            "min_price": 100000,
            "max_price": 500000,
            "property_types": [PropertyType.HOUSE, PropertyType.FLAT],
            "min_bedrooms": 2,
            "max_bedrooms": 4,
            "center_latitude": 51.5074,
            "center_longitude": -0.1278,
            "radius_km": 10.0
        }
        criteria = SearchCriteria(**criteria_data)
        assert criteria.min_price == 100000
        assert criteria.max_price == 500000
        assert len(criteria.property_types) == 2
    
    def test_price_range_validation(self):
        """Test that max_price must be greater than min_price"""
        with pytest.raises(ValidationError) as exc_info:
            SearchCriteria(
                min_price=500000,
                max_price=400000
            )
        assert "max_price must be greater than min_price" in str(exc_info.value)
    
    def test_bedroom_range_validation(self):
        """Test bedroom range validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchCriteria(
                min_bedrooms=4,
                max_bedrooms=2
            )
        assert "max_bedrooms must be greater than or equal to min_bedrooms" in str(exc_info.value)
    
    def test_location_criteria_validation(self):
        """Test location criteria validation"""
        # Test missing radius when coordinates provided
        with pytest.raises(ValidationError) as exc_info:
            SearchCriteria(
                center_latitude=51.5074,
                center_longitude=-0.1278
            )
        assert "radius_km is required when center coordinates are provided" in str(exc_info.value)
        
        # Test missing coordinates when radius provided
        with pytest.raises(ValidationError) as exc_info:
            SearchCriteria(radius_km=10.0)
        assert "center_latitude and center_longitude are required when radius_km is provided" in str(exc_info.value)
    
    def test_conflicting_amenity_filters(self):
        """Test detection of conflicting amenity filters"""
        conflicting_filters = [
            AmenityFilter(
                amenity_type=AmenityType.PARK,
                max_distance=1.0,
                required=True
            ),
            AmenityFilter(
                amenity_type=AmenityType.PARK,
                min_distance=2.0,
                required=False
            )
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            SearchCriteria(amenity_filters=conflicting_filters)
        assert "Conflicting amenity filters" in str(exc_info.value)
    
    def test_unrealistic_commute_radius_combination(self):
        """Test detection of unrealistic commute + radius combinations"""
        commute_filter = CommuteFilter(
            destination_address="Test Address",
            max_commute_minutes=5  # Very short commute
        )
        
        with pytest.raises(ValidationError) as exc_info:
            SearchCriteria(
                center_latitude=51.5074,
                center_longitude=-0.1278,
                radius_km=50,  # Very large radius
                commute_filters=[commute_filter]
            )
        assert "may be unrealistic" in str(exc_info.value)


class TestSearchResultModels:
    """Test search result response models"""
    
    def create_sample_property(self) -> Property:
        """Helper to create a sample property for testing"""
        return Property(
            id="prop_123",
            title="Test Property",
            price=350000,
            property_type=PropertyType.HOUSE,
            status=PropertyStatus.FOR_SALE,
            location=Location(
                latitude=51.5074,
                longitude=-0.1278,
                address="123 Test Street, London"
            ),
            lineage=PropertyLineage(
                source="test_source",
                source_id="test_123",
                last_updated=datetime.now(),
                reliability_score=0.9
            ),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def test_search_result_property_creation(self):
        """Test SearchResultProperty model creation"""
        base_property = self.create_sample_property()
        
        result_property = SearchResultProperty(
            **base_property.model_dump(),
            match_score=0.85,
            distance_km=2.5,
            matched_filters=[
                MatchedFilter(
                    filter_type="amenity",
                    filter_name="park_proximity",
                    match_value=0.8
                )
            ],
            amenity_distances={"park": 0.8, "train_station": 1.2},
            commute_times={"central_london": 25}
        )
        
        assert result_property.match_score == 0.85
        assert result_property.distance_km == 2.5
        assert len(result_property.matched_filters) == 1
        assert result_property.amenity_distances["park"] == 0.8
    
    def test_search_result_creation(self):
        """Test SearchResult model creation"""
        base_property = self.create_sample_property()
        result_property = SearchResultProperty(**base_property.model_dump(), match_score=0.85)
        
        search_criteria = SearchCriteria(
            min_price=200000,
            max_price=400000,
            center_latitude=51.5074,
            center_longitude=-0.1278,
            radius_km=5.0
        )
        
        search_summary = SearchSummary(
            total_properties_found=150,
            properties_returned=50,
            avg_price=325000.0,
            avg_match_score=0.78
        )
        
        search_result = SearchResult(
            properties=[result_property],
            total_count=150,
            search_time_ms=245,
            filters_applied=search_criteria,
            summary=search_summary
        )
        
        assert len(search_result.properties) == 1
        assert search_result.total_count == 150
        assert search_result.summary.avg_price == 325000.0
    
    def test_property_details_response(self):
        """Test PropertyDetailsResponse model"""
        base_property = self.create_sample_property()
        
        details_response = PropertyDetailsResponse(
            property=base_property,
            nearby_amenities={
                AmenityType.PARK: [
                    {"name": "Hyde Park", "distance_km": 0.5, "rating": 4.5}
                ]
            },
            commute_analysis={
                "central_london": {
                    "public_transport": {"time_minutes": 25, "cost": 4.50},
                    "driving": {"time_minutes": 35, "cost": 8.00}
                }
            },
            environmental_data={
                "air_quality_index": 6,
                "noise_level": 4,
                "green_space_proximity": 0.3
            }
        )
        
        assert details_response.property.id == "prop_123"
        assert AmenityType.PARK in details_response.nearby_amenities
        assert "central_london" in details_response.commute_analysis
        assert details_response.environmental_data["air_quality_index"] == 6


if __name__ == "__main__":
    pytest.main([__file__])