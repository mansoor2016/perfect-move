from typing import List, Dict, Any
from datetime import datetime, timezone
from app.models.search import SearchCriteria, SearchResultProperty, SortOption
import logging
import math

logger = logging.getLogger(__name__)


class RankingEngine:
    """Engine for ranking and scoring property search results"""
    
    def __init__(self):
        # Configurable weights for different ranking factors
        self.weights = {
            "price_score": 0.25,      # How well price matches user's likely budget
            "match_score": 0.30,      # Elasticsearch relevance score
            "proximity_score": 0.20,  # Distance from search center
            "freshness_score": 0.15,  # How recently updated
            "quality_score": 0.10     # Property quality indicators
        }
    
    async def rank_properties(
        self, 
        properties: List[SearchResultProperty], 
        criteria: SearchCriteria
    ) -> List[SearchResultProperty]:
        """Rank properties using combined scoring algorithm"""
        
        if not properties:
            return properties
        
        # Calculate individual scores for each property
        for prop in properties:
            prop.match_score = await self._calculate_combined_score(prop, criteria, properties)
        
        # Sort by match score (unless specific sort order requested)
        if criteria.sort_by == SortOption.RELEVANCE:
            properties.sort(key=lambda p: p.match_score, reverse=True)
        elif criteria.sort_by == SortOption.DISTANCE and criteria.center_latitude:
            properties.sort(key=lambda p: p.distance_km or float('inf'))
        # Other sort options are handled by Elasticsearch
        
        return properties
    
    async def _calculate_combined_score(
        self, 
        property_obj: SearchResultProperty, 
        criteria: SearchCriteria,
        all_properties: List[SearchResultProperty]
    ) -> float:
        """Calculate combined ranking score for a property"""
        
        scores = {}
        
        # 1. Price score - how well does price match expected range
        scores["price_score"] = self._calculate_price_score(property_obj, criteria, all_properties)
        
        # 2. Match score - use existing Elasticsearch score (already normalized)
        scores["match_score"] = property_obj.match_score
        
        # 3. Proximity score - distance from search center
        scores["proximity_score"] = self._calculate_proximity_score(property_obj, criteria)
        
        # 4. Freshness score - how recently updated
        scores["freshness_score"] = self._calculate_freshness_score(property_obj)
        
        # 5. Quality score - property quality indicators
        scores["quality_score"] = self._calculate_quality_score(property_obj)
        
        # Combine scores using weights
        combined_score = sum(
            scores[factor] * self.weights[factor] 
            for factor in scores
        )
        
        # Apply bonus/penalty modifiers
        combined_score = self._apply_modifiers(combined_score, property_obj, criteria)
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, combined_score))
    
    def _calculate_price_score(
        self, 
        property_obj: SearchResultProperty, 
        criteria: SearchCriteria,
        all_properties: List[SearchResultProperty]
    ) -> float:
        """Calculate price attractiveness score"""
        
        price = property_obj.price
        
        # If user specified price range, score based on position within range
        if criteria.min_price is not None and criteria.max_price is not None:
            price_range = criteria.max_price - criteria.min_price
            if price_range > 0 and price is not None:
                # Score higher for properties in lower part of user's range
                position = (price - criteria.min_price) / price_range
                return max(0.0, 1.0 - position)  # Lower price = higher score
        
        # If only min price specified
        elif criteria.min_price is not None:
            if price is not None and price >= criteria.min_price:
                # Score based on how close to minimum (prefer lower prices)
                excess = price - criteria.min_price
                max_reasonable_excess = criteria.min_price * 0.5  # 50% above min
                if max_reasonable_excess > 0:
                    return max(0.0, 1.0 - (excess / max_reasonable_excess))
                else:
                    return 1.0
            else:
                return 0.0  # Below minimum or None price
        
        # If only max price specified
        elif criteria.max_price is not None:
            if price is not None and price <= criteria.max_price:
                # Score based on how much below maximum
                if criteria.max_price > 0:
                    return price / criteria.max_price
                else:
                    return 0.5
            else:
                return 0.0  # Above maximum or None price
        
        # No price criteria - use relative pricing within result set
        else:
            if len(all_properties) > 1:
                prices = [p.price for p in all_properties]
                min_price = min(prices)
                max_price = max(prices)
                
                if max_price > min_price:
                    # Normalize price within result set (lower = better)
                    normalized = (price - min_price) / (max_price - min_price)
                    return 1.0 - normalized
            
            return 0.5  # Neutral score if can't determine
    
    def _calculate_proximity_score(
        self, 
        property_obj: SearchResultProperty, 
        criteria: SearchCriteria
    ) -> float:
        """Calculate proximity score based on distance from search center"""
        
        if property_obj.distance_km is None:
            return 0.5  # Neutral score if no distance available
        
        # Score decreases with distance
        max_reasonable_distance = criteria.radius_km if criteria.radius_km else 20.0
        
        if property_obj.distance_km <= max_reasonable_distance:
            # Linear decay from 1.0 at distance 0 to 0.0 at max distance
            return 1.0 - (property_obj.distance_km / max_reasonable_distance)
        else:
            return 0.0  # Too far away
    
    def _calculate_freshness_score(self, property_obj: SearchResultProperty) -> float:
        """Calculate freshness score based on when property was last updated"""
        
        now = datetime.now(timezone.utc)
        updated_at = property_obj.updated_at.replace(tzinfo=timezone.utc)
        
        days_old = (now - updated_at).days
        
        # Score decreases over time
        if days_old <= 7:
            return 1.0  # Very fresh
        elif days_old <= 30:
            return 0.8  # Recent
        elif days_old <= 90:
            return 0.6  # Moderately fresh
        elif days_old <= 180:
            return 0.4  # Getting old
        elif days_old <= 365:
            return 0.2  # Old
        else:
            return 0.1  # Very old
    
    def _calculate_quality_score(self, property_obj: SearchResultProperty) -> float:
        """Calculate quality score based on property characteristics"""
        
        score = 0.5  # Base score
        
        # Energy rating bonus
        energy_ratings = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2, "F": 0.1, "G": 0.0}
        if property_obj.energy_rating and property_obj.energy_rating in energy_ratings:
            score += energy_ratings[property_obj.energy_rating] * 0.2
        
        # Feature bonuses
        feature_bonuses = {
            "garden": 0.1,
            "parking": 0.1,
            "balcony": 0.05,
            "gym": 0.05,
            "concierge": 0.05,
            "lift": 0.03,
            "security": 0.03
        }
        
        for feature in property_obj.features:
            feature_lower = feature.lower()
            for bonus_feature, bonus in feature_bonuses.items():
                if bonus_feature in feature_lower:
                    score += bonus
                    break
        
        # Property type adjustments
        if property_obj.property_type.value == "house":
            score += 0.1  # Houses often preferred
        
        # Size bonus (if available)
        if property_obj.floor_area_sqft:
            # Bonus for reasonable size (not too small, not excessively large)
            if 500 <= property_obj.floor_area_sqft <= 2000:
                size_score = 1.0 - abs(property_obj.floor_area_sqft - 1000) / 1000
                score += size_score * 0.1
        
        # Reliability score from data source
        if property_obj.lineage.reliability_score:
            score += property_obj.lineage.reliability_score * 0.1
        
        return min(1.0, score)
    
    def _apply_modifiers(
        self, 
        base_score: float, 
        property_obj: SearchResultProperty, 
        criteria: SearchCriteria
    ) -> float:
        """Apply bonus/penalty modifiers to the base score"""
        
        score = base_score
        
        # Bonus for exact matches on key criteria
        if criteria.property_types:
            if property_obj.property_type in criteria.property_types:
                score += 0.05  # Small bonus for exact type match
        
        # Bonus for having required features
        if criteria.must_have_garden and property_obj.garden:
            score += 0.1
        
        if criteria.must_have_parking and property_obj.parking:
            score += 0.1
        
        # Penalty for missing common desirable features
        if not property_obj.garden and not property_obj.parking:
            score -= 0.05  # Small penalty for no garden or parking
        
        # Bonus for properties with many matched filters
        if len(property_obj.matched_filters) > 3:
            score += 0.05 * (len(property_obj.matched_filters) - 3)
        
        # Price-per-bedroom efficiency bonus
        if property_obj.bedrooms and property_obj.bedrooms > 0 and property_obj.price:
            price_per_bedroom = float(property_obj.price) / float(property_obj.bedrooms)
            
            # Bonus for good value (this is very rough and would need market data)
            if price_per_bedroom < 200000:  # Rough threshold for good value
                score += 0.05
        
        return score
    
    def get_ranking_explanation(
        self, 
        property_obj: SearchResultProperty, 
        criteria: SearchCriteria,
        all_properties: List[SearchResultProperty]
    ) -> Dict[str, Any]:
        """Get detailed explanation of how a property was ranked"""
        
        # Recalculate individual scores for explanation
        price_score = self._calculate_price_score(property_obj, criteria, all_properties)
        proximity_score = self._calculate_proximity_score(property_obj, criteria)
        freshness_score = self._calculate_freshness_score(property_obj)
        quality_score = self._calculate_quality_score(property_obj)
        
        return {
            "final_score": property_obj.match_score,
            "component_scores": {
                "price_score": price_score,
                "elasticsearch_score": property_obj.match_score,
                "proximity_score": proximity_score,
                "freshness_score": freshness_score,
                "quality_score": quality_score
            },
            "weights": self.weights,
            "matched_filters": [f.filter_name for f in property_obj.matched_filters],
            "quality_factors": {
                "energy_rating": property_obj.energy_rating,
                "features": property_obj.features,
                "reliability_score": property_obj.lineage.reliability_score
            }
        }
    
    def update_weights(self, new_weights: Dict[str, float]):
        """Update ranking weights (for A/B testing or personalization)"""
        
        # Validate weights sum to approximately 1.0
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.1:
            logger.warning(f"Ranking weights sum to {total_weight}, not 1.0")
        
        self.weights.update(new_weights)
        logger.info(f"Updated ranking weights: {self.weights}")
    
    def get_personalized_weights(self, user_preferences: Dict[str, Any]) -> Dict[str, float]:
        """Calculate personalized weights based on user preferences"""
        
        weights = self.weights.copy()
        
        # Adjust weights based on user preferences
        if user_preferences.get("price_sensitive", False):
            weights["price_score"] += 0.1
            weights["quality_score"] -= 0.05
            weights["match_score"] -= 0.05
        
        if user_preferences.get("location_priority", False):
            weights["proximity_score"] += 0.1
            weights["price_score"] -= 0.05
            weights["freshness_score"] -= 0.05
        
        if user_preferences.get("quality_focused", False):
            weights["quality_score"] += 0.1
            weights["price_score"] -= 0.05
            weights["proximity_score"] -= 0.05
        
        # Normalize weights to sum to 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}
        
        return weights