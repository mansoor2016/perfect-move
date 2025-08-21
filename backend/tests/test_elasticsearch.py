import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from app.modules.search.elasticsearch_service import elasticsearch_service, PROPERTIES_INDEX
from app.models.property import Property, PropertyType, PropertyStatus, Location, PropertyLineage
from app.core.elasticsearch import es_client


@pytest_asyncio.fixture(scope="session")
async def setup_elasticsearch():
    """Setup Elasticsearch for testing"""
    # Connect to Elasticsearch
    await es_client.connect()
    
    # Clean up any existing test index
    await elasticsearch_service.delete_properties_index()
    
    # Create fresh index
    success = await elasticsearch_service.create_properties_index()
    assert success, "Failed to create properties index"
    
    yield
    
    # Cleanup after tests
    await elasticsearch_service.delete_properties_index()
    await es_client.disconnect()


@pytest.fixture
def sample_property():
    """Create a sample property for testing"""
    return Property(
        id="test-property-1",
        title="Beautiful 2-bed flat in Central London",
        description="A stunning apartment with modern amenities and great transport links",
        price=500000,
        property_type=PropertyType.FLAT,
        status=PropertyStatus.FOR_SALE,
        bedrooms=2,
        bathrooms=1,
        location=Location(
            latitude=51.5074,
            longitude=-0.1278,
            address="123 Test Street, London",
            postcode="SW1A 1AA",
            area="Westminster",
            city="London"
        ),
        features=["balcony", "parking", "garden"],
        energy_rating="B",
        council_tax_band="D",
        tenure="leasehold",
        floor_area_sqft=800,
        garden=True,
        parking=True,
        lineage=PropertyLineage(
            source="rightmove",
            source_id="rm-123456",
            last_updated=datetime.now(timezone.utc),
            reliability_score=0.95
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_properties():
    """Create multiple sample properties for testing"""
    base_time = datetime.now(timezone.utc)
    
    properties = []
    
    # Property 1: Expensive flat in Central London
    properties.append(Property(
        id="prop-1",
        title="Luxury 3-bed penthouse",
        description="Stunning penthouse with panoramic city views",
        price=1200000,
        property_type=PropertyType.FLAT,
        status=PropertyStatus.FOR_SALE,
        bedrooms=3,
        bathrooms=2,
        location=Location(
            latitude=51.5074,
            longitude=-0.1278,
            address="1 Luxury Tower, London",
            postcode="W1K 1AA",
            area="Mayfair",
            city="London"
        ),
        features=["balcony", "concierge", "gym"],
        energy_rating="A",
        garden=False,
        parking=True,
        lineage=PropertyLineage(
            source="rightmove",
            source_id="rm-001",
            last_updated=base_time,
            reliability_score=0.98
        ),
        created_at=base_time,
        updated_at=base_time
    ))
    
    # Property 2: Affordable house in suburbs
    properties.append(Property(
        id="prop-2",
        title="Cozy 2-bed house with garden",
        description="Perfect family home in quiet neighborhood",
        price=350000,
        property_type=PropertyType.HOUSE,
        status=PropertyStatus.FOR_SALE,
        bedrooms=2,
        bathrooms=1,
        location=Location(
            latitude=51.4994,
            longitude=-0.1746,
            address="45 Suburban Road, London",
            postcode="SW6 2BB",
            area="Fulham",
            city="London"
        ),
        features=["garden", "parking", "quiet street"],
        energy_rating="C",
        garden=True,
        parking=True,
        lineage=PropertyLineage(
            source="zoopla",
            source_id="zp-002",
            last_updated=base_time,
            reliability_score=0.92
        ),
        created_at=base_time,
        updated_at=base_time
    ))
    
    # Property 3: Rental flat
    properties.append(Property(
        id="prop-3",
        title="Modern 1-bed flat to rent",
        description="Contemporary apartment near transport",
        price=2500,  # Monthly rent
        property_type=PropertyType.FLAT,
        status=PropertyStatus.FOR_RENT,
        bedrooms=1,
        bathrooms=1,
        location=Location(
            latitude=51.5155,
            longitude=-0.0922,
            address="78 Modern Block, London",
            postcode="E1 6AA",
            area="Shoreditch",
            city="London"
        ),
        features=["balcony", "gym", "24h security"],
        energy_rating="B",
        garden=False,
        parking=False,
        lineage=PropertyLineage(
            source="rightmove",
            source_id="rm-003",
            last_updated=base_time,
            reliability_score=0.89
        ),
        created_at=base_time,
        updated_at=base_time
    ))
    
    return properties


class TestElasticsearchService:
    """Test Elasticsearch service functionality"""
    
    @pytest.mark.asyncio
    async def test_create_properties_index(self, setup_elasticsearch):
        """Test creating the properties index"""
        # Index should already be created by setup fixture
        client = await elasticsearch_service._get_client()
        exists = await client.indices.exists(index=PROPERTIES_INDEX)
        assert exists, "Properties index should exist"
        
        # Test creating index again (should not fail)
        success = await elasticsearch_service.create_properties_index()
        assert success, "Should handle existing index gracefully"
    
    @pytest.mark.asyncio
    async def test_index_single_property(self, setup_elasticsearch, sample_property):
        """Test indexing a single property"""
        success = await elasticsearch_service.index_property(sample_property)
        assert success, "Should successfully index property"
        
        # Refresh index to make document searchable
        await elasticsearch_service.refresh_index()
        
        # Verify property was indexed
        client = await elasticsearch_service._get_client()
        response = await client.get(
            index=PROPERTIES_INDEX,
            id=sample_property.id
        )
        
        assert response["found"], "Property should be found in index"
        assert response["_source"]["title"] == sample_property.title
        assert response["_source"]["price"] == sample_property.price
        assert response["_source"]["location"]["coordinates"]["lat"] == sample_property.location.latitude
    
    @pytest.mark.asyncio
    async def test_bulk_index_properties(self, setup_elasticsearch, sample_properties):
        """Test bulk indexing multiple properties"""
        result = await elasticsearch_service.bulk_index_properties(sample_properties)
        
        assert result["indexed"] == len(sample_properties), "Should index all properties"
        assert result["failed"] == 0, "Should have no failures"
        
        # Refresh index
        await elasticsearch_service.refresh_index()
        
        # Verify all properties were indexed
        client = await elasticsearch_service._get_client()
        for prop in sample_properties:
            response = await client.get(
                index=PROPERTIES_INDEX,
                id=prop.id
            )
            assert response["found"], f"Property {prop.id} should be found"
    
    @pytest.mark.asyncio
    async def test_delete_property(self, setup_elasticsearch, sample_property):
        """Test deleting a property from index"""
        # First index the property
        await elasticsearch_service.index_property(sample_property)
        await elasticsearch_service.refresh_index()
        
        # Delete the property
        success = await elasticsearch_service.delete_property(sample_property.id)
        assert success, "Should successfully delete property"
        
        # Verify property was deleted
        client = await elasticsearch_service._get_client()
        try:
            await client.get(index=PROPERTIES_INDEX, id=sample_property.id)
            assert False, "Property should not be found after deletion"
        except Exception as e:
            assert "not_found" in str(e).lower(), "Should get not found error"
    
    @pytest.mark.asyncio
    async def test_geospatial_mapping(self, setup_elasticsearch, sample_property):
        """Test that geospatial coordinates are properly mapped"""
        await elasticsearch_service.index_property(sample_property)
        await elasticsearch_service.refresh_index()
        
        client = await elasticsearch_service._get_client()
        
        # Test geo_distance query to verify geo_point mapping works
        query = {
            "query": {
                "bool": {
                    "filter": {
                        "geo_distance": {
                            "distance": "1km",
                            "location.coordinates": {
                                "lat": 51.5074,
                                "lon": -0.1278
                            }
                        }
                    }
                }
            }
        }
        
        response = await client.search(
            index=PROPERTIES_INDEX,
            body=query
        )
        
        assert response["hits"]["total"]["value"] > 0, "Should find properties within distance"
        assert response["hits"]["hits"][0]["_id"] == sample_property.id
    
    @pytest.mark.asyncio
    async def test_text_search_analyzers(self, setup_elasticsearch, sample_properties):
        """Test that text analyzers work correctly"""
        await elasticsearch_service.bulk_index_properties(sample_properties)
        await elasticsearch_service.refresh_index()
        
        client = await elasticsearch_service._get_client()
        
        # Test synonym search (flat should match apartment)
        query = {
            "query": {
                "match": {
                    "search_text": "apartment"
                }
            }
        }
        
        response = await client.search(
            index=PROPERTIES_INDEX,
            body=query
        )
        
        # Should find properties with "flat" in title due to synonyms
        assert response["hits"]["total"]["value"] > 0, "Should find properties using synonyms"
    
    @pytest.mark.asyncio
    async def test_derived_fields(self, setup_elasticsearch, sample_properties):
        """Test that derived fields are calculated correctly"""
        await elasticsearch_service.bulk_index_properties(sample_properties)
        await elasticsearch_service.refresh_index()
        
        client = await elasticsearch_service._get_client()
        response = await client.get(
            index=PROPERTIES_INDEX,
            id="prop-1"  # 3-bed penthouse for £1,200,000
        )
        
        source = response["_source"]
        
        # Test price per bedroom calculation
        expected_price_per_bedroom = 1200000 / 3
        assert source["price_per_bedroom"] == expected_price_per_bedroom
        
        # Test freshness score exists and is reasonable
        assert "freshness_score" in source
        assert 0 <= source["freshness_score"] <= 1
    
    @pytest.mark.asyncio
    async def test_empty_bulk_index(self, setup_elasticsearch):
        """Test bulk indexing with empty list"""
        result = await elasticsearch_service.bulk_index_properties([])
        assert result["indexed"] == 0
        assert result["failed"] == 0


@pytest.mark.asyncio
class TestElasticsearchIntegration:
    """Integration tests for Elasticsearch functionality"""
    
    async def test_full_indexing_pipeline(self, setup_elasticsearch, sample_properties):
        """Test complete indexing pipeline from properties to searchable documents"""
        # Index all properties
        result = await elasticsearch_service.bulk_index_properties(sample_properties)
        assert result["indexed"] == len(sample_properties)
        
        await elasticsearch_service.refresh_index()
        
        client = await elasticsearch_service._get_client()
        
        # Test various search scenarios
        
        # 1. Search by property type
        query = {
            "query": {"term": {"property_type": "flat"}},
            "size": 10
        }
        response = await client.search(index=PROPERTIES_INDEX, body=query)
        flat_count = sum(1 for p in sample_properties if p.property_type == PropertyType.FLAT)
        assert response["hits"]["total"]["value"] == flat_count
        
        # 2. Search by price range
        query = {
            "query": {
                "range": {
                    "price": {
                        "gte": 300000,
                        "lte": 600000
                    }
                }
            }
        }
        response = await client.search(index=PROPERTIES_INDEX, body=query)
        assert response["hits"]["total"]["value"] > 0
        
        # 3. Geospatial search within London area
        query = {
            "query": {
                "geo_bounding_box": {
                    "location.coordinates": {
                        "top_left": {"lat": 51.52, "lon": -0.20},
                        "bottom_right": {"lat": 51.48, "lon": -0.05}
                    }
                }
            }
        }
        response = await client.search(index=PROPERTIES_INDEX, body=query)
        assert response["hits"]["total"]["value"] > 0
        
        # 4. Combined text and filter search
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"search_text": "garden"}}
                    ],
                    "filter": [
                        {"term": {"garden": True}}
                    ]
                }
            }
        }
        response = await client.search(index=PROPERTIES_INDEX, body=query)
        assert response["hits"]["total"]["value"] > 0
        
        # Verify all returned properties have gardens
        for hit in response["hits"]["hits"]:
            assert hit["_source"]["garden"] is True