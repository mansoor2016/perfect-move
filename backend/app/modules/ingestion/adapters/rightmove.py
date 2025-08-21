"""
Rightmove API adapter for property listings
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import re

from .base import BasePropertyAdapter, RawPropertyData

logger = logging.getLogger(__name__)


class RightmoveAdapter(BasePropertyAdapter):
    """Adapter for Rightmove property listings"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Rightmove typically allows 1000 requests per hour
        super().__init__(api_key, rate_limit_calls=1000, rate_limit_window=3600)
        self.base_url = "https://api.rightmove.co.uk"
        # Note: This is a mock implementation as Rightmove doesn't have a public API
        # In reality, you'd need to use web scraping or partner API access
    
    async def search_properties(self, location: str, radius_km: float = 5, 
                              max_results: int = 100) -> List[RawPropertyData]:
        """Search for properties in Rightmove"""
        try:
            # Mock implementation - in reality this would call Rightmove's API
            # For now, return sample data structure
            logger.info(f"Searching Rightmove for properties near {location}")
            
            # This would be the actual API call:
            # params = {
            #     'location': location,
            #     'radius': radius_km,
            #     'limit': max_results,
            #     'apikey': self.api_key
            # }
            # response = await self._make_request(f"{self.base_url}/properties/search", params)
            
            # Mock response for development
            mock_properties = self._generate_mock_rightmove_data(location, max_results)
            
            return [
                RawPropertyData(
                    source="rightmove",
                    source_id=prop["id"],
                    raw_data=prop,
                    fetched_at=datetime.now(),
                    url=prop.get("url")
                )
                for prop in mock_properties
            ]
            
        except Exception as e:
            logger.error(f"Error searching Rightmove properties: {str(e)}")
            return []
    
    async def get_property_details(self, property_id: str) -> Optional[RawPropertyData]:
        """Get detailed property information from Rightmove"""
        try:
            logger.info(f"Fetching Rightmove property details for {property_id}")
            
            # Mock implementation
            mock_detail = self._generate_mock_property_detail(property_id)
            
            return RawPropertyData(
                source="rightmove",
                source_id=property_id,
                raw_data=mock_detail,
                fetched_at=datetime.now(),
                url=mock_detail.get("url")
            )
            
        except Exception as e:
            logger.error(f"Error fetching Rightmove property {property_id}: {str(e)}")
            return None
    
    def normalize_property_data(self, raw_data: RawPropertyData) -> Dict[str, Any]:
        """Convert Rightmove data to normalized format"""
        data = raw_data.raw_data
        
        # Extract price (handle different formats)
        price = self._extract_price(data.get("price", ""))
        
        # Extract coordinates
        lat, lon = self._extract_coordinates(data)
        
        # Normalize property type
        property_type = self._normalize_property_type(data.get("propertyType", ""))
        
        normalized = {
            'title': data.get('displayAddress', ''),
            'description': data.get('summary', ''),
            'price': price,
            'bedrooms': self._extract_bedrooms(data.get('bedrooms')),
            'bathrooms': self._extract_bathrooms(data.get('bathrooms')),
            'property_type': property_type,
            'address': data.get('displayAddress', ''),
            'postcode': self._extract_postcode(data.get('displayAddress', '')),
            'city': data.get('location', {}).get('displayName', ''),
            'latitude': lat,
            'longitude': lon,
            'floor_area': data.get('size', {}).get('squareFeet'),
            'garden': self._has_feature(data, 'garden'),
            'parking': self._has_feature(data, 'parking'),
            'furnished': self._extract_furnished_status(data),
            'listing_url': data.get('propertyUrl', ''),
            'image_urls': data.get('propertyImages', [])
        }
        
        # Add lineage information
        return self.add_lineage_data(normalized, raw_data)
    
    def _extract_price(self, price_str: str) -> Optional[float]:
        """Extract numeric price from Rightmove price string"""
        if not price_str:
            return None
        
        # Remove currency symbols and commas
        price_clean = re.sub(r'[£,]', '', str(price_str))
        
        # Handle "POA" (Price on Application)
        if 'poa' in price_clean.lower():
            return None
        
        # Extract numbers
        numbers = re.findall(r'\d+', price_clean)
        if numbers:
            return float(numbers[0])
        
        return None
    
    def _extract_coordinates(self, data: Dict) -> tuple[Optional[float], Optional[float]]:
        """Extract latitude and longitude from Rightmove data"""
        location = data.get('location', {})
        lat = location.get('latitude')
        lon = location.get('longitude')
        
        if lat and lon:
            return float(lat), float(lon)
        
        return None, None
    
    def _normalize_property_type(self, prop_type: str) -> str:
        """Normalize Rightmove property type to standard format"""
        if not prop_type:
            return "unknown"
        
        prop_type_lower = prop_type.lower()
        
        if any(word in prop_type_lower for word in ['flat', 'apartment', 'maisonette']):
            return "flat"
        elif any(word in prop_type_lower for word in ['house', 'bungalow', 'cottage']):
            return "house"
        elif 'studio' in prop_type_lower:
            return "studio"
        else:
            return prop_type_lower
    
    def _extract_bedrooms(self, bedrooms) -> Optional[int]:
        """Extract number of bedrooms"""
        if isinstance(bedrooms, int):
            return bedrooms
        elif isinstance(bedrooms, str):
            numbers = re.findall(r'\d+', bedrooms)
            return int(numbers[0]) if numbers else None
        return None
    
    def _extract_bathrooms(self, bathrooms) -> Optional[int]:
        """Extract number of bathrooms"""
        if isinstance(bathrooms, int):
            return bathrooms
        elif isinstance(bathrooms, str):
            numbers = re.findall(r'\d+', bathrooms)
            return int(numbers[0]) if numbers else None
        return None
    
    def _extract_postcode(self, address: str) -> Optional[str]:
        """Extract UK postcode from address"""
        if not address:
            return None
        
        # UK postcode pattern
        postcode_pattern = r'[A-Z]{1,2}[0-9R][0-9A-Z]? [0-9][ABD-HJLNP-UW-Z]{2}'
        match = re.search(postcode_pattern, address.upper())
        return match.group() if match else None
    
    def _has_feature(self, data: Dict, feature: str) -> bool:
        """Check if property has a specific feature"""
        features = data.get('keyFeatures', [])
        if isinstance(features, list):
            return any(feature.lower() in str(f).lower() for f in features)
        return False
    
    def _extract_furnished_status(self, data: Dict) -> Optional[str]:
        """Extract furnished status from property data"""
        features = data.get('keyFeatures', [])
        if isinstance(features, list):
            for feature in features:
                feature_str = str(feature).lower()
                if 'furnished' in feature_str:
                    if 'unfurnished' in feature_str:
                        return 'unfurnished'
                    elif 'part' in feature_str or 'partial' in feature_str:
                        return 'part-furnished'
                    else:
                        return 'furnished'
        return None
    
    def _generate_mock_rightmove_data(self, location: str, max_results: int) -> List[Dict]:
        """Generate mock Rightmove data for development"""
        mock_data = []
        for i in range(min(max_results, 10)):  # Limit to 10 for mock
            mock_data.append({
                "id": f"rightmove_{i+1}",
                "displayAddress": f"{i+1} Mock Street, {location}",
                "price": f"£{300000 + i * 50000}",
                "bedrooms": 2 + (i % 3),
                "bathrooms": 1 + (i % 2),
                "propertyType": ["Flat", "House", "Studio"][i % 3],
                "summary": f"Beautiful {['flat', 'house', 'studio'][i % 3]} in {location}",
                "location": {
                    "latitude": 51.5074 + (i * 0.001),
                    "longitude": -0.1278 + (i * 0.001),
                    "displayName": location
                },
                "propertyUrl": f"https://rightmove.co.uk/property/{i+1}",
                "propertyImages": [f"https://rightmove.co.uk/images/{i+1}_1.jpg"],
                "keyFeatures": ["Garden", "Parking"] if i % 2 == 0 else ["Furnished"]
            })
        return mock_data
    
    def _generate_mock_property_detail(self, property_id: str) -> Dict:
        """Generate mock detailed property data"""
        return {
            "id": property_id,
            "displayAddress": "123 Mock Street, London",
            "price": "£450000",
            "bedrooms": 3,
            "bathrooms": 2,
            "propertyType": "House",
            "summary": "Spacious 3-bedroom house with garden and parking",
            "location": {
                "latitude": 51.5074,
                "longitude": -0.1278,
                "displayName": "London"
            },
            "size": {"squareFeet": 1200},
            "propertyUrl": f"https://rightmove.co.uk/property/{property_id}",
            "propertyImages": [
                f"https://rightmove.co.uk/images/{property_id}_1.jpg",
                f"https://rightmove.co.uk/images/{property_id}_2.jpg"
            ],
            "keyFeatures": ["Garden", "Parking", "Recently renovated"]
        }