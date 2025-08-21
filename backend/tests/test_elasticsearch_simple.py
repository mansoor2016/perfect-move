import pytest
import asyncio
from datetime import datetime, timezone
from app.modules.search.elasticsearch_service import elasticsearch_service, PROPERTIES_INDEX
from app.models.property import Property, PropertyType, PropertyStatus, Location, PropertyLineage
from app.core.elasticsearch import es_client


@pytest.mark.asyncio
async def test_elasticsearch_basic_functionality():
    """Test basic Elasticsearch functionality without complex fixtures"""
    
    # Connect to Elasticsearch
    await es_client.connect()
    
    try:
        # Clean up any existing test index
        await elasticsearch_service.delete_properties_index()
        
        # Create fresh index
        success = await elasticsearch_service.create_properties_index()
        assert success, "Failed to create properties index"
        
        # Create a test property
        test_property = Property(
            id="test-property-simple",
            title="Test Property for Elasticsearch",
            description="A test property to verify Elasticsearch functionality",
            price=400000,
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
            features=["balcony", "parking"],
            energy_rating="B",
            garden=False,
            parking=True,
            lineage=PropertyLineage(
                source="test",
                source_id="test-123",
                last_updated=datetime.now(timezone.utc),
                reliability_score=0.95
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Index the property
        success = await elasticsearch_service.index_property(test_property)
        assert success, "Failed to index property"
        
        # Refresh index to make document searchable
        await elasticsearch_service.refresh_index()
        
        # Verify property was indexed
        client = await elasticsearch_service._get_client()
        response = await client.get(
            index=PROPERTIES_INDEX,
            id=test_property.id
        )
        
        assert response["found"], "Property should be found in index"
        assert response["_source"]["title"] == test_property.title
        assert response["_source"]["price"] == test_property.price
        
        # Test geospatial query
        geo_query = {
            "query": {
                "geo_distance": {
                    "distance": "1km",
                    "location.coordinates": {
                        "lat": 51.5074,
                        "lon": -0.1278
                    }
                }
            }
        }
        
        search_response = await client.search(
            index=PROPERTIES_INDEX,
            body=geo_query
        )
        
        assert search_response["hits"]["total"]["value"] > 0, "Should find properties within distance"
        
        # Test text search
        text_query = {
            "query": {
                "match": {
                    "search_text": "test property"
                }
            }
        }
        
        text_response = await client.search(
            index=PROPERTIES_INDEX,
            body=text_query
        )
        
        assert text_response["hits"]["total"]["value"] > 0, "Should find properties by text search"
        
        print("✅ All Elasticsearch tests passed!")
        
    finally:
        # Cleanup
        await elasticsearch_service.delete_properties_index()
        await es_client.disconnect()


@pytest.mark.asyncio
async def test_bulk_indexing():
    """Test bulk indexing functionality"""
    
    await es_client.connect()
    
    try:
        await elasticsearch_service.delete_properties_index()
        await elasticsearch_service.create_properties_index()
        
        # Create multiple test properties
        properties = []
        for i in range(3):
            prop = Property(
                id=f"bulk-test-{i}",
                title=f"Bulk Test Property {i}",
                description=f"Test property number {i}",
                price=300000 + (i * 50000),
                property_type=PropertyType.FLAT,
                status=PropertyStatus.FOR_SALE,
                bedrooms=1 + i,
                bathrooms=1,
                location=Location(
                    latitude=51.5074 + (i * 0.001),
                    longitude=-0.1278 + (i * 0.001),
                    address=f"{i} Test Street, London",
                    postcode="SW1A 1AA",
                    area="Westminster",
                    city="London"
                ),
                features=["test"],
                lineage=PropertyLineage(
                    source="test",
                    source_id=f"bulk-{i}",
                    last_updated=datetime.now(timezone.utc),
                    reliability_score=0.9
                ),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            properties.append(prop)
        
        # Bulk index
        result = await elasticsearch_service.bulk_index_properties(properties)
        assert result["indexed"] == len(properties), "Should index all properties"
        assert result["failed"] == 0, "Should have no failures"
        
        await elasticsearch_service.refresh_index()
        
        # Verify all were indexed
        client = await elasticsearch_service._get_client()
        for prop in properties:
            response = await client.get(
                index=PROPERTIES_INDEX,
                id=prop.id
            )
            assert response["found"], f"Property {prop.id} should be found"
        
        print("✅ Bulk indexing test passed!")
        
    finally:
        await elasticsearch_service.delete_properties_index()
        await es_client.disconnect()


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_elasticsearch_basic_functionality())
    asyncio.run(test_bulk_indexing())