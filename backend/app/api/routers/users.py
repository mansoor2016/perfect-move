from fastapi import APIRouter, Depends
from typing import List
from app.models.user import User, SavedSearch, FavoriteProperty
from app.modules.users.service import UserService

router = APIRouter()

def get_user_service() -> UserService:
    return UserService()

@router.post("/", response_model=User)
async def create_user(
    user_data: dict,
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user"""
    return await user_service.create_user(user_data)

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """Get user by ID"""
    return await user_service.get_user(user_id)

@router.get("/{user_id}/searches", response_model=List[SavedSearch])
async def get_saved_searches(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """Get user's saved searches"""
    return await user_service.get_saved_searches(user_id)

@router.post("/{user_id}/searches", response_model=SavedSearch)
async def save_search(
    user_id: str,
    search_criteria: dict,
    user_service: UserService = Depends(get_user_service)
):
    """Save search criteria for user"""
    return await user_service.save_search(user_id, search_criteria)