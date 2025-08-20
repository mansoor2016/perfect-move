from typing import List
from app.models.property import Property


class IngestionService:
    """Service for ingesting property data from external sources"""
    
    def __init__(self):
        pass
    
    async def sync_rightmove_properties(self) -> List[Property]:
        """Sync properties from Rightmove API"""
        # TODO: Implement Rightmove integration
        return []
    
    async def sync_zoopla_properties(self) -> List[Property]:
        """Sync properties from Zoopla API"""
        # TODO: Implement Zoopla integration
        return []
    
    async def deduplicate_properties(self, properties: List[Property]) -> List[Property]:
        """Remove duplicate properties using fuzzy matching"""
        # TODO: Implement deduplication logic
        return properties