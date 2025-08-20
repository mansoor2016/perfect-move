from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from geoalchemy2 import Geography, Geometry
from app.core.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID


class Property(Base):
    """Property model with PostGIS spatial support"""
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic property information
    title = Column(String(500), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    property_type = Column(String(100))  # house, flat, etc.
    
    # Address and location
    address = Column(String(500), nullable=False)
    postcode = Column(String(20))
    city = Column(String(100))
    
    # PostGIS spatial column for coordinates (WGS84)
    location = Column(Geography('POINT', srid=4326), nullable=False)
    
    # Property details
    floor_area = Column(Float)  # in square meters
    garden = Column(Boolean, default=False)
    parking = Column(Boolean, default=False)
    furnished = Column(String(50))  # furnished, unfurnished, part-furnished
    
    # Listing information
    listing_url = Column(String(1000))
    image_urls = Column(JSON)  # Array of image URLs
    
    # Data lineage and quality
    source = Column(String(100), nullable=False)  # rightmove, zoopla, etc.
    source_id = Column(String(200))  # ID from the source system
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reliability_score = Column(Float, default=1.0)  # 0.0 to 1.0
    
    # Relationships
    saved_by_users = relationship("SavedProperty", back_populates="property")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_properties_location', 'location', postgresql_using='gist'),
        Index('idx_properties_price', 'price'),
        Index('idx_properties_bedrooms', 'bedrooms'),
        Index('idx_properties_property_type', 'property_type'),
        Index('idx_properties_source_id', 'source', 'source_id'),
        Index('idx_properties_last_updated', 'last_updated'),
    )


class Amenity(Base):
    """Amenity model for nearby facilities"""
    __tablename__ = "amenities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)  # park, gym, station, school, etc.
    subcategory = Column(String(100))  # tube_station, bus_stop, primary_school, etc.
    
    # Location
    address = Column(String(500))
    location = Column(Geography('POINT', srid=4326), nullable=False)
    
    # Additional information
    description = Column(Text)
    opening_hours = Column(JSON)
    website = Column(String(500))
    phone = Column(String(50))
    
    # Data source
    source = Column(String(100), nullable=False)
    source_id = Column(String(200))
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_amenities_location', 'location', postgresql_using='gist'),
        Index('idx_amenities_category', 'category'),
        Index('idx_amenities_subcategory', 'subcategory'),
    )


class User(Base):
    """User model for authentication and preferences"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Profile
    first_name = Column(String(100))
    last_name = Column(String(100))
    
    # Preferences (stored as JSON for flexibility)
    search_preferences = Column(JSON)  # Default filters, weights, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    saved_searches = relationship("SavedSearch", back_populates="user")
    saved_properties = relationship("SavedProperty", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_users_email', 'email'),
    )


class SavedSearch(Base):
    """Saved search criteria for users"""
    __tablename__ = "saved_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Search metadata
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Search criteria (stored as JSON for flexibility)
    search_criteria = Column(JSON, nullable=False)
    
    # Notification settings
    notifications_enabled = Column(Boolean, default=True)
    last_notification_sent = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="saved_searches")
    
    # Indexes
    __table_args__ = (
        Index('idx_saved_searches_user_id', 'user_id'),
        Index('idx_saved_searches_notifications', 'notifications_enabled', 'last_notification_sent'),
    )


class SavedProperty(Base):
    """User's saved/favorite properties"""
    __tablename__ = "saved_properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey('properties.id'), nullable=False)
    
    # User notes and tags
    notes = Column(Text)
    tags = Column(JSON)  # Array of user-defined tags
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="saved_properties")
    property = relationship("Property", back_populates="saved_by_users")
    
    # Indexes
    __table_args__ = (
        Index('idx_saved_properties_user_id', 'user_id'),
        Index('idx_saved_properties_property_id', 'property_id'),
        # Unique constraint to prevent duplicate saves
        Index('idx_saved_properties_unique', 'user_id', 'property_id', unique=True),
    )


class EnvironmentalData(Base):
    """Environmental data for areas (air quality, noise, etc.)"""
    __tablename__ = "environmental_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Location (could be point or polygon)
    location = Column(Geography('GEOMETRY', srid=4326), nullable=False)
    area_name = Column(String(200))  # postcode, ward, etc.
    
    # Environmental metrics
    air_quality_index = Column(Float)
    noise_level = Column(Float)  # in decibels
    flood_risk = Column(String(50))  # low, medium, high
    crime_rate = Column(Float)  # crimes per 1000 residents
    
    # Additional data
    data_source = Column(String(100), nullable=False)
    measurement_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_environmental_location', 'location', postgresql_using='gist'),
        Index('idx_environmental_area_name', 'area_name'),
    )