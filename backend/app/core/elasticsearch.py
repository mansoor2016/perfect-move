from elasticsearch import AsyncElasticsearch
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Elasticsearch client wrapper for property search"""
    
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
    
    async def connect(self):
        """Initialize Elasticsearch connection"""
        try:
            # Close existing client if any
            if self.client:
                await self.client.close()
            
            self.client = AsyncElasticsearch(
                [settings.ELASTICSEARCH_URL],
                verify_certs=False,
                ssl_show_warn=False
            )
            
            # Test connection
            await self.client.ping()
            logger.info("Connected to Elasticsearch")
            
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
    
    async def disconnect(self):
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Disconnected from Elasticsearch")
    
    async def health_check(self) -> bool:
        """Check if Elasticsearch is healthy"""
        try:
            if not self.client:
                return False
            return await self.client.ping()
        except Exception:
            return False
    
    def get_client(self) -> Optional[AsyncElasticsearch]:
        """Get the current client instance"""
        return self.client


# Global Elasticsearch client instance
es_client = ElasticsearchClient()


async def get_elasticsearch() -> AsyncElasticsearch:
    """Get Elasticsearch client instance"""
    if not es_client.client:
        await es_client.connect()
    return es_client.client