import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from app.modules.geospatial.service import GeospatialService
from app.models.geospatial import Location, Amenity, CommuteInfo, AmenityCategory
from app.db.models import Amenity as AmenityDB, Property as PropertyDB
import httpx


class TestGeospatialService:
    """Test suite for GeospatialService distance calculations and proximity queries"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def geospatial_service(self, mock_db):
        """Create GeospatialService instance with mocked dependencies"""
        return GeospatialService(db=mock_db)
    
    @pytest.fixture
    def london_location(self):
        """Test location in London"""
        return Location(
            latitude=51.5074,
            longitude=-0.1278,
            address="London, UK"
        )
    
    @pytest.fixture
    def manchester_location(self):
        """Test location in Manchester"""
        return Location(
            latitude=53.4808,
            longitude=-2.2426,
            address="Manchester, UK"
        )
    
    @pytest.fixture
    def nearby_location(self):
        """Location close to London for proximity tests"""
        return Location(
            latitude=51.5085,  # ~100m from London location
            longitude=-0.1270,
            address="Near London, UK"
        )
    
    def test_calculate_distance_straight_line(self, geospatial_service, london_location, manchester_location):
        """Test straight-line distance calculation between London and Manchester"""
        distance = geospatial_service.calculate_distance(london_location, manchester_location)
        
        # London to Manchester is approximately 262 km
        assert 260 <= distance <= 265
        assert isinstance(distance, float)
    
    def test_calculate_distance_same_point(self, geospatial_service, london_location):
        """Test distance calculation for the same point"""
        distance = geospatial_service.calculate_distance(london_location, london_location)
        assert distance == 0.0
    
    def test_calculate_distance_nearby_points(self, geospatial_service, london_location, nearby_location):
        """Test distance calculation for nearby points"""
        distance = geospatial_service.calculate_distance(london_location, nearby_location)
        
        # Should be approximately 0.1 km (100m)
        assert 0.05 <= distance <= 0.15
    
    def test_calculate_distance_postgis(self, geospatial_service, london_location, manchester_location):
        """Test PostGIS distance calculation"""
        # Mock the database query result
        mock_result = Mock()
        mock_result.distance = 262000  # 262 km in meters
        geospatial_service.db.execute.return_value.fetchone.return_value = mock_result
        
        distance = geospatial_service.calculate_distance_postgis(london_location, manchester_location)
        
        assert distance == 262.0
        geospatial_service.db.execute.assert_called_once()
    
    def test_calculate_distance_postgis_error_handling(self, geospatial_service, london_location, manchester_location):
        """Test PostGIS distance calculation error handling"""
        # Mock database error
        geospatial_service.db.execute.side_effect = Exception("Database error")
        
        distance = geospatial_service.calculate_distance_postgis(london_location, manchester_location)
        
        assert distance == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_walking_distance_with_api(self, geospatial_service, london_location, nearby_location):
        """Test walking distance calculation with Mapbox API"""
        # Mock Mapbox API response
        mock_response_data = {
            "routes": [{
                "duration": 600,  # 10 minutes
                "distance": 800,  # 800 meters
                "geometry": {"type": "LineString", "coordinates": []},
                "legs": []
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Set API key to enable API call
            geospatial_service.mapbox_api_key = "test_api_key"
            
            result = await geospatial_service.calculate_walking_distance(london_location, nearby_location)
            
            assert isinstance(result, CommuteInfo)
            assert result.duration_minutes == 10
            assert result.distance_km == 0.8
            assert result.transport_mode == "walking"
            assert result.origin == london_location
            assert result.destination == nearby_location
    
    @pytest.mark.asyncio
    async def test_calculate_walking_distance_fallback(self, geospatial_service, london_location, nearby_location):
        """Test walking distance fallback when API is unavailable"""
        # No API key set, should use fallback
        geospatial_service.mapbox_api_key = None
        
        result = await geospatial_service.calculate_walking_distance(london_location, nearby_location)
        
        assert isinstance(result, CommuteInfo)
        assert result.transport_mode == "walking_estimated"
        assert result.distance_km > 0
        assert result.duration_minutes > 0
    
    @pytest.mark.asyncio
    async def test_calculate_walking_distance_api_error(self, geospatial_service, london_location, nearby_location):
        """Test walking distance calculation when API returns error"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            geospatial_service.mapbox_api_key = "test_api_key"
            
            result = await geospatial_service.calculate_walking_distance(london_location, nearby_location)
            
            assert isinstance(result, CommuteInfo)
            assert result.transport_mode == "walking_estimated"
    
    def test_find_nearby_amenities(self, geospatial_service, london_location):
        """Test finding nearby amenities using spatial queries"""
        # Mock database amenities
        mock_amenity = Mock(spec=AmenityDB)
        mock_amenity.id = "test-amenity-1"
        mock_amenity.name = "Test Gym"
        mock_amenity.category = "fitness"
        mock_amenity.address = "123 Test Street"
        mock_amenity.opening_hours = {"monday": "06:00-22:00"}
        mock_amenity.website = "https://testgym.com"
        mock_amenity.phone = "+44123456789"
        
        # Mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_amenity]
        
        geospatial_service.db.query.return_value = mock_query
        
        # Mock coordinates query
        mock_coords = Mock()
        mock_coords.lat = 51.5074
        mock_coords.lng = -0.1278
        geospatial_service.db.execute.return_value.fetchone.return_value = mock_coords
        
        amenities = geospatial_service.find_nearby_amenities(
            location=london_location,
            amenity_category="fitness",
            radius_km=1.0
        )
        
        assert len(amenities) == 1
        assert isinstance(amenities[0], Amenity)
        assert amenities[0].name == "Test Gym"
        assert amenities[0].category == "fitness"
        assert amenities[0].location.latitude == 51.5074
        assert amenities[0].location.longitude == -0.1278
    
    def test_find_nearby_amenities_empty_result(self, geospatial_service, london_location):
        """Test finding nearby amenities with no results"""
        # Mock empty query result
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        
        geospatial_service.db.query.return_value = mock_query
        
        amenities = geospatial_service.find_nearby_amenities(
            location=london_location,
            amenity_category="fitness",
            radius_km=1.0
        )
        
        assert len(amenities) == 0
    
    def test_find_properties_within_radius(self, geospatial_service, london_location):
        """Test finding properties within radius"""
        # Mock property data
        mock_property = Mock(spec=PropertyDB)
        mock_property.id = "test-property-1"
        mock_property.title = "Test Property"
        mock_property.price = 500000
        mock_property.bedrooms = 2
        mock_property.property_type = "flat"
        mock_property.address = "123 Test Avenue"
        
        # Mock query result with distance
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(mock_property, 500.0)]  # 500m distance
        
        geospatial_service.db.query.return_value = mock_query
        
        # Mock coordinates query
        mock_coords = Mock()
        mock_coords.lat = 51.5074
        mock_coords.lng = -0.1278
        geospatial_service.db.execute.return_value.fetchone.return_value = mock_coords
        
        properties = geospatial_service.find_properties_within_radius(
            location=london_location,
            radius_km=1.0
        )
        
        assert len(properties) == 1
        property_data = properties[0]
        assert property_data['title'] == "Test Property"
        assert property_data['price'] == 500000
        assert property_data['distance_km'] == 0.5
        assert property_data['location']['latitude'] == 51.5074
    
    @pytest.mark.asyncio
    async def test_get_commute_isochrone(self, geospatial_service, london_location):
        """Test commute isochrone calculation"""
        # Mock Mapbox Isochrone API response
        mock_response_data = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"contour": 10},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-0.13, 51.50], [-0.12, 51.51], [-0.13, 51.50]]]
                }
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            geospatial_service.mapbox_api_key = "test_api_key"
            
            result = await geospatial_service.get_commute_isochrone(
                location=london_location,
                max_minutes=10,
                transport_mode="walking"
            )
            
            assert result is not None
            assert result['type'] == 'isochrone'
            assert result['transport_mode'] == 'walking'
            assert result['max_minutes'] == 10
            assert result['center']['latitude'] == london_location.latitude
            assert result['geojson'] == mock_response_data
    
    @pytest.mark.asyncio
    async def test_get_commute_isochrone_no_api_key(self, geospatial_service, london_location):
        """Test isochrone calculation without API key"""
        geospatial_service.mapbox_api_key = None
        
        result = await geospatial_service.get_commute_isochrone(
            location=london_location,
            max_minutes=10
        )
        
        assert result is None
    
    def test_get_amenity_density(self, geospatial_service, london_location):
        """Test amenity density calculation"""
        # Mock query result with category counts
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [
            ("fitness", 5),
            ("transport", 3),
            ("shopping", 8)
        ]
        
        geospatial_service.db.query.return_value = mock_query
        
        density = geospatial_service.get_amenity_density(london_location, radius_km=1.0)
        
        assert density == {
            "fitness": 5,
            "transport": 3,
            "shopping": 8
        }
    
    def test_get_amenity_density_error_handling(self, geospatial_service, london_location):
        """Test amenity density calculation error handling"""
        geospatial_service.db.query.side_effect = Exception("Database error")
        
        density = geospatial_service.get_amenity_density(london_location)
        
        assert density == {}


