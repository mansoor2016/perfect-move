"""
Zoopla API adapter for property listings
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

from .base import BasePropertyAdapter, RawPropertyData

logger = logging.getLogger(__name__)


class ZooplaAdapter(BasePropertyAdapter):
    """Adapter for Zoopla property listings"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Zoopla typically allows 100 requests per hour for free tier
        super().__init__(api_key, rate_limit_calls=100, rate_limit_window=3600)
        self.base_url = "https://api.zoopla.co.uk/api/v1"
    
    async def search_properties(self, location: str, radius_km: float = 5, 
                              max_results: int = 100) -> List[RawPropertyData]:
        """Search for properties in Zoopla"""
        try:
            logger.info(f"Searching Zoopla for properties near {location}")
            
            # This would be the actual API call with real Zoopla API:
            # params = {
            #     'area': location,
            #     'radius': radius_km,
            #     'page_size': min(max_results, 100),  # Zoopla max is 100
            #     'api_key': self.api_key,
            #     'listing_status': 'sale'
            # }
            # response = await self._make_request(f"{self.base_url}/property_listings", params)
            # data = response.json()
            
            # Mock response for development
            mock_properties = self._generate_mock_zoopla_data(location, max_results)
            
            return [
                RawPropertyData(
                    source="zoopla",
                    source_id=str(prop["listing_id"]),
                    raw_data=prop,
                    fetched_at=datetime.now(),
                    url=prop.get("details_url")
                )
                for prop in mock_properties
            ]
            
        except Exception as e:
            logger.error(f"Error searching Zoopla properties: {str(e)}")
            return []
    
    async def get_property_details(self, property_id: str) -> Optional[RawPropertyData]:
        """Get detailed property information from Zoopla"""
        try:
            logger.info(f"Fetching Zoopla property details for {property_id}")
            
            # This would be the actual API call:
            # params = {
            #     'listing_id': property_id,
            #     'api_key': self.api_key
            # }
            # response = await self._make_request(f"{self.base_url}/property_listings", params)
            
            # Mock implementation
            mock_detail = self._generate_mock_property_detail(property_id)
            
            return RawPropertyData(
                source="zoopla",
                source_id=property_id,
                raw_data=mock_detail,
                fetched_at=datetime.now(),
                url=mock_detail.get("details_url")
            )
            
        except Exception as e:
            logger.error(f"Error fetching Zoopla property {property_id}: {str(e)}")
            return None
    
    def normalize_property_data(self, raw_data: RawPropertyData) -> Dict[str, Any]:
        """Convert Zoopla data to normalized format"""
        data = raw_data.raw_data
        
        # Extract price
        price = self._extract_price(data.get("price"))
        
        # Extract coordinates
        lat, lon = self._extract_coordinates(data)
        
        # Normalize property type
        property_type = self._normalize_property_type(data.get("property_type", ""))
        
        normalized = {
            'title': data.get('displayable_address', ''),
            'description': data.get('description', ''),
            'price': price,
            'bedrooms': data.get('num_bedrooms'),
            'bathrooms': data.get('num_bathrooms'),
            'property_type': property_type,
            'address': data.get('displayable_address', ''),
            'postcode': data.get('outcode', ''),  # Zoopla provides outcode
            'city': data.get('county', ''),
            'latitude': lat,
            'longitude': lon,
            'floor_area': self._extract_floor_area(data),
            'garden': self._has_feature(data, 'garden'),
            'parking': self._has_feature(data, 'parking'),
            'furnished': self._extract_furnished_status(data),
            'listing_url': data.get('details_url', ''),
            'image_urls': self._extract_image_urls(data)
        }
        
        # Add lineage information
        return self.add_lineage_data(normalized, raw_data)
    
    def _extract_price(self, price_data) -> Optional[float]:
        """Extract numeric price from Zoopla price data"""
        if isinstance(price_data, (int, float)):
            return float(price_data)
        elif isinstance(price_data, str):
            # Remove currency symbols and commas
            price_clean = re.sub(r'[£,]', '', price_data)
            numbers = re.findall(r'\d+', price_clean)
            if numbers:
                return float(numbers[0])
        return None
    
    def _extract_coordinates(self, data: Dict) -> tuple[Optional[float], Optional[float]]:
        """Extract latitude and longitude from Zoopla data"""
        lat = data.get('latitude')
        lon = data.get('longitude')
        
        if lat and lon:
            return float(lat), float(lon)
        
        return None, None
    
    def _normalize_property_type(self, prop_type: str) -> str:
        """Normalize Zoopla property type to standard format"""
        if not prop_type:
            return "unknown"
        
        prop_type_lower = prop_type.lower()
        
        # Zoopla uses different terminology
        type_mapping = {
            'flat': 'flat',
            'apartment': 'flat',
            'maisonette': 'flat',
            'house': 'house',
            'terraced': 'house',
            'semi-detached': 'house',
            'detached': 'house',
            'bungalow': 'house',
            'studio': 'studio'
        }
        
        for key, value in type_mapping.items():
            if key in prop_type_lower:
                return value
        
        return prop_type_lower
    
    def _extract_floor_area(self, data: Dict) -> Optional[float]:
        """Extract floor area from Zoopla data"""
        # Zoopla might provide floor_area in different formats
        floor_area = data.get('floor_area')
        if isinstance(floor_area, (int, float)):
            return float(floor_area)
        elif isinstance(floor_area, dict):
            # Sometimes it's nested with units
            return floor_area.get('value')
        return None
    
    def _has_feature(self, data: Dict, feature: str) -> bool:
        """Check if property has a specific feature"""
        # Check in various possible fields
        features_to_check = [
            data.get('features', []),
            data.get('property_features', []),
            data.get('description', '')
        ]
        
        for features in features_to_check:
            if isinstance(features, list):
                if any(feature.lower() in str(f).lower() for f in features):
                    return True
            elif isinstance(features, str):
                if feature.lower() in features.lower():
                    return True
        
        return False
    
    def _extract_furnished_status(self, data: Dict) -> Optional[str]:
        """Extract furnished status from Zoopla data"""
        # Check furnished_state field first
        furnished_state = data.get('furnished_state')
        if furnished_state:
            state_lower = furnished_state.lower()
            if 'furnished' in state_lower:
                if 'unfurnished' in state_lower:
                    return 'unfurnished'
                elif 'part' in state_lower or 'partial' in state_lower:
                    return 'part-furnished'
                else:
                    return 'furnished'
        
        # Fallback to checking features
        if self._has_feature(data, 'furnished'):
            return 'furnished'
        elif self._has_feature(data, 'unfurnished'):
            return 'unfurnished'
        
        return None
    
    def _extract_image_urls(self, data: Dict) -> List[str]:
        """Extract image URLs from Zoopla data"""
        images = data.get('image_urls', [])
        if isinstance(images, list):
            return images
        elif isinstance(images, str):
            return [images]
        return []
    
    def _generate_mock_zoopla_data(self, location: str, max_results: int) -> List[Dict]:
        """Generate mock Zoopla data for development"""
        mock_data = []
        for i in range(min(max_results, 10)):  # Limit to 10 for mock
            mock_data.append({
                "listing_id": f"zoopla_{i+1}",
                "displayable_address": f"{i+10} Sample Road, {location}",
                "price": 280000 + i * 40000,
                "num_bedrooms": 1 + (i % 4),
                "num_bathrooms": 1 + (i % 3),
                "property_type": ["Flat", "Terraced house", "Semi-detached house"][i % 3],
                "description": f"Lovely {['flat', 'house', 'property'][i % 3]} in {location}",
                "latitude": 51.5074 + (i * 0.002),
                "longitude": -0.1278 + (i * 0.002),
                "outcode": f"SW{i+1}",
                "county": location,
                "details_url": f"https://zoopla.co.uk/property/{i+1}",
                "image_urls": [f"https://zoopla.co.uk/images/{i+1}_1.jpg"],
                "features": ["Garden", "Parking"] if i % 2 == 0 else ["Furnished"],
                "furnished_state": "Furnished" if i % 3 == 0 else "Unfurnished"
            })
        return mock_data
    
    def _generate_mock_property_detail(self, property_id: str) -> Dict:
        """Generate mock detailed property data"""
        return {
            "listing_id": property_id,
            "displayable_address": "456 Sample Road, London",
            "price": 380000,
            "num_bedrooms": 2,
            "num_bathrooms": 1,
            "property_type": "Flat",
            "description": "Modern 2-bedroom flat with excellent transport links",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "outcode": "SW1",
            "county": "London",
            "floor_area": 850,
            "details_url": f"https://zoopla.co.uk/property/{property_id}",
            "image_urls": [
                f"https://zoopla.co.uk/images/{property_id}_1.jpg",
                f"https://zoopla.co.uk/images/{property_id}_2.jpg"
            ],
            "features": ["Balcony", "Modern kitchen", "Close to transport"],
            "furnished_state": "Part furnished"
        }