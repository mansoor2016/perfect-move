import json
from datetime import datetime, time
from app.models.search import SearchCriteria, AmenityFilter, AmenityType, CommuteFilter, TransportMode
from app.models.property import PropertyType, PropertyStatus


def test_search_criteria_serialization():
    """Test that SearchCriteria can be serialized to and from JSON"""
    
    # Create a complex SearchCriteria object
    criteria = SearchCriteria(
        min_price=200000,
        max_price=500000,
        property_types=[PropertyType.HOUSE, PropertyType.FLAT],
        status=[PropertyStatus.FOR_SALE],
        min_bedrooms=2,
        max_bedrooms=4,
        center_latitude=51.5074,
        center_longitude=-0.1278,
        radius_km=10.0,
        amenity_filters=[
            AmenityFilter(
                amenity_type=AmenityType.PARK,
                max_distance=1.0,
                required=True
            ),
            AmenityFilter(
                amenity_type=AmenityType.TRAIN_STATION,
                max_distance=0.5,
                required=True
            )
        ],
        commute_filters=[
            CommuteFilter(
                destination_address="London Bridge Station",
                max_commute_minutes=30,
                transport_modes=[TransportMode.PUBLIC_TRANSPORT],
                arrival_time=time(9, 0)
            )
        ]
    )
    
    # Test serialization to JSON
    json_data = criteria.model_dump_json()
    assert isinstance(json_data, str)
    
    # Test deserialization from JSON
    parsed_data = json.loads(json_data)
    reconstructed = SearchCriteria.model_validate(parsed_data)
    
    # Verify key fields are preserved
    assert reconstructed.min_price == 200000
    assert reconstructed.max_price == 500000
    assert len(reconstructed.property_types) == 2
    assert len(reconstructed.amenity_filters) == 2
    assert len(reconstructed.commute_filters) == 1
    assert reconstructed.commute_filters[0].arrival_time == time(9, 0)


def test_amenity_filter_serialization():
    """Test AmenityFilter serialization with time fields"""
    
    amenity_filter = AmenityFilter(
        amenity_type=AmenityType.GYM,
        max_distance=2.5,
        walking_distance=True,
        required=True
    )
    
    # Test serialization
    json_data = amenity_filter.model_dump_json()
    parsed_data = json.loads(json_data)
    
    # Verify structure
    assert parsed_data["amenity_type"] == "gym"
    assert parsed_data["max_distance"] == 2.5
    assert parsed_data["walking_distance"] is True
    assert parsed_data["required"] is True
    
    # Test deserialization
    reconstructed = AmenityFilter.model_validate(parsed_data)
    assert reconstructed.amenity_type == AmenityType.GYM
    assert reconstructed.max_distance == 2.5


if __name__ == "__main__":
    test_search_criteria_serialization()
    test_amenity_filter_serialization()
    print("All serialization tests passed!")