class TestGeospatialAccuracy:
    """Test suite for geospatial calculation accuracy"""
    
    def test_distance_calculation_accuracy(self):
        """Test accuracy of distance calculations against known distances"""
        # Known distance: London to Paris is approximately 344 km
        london = Location(latitude=51.5074, longitude=-0.1278)
        paris = Location(latitude=48.8566, longitude=2.3522)
        
        service = GeospatialService(db=Mock())
        distance = service.calculate_distance(london, paris)
        
        # Allow 1% tolerance for geodesic calculations
        expected_distance = 344
        tolerance = expected_distance * 0.01
        assert abs(distance - expected_distance) <= tolerance
    
    def test_short_distance_accuracy(self):
        """Test accuracy for short distances"""
        # Two points approximately 1 km apart in London
        point1 = Location(latitude=51.5074, longitude=-0.1278)  # Trafalgar Square
        point2 = Location(latitude=51.5145, longitude=-0.1270)  # British Museum
        
        service = GeospatialService(db=Mock())
        distance = service.calculate_distance(point1, point2)
        
        # Expected distance is approximately 0.8 km
        assert 0.7 <= distance <= 0.9
    
    def test_coordinate_precision(self):
        """Test that coordinate precision is maintained"""
        # Use coordinates with larger difference to ensure measurable distance
        location1 = Location(latitude=51.5074, longitude=-0.1278)
        location2 = Location(latitude=51.5084, longitude=-0.1268)  # ~100m difference
        
        service = GeospatialService(db=Mock())
        distance = service.calculate_distance(location1, location2)
        
        # Distance should be approximately 0.1 km (100m)
        assert 0.05 <= distance <= 0.15
        assert distance > 0