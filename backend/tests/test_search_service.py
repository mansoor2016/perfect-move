import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.search.service import SearchService
from app.modules.search.query_builder import SearchQueryBuilder
from app.modules.search.ranking_engine import RankingEngine
from app.models.search import (
    SearchCriteria, SearchResult, SearchResultProperty, SortOption,
    AmenityFilter, AmenityType, DistanceUnit, EnvironmentalFilter
)
from app.models.property import Property, PropertyType, PropertyStatus, Location, PropertyLineage


@pytest.fixture
def search_service():
    """Create SearchService instance for testing"""
    return SearchService()


@pytest.fixture
def sample_search_criteria():
    """Create sample search criteria"""
    return SearchCriteria(
        min_price=300000,
        max_price=600000,
        property_types=[PropertyType.FLAT, PropertyType.HOUSE],
        min_bedrooms=2,
        center_latitude=51.5074,
        center_longitude=-0.1278,
        radius_km=5.0,
        must_have_parking=True,
        limit=20
    )


@pytest.fixture
def sample_properties():
    """Create sample properties for testing"""
    base_time = datetime.now(timezone.utc)
    
    properties = []
    
    # Property 1: Matches criteria well
    prop1 = Property(
        id="test-1",
        title="Modern 2-bed flat with parking",
        description="Beautiful apartment in central location",
        price=450000,
        property_type=PropertyType.FLAT,
        status=PropertyStatus.FOR_SALE,
        bedrooms=2,
        bathrooms=1,
        location=Location(
            latitude=51.5074,
            longitude=-0.1278,
            address="123 Test Street, London",
            postcode="W1A 1AA",
            area="Westminster",
            city="London"
        ),
        features=["parking", "balcony"],
        energy_rating="B",
        parking=True,
        lineage=PropertyLineage(
            source="rightmove",
            source_id="rm-1",
            last_updated=base_time,
            reliability_score=0.95
        ),
        created_at=base_time,
        updated_at=base_time
    )
    
    # Property 2: Higher price, different location
    prop2 = Property(
        id="test-2",
        title="Luxury 3-bed house",
        description="Spacious family home with garden",
        price=750000,
        property_type=PropertyType.HOUSE,
        status=PropertyStatus.FOR_SALE,
        bedrooms=3,
        bathrooms=2,
        location=Location(
            latitude=51.4994,
            longitude=-0.1746,
            address="45 Luxury Road, London",
            postcode="SW6 2BB",
            area="Fulham",
            city="London"
        ),
        features=["garden", "parking", "garage"],
        energy_rating="A",
        garden=True,
        parking=True,
        lineage=PropertyLineage(
            source="zoopla",
            source_id="zp-2",
            last_updated=base_time,
            reliability_score=0.92
        ),
        created_at=base_time,
        updated_at=base_time
    )
    
    return [prop1, prop2]


