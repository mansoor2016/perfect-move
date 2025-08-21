from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.search import (
    SearchCriteria, SearchResult, SearchResultProperty, SearchSummary,
    MatchedFilter, SortOption, AmenityType, DistanceUnit
)
from app.modules.search.elasticsearch_service import elasticsearch_service, PROPERTIES_INDEX
from app.modules.search.query_builder import SearchQueryBuilder
from app.modules.search.ranking_engine import RankingEngine
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """Service for handling property search operations"""
    
    def __init__(self):
        self.query_builder = SearchQueryBuilder()
        self.ranking_engine = RankingEngine()
    
    async def search_properties(self, criteria: SearchCriteria) -> SearchResult:
        """Search for properties based on criteria"""
        start_time = datetime.now()
        
        try:
            # Build Elasticsearch query
            es_query = await self.query_builder.build_query(criteria)
            
            # Execute search
            client = await elasticsearch_service._get_client()
            
            try:
                response = await client.search(
                    index=PROPERTIES_INDEX,
                    body=es_query,
                    size=criteria.limit,
                    from_=criteria.offset
                )
                
                # Process results
                properties = []
                for hit in response["hits"]["hits"]:
                    property_data = hit["_source"]
                    
                    # Convert to SearchResultProperty
                    search_property = await self._convert_to_search_result_property(
                        property_data, hit["_score"], criteria
                    )
                    properties.append(search_property)
                
                # Apply ranking
                properties = await self.ranking_engine.rank_properties(properties, criteria)
                
                # Generate summary
                summary = self._generate_search_summary(properties, response["hits"]["total"]["value"])
                
                # Calculate search time
                search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                return SearchResult(
                    properties=properties,
                    total_count=response["hits"]["total"]["value"],
                    search_time_ms=search_time_ms,
                    filters_applied=criteria,
                    summary=summary,
                    validation_warnings=[]
                )
                
            finally:
                await client.close()
                
        except Exception as e:
            logger.error(f"Search failed: {e}")
            import traceback
            traceback.print_exc()
            # Return empty result on error
            search_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            return SearchResult(
                properties=[],
                total_count=0,
                search_time_ms=search_time_ms,
                filters_applied=criteria,
                summary=SearchSummary(
                    total_properties_found=0,
                    properties_returned=0
                ),
                validation_warnings=[]
            )
    
    async def _convert_to_search_result_property(
        self, 
        property_data: Dict[str, Any], 
        es_score: float, 
        criteria: SearchCriteria
    ) -> SearchResultProperty:
        """Convert Elasticsearch result to SearchResultProperty"""
        
        # Calculate match score (normalize ES score to 0-1 range)
        if es_score is not None:
            match_score = min(es_score / 10.0, 1.0)  # Assuming max ES score around 10
        else:
            match_score = 0.5  # Default score if ES doesn't provide one
        
        # Calculate distance if center coordinates provided
        distance_km = None
        if (criteria.center_latitude is not None and criteria.center_longitude is not None and
            property_data.get("location", {}).get("coordinates")):
            # Use Haversine formula or get from ES geo_distance
            lat1, lon1 = criteria.center_latitude, criteria.center_longitude
            coords = property_data["location"]["coordinates"]
            if coords.get("lat") is not None and coords.get("lon") is not None:
                lat2, lon2 = coords["lat"], coords["lon"]
                distance_km = self._calculate_distance(lat1, lon1, lat2, lon2)
        
        # Identify matched filters
        matched_filters = self._identify_matched_filters(property_data, criteria)
        
        # Convert property data to SearchResultProperty
        from app.models.property import Property, PropertyType, PropertyStatus, Location, PropertyLineage
        from datetime import datetime
        
        # Reconstruct Property object
        property_obj = Property(
            id=property_data["id"],
            title=property_data["title"],
            description=property_data.get("description"),
            price=property_data["price"],
            property_type=PropertyType(property_data["property_type"]),
            status=PropertyStatus(property_data["status"]),
            bedrooms=property_data.get("bedrooms"),
            bathrooms=property_data.get("bathrooms"),
            location=Location(
                latitude=property_data["location"]["coordinates"]["lat"],
                longitude=property_data["location"]["coordinates"]["lon"],
                address=property_data["location"]["address"],
                postcode=property_data["location"].get("postcode"),
                area=property_data["location"].get("area"),
                city=property_data["location"].get("city")
            ),
            features=property_data.get("features", []),
            energy_rating=property_data.get("energy_rating"),
            council_tax_band=property_data.get("council_tax_band"),
            tenure=property_data.get("tenure"),
            floor_area_sqft=property_data.get("floor_area_sqft"),
            garden=property_data.get("garden"),
            parking=property_data.get("parking"),
            lineage=PropertyLineage(
                source=property_data["lineage"]["source"],
                source_id=property_data["lineage"]["source_id"],
                last_updated=datetime.fromisoformat(property_data["lineage"]["last_updated"]),
                reliability_score=property_data["lineage"]["reliability_score"]
            ),
            created_at=datetime.fromisoformat(property_data["created_at"]),
            updated_at=datetime.fromisoformat(property_data["updated_at"])
        )
        
        # Create SearchResultProperty
        return SearchResultProperty(
            **property_obj.model_dump(),
            match_score=match_score,
            distance_km=distance_km,
            matched_filters=matched_filters,
            amenity_distances={},  # TODO: Calculate from geospatial data
            commute_times={},      # TODO: Calculate from transport APIs
            environmental_scores={}  # TODO: Get from environmental data
        )
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        
        return c * r
    
    def _identify_matched_filters(
        self, 
        property_data: Dict[str, Any], 
        criteria: SearchCriteria
    ) -> List[MatchedFilter]:
        """Identify which filters this property matched"""
        matched = []
        
        # Price filters
        if criteria.min_price and property_data["price"] >= criteria.min_price:
            matched.append(MatchedFilter(
                filter_type="price",
                filter_name="min_price",
                match_value=property_data["price"]
            ))
        
        if criteria.max_price and property_data["price"] <= criteria.max_price:
            matched.append(MatchedFilter(
                filter_type="price",
                filter_name="max_price",
                match_value=property_data["price"]
            ))
        
        # Property type filter
        if criteria.property_types and property_data["property_type"] in [pt.value for pt in criteria.property_types]:
            matched.append(MatchedFilter(
                filter_type="property_type",
                filter_name="property_type",
                match_value=property_data["property_type"]
            ))
        
        # Bedroom filters
        if criteria.min_bedrooms and property_data.get("bedrooms", 0) >= criteria.min_bedrooms:
            matched.append(MatchedFilter(
                filter_type="bedrooms",
                filter_name="min_bedrooms",
                match_value=property_data.get("bedrooms")
            ))
        
        # Feature filters
        if criteria.must_have_garden and property_data.get("garden"):
            matched.append(MatchedFilter(
                filter_type="features",
                filter_name="garden",
                match_value=True
            ))
        
        if criteria.must_have_parking and property_data.get("parking"):
            matched.append(MatchedFilter(
                filter_type="features",
                filter_name="parking",
                match_value=True
            ))
        
        return matched
    
    def _generate_search_summary(
        self, 
        properties: List[SearchResultProperty], 
        total_found: int
    ) -> SearchSummary:
        """Generate summary statistics for search results"""
        
        if not properties:
            return SearchSummary(
                total_properties_found=total_found,
                properties_returned=0
            )
        
        prices = [p.price for p in properties]
        match_scores = [p.match_score for p in properties]
        areas = [p.location.area for p in properties if p.location.area]
        
        # Count area frequency
        area_counts = {}
        for area in areas:
            area_counts[area] = area_counts.get(area, 0) + 1
        
        # Get most common areas
        common_areas = sorted(area_counts.keys(), key=lambda x: area_counts[x], reverse=True)[:5]
        
        return SearchSummary(
            total_properties_found=total_found,
            properties_returned=len(properties),
            avg_price=sum(prices) / len(prices) if prices else None,
            price_range={"min": min(prices), "max": max(prices)} if prices else None,
            avg_match_score=sum(match_scores) / len(match_scores) if match_scores else None,
            common_areas=common_areas
        )
    
    async def get_search_suggestions(self, query: str) -> List[str]:
        """Get intelligent search suggestions"""
        suggestions = []
        
        # Basic suggestions based on query content
        query_lower = query.lower()
        
        # Location-based suggestions
        if any(word in query_lower for word in ["near", "close", "by"]):
            suggestions.extend([
                "within 10 minutes walk of a train station",
                "near parks and green spaces",
                "close to good schools",
                "near shopping centers"
            ])
        
        # Property type suggestions
        if any(word in query_lower for word in ["flat", "apartment", "house"]):
            suggestions.extend([
                "2 bedroom flat with garden",
                "house with parking",
                "modern apartment with balcony"
            ])
        
        # Lifestyle suggestions
        if any(word in query_lower for word in ["quiet", "peaceful"]):
            suggestions.extend([
                "quiet area away from main roads",
                "peaceful neighborhood with low noise",
                "away from airports and busy areas"
            ])
        
        # Transport suggestions
        if any(word in query_lower for word in ["transport", "commute", "travel"]):
            suggestions.extend([
                "good transport links to central London",
                "within 30 minutes commute to City",
                "near underground stations"
            ])
        
        # Default suggestions if no specific patterns found
        if not suggestions:
            suggestions = [
                "2-3 bedroom house with garden",
                "flat near train station under £500k",
                "property with parking in quiet area",
                "modern apartment with good transport links",
                "family home near good schools"
            ]
        
        return suggestions[:10]  # Return top 10 suggestions
    
    async def get_aggregations(self, criteria: SearchCriteria) -> Dict[str, Any]:
        """Get search result aggregations for faceted filtering"""
        
        try:
            # Build base query without limits
            base_query = await self.query_builder.build_query(criteria)
            
            # Add aggregations
            agg_query = {
                **base_query,
                "size": 0,  # Don't return documents, just aggregations
                "aggs": {
                    "property_types": {
                        "terms": {"field": "property_type", "size": 10}
                    },
                    "price_ranges": {
                        "range": {
                            "field": "price",
                            "ranges": [
                                {"to": 200000, "key": "under_200k"},
                                {"from": 200000, "to": 400000, "key": "200k_400k"},
                                {"from": 400000, "to": 600000, "key": "400k_600k"},
                                {"from": 600000, "to": 1000000, "key": "600k_1m"},
                                {"from": 1000000, "key": "over_1m"}
                            ]
                        }
                    },
                    "bedrooms": {
                        "terms": {"field": "bedrooms", "size": 10}
                    },
                    "areas": {
                        "terms": {"field": "location.area", "size": 20}
                    },
                    "energy_ratings": {
                        "terms": {"field": "energy_rating", "size": 10}
                    },
                    "avg_price": {
                        "avg": {"field": "price"}
                    },
                    "price_stats": {
                        "stats": {"field": "price"}
                    }
                }
            }
            
            client = await elasticsearch_service._get_client()
            
            try:
                response = await client.search(
                    index=PROPERTIES_INDEX,
                    body=agg_query
                )
                
                return response.get("aggregations", {})
                
            finally:
                await client.close()
                
        except Exception as e:
            logger.error(f"Failed to get aggregations: {e}")
            return {}