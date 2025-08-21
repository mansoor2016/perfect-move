"""
Natural Language Processing service for parsing search queries and generating suggestions.

This module handles:
- Parsing free-form text queries into structured SearchCriteria
- Generating intelligent autocomplete suggestions
- Managing common search patterns and examples
"""

import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from app.models.search import (
    SearchCriteria, AmenityFilter, AmenityType, DistanceUnit,
    CommuteFilter, TransportMode, EnvironmentalFilter, PropertyType
)


class QueryIntent(str, Enum):
    """Types of search intents we can detect"""
    LOCATION_SEARCH = "location_search"
    AMENITY_PROXIMITY = "amenity_proximity"
    COMMUTE_BASED = "commute_based"
    PRICE_RANGE = "price_range"
    PROPERTY_TYPE = "property_type"
    ENVIRONMENTAL = "environmental"
    MIXED = "mixed"


@dataclass
class ParsedEntity:
    """Represents an extracted entity from natural language text"""
    entity_type: str
    value: Any
    confidence: float
    original_text: str
    start_pos: int
    end_pos: int


@dataclass
class SearchSuggestion:
    """Represents an autocomplete suggestion"""
    text: str
    description: str
    category: str
    filters: Optional[Dict[str, Any]] = None
    confidence: float = 1.0


