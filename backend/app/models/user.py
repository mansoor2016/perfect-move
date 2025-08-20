from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.search import SearchCriteria


class User(BaseModel):
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    preferences: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SavedSearch(BaseModel):
    id: str
    user_id: str
    name: str
    criteria: SearchCriteria
    notifications_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FavoriteProperty(BaseModel):
    id: str
    user_id: str
    property_id: str
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserPreferences(BaseModel):
    default_search_radius_km: float = 10.0
    preferred_property_types: List[str] = []
    max_budget: Optional[int] = None
    notification_frequency: str = "daily"  # "immediate", "daily", "weekly"