from elasticsearch import AsyncElasticsearch
from typing import Dict, List, Optional, Any
from app.core.elasticsearch import get_elasticsearch
from app.models.property import Property
import logging

logger = logging.getLogger(__name__)

# Elasticsearch index name for properties
PROPERTIES_INDEX = "properties"


class ElasticsearchService:
    """Service for Elasticsearch operations on properties"""
    
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
    
    async def _get_client(self) -> AsyncElasticsearch:
        """Get Elasticsearch client"""
        # Create a fresh client for each operation to avoid event loop issues
        from elasticsearch import AsyncElasticsearch
        from app.core.config import settings
        
        client = AsyncElasticsearch(
            [settings.ELASTICSEARCH_URL],
            verify_certs=False,
            ssl_show_warn=False
        )
        return client
    
    async def create_properties_index(self) -> bool:
        """Create the properties index with proper mapping"""
        client = await self._get_client()
        
        # Define the mapping for properties with geospatial support
        mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "property_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "property_analyzer"
                    },
                    "price": {"type": "integer"},
                    "property_type": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "bedrooms": {"type": "integer"},
                    "bathrooms": {"type": "integer"},
                    "location": {
                        "properties": {
                            "coordinates": {"type": "geo_point"},
                            "address": {
                                "type": "text",
                                "analyzer": "address_analyzer",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "postcode": {"type": "keyword"},
                            "area": {"type": "keyword"},
                            "city": {"type": "keyword"}
                        }
                    },
                    "features": {"type": "keyword"},
                    "energy_rating": {"type": "keyword"},
                    "council_tax_band": {"type": "keyword"},
                    "tenure": {"type": "keyword"},
                    "floor_area_sqft": {"type": "integer"},
                    "garden": {"type": "boolean"},
                    "parking": {"type": "boolean"},
                    "lineage": {
                        "properties": {
                            "source": {"type": "keyword"},
                            "source_id": {"type": "keyword"},
                            "last_updated": {"type": "date"},
                            "reliability_score": {"type": "float"}
                        }
                    },
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    # Additional fields for search optimization
                    "search_text": {
                        "type": "text",
                        "analyzer": "property_analyzer"
                    },
                    "price_per_bedroom": {"type": "float"},
                    "freshness_score": {"type": "float"}
                }
            },
            "settings": {
                "analysis": {
                    "analyzer": {
                        "property_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "stop",
                                "property_synonyms",
                                "stemmer"
                            ]
                        },
                        "address_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase", "trim"]
                        }
                    },
                    "filter": {
                        "property_synonyms": {
                            "type": "synonym",
                            "synonyms": [
                                "flat,apartment",
                                "house,home",
                                "garden,outdoor space",
                                "parking,garage,car space",
                                "ensuite,en-suite,en suite"
                            ]
                        },
                        "stemmer": {
                            "type": "stemmer",
                            "language": "english"
                        }
                    }
                },
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
        
        try:
            # Check if index exists
            exists = await client.indices.exists(index=PROPERTIES_INDEX)
            if exists:
                logger.info(f"Index {PROPERTIES_INDEX} already exists")
                return True
            
            # Create the index
            response = await client.indices.create(
                index=PROPERTIES_INDEX,
                body=mapping
            )
            
            logger.info(f"Created index {PROPERTIES_INDEX}: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index {PROPERTIES_INDEX}: {e}")
            return False
    
    async def delete_properties_index(self) -> bool:
        """Delete the properties index (useful for testing)"""
        client = await self._get_client()
        
        try:
            exists = await client.indices.exists(index=PROPERTIES_INDEX)
            if not exists:
                logger.info(f"Index {PROPERTIES_INDEX} does not exist")
                return True
            
            response = await client.indices.delete(index=PROPERTIES_INDEX)
            logger.info(f"Deleted index {PROPERTIES_INDEX}: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete index {PROPERTIES_INDEX}: {e}")
            return False
    
    def _prepare_property_document(self, property_obj: Property) -> Dict[str, Any]:
        """Convert Property model to Elasticsearch document"""
        # Create search text combining title, description, and features
        search_text_parts = [property_obj.title]
        if property_obj.description:
            search_text_parts.append(property_obj.description)
        search_text_parts.extend(property_obj.features)
        
        # Calculate derived fields
        price_per_bedroom = None
        if property_obj.bedrooms and property_obj.bedrooms > 0:
            price_per_bedroom = float(property_obj.price) / float(property_obj.bedrooms)
        
        # Calculate freshness score (newer properties get higher score)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        days_old = (now - property_obj.updated_at.replace(tzinfo=timezone.utc)).days
        freshness_score = max(0, 1 - (days_old / 365))  # Score decreases over a year
        
        doc = {
            "id": property_obj.id,
            "title": property_obj.title,
            "description": property_obj.description,
            "price": property_obj.price,
            "property_type": property_obj.property_type.value,
            "status": property_obj.status.value,
            "bedrooms": property_obj.bedrooms,
            "bathrooms": property_obj.bathrooms,
            "location": {
                "coordinates": {
                    "lat": property_obj.location.latitude,
                    "lon": property_obj.location.longitude
                },
                "address": property_obj.location.address,
                "postcode": property_obj.location.postcode,
                "area": property_obj.location.area,
                "city": property_obj.location.city
            },
            "features": property_obj.features,
            "energy_rating": property_obj.energy_rating,
            "council_tax_band": property_obj.council_tax_band,
            "tenure": property_obj.tenure,
            "floor_area_sqft": property_obj.floor_area_sqft,
            "garden": property_obj.garden,
            "parking": property_obj.parking,
            "lineage": {
                "source": property_obj.lineage.source,
                "source_id": property_obj.lineage.source_id,
                "last_updated": property_obj.lineage.last_updated.isoformat(),
                "reliability_score": property_obj.lineage.reliability_score
            },
            "created_at": property_obj.created_at.isoformat(),
            "updated_at": property_obj.updated_at.isoformat(),
            "search_text": " ".join(search_text_parts),
            "price_per_bedroom": price_per_bedroom,
            "freshness_score": freshness_score
        }
        
        return doc
    
    async def index_property(self, property_obj: Property) -> bool:
        """Index a single property"""
        client = await self._get_client()
        
        try:
            doc = self._prepare_property_document(property_obj)
            
            response = await client.index(
                index=PROPERTIES_INDEX,
                id=property_obj.id,
                body=doc
            )
            
            logger.debug(f"Indexed property {property_obj.id}: {response['result']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index property {property_obj.id}: {e}")
            return False
    
    async def bulk_index_properties(self, properties: List[Property]) -> Dict[str, int]:
        """Bulk index multiple properties"""
        client = await self._get_client()
        
        if not properties:
            return {"indexed": 0, "failed": 0}
        
        # Prepare bulk operations
        operations = []
        for property_obj in properties:
            doc = self._prepare_property_document(property_obj)
            
            operations.append({
                "_index": PROPERTIES_INDEX,
                "_id": property_obj.id,
                "_source": doc
            })
        
        try:
            from elasticsearch.helpers import async_bulk
            
            success_count, failed_items = await async_bulk(
                client,
                operations,
                chunk_size=100
            )
            
            failed_count = len(failed_items) if failed_items else 0
            
            logger.info(f"Bulk indexed {success_count} properties, {failed_count} failed")
            
            return {
                "indexed": success_count,
                "failed": failed_count
            }
            
        except Exception as e:
            logger.error(f"Failed to bulk index properties: {e}")
            return {"indexed": 0, "failed": len(properties)}
    
    async def delete_property(self, property_id: str) -> bool:
        """Delete a property from the index"""
        client = await self._get_client()
        
        try:
            response = await client.delete(
                index=PROPERTIES_INDEX,
                id=property_id
            )
            
            logger.debug(f"Deleted property {property_id}: {response['result']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete property {property_id}: {e}")
            return False
    
    async def refresh_index(self) -> bool:
        """Refresh the properties index to make changes visible"""
        client = await self._get_client()
        
        try:
            await client.indices.refresh(index=PROPERTIES_INDEX)
            return True
        except Exception as e:
            logger.error(f"Failed to refresh index: {e}")
            return False


# Global service instance
elasticsearch_service = ElasticsearchService()