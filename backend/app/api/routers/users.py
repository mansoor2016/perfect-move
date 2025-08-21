from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import timedelta
from pydantic import BaseModel, EmailStr
from app.models.user import User, SavedSearch, FavoriteProperty
from app.models.search import SearchCriteria
from app.modules.users.service import UserService
from app.core.database import get_db
from app.core.auth import AuthService, get_current_user_id
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Request/Response models
class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SaveSearchRequest(BaseModel):
    name: str
    criteria: SearchCriteria
    notifications_enabled: bool = True

class UpdateSearchRequest(BaseModel):
    name: Optional[str] = None
    criteria: Optional[SearchCriteria] = None
    notifications_enabled: Optional[bool] = None

class AddFavoriteRequest(BaseModel):
    property_id: str
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class UpdatePreferencesRequest(BaseModel):
    preferences: Dict[str, Any]

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

# Authentication endpoints
@router.post("/register", response_model=User)
async def register_user(
    user_data: UserRegistration,
    user_service: UserService = Depends(get_user_service)
):
    """
    Register a new user account.
    
    Creates a new user with hashed password and returns user details.
    """
    try:
        user = await user_service.create_user(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        return user
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    """
    Authenticate user and return JWT access token.
    
    Token can be used for authenticated endpoints.
    """
    try:
        user = await user_service.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token = AuthService.create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        
        return TokenResponse(
            access_token=access_token,
            expires_in=30 * 60  # 30 minutes in seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

# User profile endpoints
@router.get("/me", response_model=User)
async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Get current user's profile information."""
    try:
        user = await user_service.get_user(current_user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )

@router.put("/me/preferences", response_model=User)
async def update_user_preferences(
    preferences_data: UpdatePreferencesRequest,
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Update current user's search preferences and settings."""
    try:
        user = await user_service.update_user_preferences(
            current_user_id, 
            preferences_data.preferences
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )

# Saved searches endpoints
@router.get("/me/searches", response_model=List[SavedSearch])
async def get_saved_searches(
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Get current user's saved searches."""
    try:
        searches = await user_service.get_saved_searches(current_user_id)
        return searches
        
    except Exception as e:
        logger.error(f"Failed to get saved searches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve saved searches"
        )

@router.post("/me/searches", response_model=SavedSearch)
async def save_search(
    search_data: SaveSearchRequest,
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Save a new search for the current user."""
    try:
        saved_search = await user_service.save_search(
            user_id=current_user_id,
            name=search_data.name,
            criteria=search_data.criteria,
            notifications_enabled=search_data.notifications_enabled
        )
        return saved_search
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to save search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save search"
        )

@router.put("/me/searches/{search_id}", response_model=SavedSearch)
async def update_saved_search(
    search_id: str,
    search_data: UpdateSearchRequest,
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Update an existing saved search."""
    try:
        updated_search = await user_service.update_saved_search(
            user_id=current_user_id,
            search_id=search_id,
            name=search_data.name,
            criteria=search_data.criteria,
            notifications_enabled=search_data.notifications_enabled
        )
        
        if not updated_search:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found"
            )
        
        return updated_search
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update saved search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update saved search"
        )

@router.delete("/me/searches/{search_id}")
async def delete_saved_search(
    search_id: str,
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Delete a saved search."""
    try:
        success = await user_service.delete_saved_search(current_user_id, search_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved search not found"
            )
        
        return {"message": "Saved search deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete saved search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete saved search"
        )

# Favorites endpoints
@router.get("/me/favorites", response_model=List[FavoriteProperty])
async def get_favorite_properties(
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Get current user's favorite properties."""
    try:
        favorites = await user_service.get_favorite_properties(current_user_id)
        return favorites
        
    except Exception as e:
        logger.error(f"Failed to get favorite properties: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve favorite properties"
        )

@router.post("/me/favorites", response_model=FavoriteProperty)
async def add_favorite_property(
    favorite_data: AddFavoriteRequest,
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Add a property to current user's favorites."""
    try:
        favorite = await user_service.add_favorite_property(
            user_id=current_user_id,
            property_id=favorite_data.property_id,
            notes=favorite_data.notes,
            tags=favorite_data.tags
        )
        return favorite
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to add favorite property: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add favorite property"
        )

@router.delete("/me/favorites/{property_id}")
async def remove_favorite_property(
    property_id: str,
    current_user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """Remove a property from current user's favorites."""
    try:
        success = await user_service.remove_favorite_property(current_user_id, property_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Favorite property not found"
            )
        
        return {"message": "Property removed from favorites"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove favorite property: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove favorite property"
        )