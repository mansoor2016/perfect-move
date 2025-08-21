"""
Property deduplication service using fuzzy address matching and geocoding
"""
import logging
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from fuzzywuzzy import fuzz
from geopy.distance import geodesic
import re

logger = logging.getLogger(__name__)


@dataclass
class PropertyMatch:
    """Represents a potential duplicate property match"""
    property1_id: str
    property2_id: str
    similarity_score: float
    match_reasons: List[str]
    confidence: str  # 'high', 'medium', 'low'


class PropertyDeduplicator:
    """Service for identifying and handling duplicate properties"""
    
    def __init__(self, 
                 address_similarity_threshold: float = 0.85,
                 coordinate_distance_threshold: float = 0.05,  # 50 meters
                 price_difference_threshold: float = 0.1):  # 10%
        self.address_similarity_threshold = address_similarity_threshold
        self.coordinate_distance_threshold = coordinate_distance_threshold
        self.price_difference_threshold = price_difference_threshold
    
    def find_duplicates(self, properties: List[Dict]) -> List[PropertyMatch]:
        """Find potential duplicate properties in a list"""
        matches = []
        
        for i, prop1 in enumerate(properties):
            for j, prop2 in enumerate(properties[i+1:], i+1):
                match = self._compare_properties(prop1, prop2)
                if match:
                    matches.append(match)
        
        return matches
    
    def deduplicate_properties(self, properties: List[Dict]) -> List[Dict]:
        """Remove duplicates from property list, keeping the best version"""
        if len(properties) <= 1:
            return properties
        
        # Find all potential matches
        matches = self.find_duplicates(properties)
        
        # Group properties that are duplicates of each other
        duplicate_groups = self._group_duplicates(properties, matches)
        
        # Keep the best property from each group
        deduplicated = []
        processed_ids = set()
        
        for group in duplicate_groups:
            if not any(prop['source_id'] in processed_ids for prop in group):
                best_property = self._select_best_property(group)
                deduplicated.append(best_property)
                processed_ids.update(prop['source_id'] for prop in group)
        
        # Add properties that weren't part of any duplicate group
        for prop in properties:
            if prop['source_id'] not in processed_ids:
                deduplicated.append(prop)
        
        logger.info(f"Deduplicated {len(properties)} properties to {len(deduplicated)}")
        return deduplicated
    
    def _compare_properties(self, prop1: Dict, prop2: Dict) -> Optional[PropertyMatch]:
        """Compare two properties and return match if they're likely duplicates"""
        similarity_score = 0.0
        match_reasons = []
        
        # Don't compare properties from the same source with same ID
        if (prop1.get('source') == prop2.get('source') and 
            prop1.get('source_id') == prop2.get('source_id')):
            return None
        
        # Address similarity
        address_score = self._calculate_address_similarity(
            prop1.get('address', ''), 
            prop2.get('address', '')
        )
        if address_score > self.address_similarity_threshold:
            similarity_score += address_score * 0.4
            match_reasons.append(f"Similar address ({address_score:.2f})")
        
        # Coordinate proximity
        coord_score = self._calculate_coordinate_similarity(prop1, prop2)
        if coord_score > 0:
            similarity_score += coord_score * 0.3
            match_reasons.append(f"Close coordinates ({coord_score:.2f})")
        
        # Price similarity
        price_score = self._calculate_price_similarity(prop1, prop2)
        if price_score > 0:
            similarity_score += price_score * 0.2
            match_reasons.append(f"Similar price ({price_score:.2f})")
        
        # Property characteristics similarity
        char_score = self._calculate_characteristics_similarity(prop1, prop2)
        if char_score > 0:
            similarity_score += char_score * 0.1
            match_reasons.append(f"Similar characteristics ({char_score:.2f})")
        
        # Determine if this is a match
        if similarity_score > 0.7:
            confidence = 'high' if similarity_score > 0.9 else 'medium'
            return PropertyMatch(
                property1_id=prop1.get('source_id', ''),
                property2_id=prop2.get('source_id', ''),
                similarity_score=similarity_score,
                match_reasons=match_reasons,
                confidence=confidence
            )
        
        return None
    
    def _calculate_address_similarity(self, address1: str, address2: str) -> float:
        """Calculate similarity between two addresses"""
        if not address1 or not address2:
            return 0.0
        
        # Normalize addresses
        addr1_norm = self._normalize_address(address1)
        addr2_norm = self._normalize_address(address2)
        
        # Use multiple fuzzy matching algorithms
        ratio = fuzz.ratio(addr1_norm, addr2_norm) / 100.0
        partial_ratio = fuzz.partial_ratio(addr1_norm, addr2_norm) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(addr1_norm, addr2_norm) / 100.0
        
        # Return the best score
        return max(ratio, partial_ratio, token_sort_ratio)
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address for comparison"""
        if not address:
            return ""
        
        # Convert to lowercase
        normalized = address.lower()
        
        # Remove common abbreviations and standardize
        replacements = {
            r'\bst\b': 'street',
            r'\brd\b': 'road',
            r'\bave\b': 'avenue',
            r'\bdr\b': 'drive',
            r'\bln\b': 'lane',
            r'\bpl\b': 'place',
            r'\bct\b': 'court',
            r'\bapt\b': 'apartment',
            r'\bflat\b': 'apartment',
        }
        
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Remove extra whitespace and punctuation
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_coordinate_similarity(self, prop1: Dict, prop2: Dict) -> float:
        """Calculate similarity based on coordinates"""
        lat1, lon1 = prop1.get('latitude'), prop1.get('longitude')
        lat2, lon2 = prop2.get('latitude'), prop2.get('longitude')
        
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0
        
        try:
            distance = geodesic((lat1, lon1), (lat2, lon2)).kilometers
            
            # Convert distance to similarity score (closer = higher score)
            if distance <= self.coordinate_distance_threshold:
                # Perfect match if within threshold
                return 1.0 - (distance / self.coordinate_distance_threshold) * 0.2
            elif distance <= 0.5:  # Within 500m
                return 0.8 - (distance / 0.5) * 0.3
            elif distance <= 1.0:  # Within 1km
                return 0.5 - (distance / 1.0) * 0.3
            else:
                return 0.0
                
        except Exception as e:
            logger.warning(f"Error calculating distance: {e}")
            return 0.0
    
    def _calculate_price_similarity(self, prop1: Dict, prop2: Dict) -> float:
        """Calculate similarity based on price"""
        price1 = prop1.get('price')
        price2 = prop2.get('price')
        
        if not price1 or not price2:
            return 0.0
        
        try:
            price1, price2 = float(price1), float(price2)
            
            # Calculate percentage difference
            avg_price = (price1 + price2) / 2
            price_diff = abs(price1 - price2) / avg_price
            
            if price_diff <= self.price_difference_threshold:
                return 1.0 - (price_diff / self.price_difference_threshold) * 0.5
            elif price_diff <= 0.3:  # Within 30%
                return 0.5 - ((price_diff - self.price_difference_threshold) / 0.2) * 0.3
            else:
                return 0.0
                
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def _calculate_characteristics_similarity(self, prop1: Dict, prop2: Dict) -> float:
        """Calculate similarity based on property characteristics"""
        score = 0.0
        comparisons = 0
        
        # Compare bedrooms
        if prop1.get('bedrooms') and prop2.get('bedrooms'):
            if prop1['bedrooms'] == prop2['bedrooms']:
                score += 1.0
            comparisons += 1
        
        # Compare bathrooms
        if prop1.get('bathrooms') and prop2.get('bathrooms'):
            if prop1['bathrooms'] == prop2['bathrooms']:
                score += 1.0
            comparisons += 1
        
        # Compare property type
        if prop1.get('property_type') and prop2.get('property_type'):
            if prop1['property_type'].lower() == prop2['property_type'].lower():
                score += 1.0
            comparisons += 1
        
        return score / comparisons if comparisons > 0 else 0.0
    
    def _group_duplicates(self, properties: List[Dict], 
                         matches: List[PropertyMatch]) -> List[List[Dict]]:
        """Group properties that are duplicates of each other"""
        # Create a mapping from source_id to property
        prop_map = {prop['source_id']: prop for prop in properties}
        
        # Build adjacency list of matches
        adjacency = {}
        for match in matches:
            if match.confidence in ['high', 'medium']:
                if match.property1_id not in adjacency:
                    adjacency[match.property1_id] = []
                if match.property2_id not in adjacency:
                    adjacency[match.property2_id] = []
                
                adjacency[match.property1_id].append(match.property2_id)
                adjacency[match.property2_id].append(match.property1_id)
        
        # Find connected components (groups of duplicates)
        visited = set()
        groups = []
        
        for prop_id in adjacency:
            if prop_id not in visited:
                group = []
                self._dfs_group(prop_id, adjacency, visited, group)
                if len(group) > 1:
                    # Convert IDs back to property objects
                    prop_group = [prop_map[pid] for pid in group if pid in prop_map]
                    if len(prop_group) > 1:
                        groups.append(prop_group)
        
        return groups
    
    def _dfs_group(self, prop_id: str, adjacency: Dict, visited: Set, group: List):
        """Depth-first search to find connected duplicate properties"""
        visited.add(prop_id)
        group.append(prop_id)
        
        for neighbor in adjacency.get(prop_id, []):
            if neighbor not in visited:
                self._dfs_group(neighbor, adjacency, visited, group)
    
    def _select_best_property(self, duplicate_group: List[Dict]) -> Dict:
        """Select the best property from a group of duplicates"""
        if len(duplicate_group) == 1:
            return duplicate_group[0]
        
        # Score each property based on data quality
        best_property = None
        best_score = -1
        
        for prop in duplicate_group:
            score = self._calculate_quality_score(prop)
            if score > best_score:
                best_score = score
                best_property = prop
        
        return best_property or duplicate_group[0]
    
    def _calculate_quality_score(self, prop: Dict) -> float:
        """Calculate data quality score for a property"""
        score = 0.0
        
        # Reliability score from source
        score += prop.get('reliability_score', 0.5) * 0.3
        
        # Completeness score
        required_fields = ['price', 'address', 'bedrooms', 'property_type']
        optional_fields = ['description', 'bathrooms', 'image_urls', 'floor_area']
        
        required_complete = sum(1 for field in required_fields if prop.get(field))
        optional_complete = sum(1 for field in optional_fields if prop.get(field))
        
        completeness = (required_complete / len(required_fields)) * 0.7 + \
                      (optional_complete / len(optional_fields)) * 0.3
        score += completeness * 0.4
        
        # Recency score (prefer more recent data)
        last_updated = prop.get('last_updated')
        if last_updated:
            # This would need proper datetime handling in real implementation
            score += 0.2
        
        # Source preference (could be configured)
        source_scores = {'rightmove': 0.6, 'zoopla': 0.5}
        score += source_scores.get(prop.get('source', ''), 0.3) * 0.1
        
        return score