class TestSearchQueryBuilder:
    """Test SearchQueryBuilder functionality"""
    
    def test_build_basic_query(self):
        """Test building basic query with price and property type filters"""
        builder = SearchQueryBuilder()
        
        criteria = SearchCriteria(
            min_price=200000,
            max_price=500000,
            property_types=[PropertyType.FLAT],
            min_bedrooms=1
        )
        
        query = asyncio.run(builder.build_query(criteria))
        
        # Check structure
        assert "query" in query
        assert "bool" in query["query"]
        
        # Check filters
        filters = query["query"]["bool"]["filter"]
        
        # Price filter
        price_filter = next((f for f in filters if "range" in f and "price" in f["range"]), None)
        assert price_filter is not None
        assert price_filter["range"]["price"]["gte"] == 200000
        assert price_filter["range"]["price"]["lte"] == 500000
        
        # Property type filter
        type_filter = next((f for f in filters if "terms" in f and "property_type" in f["terms"]), None)
        assert type_filter is not None
        assert "flat" in type_filter["terms"]["property_type"]
        
        # Bedroom filter
        bedroom_filter = next((f for f in filters if "range" in f and "bedrooms" in f["range"]), None)
        assert bedroom_filter is not None
        assert bedroom_filter["range"]["bedrooms"]["gte"] == 1
    
    def test_build_location_query(self):
        """Test building query with location filters"""
        builder = SearchQueryBuilder()
        
        criteria = SearchCriteria(
            center_latitude=51.5074,
            center_longitude=-0.1278,
            radius_km=2.0,
            areas=["Westminster", "W1"]
        )
        
        query = asyncio.run(builder.build_query(criteria))
        
        filters = query["query"]["bool"]["filter"]
        
        # Geo distance filter
        geo_filter = next((f for f in filters if "geo_distance" in f), None)
        assert geo_filter is not None
        assert geo_filter["geo_distance"]["distance"] == "2.0km"
        assert geo_filter["geo_distance"]["location.coordinates"]["lat"] == 51.5074
        
        # Area filters should be in should clauses
        should_clauses = query["query"]["bool"].get("should", [])
        assert len(should_clauses) > 0
    
    def test_build_lifestyle_query(self):
        """Test building query with lifestyle filters"""
        builder = SearchQueryBuilder()
        
        amenity_filter = AmenityFilter(
            amenity_type=AmenityType.TRAIN_STATION,
            max_distance=0.5,
            distance_unit=DistanceUnit.KILOMETERS,
            required=True
        )
        
        env_filter = EnvironmentalFilter(
            avoid_flood_risk=True,
            min_green_space_proximity=1.0
        )
        
        criteria = SearchCriteria(
            amenity_filters=[amenity_filter],
            environmental_filters=env_filter
        )
        
        query = asyncio.run(builder.build_query(criteria))
        
        # Should have boost clauses for amenities and environmental factors
        should_clauses = query["query"]["bool"].get("should", [])
        assert len(should_clauses) > 0
        
        # Check for train station related boosts
        train_boost = any(
            "multi_match" in clause and "train" in str(clause).lower()
            for clause in should_clauses
        )
        assert train_boost
    
    def test_build_sorting_query(self):
        """Test different sorting options"""
        builder = SearchQueryBuilder()
        
        # Test price sorting
        criteria = SearchCriteria(sort_by=SortOption.PRICE_ASC)
        query = asyncio.run(builder.build_query(criteria))
        assert query["sort"] == [{"price": {"order": "asc"}}]
        
        # Test distance sorting
        criteria = SearchCriteria(
            sort_by=SortOption.DISTANCE,
            center_latitude=51.5074,
            center_longitude=-0.1278,
            radius_km=5.0
        )
        query = asyncio.run(builder.build_query(criteria))
        assert "_geo_distance" in query["sort"][0]


