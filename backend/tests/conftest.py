import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from geoalchemy2 import Geography
from app.core.database import Base, get_db
from app.db.models import Property, Amenity, User, SavedSearch, SavedProperty, EnvironmentalData
import os

# Use in-memory SQLite for tests (note: PostGIS features will be mocked)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return engine

@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Create a test database session"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def override_get_db(test_db_session):
    """Override the get_db dependency for testing"""
    def _override_get_db():
        try:
            yield test_db_session
        finally:
            pass
    return _override_get_db