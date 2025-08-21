import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.modules.geospatial.environmental_service import EnvironmentalDataService
from app.modules.geospatial.transport_service import TransportDataService
from app.models.geospatial import Location, EnvironmentalData, TransportLink, CommuteInfo
from app.db.models import EnvironmentalData as EnvironmentalDataDB
import httpx


class TestEnvironmentalDataService:
    """Test suite for EnvironmentalDataService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def environmental_service(self, mock_db):
        """Create EnvironmentalDataService instance"""
        return EnvironmentalDataService(db=mock_db)
    
    @pytest.fixture
    def test_location(self):
        """Test location in London"""
        return Location(
            latitude=51.5074,
            longitude=-0.1278,
            address="London, UK"
        )
    
    @pytest.mark.asyncio
    async def test_get_air_quality_data(self, environmental_service, test_location):
        """Test air quality data fetching"""
        mock_response_data = {
            "HourlyAirQualityIndex": {
                "LocalAuthority": [{
                    "@AirQualityIndex": "3",
                    "@AirQualityBand": "Low",
                    "@IndexSource": "2024-01-15T10:00:00Z"
                }]
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await environmental_service.get_air_quality_data(test_location)
            
            assert result is not None
            assert result['air_quality_index'] == "3"
            assert result['air_quality_band'] == "Low"
            assert result['source'] == 'uk_air_quality_api'
    
    @pytest.mark.asyncio
    async def test_get_air_quality_data_api_error(self, environmental_service, test_location):
        """Test air quality data fetching with API error"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await environmental_service.get_air_quality_data(test_location)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_flood_risk_data(self, environmental_service, test_location):
        """Test flood risk data fetching"""
        mock_response_data = {
            "items": [
                {"floodAreaID": "area1", "description": "River Thames"},
                {"floodAreaID": "area2", "description": "Local drainage"}
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await environmental_service.get_flood_risk_data(test_location)
            
            assert result is not None
            assert result['flood_risk_level'] == 'medium'  # 2 flood areas = medium risk
            assert result['flood_areas_count'] == 2
            assert result['source'] == 'environment_agency'
    
    @pytest.mark.asyncio
    async def test_get_flood_risk_data_no_areas(self, environmental_service, test_location):
        """Test flood risk data with no flood areas"""
        mock_response_data = {"items": []}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await environmental_service.get_flood_risk_data(test_location)
            
            assert result is not None
            assert result['flood_risk_level'] == 'low'
            assert result['flood_areas_count'] == 0
    
    @pytest.mark.asyncio
    async def test_get_crime_statistics(self, environmental_service, test_location):
        """Test crime statistics fetching"""
        mock_response_data = [
            {"category": "theft", "location": {"latitude": "51.5074"}},
            {"category": "burglary", "location": {"latitude": "51.5075"}},
            {"category": "violence", "location": {"latitude": "51.5076"}}
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await environmental_service.get_crime_statistics(test_location)
            
            assert result is not None
            assert result['crime_count'] == 3
            assert result['crime_rate'] == 3.0  # 3 crimes per 1000 residents
            assert result['source'] == 'police_api'
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_environmental_data(self, environmental_service, test_location):
        """Test comprehensive environmental data fetching"""
        # Mock all individual data fetching methods
        environmental_service.get_air_quality_data = AsyncMock(return_value={
            'air_quality_index': 25,
            'source': 'uk_air_quality_api'
        })
        environmental_service.get_flood_risk_data = AsyncMock(return_value={
            'flood_risk_level': 'low',
            'source': 'environment_agency'
        })
        environmental_service.get_crime_statistics = AsyncMock(return_value={
            'crime_rate': 15.5,
            'source': 'police_api'
        })
        
        # Mock database operations
        environmental_service.db.add = Mock()
        environmental_service.db.commit = Mock()
        
        result = await environmental_service.get_comprehensive_environmental_data(test_location)
        
        assert result['location'] == test_location
        assert result['air_quality'] is not None
        assert result['flood_risk'] is not None
        assert result['crime_statistics'] is not None
        assert 'timestamp' in result
    
    def test_get_cached_environmental_data(self, environmental_service, test_location):
        """Test cached environmental data retrieval"""
        # Mock database query result
        mock_env_data = Mock(spec=EnvironmentalDataDB)
        mock_env_data.id = "test-id"
        mock_env_data.area_name = "Test Area"
        mock_env_data.air_quality_index = 30
        mock_env_data.flood_risk = "low"
        mock_env_data.crime_rate = 12.5
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_env_data
        
        environmental_service.db.query.return_value = mock_query
        
        # Mock coordinates query
        mock_coords = Mock()
        mock_coords.lat = 51.5074
        mock_coords.lng = -0.1278
        environmental_service.db.execute.return_value.fetchone.return_value = mock_coords
        
        result = environmental_service.get_cached_environmental_data(test_location)
        
        assert isinstance(result, EnvironmentalData)
        assert result.air_quality_index == 30
        assert result.flood_risk_level == "low"
        assert result.crime_rate == 12.5
    
    def test_get_cached_environmental_data_no_result(self, environmental_service, test_location):
        """Test cached environmental data retrieval with no results"""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None
        
        environmental_service.db.query.return_value = mock_query
        
        result = environmental_service.get_cached_environmental_data(test_location)
        
        assert result is None


class TestTransportDataService:
    """Test suite for TransportDataService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def transport_service(self, mock_db):
        """Create TransportDataService instance"""
        service = TransportDataService(db=mock_db)
        service.tfl_api_key = "test_api_key"  # Set API key for testing
        return service
    
    @pytest.fixture
    def test_location(self):
        """Test location in London"""
        return Location(
            latitude=51.5074,
            longitude=-0.1278,
            address="London, UK"
        )
    
    @pytest.mark.asyncio
    async def test_get_nearby_transport_links(self, transport_service, test_location):
        """Test nearby transport links fetching"""
        mock_response_data = {
            "stopPoints": [{
                "id": "940GZZLUTCR",
                "commonName": "Tottenham Court Road Underground Station",
                "lat": 51.5165,
                "lon": -0.1308,
                "modes": [{"modeName": "tube"}],
                "lines": [{"name": "Central line"}, {"name": "Northern line"}],
                "additionalProperties": [{"key": "Zone", "value": "1"}]
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await transport_service.get_nearby_transport_links(test_location)
            
            assert len(result) == 1
            transport_link = result[0]
            assert isinstance(transport_link, TransportLink)
            assert transport_link.name == "Tottenham Court Road Underground Station"
            assert transport_link.transport_type == "tube"
            assert "Central line" in transport_link.lines
            assert "1" in transport_link.zones
    
    @pytest.mark.asyncio
    async def test_get_nearby_transport_links_no_api_key(self, mock_db, test_location):
        """Test transport links fetching without API key"""
        service = TransportDataService(db=mock_db)
        service.tfl_api_key = None
        
        result = await service.get_nearby_transport_links(test_location)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_journey_planner_data(self, transport_service, test_location):
        """Test journey planner data fetching"""
        destination = Location(latitude=51.5145, longitude=-0.1270, address="British Museum")
        
        mock_response_data = {
            "journeys": [{
                "duration": 15,
                "legs": [{
                    "mode": {"name": "walking"},
                    "duration": 5,
                    "instruction": {"summary": "Walk to station"},
                    "departurePoint": {"commonName": "Start"},
                    "arrivalPoint": {"commonName": "Station"}
                }],
                "fare": {"totalCost": 280}
            }]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await transport_service.get_journey_planner_data(test_location, destination)
            
            assert isinstance(result, CommuteInfo)
            assert result.duration_minutes == 15
            assert result.transport_mode == "public_transport"
            assert result.origin == test_location
            assert result.destination == destination
    
    @pytest.mark.asyncio
    async def test_get_line_status_updates(self, transport_service):
        """Test line status updates fetching"""
        mock_response_data = [{
            "id": "central",
            "name": "Central",
            "lineStatuses": [{
                "statusSeverityDescription": "Good Service",
                "reason": "",
                "disruption": {}
            }]
        }]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await transport_service.get_line_status_updates()
            
            assert "central" in result
            assert result["central"]["name"] == "Central"
            assert result["central"]["status"] == "Good Service"
    
    @pytest.mark.asyncio
    async def test_calculate_transport_score(self, transport_service, test_location):
        """Test transport score calculation"""
        # Mock the get_nearby_transport_links method
        mock_tube_link = TransportLink(
            id="tube1", name="Test Tube", transport_type="tube",
            location=test_location, lines=["Central"], zones=["1"]
        )
        mock_bus_links = [
            TransportLink(id="bus1", name="Bus Stop 1", transport_type="bus", 
                         location=test_location, lines=["24"], zones=[]),
            TransportLink(id="bus2", name="Bus Stop 2", transport_type="bus", 
                         location=test_location, lines=["29"], zones=[])
        ]
        
        # Mock different calls for different radii
        async def mock_get_transport_links(location, radius_meters):
            if radius_meters == 500:
                return [mock_tube_link] + mock_bus_links
            else:  # 1000m
                return [mock_tube_link] + mock_bus_links
        
        transport_service.get_nearby_transport_links = mock_get_transport_links
        
        result = await transport_service.calculate_transport_score(test_location)
        
        assert 'transport_score' in result
        assert result['transport_score'] > 0
        assert 'breakdown' in result
        assert result['breakdown']['tube_stations_500m'] == 1
        assert result['breakdown']['bus_stops_500m'] == 2
    
    def test_map_tfl_mode_to_type(self, transport_service):
        """Test TfL mode mapping"""
        # Test tube mapping
        modes = [{"modeName": "tube"}]
        result = transport_service._map_tfl_mode_to_type(modes)
        assert result == "tube"
        
        # Test bus mapping
        modes = [{"modeName": "bus"}]
        result = transport_service._map_tfl_mode_to_type(modes)
        assert result == "bus"
        
        # Test unknown mode
        modes = [{"modeName": "unknown_mode"}]
        result = transport_service._map_tfl_mode_to_type(modes)
        assert result == "unknown_mode"
        
        # Test empty modes
        result = transport_service._map_tfl_mode_to_type([])
        assert result == "unknown"
    
    def test_extract_lines_from_stop(self, transport_service):
        """Test line extraction from TfL stop data"""
        stop_data = {
            "lines": [
                {"name": "Central line"},
                {"name": "Northern line"}
            ]
        }
        
        result = transport_service._extract_lines_from_stop(stop_data)
        
        assert "Central line" in result
        assert "Northern line" in result
        assert len(result) == 2
    
    def test_extract_zones_from_stop(self, transport_service):
        """Test zone extraction from TfL stop data"""
        stop_data = {
            "additionalProperties": [
                {"key": "Zone", "value": "1"},
                {"key": "Other", "value": "something"}
            ]
        }
        
        result = transport_service._extract_zones_from_stop(stop_data)
        
        assert "1" in result
        assert len(result) == 1


class TestIntegratedGeospatialService:
    """Test integration between environmental and transport services"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def test_location(self):
        return Location(latitude=51.5074, longitude=-0.1278, address="London, UK")
    
    @pytest.mark.asyncio
    async def test_environmental_data_caching_and_freshness(self, mock_db, test_location):
        """Test that environmental data is cached and freshness is monitored"""
        service = EnvironmentalDataService(db=mock_db)
        
        # Mock fresh cached data
        mock_env_data = Mock(spec=EnvironmentalDataDB)
        mock_env_data.id = "test-env-id"
        mock_env_data.measurement_date = datetime.now() - timedelta(hours=1)  # 1 hour old
        mock_env_data.air_quality_index = 25
        mock_env_data.flood_risk = "low"
        mock_env_data.crime_rate = 15.0
        mock_env_data.area_name = "Test Area"  # Fix: provide string value
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_env_data
        
        service.db.query.return_value = mock_query
        
        # Mock coordinates
        mock_coords = Mock()
        mock_coords.lat = test_location.latitude
        mock_coords.lng = test_location.longitude
        service.db.execute.return_value.fetchone.return_value = mock_coords
        
        result = service.get_cached_environmental_data(test_location)
        
        assert result is not None
        assert result.air_quality_index == 25
    
    @pytest.mark.asyncio
    async def test_transport_data_error_handling(self, mock_db, test_location):
        """Test transport service error handling"""
        service = TransportDataService(db=mock_db)
        service.tfl_api_key = "test_key"
        
        with patch('httpx.AsyncClient') as mock_client:
            # Simulate network error
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )
            
            result = await service.get_nearby_transport_links(test_location)
            
            assert result == []