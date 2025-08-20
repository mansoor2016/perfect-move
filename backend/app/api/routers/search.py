from fastapi import APIRouter, Depends
from typing import List
from app.models.search import SearchCriteria, SearchResult
from app.modules.search.service import SearchService

router = APIRouter()

def get_search_service() -> SearchService:
    return SearchService()

@router.post("/", response_model=List[SearchResult])
async def search_properties(
    criteria: SearchCriteria,
    search_service: SearchService = Depends(get_search_service)
):
    """Search for properties based on criteria"""
    return await search_service.search_properties(criteria)

@router.get("/suggestions")
async def get_search_suggestions(
    query: str,
    search_service: SearchService = Depends(get_search_service)
):
    """Get intelligent search suggestions"""
    suggestions = await search_service.get_search_suggestions(query)
    return {"suggestions": suggestions}