"""
Tests for the ingestion module
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.ingestion.service import IngestionService
from app.modules.ingestion.adapters.base import RawPropertyData
from app.modules.ingestion.adapters.rightmove import RightmoveAdapter
from app.modules.ingestion.adapters.zoopla import ZooplaAdapter
from app.modules.ingestion.deduplication import PropertyDeduplicator, PropertyMatch


class TestRightmoveAdapter:
    """Test Rightmove adapter functionality"""
    
    @pytest.fixture
    def adapter(self):
        return RightmoveAdapter()
    
    @pytest.mark.asyncio
    async def test_search_properties(self, adapter):
        """Test property search functionality"""
        properties = await adapter.search_properties("London", radius_km=5, max_results=10)
        
        assert isinstance(properties, list)
        assert len(properties) <= 10
        
        if properties:
            prop = properties[0]
            assert isinstance(prop, RawPropertyData)
            assert prop.source == "rightmove"
            assert prop.source_id is not None
            assert prop.raw_data is not None
    
    def test_normalize_property_data(self, adapter):
        """Test property data normalization"""
        raw_data = RawPropertyData(
            source="rightmove",
            source_id="test_123",
            raw_data={
                "displayAddress": "123 Test Street, London",
                "price": "£450000",
                "bedrooms": 3,
                "bathrooms": 2,
                "propertyType": "House",
                "summary": "Beautiful house in London",
                "location": {
                    "latitude": 51.5074,
                    "longitude": -0.1278,
                    "displayName": "London"
                },
                "propertyUrl": "https://rightmove.co.uk/property/123",
                "propertyImages": ["image1.jpg", "image2.jpg"],
                "keyFeatures": ["Garden", "Parking"]
            },
            fetched_at=datetime.now()
        )
        
        normalized = adapter.normalize_property_data(raw_data)
        
        assert normalized['title'] == "123 Test Street, London"
        assert normalized['price'] == 450000.0
        assert normalized['bedrooms'] == 3
        assert normalized['bathrooms'] == 2
        assert normalized['property_type'] == "house"
        assert normalized['latitude'] == 51.5074
        assert normalized['longitude'] == -0.1278
        assert normalized['garden'] is True
        assert normalized['parking'] is True
        assert normalized['source'] == "rightmove"
        assert normalized['source_id'] == "test_123"
    
    def test_extract_price(self, adapter):
        """Test price extraction from various formats"""
        assert adapter._extract_price("£450000") == 450000.0
        assert adapter._extract_price("£450,000") == 450000.0
        assert adapter._extract_price("POA") is None
        assert adapter._extract_price("") is None
        assert adapter._extract_price("£1,250,000") == 1250000.0
    
    def test_normalize_property_type(self, adapter):
        """Test property type normalization"""
        assert adapter._normalize_property_type("Flat") == "flat"
        assert adapter._normalize_property_type("Apartment") == "flat"
        assert adapter._normalize_property_type("Terraced House") == "house"
        assert adapter._normalize_property_type("Studio") == "studio"
        assert adapter._normalize_property_type("") == "unknown"


class TestZooplaAdapter:
    """Test Zoopla adapter functionality"""
    
    @pytest.fixture
    def adapter(self):
        return ZooplaAdapter()
    
    @pytest.mark.asyncio
    async def test_search_properties(self, adapter):
        """Test property search functionality"""
        properties = await adapter.search_properties("London", radius_km=5, max_results=10)
        
        assert isinstance(properties, list)
        assert len(properties) <= 10
        
        if properties:
            prop = properties[0]
            assert isinstance(prop, RawPropertyData)
            assert prop.source == "zoopla"
            assert prop.source_id is not None
    
    def test_normalize_property_data(self, adapter):
        """Test property data normalization"""
        raw_data = RawPropertyData(
            source="zoopla",
            source_id="zoopla_456",
            raw_data={
                "listing_id": "zoopla_456",
                "displayable_address": "456 Sample Road, London",
                "price": 380000,
                "num_bedrooms": 2,
                "num_bathrooms": 1,
                "property_type": "Flat",
                "description": "Modern flat in London",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "outcode": "SW1",
                "county": "London",
                "details_url": "https://zoopla.co.uk/property/456",
                "image_urls": ["image1.jpg"],
                "features": ["Balcony"],
                "furnished_state": "Furnished"
            },
            fetched_at=datetime.now()
        )
        
        normalized = adapter.normalize_property_data(raw_data)
        
        assert normalized['title'] == "456 Sample Road, London"
        assert normalized['price'] == 380000.0
        assert normalized['bedrooms'] == 2
        assert normalized['bathrooms'] == 1
        assert normalized['property_type'] == "flat"
        assert normalized['furnished'] == "furnished"
        assert normalized['source'] == "zoopla"


class TestPropertyDeduplicator:
    """Test property deduplication functionality"""
    
    @pytest.fixture
    def deduplicator(self):
        return PropertyDeduplicator()
    
    @pytest.fixture
    def sample_properties(self):
        return [
            {
                'source_id': 'rightmove_1',
                'source': 'rightmove',
                'address': '123 Test Street, London SW1 1AA',
                'price': 450000,
                'bedrooms': 3,
                'bathrooms': 2,
                'property_type': 'house',
                'latitude': 51.5074,
                'longitude': -0.1278,
                'reliability_score': 0.9
            },
            {
                'source_id': 'zoopla_1',
                'source': 'zoopla',
                'address': '123 Test St, London SW1 1AA',
                'price': 455000,
                'bedrooms': 3,
                'bathrooms': 2,
                'property_type': 'house',
                'latitude': 51.5075,
                'longitude': -0.1279,
                'reliability_score': 0.8
            },
            {
                'source_id': 'rightmove_2',
                'source': 'rightmove',
                'address': '456 Different Road, London SW2 2BB',
                'price': 300000,
                'bedrooms': 2,
                'bathrooms': 1,
                'property_type': 'flat',
                'latitude': 51.5100,
                'longitude': -0.1300,
                'reliability_score': 0.85
            }
        ]
    
    def test_find_duplicates(self, deduplicator, sample_properties):
        """Test duplicate detection"""
        matches = deduplicator.find_duplicates(sample_properties)
        
        # Should find one match between the first two properties
        assert len(matches) >= 1
        
        # Check that the match is between the similar properties
        match = matches[0]
        assert isinstance(match, PropertyMatch)
        assert match.similarity_score > 0.7
        assert match.confidence in ['high', 'medium']
    
    def test_deduplicate_properties(self, deduplicator, sample_properties):
        """Test property deduplication"""
        deduplicated = deduplicator.deduplicate_properties(sample_properties)
        
        # Should have fewer properties after deduplication
        assert len(deduplicated) <= len(sample_properties)
        
        # Should keep the unique property
        unique_addresses = [prop['address'] for prop in deduplicated]
        assert '456 Different Road, London SW2 2BB' in unique_addresses
    
    def test_address_similarity(self, deduplicator):
        """Test address similarity calculation"""
        addr1 = "123 Test Street, London SW1 1AA"
        addr2 = "123 Test St, London SW1 1AA"
        addr3 = "456 Different Road, London SW2 2BB"
        
        similarity1 = deduplicator._calculate_address_similarity(addr1, addr2)
        similarity2 = deduplicator._calculate_address_similarity(addr1, addr3)
        
        assert similarity1 > 0.8  # Should be very similar
        assert similarity2 < 0.6  # Should be different
    
    def test_coordinate_similarity(self, deduplicator):
        """Test coordinate-based similarity"""
        prop1 = {'latitude': 51.5074, 'longitude': -0.1278}
        prop2 = {'latitude': 51.5075, 'longitude': -0.1279}  # Very close
        prop3 = {'latitude': 51.5100, 'longitude': -0.1300}  # Further away
        
        similarity1 = deduplicator._calculate_coordinate_similarity(prop1, prop2)
        similarity2 = deduplicator._calculate_coordinate_similarity(prop1, prop3)
        
        assert similarity1 > similarity2
        assert similarity1 > 0.8  # Should be very similar for close coordinates


class TestIngestionService:
    """Test ingestion service functionality"""
    
    @pytest.fixture
    def service(self):
        return IngestionService()
    
    @pytest.mark.asyncio
    async def test_sync_properties_for_location(self, service):
        """Test syncing properties from multiple sources"""
        properties = await service.sync_properties_for_location("London", radius_km=5, max_results=10)
        
        assert isinstance(properties, list)
        # Should have properties from both sources (mock data)
        if properties:
            sources = {prop.get('source') for prop in properties}
            # At least one source should be present
            assert len(sources) >= 1
    
    @pytest.mark.asyncio
    async def test_sync_rightmove_properties(self, service):
        """Test syncing from Rightmove only"""
        properties = await service.sync_rightmove_properties("London", max_results=5)
        
        assert isinstance(properties, list)
        if properties:
            assert all(prop.get('source') == 'rightmove' for prop in properties)
    
    @pytest.mark.asyncio
    async def test_sync_zoopla_properties(self, service):
        """Test syncing from Zoopla only"""
        properties = await service.sync_zoopla_properties("London", max_results=5)
        
        assert isinstance(properties, list)
        if properties:
            assert all(prop.get('source') == 'zoopla' for prop in properties)
    
    def test_deduplicate_properties(self, service):
        """Test deduplication through service"""
        sample_properties = [
            {
                'source_id': 'test_1',
                'source': 'rightmove',
                'address': '123 Test Street',
                'price': 450000,
                'latitude': 51.5074,
                'longitude': -0.1278,
                'reliability_score': 0.9
            },
            {
                'source_id': 'test_2',
                'source': 'zoopla',
                'address': '123 Test St',
                'price': 455000,
                'latitude': 51.5075,
                'longitude': -0.1279,
                'reliability_score': 0.8
            }
        ]
        
        deduplicated = service.deduplicate_properties(sample_properties)
        assert isinstance(deduplicated, list)
        assert len(deduplicated) <= len(sample_properties)


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        from app.modules.ingestion.adapters.base import RateLimiter
        
        # Allow 2 calls per 1 second
        limiter = RateLimiter(max_calls=2, time_window=1)
        
        # First two calls should be immediate
        await limiter.acquire()
        await limiter.acquire()
        
        # Third call should be delayed (but we won't wait in test)
        # Just verify the limiter tracks calls correctly
        assert len(limiter.calls) == 2


@pytest.mark.asyncio
async def test_integration_full_pipeline():
    """Integration test for the full ingestion pipeline"""
    service = IngestionService()
    
    # Test the full pipeline
    properties = await service.sync_properties_for_location("London", radius_km=2, max_results=5)
    
    assert isinstance(properties, list)
    
    # Verify properties have required fields
    for prop in properties:
        assert 'source' in prop
        assert 'source_id' in prop
        assert 'price' in prop or prop['price'] is None
        assert 'address' in prop
        assert 'reliability_score' in prop