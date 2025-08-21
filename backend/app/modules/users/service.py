from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime
import uuid
from app.models.user import User, SavedSearch, FavoriteProperty, UserPreferences
from app.models.search import SearchCriteria
from app.core.database import get_db
from app.core.auth import AuthService
from app.db.models import User as DBUser, SavedSearch as DBSavedSearch, SavedProperty as DBSavedProperty
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management and saved searches"""
    
    def __init__(self, db: Session = None):
        self.db = db
    
    async def create_user(self, email: str, password: str, first_name: Optional[str] = None, last_name: Optional[str] = None) -> User:
        """Create a new user with hashed password"""
        try:
            # Check if user already exists
            existing_user = self.db.query(DBUser).filter(DBUser.email == email).first()
            if existing_user:
                raise ValueError("User with this email already exists")
            
            # Hash password
            hashed_password = AuthService.get_password_hash(password)
            
            # Create user
            db_user = DBUser(
                id=uuid.uuid4(),
                email=email,
                hashed_password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                search_preferences={},
                created_at=datetime.utcnow()
            )
            
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            
            # Convert to Pydantic model
            return User(
                id=str(db_user.id),
                email=db_user.email,
                first_name=db_user.first_name,
                last_name=db_user.last_name,
                is_active=db_user.is_active,
                preferences=db_user.search_preferences or {},
                created_at=db_user.created_at,
                updated_at=db_user.created_at
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        try:
            db_user = self.db.query(DBUser).filter(
                and_(DBUser.email == email, DBUser.is_active == True)
            ).first()
            
            if not db_user or not AuthService.verify_password(password, db_user.hashed_password):
                return None
            
            # Update last login
            db_user.last_login = datetime.utcnow()
            self.db.commit()
            
            return User(
                id=str(db_user.id),
                email=db_user.email,
                first_name=db_user.first_name,
                last_name=db_user.last_name,
                is_active=db_user.is_active,
                preferences=db_user.search_preferences or {},
                created_at=db_user.created_at,
                updated_at=db_user.created_at
            )
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            db_user = self.db.query(DBUser).filter(
                and_(DBUser.id == uuid.UUID(user_id), DBUser.is_active == True)
            ).first()
            
            if not db_user:
                return None
            
            return User(
                id=str(db_user.id),
                email=db_user.email,
                first_name=db_user.first_name,
                last_name=db_user.last_name,
                is_active=db_user.is_active,
                preferences=db_user.search_preferences or {},
                created_at=db_user.created_at,
                updated_at=db_user.created_at
            )
            
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Optional[User]:
        """Update user preferences"""
        try:
            db_user = self.db.query(DBUser).filter(DBUser.id == uuid.UUID(user_id)).first()
            
            if not db_user:
                return None
            
            # Merge with existing preferences
            current_prefs = db_user.search_preferences or {}
            current_prefs.update(preferences)
            db_user.search_preferences = current_prefs
            
            self.db.commit()
            self.db.refresh(db_user)
            
            return await self.get_user(user_id)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update user preferences: {e}")
            return None
    
    async def save_search(self, user_id: str, name: str, criteria: SearchCriteria, notifications_enabled: bool = True) -> SavedSearch:
        """Save search criteria for user"""
        try:
            # Verify user exists
            user = await self.get_user(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Create saved search
            db_saved_search = DBSavedSearch(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                name=name,
                search_criteria=criteria.model_dump(),
                notifications_enabled=notifications_enabled,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(db_saved_search)
            self.db.commit()
            self.db.refresh(db_saved_search)
            
            return SavedSearch(
                id=str(db_saved_search.id),
                user_id=str(db_saved_search.user_id),
                name=db_saved_search.name,
                criteria=SearchCriteria.model_validate(db_saved_search.search_criteria),
                notifications_enabled=db_saved_search.notifications_enabled,
                created_at=db_saved_search.created_at,
                updated_at=db_saved_search.updated_at
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save search: {e}")
            raise
    
    async def get_saved_searches(self, user_id: str) -> List[SavedSearch]:
        """Get user's saved searches"""
        try:
            db_searches = self.db.query(DBSavedSearch).filter(
                DBSavedSearch.user_id == uuid.UUID(user_id)
            ).order_by(desc(DBSavedSearch.updated_at)).all()
            
            return [
                SavedSearch(
                    id=str(search.id),
                    user_id=str(search.user_id),
                    name=search.name,
                    criteria=SearchCriteria.model_validate(search.search_criteria),
                    notifications_enabled=search.notifications_enabled,
                    created_at=search.created_at,
                    updated_at=search.updated_at
                )
                for search in db_searches
            ]
            
        except Exception as e:
            logger.error(f"Failed to get saved searches for user {user_id}: {e}")
            return []
    
    async def update_saved_search(self, user_id: str, search_id: str, name: Optional[str] = None, criteria: Optional[SearchCriteria] = None, notifications_enabled: Optional[bool] = None) -> Optional[SavedSearch]:
        """Update a saved search"""
        try:
            db_search = self.db.query(DBSavedSearch).filter(
                and_(
                    DBSavedSearch.id == uuid.UUID(search_id),
                    DBSavedSearch.user_id == uuid.UUID(user_id)
                )
            ).first()
            
            if not db_search:
                return None
            
            # Update fields if provided
            if name is not None:
                db_search.name = name
            if criteria is not None:
                db_search.search_criteria = criteria.model_dump()
            if notifications_enabled is not None:
                db_search.notifications_enabled = notifications_enabled
            
            db_search.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(db_search)
            
            return SavedSearch(
                id=str(db_search.id),
                user_id=str(db_search.user_id),
                name=db_search.name,
                criteria=SearchCriteria.model_validate(db_search.search_criteria),
                notifications_enabled=db_search.notifications_enabled,
                created_at=db_search.created_at,
                updated_at=db_search.updated_at
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update saved search: {e}")
            return None
    
    async def delete_saved_search(self, user_id: str, search_id: str) -> bool:
        """Delete a saved search"""
        try:
            db_search = self.db.query(DBSavedSearch).filter(
                and_(
                    DBSavedSearch.id == uuid.UUID(search_id),
                    DBSavedSearch.user_id == uuid.UUID(user_id)
                )
            ).first()
            
            if not db_search:
                return False
            
            self.db.delete(db_search)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete saved search: {e}")
            return False
    
    async def add_favorite_property(self, user_id: str, property_id: str, notes: Optional[str] = None, tags: Optional[List[str]] = None) -> FavoriteProperty:
        """Add property to user's favorites"""
        try:
            # Check if already favorited
            existing = self.db.query(DBSavedProperty).filter(
                and_(
                    DBSavedProperty.user_id == uuid.UUID(user_id),
                    DBSavedProperty.property_id == uuid.UUID(property_id)
                )
            ).first()
            
            if existing:
                raise ValueError("Property already in favorites")
            
            # Create favorite
            db_favorite = DBSavedProperty(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                property_id=uuid.UUID(property_id),
                notes=notes,
                tags=tags or [],
                created_at=datetime.utcnow()
            )
            
            self.db.add(db_favorite)
            self.db.commit()
            self.db.refresh(db_favorite)
            
            return FavoriteProperty(
                id=str(db_favorite.id),
                user_id=str(db_favorite.user_id),
                property_id=str(db_favorite.property_id),
                notes=db_favorite.notes,
                created_at=db_favorite.created_at
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add favorite property: {e}")
            raise
    
    async def get_favorite_properties(self, user_id: str) -> List[FavoriteProperty]:
        """Get user's favorite properties"""
        try:
            db_favorites = self.db.query(DBSavedProperty).filter(
                DBSavedProperty.user_id == uuid.UUID(user_id)
            ).order_by(desc(DBSavedProperty.created_at)).all()
            
            return [
                FavoriteProperty(
                    id=str(fav.id),
                    user_id=str(fav.user_id),
                    property_id=str(fav.property_id),
                    notes=fav.notes,
                    created_at=fav.created_at
                )
                for fav in db_favorites
            ]
            
        except Exception as e:
            logger.error(f"Failed to get favorite properties for user {user_id}: {e}")
            return []
    
    async def remove_favorite_property(self, user_id: str, property_id: str) -> bool:
        """Remove property from user's favorites"""
        try:
            db_favorite = self.db.query(DBSavedProperty).filter(
                and_(
                    DBSavedProperty.user_id == uuid.UUID(user_id),
                    DBSavedProperty.property_id == uuid.UUID(property_id)
                )
            ).first()
            
            if not db_favorite:
                return False
            
            self.db.delete(db_favorite)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to remove favorite property: {e}")
            return False