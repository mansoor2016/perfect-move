from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import redis.asyncio as redis
import json
import hashlib
from datetime import timedelta
from app.models.search import SearchCriteria, SearchResult, PropertyDetailsResponse
from app.models.property import Property
from app.modules.search.service import SearchService
from app.modules.search.nlp_service import NLPService, SearchSuggestion, ParsedEntity
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis client for caching
redis_client = None

async def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client

def get_search_service() -> SearchService:
    return SearchService()

def get_nlp_service() -> NLPService:
    return NLPService()

def generate_cache_key(criteria: SearchCriteria) -> str:
    """Generate a cache key for search criteria"""
    # Create a hash of the search criteria for caching
    criteria_dict = criteria.model_dump()
    criteria_str = json.dumps(criteria_dict, sort_keys=True)
    return f"search:{hashlib.md5(criteria_str.encode()).hexdigest()}"

@router.post("/", response_model=SearchResult)
async def search_properties(
    criteria: SearchCriteria,
    use_cache: bool = Query(True, description="Whether to use cached results"),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Search for properties based on complex lifestyle filtering criteria.
    
    Supports:
    - Basic filters (price, bedrooms, property type)
    - Location filters (coordinates + radius, specific areas)
    - Lifestyle filters (amenities, commute, environmental)
    - Pagination and sorting
    """
    try:
        # Check cache first if enabled
        if use_cache:
            try:
                redis_conn = await get_redis_client()
                cache_key = generate_cache_key(criteria)
                cached_result = await redis_conn.get(cache_key)
                
                if cached_result:
                    logger.info(f"Cache hit for search: {cache_key}")
                    return SearchResult.model_validate(json.loads(cached_result))
            except Exception as e:
                logger.warning(f"Cache lookup failed: {e}")
        
        # Perform search
        result = await search_service.search_properties(criteria)
        
        # Cache the result if caching is enabled
        if use_cache:
            try:
                redis_conn = await get_redis_client()
                cache_key = generate_cache_key(criteria)
                # Cache for 5 minutes
                await redis_conn.setex(
                    cache_key, 
                    timedelta(minutes=5), 
                    result.model_dump_json()
                )
                logger.info(f"Cached search result: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")
        
        return result
        
    except ValueError as e:
        # Handle validation errors from search criteria
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search criteria: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search service temporarily unavailable"
        )

@router.get("/aggregations")
async def get_search_aggregations(
    criteria: SearchCriteria = Depends(),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Get aggregated data for faceted filtering.
    
    Returns statistics like:
    - Property type distribution
    - Price ranges
    - Bedroom counts
    - Popular areas
    - Energy ratings
    """
    try:
        aggregations = await search_service.get_aggregations(criteria)
        return {"aggregations": aggregations}
    except Exception as e:
        logger.error(f"Failed to get aggregations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve search aggregations"
        )

@router.post("/parse")
async def parse_natural_language_query(
    query: str = Query(..., description="Natural language search query"),
    nlp_service: NLPService = Depends(get_nlp_service)
):
    """
    Parse a natural language query into structured search criteria.
    
    Examples:
    - "2 bedroom flat near train station under £400k"
    - "house with garden in quiet area"
    - "property within 30 minutes commute to London Bridge"
    """
    try:
        search_criteria, entities = nlp_service.parse_query(query)
        
        return {
            "query": query,
            "parsed_criteria": search_criteria.model_dump(),
            "extracted_entities": [
                {
                    "type": entity.entity_type,
                    "value": entity.value,
                    "confidence": entity.confidence,
                    "text": entity.original_text,
                    "position": [entity.start_pos, entity.end_pos]
                }
                for entity in entities
            ],
            "intent": nlp_service.detect_query_intent(query)
        }
    except Exception as e:
        logger.error(f"NLP parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Natural language processing temporarily unavailable"
        )

@router.get("/autocomplete")
async def get_autocomplete_suggestions(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
    nlp_service: NLPService = Depends(get_nlp_service)
):
    """
    Get intelligent autocomplete suggestions based on partial query.
    
    Provides contextual suggestions that demonstrate platform capabilities.
    """
    try:
        suggestions = nlp_service.get_autocomplete_suggestions(q, limit)
        
        return {
            "query": q,
            "suggestions": [
                {
                    "text": suggestion.text,
                    "description": suggestion.description,
                    "category": suggestion.category,
                    "confidence": suggestion.confidence,
                    "filters": suggestion.filters
                }
                for suggestion in suggestions
            ]
        }
    except Exception as e:
        logger.error(f"Autocomplete failed: {e}")
        # Return empty suggestions on error rather than failing
        return {
            "query": q,
            "suggestions": []
        }

@router.get("/examples")
async def get_search_examples(
    nlp_service: NLPService = Depends(get_nlp_service)
):
    """
    Get example search queries to help users understand platform capabilities.
    
    Returns categorized examples showing different types of searches possible.
    """
    try:
        examples = nlp_service.get_search_examples()
        
        return {
            "examples": examples,
            "description": "Try these example searches to explore our advanced filtering capabilities"
        }
    except Exception as e:
        logger.error(f"Failed to get examples: {e}")
        # Return basic examples on error
        return {
            "examples": [
                "2 bedroom flat near train station under £400k",
                "house with garden in quiet area",
                "property within 30 minutes commute to London Bridge"
            ],
            "description": "Try these example searches to explore our advanced filtering capabilities"
        }

@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., description="Search query for suggestions"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
    search_service: SearchService = Depends(get_search_service)
):
    """
    Get intelligent search suggestions based on query content.
    
    Legacy endpoint - use /autocomplete for better functionality.
    """
    try:
        suggestions = await search_service.get_search_suggestions(query)
        return {
            "query": query,
            "suggestions": suggestions[:limit]
        }
    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        return {
            "query": query,
            "suggestions": []
        }

@router.get("/validate")
async def validate_search_criteria(
    criteria: SearchCriteria = Depends()
):
    """
    Validate search criteria and return any conflicts or issues.
    
    Useful for frontend validation before submitting search.
    """
    try:
        # The SearchCriteria model validation will catch most issues
        # Additional business logic validation can be added here
        
        validation_warnings = []
        
        # Check for potentially conflicting filters
        if criteria.max_price and criteria.min_price and criteria.max_price <= criteria.min_price:
            validation_warnings.append({
                "field": "price_range",
                "message": "Maximum price should be greater than minimum price",
                "suggested_fix": "Adjust price range"
            })
        
        # Check for unrealistic combinations
        if criteria.commute_filters and criteria.radius_km:
            for commute in criteria.commute_filters:
                if commute.max_commute_minutes < 15 and criteria.radius_km > 30:
                    validation_warnings.append({
                        "field": "commute_radius",
                        "message": f"Short commute time ({commute.max_commute_minutes} min) with large search radius ({criteria.radius_km} km) may yield no results",
                        "suggested_fix": "Reduce search radius or increase commute time"
                    })
        
        return {
            "valid": len(validation_warnings) == 0,
            "warnings": validation_warnings,
            "criteria": criteria.model_dump()
        }
        
    except ValueError as e:
        return {
            "valid": False,
            "warnings": [{
                "field": "general",
                "message": str(e),
                "suggested_fix": "Review and correct the highlighted fields"
            }],
            "criteria": None
        }