class TestRankingEngine:
    """Test RankingEngine functionality"""
    
    def test_calculate_price_score(self, sample_properties):
        """Test price score calculation"""
        engine = RankingEngine()
        
        criteria = SearchCriteria(min_price=300000, max_price=600000)
        
        # Property 1: £450k (middle of range) should score well
        prop1 = sample_properties[0]  # £450k
        score1 = engine._calculate_price_score(prop1, criteria, sample_properties)
        
        # Property 2: £750k (above range) should score poorly
        prop2 = sample_properties[1]  # £750k
        score2 = engine._calculate_price_score(prop2, criteria, sample_properties)
        
        assert 0 <= score1 <= 1
        assert 0 <= score2 <= 1
        assert score1 > score2  # Property in range should score better
    
    def test_calculate_proximity_score(self, sample_properties):
        """Test proximity score calculation"""
        engine = RankingEngine()
        
        criteria = SearchCriteria(
            center_latitude=51.5074,
            center_longitude=-0.1278,
            radius_km=5.0
        )
        
        # Create SearchResultProperty objects with distance
        from app.models.search import SearchResultProperty
        
        prop1 = SearchResultProperty(
            **sample_properties[0].model_dump(),
            match_score=0.5,
            distance_km=1.0,  # Close
            matched_filters=[],
            amenity_distances={},
            commute_times={},
            environmental_scores={}
        )
        
        prop2 = SearchResultProperty(
            **sample_properties[1].model_dump(),
            match_score=0.5,
            distance_km=4.0,  # Further
            matched_filters=[],
            amenity_distances={},
            commute_times={},
            environmental_scores={}
        )
        
        score1 = engine._calculate_proximity_score(prop1, criteria)
        score2 = engine._calculate_proximity_score(prop2, criteria)
        
        assert score1 > score2  # Closer property should score better
        assert 0 <= score1 <= 1
        assert 0 <= score2 <= 1
    
    def test_calculate_freshness_score(self, sample_properties):
        """Test freshness score calculation"""
        engine = RankingEngine()
        
        # Fresh property (updated today)
        prop1 = sample_properties[0]
        prop1.updated_at = datetime.now(timezone.utc)
        
        # Old property (updated 6 months ago)
        prop2 = sample_properties[1]
        prop2.updated_at = datetime.now(timezone.utc).replace(month=1)
        
        score1 = engine._calculate_freshness_score(prop1)
        score2 = engine._calculate_freshness_score(prop2)
        
        assert score1 > score2  # Fresh property should score better
        assert 0 <= score1 <= 1
        assert 0 <= score2 <= 1
    
    def test_calculate_quality_score(self, sample_properties):
        """Test quality score calculation"""
        engine = RankingEngine()
        
        # High quality property
        prop1 = sample_properties[0]
        prop1.energy_rating = "A"
        prop1.features = ["parking", "garden", "gym", "concierge"]
        prop1.lineage.reliability_score = 0.95
        
        # Lower quality property
        prop2 = sample_properties[1]
        prop2.energy_rating = "E"
        prop2.features = []
        prop2.lineage.reliability_score = 0.70
        
        score1 = engine._calculate_quality_score(prop1)
        score2 = engine._calculate_quality_score(prop2)
        
        assert score1 > score2  # Higher quality should score better
        assert 0 <= score1 <= 1
        assert 0 <= score2 <= 1
    
    @pytest.mark.asyncio
    async def test_rank_properties(self, sample_properties, sample_search_criteria):
        """Test complete property ranking"""
        engine = RankingEngine()
        
        # Convert to SearchResultProperty objects
        search_props = []
        for prop in sample_properties:
            search_prop = SearchResultProperty(
                **prop.model_dump(),
                match_score=0.5,  # Initial score
                distance_km=2.0,
                matched_filters=[],
                amenity_distances={},
                commute_times={},
                environmental_scores={}
            )
            search_props.append(search_prop)
        
        ranked_props = await engine.rank_properties(search_props, sample_search_criteria)
        
        assert len(ranked_props) == len(search_props)
        
        # Check that scores were updated
        for prop in ranked_props:
            assert 0 <= prop.match_score <= 1
        
        # Properties should be sorted by score (for relevance sort)
        if len(ranked_props) > 1:
            assert ranked_props[0].match_score >= ranked_props[1].match_score


