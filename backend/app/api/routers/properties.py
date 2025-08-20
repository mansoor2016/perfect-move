from fastapi import APIRouter
from typing import List
from app.models.property import Property

router = APIRouter()

@router.get("/", response_model=List[Property])
async def get_properties():
    """Get all properties"""
    # TODO: Implement property retrieval
    return []

@router.get("/{property_id}", response_model=Property)
async def get_property(property_id: str):
    """Get property by ID"""
    # TODO: Implement property retrieval by ID
    pass