class NLPService:
    """Service for natural language processing of search queries"""
    
    def __init__(self):
        self._initialize_patterns()
        self._initialize_suggestions()
    
    def _initialize_patterns(self):
        """Initialize regex patterns for entity extraction"""
        
        # Distance patterns - order matters! More specific patterns first
        self.distance_patterns = [
            (r'(\d+(?:\.\d+)?)\s*(minute|minutes|min)\s*walk', 'walking_distance'),
            (r'walking distance of (\d+(?:\.\d+)?)\s*(minute|minutes|min)', 'walking_distance'),
            (r'within (\d+(?:\.\d+)?)\s*(m\b|meter|meters|km|kilometer|kilometers|mile|miles)', 'distance'),
            (r'(\d+(?:\.\d+)?)\s*(m\b|meter|meters|km|kilometer|kilometers|mile|miles) from', 'distance'),
        ]
        
        # Price patterns
        self.price_patterns = [
            (r'under £?(\d{1,3}(?:,\d{3})*(?:k|K)?)', 'max_price'),
            (r'below £?(\d{1,3}(?:,\d{3})*(?:k|K)?)', 'max_price'),
            (r'up to £?(\d{1,3}(?:,\d{3})*(?:k|K)?)', 'max_price'),
            (r'over £?(\d{1,3}(?:,\d{3})*(?:k|K)?)', 'min_price'),
            (r'above £?(\d{1,3}(?:,\d{3})*(?:k|K)?)', 'min_price'),
            (r'£?(\d{1,3}(?:,\d{3})*(?:k|K)?)\s*-\s*£?(\d{1,3}(?:,\d{3})*(?:k|K)?)', 'price_range'),
            (r'between £?(\d{1,3}(?:,\d{3})*(?:k|K)?)\s*and\s*£?(\d{1,3}(?:,\d{3})*(?:k|K)?)', 'price_range'),
        ]
        
        # Bedroom patterns
        self.bedroom_patterns = [
            (r'(\d+)\s*bed(?:room)?s?', 'bedrooms'),
            (r'(\d+)br?', 'bedrooms'),
        ]
        
        # Amenity patterns - mapping natural language to AmenityType
        self.amenity_mappings = {
            # Transport
            'train station': AmenityType.TRAIN_STATION,
            'railway station': AmenityType.TRAIN_STATION,
            'tube station': AmenityType.UNDERGROUND_STATION,
            'underground station': AmenityType.UNDERGROUND_STATION,
            'metro station': AmenityType.UNDERGROUND_STATION,
            'bus stop': AmenityType.BUS_STOP,
            
            # Green spaces
            'park': AmenityType.PARK,
            'parks': AmenityType.PARK,
            'green space': AmenityType.GREEN_SPACE,
            'green spaces': AmenityType.GREEN_SPACE,
            
            # Fitness
            'gym': AmenityType.GYM,
            'fitness center': AmenityType.GYM,
            'fitness centre': AmenityType.GYM,
            
            # Education
            'school': AmenityType.SCHOOL,
            'schools': AmenityType.SCHOOL,
            
            # Healthcare
            'hospital': AmenityType.HOSPITAL,
            'pharmacy': AmenityType.PHARMACY,
            
            # Shopping
            'shopping center': AmenityType.SHOPPING_CENTER,
            'shopping centre': AmenityType.SHOPPING_CENTER,
            'supermarket': AmenityType.SUPERMARKET,
            'grocery store': AmenityType.SUPERMARKET,
            
            # Services
            'library': AmenityType.LIBRARY,
            'post office': AmenityType.POST_OFFICE,
            'restaurant': AmenityType.RESTAURANT,
            'restaurants': AmenityType.RESTAURANT,
        }
        
        # Property type patterns
        self.property_type_mappings = {
            'flat': PropertyType.FLAT,
            'flats': PropertyType.FLAT,
            'apartment': PropertyType.FLAT,
            'apartments': PropertyType.FLAT,
            'house': PropertyType.HOUSE,
            'houses': PropertyType.HOUSE,
            'terraced house': PropertyType.HOUSE,
            'terrace': PropertyType.HOUSE,
            'semi-detached': PropertyType.HOUSE,
            'semi detached': PropertyType.HOUSE,
            'detached house': PropertyType.HOUSE,
            'detached': PropertyType.HOUSE,
            'bungalow': PropertyType.BUNGALOW,
            'maisonette': PropertyType.MAISONETTE,
            'land': PropertyType.LAND,
        }
        
        # Location patterns (UK postcodes and areas)
        self.postcode_pattern = r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b'
        self.area_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
    
    def _initialize_suggestions(self):
        """Initialize common search suggestions and examples"""
        
        self.suggestion_templates = [
            # Location-based suggestions
            SearchSuggestion(
                text="near {location}",
                description="Search for properties in a specific area",
                category="location",
                filters={"areas": ["{location}"]}
            ),
            
            # Amenity-based suggestions
            SearchSuggestion(
                text="within 10 minutes walk of a train station",
                description="Properties close to public transport",
                category="transport",
                filters={
                    "amenity_filters": [{
                        "amenity_type": "train_station",
                        "max_distance": 0.8,  # ~10 min walk
                        "distance_unit": "kilometers",
                        "walking_distance": True
                    }]
                }
            ),
            SearchSuggestion(
                text="near parks and green spaces",
                description="Properties close to outdoor recreation",
                category="lifestyle",
                filters={
                    "amenity_filters": [{
                        "amenity_type": "park",
                        "max_distance": 1.0,
                        "distance_unit": "kilometers"
                    }]
                }
            ),
            SearchSuggestion(
                text="close to gyms and fitness centers",
                description="Properties near fitness facilities",
                category="lifestyle",
                filters={
                    "amenity_filters": [{
                        "amenity_type": "gym",
                        "max_distance": 2.0,
                        "distance_unit": "kilometers"
                    }]
                }
            ),
            
            # Price-based suggestions
            SearchSuggestion(
                text="under £500k",
                description="Properties below £500,000",
                category="price",
                filters={"max_price": 500000}
            ),
            SearchSuggestion(
                text="between £300k and £600k",
                description="Properties in mid-range price bracket",
                category="price",
                filters={"min_price": 300000, "max_price": 600000}
            ),
            
            # Property type suggestions
            SearchSuggestion(
                text="2 bedroom flats",
                description="Two bedroom apartments",
                category="property_type",
                filters={
                    "property_types": ["flat"],
                    "min_bedrooms": 2,
                    "max_bedrooms": 2
                }
            ),
            SearchSuggestion(
                text="family houses with gardens",
                description="Houses suitable for families",
                category="property_type",
                filters={
                    "property_types": ["house", "bungalow"],
                    "min_bedrooms": 3,
                    "must_have_garden": True
                }
            ),
            
            # Commute-based suggestions
            SearchSuggestion(
                text="30 minutes to Central London",
                description="Properties with good commute to city center",
                category="commute",
                filters={
                    "commute_filters": [{
                        "destination_address": "Central London",
                        "max_commute_minutes": 30,
                        "transport_modes": ["public_transport"]
                    }]
                }
            ),
            
            # Environmental suggestions
            SearchSuggestion(
                text="quiet areas with low pollution",
                description="Properties in peaceful, clean environments",
                category="environmental",
                filters={
                    "environmental_filters": {
                        "max_air_pollution_level": 3,
                        "max_noise_level": 3,
                        "avoid_flood_risk": True
                    }
                }
            ),
        ]
    
    def parse_query(self, query: str) -> Tuple[SearchCriteria, List[ParsedEntity]]:
        """
        Parse a natural language query into structured SearchCriteria.
        
        Args:
            query: The natural language search query
            
        Returns:
            Tuple of (SearchCriteria, List of ParsedEntity)
        """
        query = query.lower().strip()
        entities = []
        criteria_dict = {}
        
        # Extract price information
        price_entities = self._extract_prices(query)
        entities.extend(price_entities)
        for entity in price_entities:
            if entity.entity_type == 'max_price':
                criteria_dict['max_price'] = entity.value
            elif entity.entity_type == 'min_price':
                criteria_dict['min_price'] = entity.value
            elif entity.entity_type == 'price_range':
                criteria_dict['min_price'] = entity.value[0]
                criteria_dict['max_price'] = entity.value[1]
        
        # Extract bedroom information
        bedroom_entities = self._extract_bedrooms(query)
        entities.extend(bedroom_entities)
        for entity in bedroom_entities:
            if entity.entity_type == 'bedrooms':
                criteria_dict['min_bedrooms'] = entity.value
                criteria_dict['max_bedrooms'] = entity.value
        
        # Extract amenity information
        amenity_entities = self._extract_amenities(query)
        entities.extend(amenity_entities)
        if amenity_entities:
            criteria_dict['amenity_filters'] = []
            for entity in amenity_entities:
                amenity_filter = AmenityFilter(
                    amenity_type=entity.value['amenity_type'],
                    max_distance=entity.value.get('max_distance', 2.0),
                    distance_unit=entity.value.get('distance_unit', DistanceUnit.KILOMETERS),
                    walking_distance=entity.value.get('walking_distance', False),
                    required=True
                )
                criteria_dict['amenity_filters'].append(amenity_filter)
        
        # Extract property type information
        property_type_entities = self._extract_property_types(query)
        entities.extend(property_type_entities)
        if property_type_entities:
            criteria_dict['property_types'] = [entity.value for entity in property_type_entities]
        
        # Extract location information
        location_entities = self._extract_locations(query)
        entities.extend(location_entities)
        if location_entities:
            areas = [entity.value for entity in location_entities if entity.entity_type == 'area']
            if areas:
                criteria_dict['areas'] = areas
        
        # Extract commute information
        commute_entities = self._extract_commute_info(query)
        entities.extend(commute_entities)
        if commute_entities:
            criteria_dict['commute_filters'] = []
            for entity in commute_entities:
                commute_filter = CommuteFilter(
                    destination_address=entity.value['destination'],
                    max_commute_minutes=entity.value['max_minutes'],
                    transport_modes=entity.value.get('transport_modes', [TransportMode.PUBLIC_TRANSPORT])
                )
                criteria_dict['commute_filters'].append(commute_filter)
        
        # Create SearchCriteria object
        try:
            search_criteria = SearchCriteria(**criteria_dict)
        except Exception as e:
            # If validation fails, create a basic criteria object
            search_criteria = SearchCriteria()
        
        return search_criteria, entities
    
    def _extract_prices(self, query: str) -> List[ParsedEntity]:
        """Extract price information from query"""
        entities = []
        
        for pattern, price_type in self.price_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                if price_type == 'price_range':
                    # Handle price range (two values)
                    min_price = self._parse_price_value(match.group(1))
                    max_price = self._parse_price_value(match.group(2))
                    entities.append(ParsedEntity(
                        entity_type='price_range',
                        value=(min_price, max_price),
                        confidence=0.9,
                        original_text=match.group(0),
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
                else:
                    # Handle single price value
                    price_value = self._parse_price_value(match.group(1))
                    entities.append(ParsedEntity(
                        entity_type=price_type,
                        value=price_value,
                        confidence=0.9,
                        original_text=match.group(0),
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
        
        return entities
    
    def _parse_price_value(self, price_str: str) -> int:
        """Convert price string to integer value"""
        # Remove commas and convert k/K to thousands
        price_str = price_str.replace(',', '')
        if price_str.lower().endswith('k'):
            return int(float(price_str[:-1]) * 1000)
        return int(price_str)
    
    def _extract_bedrooms(self, query: str) -> List[ParsedEntity]:
        """Extract bedroom count from query"""
        entities = []
        
        for pattern, entity_type in self.bedroom_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                bedroom_count = int(match.group(1))
                entities.append(ParsedEntity(
                    entity_type=entity_type,
                    value=bedroom_count,
                    confidence=0.95,
                    original_text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return entities
    
    def _extract_amenities(self, query: str) -> List[ParsedEntity]:
        """Extract amenity requirements from query"""
        entities = []
        
        for amenity_text, amenity_type in self.amenity_mappings.items():
            if amenity_text in query:
                # Look for distance modifiers near the amenity
                distance_info = self._extract_distance_for_amenity(query, amenity_text)
                
                amenity_value = {
                    'amenity_type': amenity_type,
                    **distance_info
                }
                
                entities.append(ParsedEntity(
                    entity_type='amenity',
                    value=amenity_value,
                    confidence=0.8,
                    original_text=amenity_text,
                    start_pos=query.find(amenity_text),
                    end_pos=query.find(amenity_text) + len(amenity_text)
                ))
        
        return entities
    
    def _extract_distance_for_amenity(self, query: str, amenity_text: str) -> Dict[str, Any]:
        """Extract distance information related to a specific amenity"""
        distance_info = {}
        
        # Look for distance patterns near the amenity mention
        amenity_pos = query.find(amenity_text)
        context_start = max(0, amenity_pos - 50)
        context_end = min(len(query), amenity_pos + len(amenity_text) + 50)
        context = query[context_start:context_end]
        
        for pattern, distance_type in self.distance_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                if distance_type == 'walking_distance':
                    # Convert minutes to approximate distance (assuming 5 km/h walking speed)
                    minutes = float(match.group(1))
                    distance_km = (minutes / 60) * 5  # 5 km/h walking speed
                    distance_info.update({
                        'max_distance': distance_km,
                        'distance_unit': DistanceUnit.KILOMETERS,
                        'walking_distance': True
                    })
                else:
                    # Regular distance
                    distance_value = float(match.group(1))
                    unit = match.group(2).lower()
                    
                    # Normalize to kilometers
                    if unit.startswith('m') and not unit.startswith('mile'):
                        distance_km = distance_value / 1000
                    elif unit.startswith('mile'):
                        distance_km = distance_value * 1.609344  # Exact conversion
                    else:
                        distance_km = distance_value
                    
                    distance_info.update({
                        'max_distance': distance_km,
                        'distance_unit': DistanceUnit.KILOMETERS,
                        'walking_distance': False
                    })
                break
        
        # Default distance if none specified
        if 'max_distance' not in distance_info:
            distance_info.update({
                'max_distance': 2.0,  # Default 2km
                'distance_unit': DistanceUnit.KILOMETERS,
                'walking_distance': False
            })
        
        return distance_info
    
    def _extract_property_types(self, query: str) -> List[ParsedEntity]:
        """Extract property type preferences from query"""
        entities = []
        
        for property_text, property_type in self.property_type_mappings.items():
            if property_text in query:
                entities.append(ParsedEntity(
                    entity_type='property_type',
                    value=property_type,
                    confidence=0.9,
                    original_text=property_text,
                    start_pos=query.find(property_text),
                    end_pos=query.find(property_text) + len(property_text)
                ))
        
        return entities
    
    def _extract_locations(self, query: str) -> List[ParsedEntity]:
        """Extract location information from query"""
        entities = []
        
        # Extract postcodes
        postcode_matches = re.finditer(self.postcode_pattern, query, re.IGNORECASE)
        for match in postcode_matches:
            entities.append(ParsedEntity(
                entity_type='postcode',
                value=match.group(0).upper(),
                confidence=0.95,
                original_text=match.group(0),
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Extract area names (simplified - in production would use gazetteer)
        area_matches = re.finditer(self.area_pattern, query)
        for match in area_matches:
            area_name = match.group(0)
            # Simple heuristic: if it's capitalized and not a common word, it might be a place
            if area_name not in ['Near', 'Close', 'Within', 'From', 'To', 'And', 'The', 'Of']:
                entities.append(ParsedEntity(
                    entity_type='area',
                    value=area_name,
                    confidence=0.6,  # Lower confidence for area names
                    original_text=area_name,
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return entities
    
    def _extract_commute_info(self, query: str) -> List[ParsedEntity]:
        """Extract commute-related information from query"""
        entities = []
        
        # Pattern for commute time to destinations
        commute_patterns = [
            (r'(\d+)\s*(?:minute|minutes|min)\s*to\s+([A-Za-z\s]+)', 'commute_time'),
            (r'commute\s*(?:of|under)?\s*(\d+)\s*(?:minute|minutes|min)\s*to\s+([A-Za-z\s]+)', 'commute_time'),
        ]
        
        for pattern, entity_type in commute_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                max_minutes = int(match.group(1))
                destination = match.group(2).strip().title()  # Capitalize properly
                
                entities.append(ParsedEntity(
                    entity_type='commute',
                    value={
                        'max_minutes': max_minutes,
                        'destination': destination,
                        'transport_modes': [TransportMode.PUBLIC_TRANSPORT]
                    },
                    confidence=0.8,
                    original_text=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        
        return entities
    
    def get_autocomplete_suggestions(self, partial_query: str, limit: int = 10) -> List[SearchSuggestion]:
        """
        Generate autocomplete suggestions based on partial query input.
        
        Args:
            partial_query: The partial search query
            limit: Maximum number of suggestions to return
            
        Returns:
            List of SearchSuggestion objects
        """
        suggestions = []
        query_lower = partial_query.lower().strip()
        
        if not query_lower:
            # Return popular suggestions when query is empty
            return self.suggestion_templates[:limit]
        
        # Score suggestions based on relevance to partial query
        for suggestion in self.suggestion_templates:
            score = self._calculate_suggestion_score(query_lower, suggestion)
            if score > 0:
                suggestion_copy = SearchSuggestion(
                    text=suggestion.text,
                    description=suggestion.description,
                    category=suggestion.category,
                    filters=suggestion.filters,
                    confidence=score
                )
                suggestions.append(suggestion_copy)
        
        # Sort by confidence score and return top results
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        return suggestions[:limit]
    
    def _calculate_suggestion_score(self, query: str, suggestion: SearchSuggestion) -> float:
        """Calculate relevance score for a suggestion given the partial query"""
        suggestion_text = suggestion.text.lower()
        
        # Exact match gets highest score
        if query in suggestion_text:
            return 1.0
        
        # Check for word matches
        query_words = query.split()
        suggestion_words = suggestion_text.split()
        
        matching_words = sum(1 for word in query_words if word in suggestion_words)
        if matching_words > 0:
            return matching_words / len(query_words) * 0.8
        
        # Check for partial word matches
        partial_matches = sum(1 for word in query_words 
                            if any(word in s_word for s_word in suggestion_words))
        if partial_matches > 0:
            return partial_matches / len(query_words) * 0.5
        
        return 0.0
    
    def get_search_examples(self) -> List[str]:
        """Get example search queries to show users"""
        return [
            "2 bedroom flat near train station under £400k",
            "house with garden within 30 minutes to Central London",
            "quiet area near parks under £600k",
            "3 bed house close to good schools",
            "flat near gym and supermarket",
            "property with parking near tube station",
        ]
    
    def detect_query_intent(self, query: str) -> QueryIntent:
        """Detect the primary intent of a search query"""
        query_lower = query.lower()
        
        # Count different types of entities
        has_location = bool(re.search(self.postcode_pattern, query, re.IGNORECASE) or 
                           any(area in query_lower for area in ['london', 'manchester', 'birmingham']))
        has_amenity = any(amenity in query_lower for amenity in self.amenity_mappings.keys())
        has_price = any(re.search(pattern, query, re.IGNORECASE) for pattern, _ in self.price_patterns)
        has_property_type = any(prop_type in query_lower for prop_type in self.property_type_mappings.keys())
        has_commute = 'commute' in query_lower or 'minutes to' in query_lower
        
        # Determine primary intent
        intent_count = sum([has_location, has_amenity, has_price, has_property_type, has_commute])
        
        if intent_count > 2:
            return QueryIntent.MIXED
        elif has_commute:
            return QueryIntent.COMMUTE_BASED
        elif has_amenity:
            return QueryIntent.AMENITY_PROXIMITY
        elif has_location:
            return QueryIntent.LOCATION_SEARCH
        elif has_price:
            return QueryIntent.PRICE_RANGE
        elif has_property_type:
            return QueryIntent.PROPERTY_TYPE
        else:
            return QueryIntent.LOCATION_SEARCH  # Default