from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.models.search import SearchCriteria, SearchResult
from app.modules.search.service import SearchService
from app.modules.search.nlp_service import NLPService, SearchSuggestion, ParsedEntity

router = APIRouter()

def get_search_service() -> SearchService:
    return SearchService()

def get_nlp_service() -> NLPService:
    return NLPService()

@router.post("/", response_model=List[SearchResult])
async def search_properties(
    criteria: SearchCriteria,
    search_service: SearchService = Depends(get_search_service)
):
    """Search for properties based on criteria"""
    return await search_service.search_properties(criteria)

@router.post("/parse")
async def parse_natural_language_query(
    query: str,
    nlp_service: NLPService = Depends(get_nlp_service)
):
    """Parse a natural language query into structured search criteria"""
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

@router.get("/autocomplete")
async def get_autocomplete_suggestions(
    q: str = Query(..., description="Partial search query"),
    limit: int = Query(10, ge=1, le=20, description="Maximum number of suggestions"),
    nlp_service: NLPService = Depends(get_nlp_service)
):
    """Get intelligent autocomplete suggestions based on partial query"""
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

@router.get("/examples")
async def get_search_examples(
    nlp_service: NLPService = Depends(get_nlp_service)
):
    """Get example search queries to help users understand capabilities"""
    examples = nlp_service.get_search_examples()
    
    return {
        "examples": examples,
        "description": "Try these example searches to explore our advanced filtering capabilities"
    }

@router.get("/suggestions")
async def get_search_suggestions(
    query: str,
    search_service: SearchService = Depends(get_search_service)
):
    """Get intelligent search suggestions (legacy endpoint)"""
    suggestions = await search_service.get_search_suggestions(query)
    return {"suggestions": suggestions}