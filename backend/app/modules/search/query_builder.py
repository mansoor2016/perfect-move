from typing import Dict, Any, List, Optional
from app.models.search import (
    SearchCriteria, SortOption, AmenityFilter, ProximityFilter, 
    EnvironmentalFilter, CommuteFilter, DistanceUnit
)
import logging

logger = logging.getLogger(__name__)


class SearchQueryBuilder:
    """Builds complex Elasticsearch queries from search criteria"""
    
    def __init__(self):
        pass
    
    async def build_query(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Build complete Elasticsearch query from search criteria"""
        
        query = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": [],
                    "should": [],
                    "must_not": []
                }
            }
        }
        
        # Add basic filters
        self._add_basic_filters(query, criteria)
        
        # Add location filters
        self._add_location_filters(query, criteria)
        
        # Add lifestyle filters
        self._add_lifestyle_filters(query, criteria)
        
        # Add property feature filters
        self._add_feature_filters(query, criteria)
        
        # Add sorting
        self._add_sorting(query, criteria)
        
        # If no must clauses, add match_all
        if not query["query"]["bool"]["must"]:
            query["query"]["bool"]["must"].append({"match_all": {}})
        
        # Clean up empty clauses
        query["query"]["bool"] = {
            k: v for k, v in query["query"]["bool"].items() 
            if v  # Remove empty lists
        }
        
        logger.debug(f"Built query: {query}")
        return query
    
    def _add_basic_filters(self, query: Dict[str, Any], criteria: SearchCriteria):
        """Add basic property filters (price, type, bedrooms, etc.)"""
        
        bool_query = query["query"]["bool"]
        
        # Price range filter
        price_filter = {}
        if criteria.min_price is not None:
            price_filter["gte"] = criteria.min_price
        if criteria.max_price is not None:
            price_filter["lte"] = criteria.max_price
        
        if price_filter:
            bool_query["filter"].append({
                "range": {"price": price_filter}
            })
        
        # Property types filter
        if criteria.property_types:
            bool_query["filter"].append({
                "terms": {
                    "property_type": [pt.value for pt in criteria.property_types]
                }
            })
        
        # Status filter
        if criteria.status:
            bool_query["filter"].append({
                "terms": {
                    "status": [s.value for s in criteria.status]
                }
            })
        
        # Bedroom range filter
        bedroom_filter = {}
        if criteria.min_bedrooms is not None:
            bedroom_filter["gte"] = criteria.min_bedrooms
        if criteria.max_bedrooms is not None:
            bedroom_filter["lte"] = criteria.max_bedrooms
        
        if bedroom_filter:
            bool_query["filter"].append({
                "range": {"bedrooms": bedroom_filter}
            })
        
        # Bathroom filter
        if criteria.min_bathrooms is not None:
            bool_query["filter"].append({
                "range": {"bathrooms": {"gte": criteria.min_bathrooms}}
            })
        
        # Floor area filter
        if criteria.min_floor_area_sqft is not None:
            bool_query["filter"].append({
                "range": {"floor_area_sqft": {"gte": criteria.min_floor_area_sqft}}
            })
    
    def _add_location_filters(self, query: Dict[str, Any], criteria: SearchCriteria):
        """Add location-based filters"""
        
        bool_query = query["query"]["bool"]
        
        # Coordinate-based radius search
        if (criteria.center_latitude is not None and 
            criteria.center_longitude is not None and 
            criteria.radius_km is not None):
            
            bool_query["filter"].append({
                "geo_distance": {
                    "distance": f"{criteria.radius_km}km",
                    "location.coordinates": {
                        "lat": criteria.center_latitude,
                        "lon": criteria.center_longitude
                    }
                }
            })
        
        # Area-based search
        if criteria.areas:
            # Support both exact area matches and postcode prefixes
            area_queries = []
            
            for area in criteria.areas:
                # Exact area match
                area_queries.append({
                    "term": {"location.area.keyword": area}
                })
                
                # Postcode prefix match
                if len(area) <= 4:  # Likely a postcode prefix
                    area_queries.append({
                        "prefix": {"location.postcode": area.upper()}
                    })
            
            if area_queries:
                bool_query["should"].extend(area_queries)
                # Ensure at least one area matches
                bool_query["filter"].append({
                    "bool": {"should": area_queries, "minimum_should_match": 1}
                })
    
    def _add_lifestyle_filters(self, query: Dict[str, Any], criteria: SearchCriteria):
        """Add lifestyle-based filters (amenities, environment, commute)"""
        
        bool_query = query["query"]["bool"]
        
        # Process amenity filters (both old ProximityFilter and new AmenityFilter)
        all_amenity_filters = []
        
        # Convert legacy proximity filters to amenity filters
        for prox_filter in criteria.proximity_filters:
            amenity_filter = AmenityFilter(
                amenity_type=prox_filter.amenity_type,
                max_distance=prox_filter.max_distance,
                distance_unit=prox_filter.distance_unit,
                walking_distance=prox_filter.walking_distance,
                required=True
            )
            all_amenity_filters.append(amenity_filter)
        
        # Add new amenity filters
        all_amenity_filters.extend(criteria.amenity_filters)
        
        # Process each amenity filter
        for amenity_filter in all_amenity_filters:
            self._add_amenity_filter(bool_query, amenity_filter)
        
        # Environmental filters
        if criteria.environmental_filters:
            self._add_environmental_filters(bool_query, criteria.environmental_filters)
        
        # Commute filters
        for commute_filter in criteria.commute_filters:
            self._add_commute_filter(bool_query, commute_filter)
    
    def _add_amenity_filter(self, bool_query: Dict[str, Any], amenity_filter: AmenityFilter):
        """Add a single amenity filter to the query"""
        
        # For now, we'll use a placeholder approach since we don't have 
        # actual amenity geospatial data indexed yet
        # In a real implementation, this would query against amenity locations
        
        # Add to should clauses to boost properties that mention this amenity
        amenity_name = amenity_filter.amenity_type.value.replace("_", " ")
        
        # Boost properties that mention this amenity in features or description
        bool_query["should"].append({
            "multi_match": {
                "query": amenity_name,
                "fields": ["features^2", "description", "search_text"],
                "boost": 2.0 if amenity_filter.required else 1.0
            }
        })
        
        # If required, add as a filter (for now, just boost heavily)
        if amenity_filter.required:
            bool_query["should"].append({
                "match": {
                    "features": {
                        "query": amenity_name,
                        "boost": 5.0
                    }
                }
            })
    
    def _add_environmental_filters(self, bool_query: Dict[str, Any], env_filter: EnvironmentalFilter):
        """Add environmental quality filters"""
        
        # For now, these are placeholder implementations
        # In a real system, these would query against environmental data indices
        
        if env_filter.avoid_flood_risk:
            # Boost properties that mention "no flood risk" or similar
            bool_query["should"].append({
                "multi_match": {
                    "query": "no flood risk safe area",
                    "fields": ["description", "features"],
                    "boost": 1.5
                }
            })
        
        if env_filter.min_green_space_proximity:
            # Boost properties near parks/green spaces
            bool_query["should"].append({
                "multi_match": {
                    "query": "park green space garden nature",
                    "fields": ["description", "features", "search_text"],
                    "boost": 2.0
                }
            })
        
        # Avoidance filters
        if env_filter.avoidance_filters:
            avoidance = env_filter.avoidance_filters
            
            # Avoid noise sources
            for noise_source in avoidance.noise_sources:
                noise_terms = {
                    "airport": ["airport", "flight path", "aircraft noise"],
                    "major_road": ["main road", "busy road", "traffic", "A road", "motorway"],
                    "railway": ["railway", "train line", "rail noise"],
                    "industrial_area": ["industrial", "factory", "warehouse"],
                    "nightlife": ["nightclub", "pub", "bar", "nightlife"]
                }
                
                terms = noise_terms.get(noise_source.value, [noise_source.value])
                
                for term in terms:
                    bool_query["must_not"].append({
                        "multi_match": {
                            "query": term,
                            "fields": ["description", "features", "location.address"]
                        }
                    })
    
    def _add_commute_filter(self, bool_query: Dict[str, Any], commute_filter: CommuteFilter):
        """Add commute time filters"""
        
        # For now, this is a placeholder implementation
        # In a real system, this would integrate with transport APIs
        # and pre-calculated commute time data
        
        # Boost properties that mention good transport links
        transport_terms = []
        
        for mode in commute_filter.transport_modes:
            if mode.value == "public_transport":
                transport_terms.extend(["station", "bus", "transport", "tube", "underground"])
            elif mode.value == "walking":
                transport_terms.extend(["walkable", "walking distance", "pedestrian"])
            elif mode.value == "cycling":
                transport_terms.extend(["cycle", "bike", "cycling"])
            elif mode.value == "driving":
                transport_terms.extend(["parking", "garage", "car", "driving"])
        
        if transport_terms:
            bool_query["should"].append({
                "multi_match": {
                    "query": " ".join(transport_terms),
                    "fields": ["description", "features", "search_text"],
                    "boost": 1.5
                }
            })
    
    def _add_feature_filters(self, query: Dict[str, Any], criteria: SearchCriteria):
        """Add property feature filters"""
        
        bool_query = query["query"]["bool"]
        
        # Garden requirement
        if criteria.must_have_garden is not None:
            bool_query["filter"].append({
                "term": {"garden": criteria.must_have_garden}
            })
        
        # Parking requirement
        if criteria.must_have_parking is not None:
            bool_query["filter"].append({
                "term": {"parking": criteria.must_have_parking}
            })
    
    def _add_sorting(self, query: Dict[str, Any], criteria: SearchCriteria):
        """Add sorting to the query"""
        
        sort_configs = {
            SortOption.RELEVANCE: [{"_score": {"order": "desc"}}],
            SortOption.PRICE_ASC: [{"price": {"order": "asc"}}],
            SortOption.PRICE_DESC: [{"price": {"order": "desc"}}],
            SortOption.NEWEST: [{"created_at": {"order": "desc"}}],
            SortOption.OLDEST: [{"created_at": {"order": "asc"}}]
        }
        
        # Distance sorting (if center coordinates provided)
        if (criteria.sort_by == SortOption.DISTANCE and 
            criteria.center_latitude is not None and 
            criteria.center_longitude is not None):
            
            sort_configs[SortOption.DISTANCE] = [{
                "_geo_distance": {
                    "location.coordinates": {
                        "lat": criteria.center_latitude,
                        "lon": criteria.center_longitude
                    },
                    "order": "asc",
                    "unit": "km"
                }
            }]
        
        query["sort"] = sort_configs.get(criteria.sort_by, sort_configs[SortOption.RELEVANCE])
    
    def build_suggestion_query(self, query_text: str) -> Dict[str, Any]:
        """Build query for search suggestions/autocomplete"""
        
        return {
            "suggest": {
                "property_suggest": {
                    "prefix": query_text,
                    "completion": {
                        "field": "suggest",
                        "size": 10
                    }
                },
                "area_suggest": {
                    "text": query_text,
                    "term": {
                        "field": "location.area",
                        "size": 5
                    }
                }
            }
        }
    
    def build_similar_properties_query(
        self, 
        property_id: str, 
        property_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build query to find similar properties"""
        
        return {
            "query": {
                "bool": {
                    "must": [
                        {"match_all": {}}
                    ],
                    "should": [
                        # Similar price range (±20%)
                        {
                            "range": {
                                "price": {
                                    "gte": property_data["price"] * 0.8,
                                    "lte": property_data["price"] * 1.2
                                }
                            }
                        },
                        # Same property type
                        {
                            "term": {
                                "property_type": property_data["property_type"]
                            }
                        },
                        # Similar bedrooms (±1)
                        {
                            "range": {
                                "bedrooms": {
                                    "gte": max(0, property_data.get("bedrooms", 0) - 1),
                                    "lte": property_data.get("bedrooms", 0) + 1
                                }
                            }
                        },
                        # Same area
                        {
                            "term": {
                                "location.area.keyword": property_data["location"]["area"]
                            }
                        }
                    ],
                    "must_not": [
                        # Exclude the property itself
                        {"term": {"id": property_id}}
                    ]
                }
            },
            "size": 5
        }