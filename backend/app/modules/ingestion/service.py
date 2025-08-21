import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from geoalchemy2 import WKTElement

from app.models.property import Property
from app.db.models import Property as PropertyModel
from .adapters.rightmove import RightmoveAdapter
from .adapters.zoopla import ZooplaAdapter
from .deduplication import PropertyDeduplicator

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting property data from external sources"""
    
    def __init__(self, rightmove_api_key: Optional[str] = None, 
                 zoopla_api_key: Optional[str] = None):
        self.rightmove_adapter = RightmoveAdapter(rightmove_api_key)
        self.zoopla_adapter = ZooplaAdapter(zoopla_api_key)
        self.deduplicator = PropertyDeduplicator()
    
    async def sync_properties_for_location(self, location: str, radius_km: float = 5,
                                         max_results: int = 100) -> List[Dict[str, Any]]:
        """Sync properties from all sources for a given location"""
        all_properties = []
        
        # Fetch from Rightmove
        try:
            async with self.rightmove_adapter as adapter:
                rightmove_raw = await adapter.search_properties(location, radius_km, max_results)
                rightmove_normalized = [
                    adapter.normalize_property_data(raw_prop) 
                    for raw_prop in rightmove_raw
                ]
                all_properties.extend(rightmove_normalized)
                logger.info(f"Fetched {len(rightmove_normalized)} properties from Rightmove")
        except Exception as e:
            logger.error(f"Error fetching from Rightmove: {str(e)}")
        
        # Fetch from Zoopla
        try:
            async with self.zoopla_adapter as adapter:
                zoopla_raw = await adapter.search_properties(location, radius_km, max_results)
                zoopla_normalized = [
                    adapter.normalize_property_data(raw_prop) 
                    for raw_prop in zoopla_raw
                ]
                all_properties.extend(zoopla_normalized)
                logger.info(f"Fetched {len(zoopla_normalized)} properties from Zoopla")
        except Exception as e:
            logger.error(f"Error fetching from Zoopla: {str(e)}")
        
        # Deduplicate properties
        deduplicated_properties = self.deduplicator.deduplicate_properties(all_properties)
        
        logger.info(f"Ingested {len(deduplicated_properties)} unique properties for {location}")
        return deduplicated_properties
    
    async def sync_rightmove_properties(self, location: str, radius_km: float = 5,
                                      max_results: int = 100) -> List[Dict[str, Any]]:
        """Sync properties from Rightmove API"""
        try:
            async with self.rightmove_adapter as adapter:
                raw_properties = await adapter.search_properties(location, radius_km, max_results)
                normalized_properties = [
                    adapter.normalize_property_data(raw_prop) 
                    for raw_prop in raw_properties
                ]
                logger.info(f"Synced {len(normalized_properties)} properties from Rightmove")
                return normalized_properties
        except Exception as e:
            logger.error(f"Error syncing Rightmove properties: {str(e)}")
            return []
    
    async def sync_zoopla_properties(self, location: str, radius_km: float = 5,
                                   max_results: int = 100) -> List[Dict[str, Any]]:
        """Sync properties from Zoopla API"""
        try:
            async with self.zoopla_adapter as adapter:
                raw_properties = await adapter.search_properties(location, radius_km, max_results)
                normalized_properties = [
                    adapter.normalize_property_data(raw_prop) 
                    for raw_prop in raw_properties
                ]
                logger.info(f"Synced {len(normalized_properties)} properties from Zoopla")
                return normalized_properties
        except Exception as e:
            logger.error(f"Error syncing Zoopla properties: {str(e)}")
            return []
    
    def deduplicate_properties(self, properties: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate properties using fuzzy matching"""
        return self.deduplicator.deduplicate_properties(properties)
    
    async def get_property_details(self, source: str, property_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed property information from a specific source"""
        try:
            if source.lower() == 'rightmove':
                async with self.rightmove_adapter as adapter:
                    raw_data = await adapter.get_property_details(property_id)
                    if raw_data:
                        return adapter.normalize_property_data(raw_data)
            elif source.lower() == 'zoopla':
                async with self.zoopla_adapter as adapter:
                    raw_data = await adapter.get_property_details(property_id)
                    if raw_data:
                        return adapter.normalize_property_data(raw_data)
            else:
                logger.error(f"Unknown source: {source}")
                return None
        except Exception as e:
            logger.error(f"Error getting property details from {source}: {str(e)}")
            return None
    
    def save_properties_to_db(self, properties: List[Dict[str, Any]], db: Session) -> List[PropertyModel]:
        """Save normalized properties to database"""
        saved_properties = []
        
        for prop_data in properties:
            try:
                # Check if property already exists
                existing = db.query(PropertyModel).filter(
                    PropertyModel.source == prop_data.get('source'),
                    PropertyModel.source_id == prop_data.get('source_id')
                ).first()
                
                if existing:
                    # Update existing property
                    self._update_property_from_dict(existing, prop_data)
                    db.commit()
                    saved_properties.append(existing)
                    logger.debug(f"Updated existing property {existing.id}")
                else:
                    # Create new property
                    new_property = self._create_property_from_dict(prop_data)
                    db.add(new_property)
                    db.commit()
                    saved_properties.append(new_property)
                    logger.debug(f"Created new property {new_property.id}")
                    
            except Exception as e:
                logger.error(f"Error saving property to database: {str(e)}")
                db.rollback()
                continue
        
        logger.info(f"Saved {len(saved_properties)} properties to database")
        return saved_properties
    
    def _create_property_from_dict(self, prop_data: Dict[str, Any]) -> PropertyModel:
        """Create PropertyModel from normalized property data"""
        # Create PostGIS point from coordinates
        location = None
        if prop_data.get('latitude') and prop_data.get('longitude'):
            location = WKTElement(
                f"POINT({prop_data['longitude']} {prop_data['latitude']})",
                srid=4326
            )
        
        return PropertyModel(
            title=prop_data.get('title', ''),
            description=prop_data.get('description', ''),
            price=prop_data.get('price'),
            bedrooms=prop_data.get('bedrooms'),
            bathrooms=prop_data.get('bathrooms'),
            property_type=prop_data.get('property_type'),
            address=prop_data.get('address', ''),
            postcode=prop_data.get('postcode'),
            city=prop_data.get('city'),
            location=location,
            floor_area=prop_data.get('floor_area'),
            garden=prop_data.get('garden', False),
            parking=prop_data.get('parking', False),
            furnished=prop_data.get('furnished'),
            listing_url=prop_data.get('listing_url'),
            image_urls=prop_data.get('image_urls', []),
            source=prop_data.get('source'),
            source_id=prop_data.get('source_id'),
            reliability_score=prop_data.get('reliability_score', 1.0)
        )
    
    def _update_property_from_dict(self, property_model: PropertyModel, 
                                 prop_data: Dict[str, Any]) -> None:
        """Update existing PropertyModel with new data"""
        # Update fields that might have changed
        property_model.title = prop_data.get('title', property_model.title)
        property_model.description = prop_data.get('description', property_model.description)
        property_model.price = prop_data.get('price', property_model.price)
        property_model.bedrooms = prop_data.get('bedrooms', property_model.bedrooms)
        property_model.bathrooms = prop_data.get('bathrooms', property_model.bathrooms)
        property_model.property_type = prop_data.get('property_type', property_model.property_type)
        property_model.address = prop_data.get('address', property_model.address)
        property_model.postcode = prop_data.get('postcode', property_model.postcode)
        property_model.city = prop_data.get('city', property_model.city)
        
        # Update location if coordinates are provided
        if prop_data.get('latitude') and prop_data.get('longitude'):
            property_model.location = WKTElement(
                f"POINT({prop_data['longitude']} {prop_data['latitude']})",
                srid=4326
            )
        
        property_model.floor_area = prop_data.get('floor_area', property_model.floor_area)
        property_model.garden = prop_data.get('garden', property_model.garden)
        property_model.parking = prop_data.get('parking', property_model.parking)
        property_model.furnished = prop_data.get('furnished', property_model.furnished)
        property_model.listing_url = prop_data.get('listing_url', property_model.listing_url)
        property_model.image_urls = prop_data.get('image_urls', property_model.image_urls)
        property_model.reliability_score = prop_data.get('reliability_score', property_model.reliability_score)
        property_model.last_updated = datetime.now()