class TestSearchService:
    """Test SearchService functionality"""
    
    @pytest.mark.asyncio
    async def test_search_suggestions(self, search_service):
        """Test search suggestion generation"""
        
        # Test location-based suggestions
        suggestions = await search_service.get_search_suggestions("near park")
        assert len(suggestions) > 0
        assert any("park" in s.lower() for s in suggestions)
        
        # Test property type suggestions
        suggestions = await search_service.get_search_suggestions("flat")
        assert len(suggestions) > 0
        assert any("flat" in s.lower() or "apartment" in s.lower() for s in suggestions)
        
        # Test transport suggestions
        suggestions = await search_service.get_search_suggestions("transport")
        assert len(suggestions) > 0
        assert any("transport" in s.lower() or "station" in s.lower() for s in suggestions)
    
    def test_calculate_distance(self, search_service):
        """Test distance calculation"""
        
        # London coordinates
        lat1, lon1 = 51.5074, -0.1278  # Central London
        lat2, lon2 = 51.4994, -0.1746  # Fulham
        
        distance = search_service._calculate_distance(lat1, lon1, lat2, lon2)
        
        assert distance > 0
        assert distance < 10  # Should be less than 10km
    
    def test_identify_matched_filters(self, search_service, sample_properties):
        """Test filter matching identification"""
        
        criteria = SearchCriteria(
            min_price=300000,
            max_price=600000,
            property_types=[PropertyType.FLAT],
            must_have_parking=True
        )
        
        # Convert property to dict format (as it would come from Elasticsearch)
        prop_data = {
            "id": sample_properties[0].id,
            "price": sample_properties[0].price,
            "property_type": sample_properties[0].property_type.value,
            "bedrooms": sample_properties[0].bedrooms,
            "parking": sample_properties[0].parking,
            "garden": sample_properties[0].garden
        }
        
        matched_filters = search_service._identify_matched_filters(prop_data, criteria)
        
        assert len(matched_filters) > 0
        
        # Should match price and parking filters
        filter_names = [f.filter_name for f in matched_filters]
        assert "min_price" in filter_names
        assert "parking" in filter_names
    
    @patch('app.modules.search.service.elasticsearch_service')
    @pytest.mark.asyncio
    async def test_search_properties_success(self, mock_es_service, search_service, sample_search_criteria):
        """Test successful property search"""
        
        # Mock Elasticsearch response
        mock_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "test-1",
                        "_score": 1.5,
                        "_source": {
                            "id": "test-1",
                            "title": "Test Property 1",
                            "price": 450000,
                            "property_type": "flat",
                            "status": "for_sale",
                            "bedrooms": 2,
                            "bathrooms": 1,
                            "location": {
                                "coordinates": {"lat": 51.5074, "lon": -0.1278},
                                "address": "123 Test St",
                                "area": "Westminster",
                                "city": "London"
                            },
                            "features": ["parking"],
                            "parking": True,
                            "lineage": {
                                "source": "test",
                                "source_id": "test-1",
                                "last_updated": datetime.now(timezone.utc).isoformat(),
                                "reliability_score": 0.9
                            },
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                ]
            }
        }
        
        # Mock the client and its methods
        mock_client = AsyncMock()
        mock_client.search.return_value = mock_response
        mock_client.close = AsyncMock()
        
        mock_es_service._get_client.return_value = mock_client
        
        # Execute search
        result = await search_service.search_properties(sample_search_criteria)
        
        # Verify result
        assert isinstance(result, SearchResult)
        assert result.total_count == 2
        assert len(result.properties) == 1
        assert result.properties[0].id == "test-1"
        assert result.search_time_ms > 0
        
        # Verify client was called correctly
        mock_client.search.assert_called_once()
        mock_client.close.assert_called_once()
    
    @patch('app.modules.search.service.elasticsearch_service')
    @pytest.mark.asyncio
    async def test_search_properties_error_handling(self, mock_es_service, search_service, sample_search_criteria):
        """Test search error handling"""
        
        # Mock client that raises an exception
        mock_client = AsyncMock()
        mock_client.search.side_effect = Exception("Elasticsearch error")
        mock_client.close = AsyncMock()
        
        mock_es_service._get_client.return_value = mock_client
        
        # Execute search
        result = await search_service.search_properties(sample_search_criteria)
        
        # Should return empty result, not raise exception
        assert isinstance(result, SearchResult)
        assert result.total_count == 0
        assert len(result.properties) == 0
        assert result.search_time_ms > 0
    
    @patch('app.modules.search.service.elasticsearch_service')
    @pytest.mark.asyncio
    async def test_get_aggregations(self, mock_es_service, search_service, sample_search_criteria):
        """Test search aggregations"""
        
        mock_response = {
            "aggregations": {
                "property_types": {
                    "buckets": [
                        {"key": "flat", "doc_count": 15},
                        {"key": "house", "doc_count": 8}
                    ]
                },
                "avg_price": {"value": 425000}
            }
        }
        
        mock_client = AsyncMock()
        mock_client.search.return_value = mock_response
        mock_client.close = AsyncMock()
        
        mock_es_service._get_client.return_value = mock_client
        
        # Execute aggregations
        aggs = await search_service.get_aggregations(sample_search_criteria)
        
        # Verify result
        assert "property_types" in aggs
        assert "avg_price" in aggs
        assert aggs["avg_price"]["value"] == 425000


if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v"])