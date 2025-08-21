import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import AuthService
import uuid

client = TestClient(app)

class TestUserAuthentication:
    """Test cases for user authentication endpoints"""
    
    def test_user_registration_success(self):
        """Test successful user registration"""
        user_data = {
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = client.post("/api/v1/users/register", json=user_data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check response structure
        assert "id" in result
        assert "email" in result
        assert "first_name" in result
        assert "last_name" in result
        assert "is_active" in result
        assert "preferences" in result
        assert "created_at" in result
        
        # Check values
        assert result["email"] == user_data["email"]
        assert result["first_name"] == user_data["first_name"]
        assert result["last_name"] == user_data["last_name"]
        assert result["is_active"] is True
        
        # Password should not be in response
        assert "password" not in result
        assert "hashed_password" not in result
    
    def test_user_registration_duplicate_email(self):
        """Test registration with duplicate email"""
        email = f"duplicate_{uuid.uuid4()}@example.com"
        
        user_data = {
            "email": email,
            "password": "testpassword123",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # First registration should succeed
        response1 = client.post("/api/v1/users/register", json=user_data)
        assert response1.status_code == 200
        
        # Second registration with same email should fail
        response2 = client.post("/api/v1/users/register", json=user_data)
        assert response2.status_code == 400
        assert "already exists" in response2.json()["detail"]
    
    def test_user_registration_invalid_email(self):
        """Test registration with invalid email"""
        user_data = {
            "email": "invalid-email",
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/users/register", json=user_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_user_login_success(self):
        """Test successful user login"""
        # First register a user
        email = f"login_test_{uuid.uuid4()}@example.com"
        password = "testpassword123"
        
        registration_data = {
            "email": email,
            "password": password,
            "first_name": "Login",
            "last_name": "Test"
        }
        
        reg_response = client.post("/api/v1/users/register", json=registration_data)
        assert reg_response.status_code == 200
        
        # Now test login
        login_data = {
            "email": email,
            "password": password
        }
        
        response = client.post("/api/v1/users/login", json=login_data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check response structure
        assert "access_token" in result
        assert "token_type" in result
        assert "expires_in" in result
        
        # Check values
        assert result["token_type"] == "bearer"
        assert result["expires_in"] > 0
        assert len(result["access_token"]) > 0
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/users/login", json=login_data)
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_user_login_missing_fields(self):
        """Test login with missing fields"""
        login_data = {
            "email": "test@example.com"
            # Missing password
        }
        
        response = client.post("/api/v1/users/login", json=login_data)
        
        assert response.status_code == 422  # Validation error

class TestUserProfile:
    """Test cases for user profile endpoints"""
    
    def setup_method(self):
        """Set up test user and authentication"""
        self.email = f"profile_test_{uuid.uuid4()}@example.com"
        self.password = "testpassword123"
        
        # Register user
        registration_data = {
            "email": self.email,
            "password": self.password,
            "first_name": "Profile",
            "last_name": "Test"
        }
        
        reg_response = client.post("/api/v1/users/register", json=registration_data)
        assert reg_response.status_code == 200
        
        # Login to get token
        login_data = {
            "email": self.email,
            "password": self.password
        }
        
        login_response = client.post("/api/v1/users/login", json=login_data)
        assert login_response.status_code == 200
        
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_current_user(self):
        """Test getting current user profile"""
        response = client.get("/api/v1/users/me", headers=self.headers)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["email"] == self.email
        assert result["first_name"] == "Profile"
        assert result["last_name"] == "Test"
        assert result["is_active"] is True
    
    def test_get_current_user_without_auth(self):
        """Test getting current user without authentication"""
        response = client.get("/api/v1/users/me")
        
        assert response.status_code == 403  # Forbidden
    
    def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_update_user_preferences(self):
        """Test updating user preferences"""
        preferences_data = {
            "preferences": {
                "default_search_radius_km": 15.0,
                "preferred_property_types": ["flat", "house"],
                "max_budget": 500000,
                "notification_frequency": "weekly"
            }
        }
        
        response = client.put("/api/v1/users/me/preferences", json=preferences_data, headers=self.headers)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check that preferences were updated
        prefs = result["preferences"]
        assert prefs["default_search_radius_km"] == 15.0
        assert prefs["preferred_property_types"] == ["flat", "house"]
        assert prefs["max_budget"] == 500000
        assert prefs["notification_frequency"] == "weekly"

class TestSavedSearches:
    """Test cases for saved searches functionality"""
    
    def setup_method(self):
        """Set up test user and authentication"""
        self.email = f"search_test_{uuid.uuid4()}@example.com"
        self.password = "testpassword123"
        
        # Register and login
        registration_data = {
            "email": self.email,
            "password": self.password,
            "first_name": "Search",
            "last_name": "Test"
        }
        
        reg_response = client.post("/api/v1/users/register", json=registration_data)
        assert reg_response.status_code == 200
        
        login_data = {"email": self.email, "password": self.password}
        login_response = client.post("/api/v1/users/login", json=login_data)
        assert login_response.status_code == 200
        
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_save_search(self):
        """Test saving a search"""
        search_data = {
            "name": "My Test Search",
            "criteria": {
                "min_price": 200000,
                "max_price": 500000,
                "property_types": ["flat"],
                "status": ["for_sale"],
                "limit": 20
            },
            "notifications_enabled": True
        }
        
        response = client.post("/api/v1/users/me/searches", json=search_data, headers=self.headers)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check response structure
        assert "id" in result
        assert "user_id" in result
        assert "name" in result
        assert "criteria" in result
        assert "notifications_enabled" in result
        assert "created_at" in result
        assert "updated_at" in result
        
        # Check values
        assert result["name"] == search_data["name"]
        assert result["notifications_enabled"] is True
        assert result["criteria"]["min_price"] == 200000
        assert result["criteria"]["max_price"] == 500000
    
    def test_get_saved_searches(self):
        """Test getting saved searches"""
        # First save a search
        search_data = {
            "name": "Test Search for Retrieval",
            "criteria": {
                "min_price": 300000,
                "max_price": 600000,
                "property_types": ["house"],
                "limit": 10
            },
            "notifications_enabled": False
        }
        
        save_response = client.post("/api/v1/users/me/searches", json=search_data, headers=self.headers)
        assert save_response.status_code == 200
        
        # Now get all saved searches
        response = client.get("/api/v1/users/me/searches", headers=self.headers)
        
        assert response.status_code == 200
        result = response.json()
        
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Find our saved search
        saved_search = next((s for s in result if s["name"] == search_data["name"]), None)
        assert saved_search is not None
        assert saved_search["notifications_enabled"] is False
    
    def test_update_saved_search(self):
        """Test updating a saved search"""
        # First save a search
        search_data = {
            "name": "Original Search Name",
            "criteria": {
                "min_price": 200000,
                "max_price": 400000,
                "limit": 15
            },
            "notifications_enabled": True
        }
        
        save_response = client.post("/api/v1/users/me/searches", json=search_data, headers=self.headers)
        assert save_response.status_code == 200
        search_id = save_response.json()["id"]
        
        # Update the search
        update_data = {
            "name": "Updated Search Name",
            "notifications_enabled": False
        }
        
        response = client.put(f"/api/v1/users/me/searches/{search_id}", json=update_data, headers=self.headers)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["name"] == "Updated Search Name"
        assert result["notifications_enabled"] is False
        # Criteria should remain unchanged
        assert result["criteria"]["min_price"] == 200000
    
    def test_delete_saved_search(self):
        """Test deleting a saved search"""
        # First save a search
        search_data = {
            "name": "Search to Delete",
            "criteria": {
                "min_price": 250000,
                "limit": 10
            }
        }
        
        save_response = client.post("/api/v1/users/me/searches", json=search_data, headers=self.headers)
        assert save_response.status_code == 200
        search_id = save_response.json()["id"]
        
        # Delete the search
        response = client.delete(f"/api/v1/users/me/searches/{search_id}", headers=self.headers)
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify it's deleted by trying to update it
        update_response = client.put(f"/api/v1/users/me/searches/{search_id}", json={"name": "Should Fail"}, headers=self.headers)
        assert update_response.status_code == 404

class TestFavoriteProperties:
    """Test cases for favorite properties functionality"""
    
    def setup_method(self):
        """Set up test user and authentication"""
        self.email = f"favorites_test_{uuid.uuid4()}@example.com"
        self.password = "testpassword123"
        
        # Register and login
        registration_data = {
            "email": self.email,
            "password": self.password,
            "first_name": "Favorites",
            "last_name": "Test"
        }
        
        reg_response = client.post("/api/v1/users/register", json=registration_data)
        assert reg_response.status_code == 200
        
        login_data = {"email": self.email, "password": self.password}
        login_response = client.post("/api/v1/users/login", json=login_data)
        assert login_response.status_code == 200
        
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_add_favorite_property(self):
        """Test adding a property to favorites"""
        property_id = str(uuid.uuid4())
        
        favorite_data = {
            "property_id": property_id,
            "notes": "Great location and price",
            "tags": ["shortlist", "good_value"]
        }
        
        response = client.post("/api/v1/users/me/favorites", json=favorite_data, headers=self.headers)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check response structure
        assert "id" in result
        assert "user_id" in result
        assert "property_id" in result
        assert "notes" in result
        assert "created_at" in result
        
        # Check values
        assert result["property_id"] == property_id
        assert result["notes"] == favorite_data["notes"]
    
    def test_get_favorite_properties(self):
        """Test getting favorite properties"""
        # First add a favorite
        property_id = str(uuid.uuid4())
        favorite_data = {
            "property_id": property_id,
            "notes": "Test favorite property"
        }
        
        add_response = client.post("/api/v1/users/me/favorites", json=favorite_data, headers=self.headers)
        assert add_response.status_code == 200
        
        # Now get all favorites
        response = client.get("/api/v1/users/me/favorites", headers=self.headers)
        
        assert response.status_code == 200
        result = response.json()
        
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Find our favorite
        favorite = next((f for f in result if f["property_id"] == property_id), None)
        assert favorite is not None
        assert favorite["notes"] == "Test favorite property"
    
    def test_remove_favorite_property(self):
        """Test removing a property from favorites"""
        # First add a favorite
        property_id = str(uuid.uuid4())
        favorite_data = {
            "property_id": property_id,
            "notes": "Favorite to remove"
        }
        
        add_response = client.post("/api/v1/users/me/favorites", json=favorite_data, headers=self.headers)
        assert add_response.status_code == 200
        
        # Remove the favorite
        response = client.delete(f"/api/v1/users/me/favorites/{property_id}", headers=self.headers)
        
        assert response.status_code == 200
        assert "removed from favorites" in response.json()["message"]
        
        # Verify it's removed
        get_response = client.get("/api/v1/users/me/favorites", headers=self.headers)
        assert get_response.status_code == 200
        
        favorites = get_response.json()
        favorite_ids = [f["property_id"] for f in favorites]
        assert property_id not in favorite_ids
    
    def test_add_duplicate_favorite(self):
        """Test adding the same property to favorites twice"""
        property_id = str(uuid.uuid4())
        
        favorite_data = {
            "property_id": property_id,
            "notes": "First favorite"
        }
        
        # First addition should succeed
        response1 = client.post("/api/v1/users/me/favorites", json=favorite_data, headers=self.headers)
        assert response1.status_code == 200
        
        # Second addition should fail
        response2 = client.post("/api/v1/users/me/favorites", json=favorite_data, headers=self.headers)
        assert response2.status_code == 400
        assert "already in favorites" in response2.json()["detail"]

class TestUserAPIErrorHandling:
    """Test error handling in user API endpoints"""
    
    def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoints without authentication"""
        endpoints = [
            "/api/v1/users/me",
            "/api/v1/users/me/searches",
            "/api/v1/users/me/favorites"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 403
    
    def test_invalid_json_in_requests(self):
        """Test endpoints with invalid JSON"""
        response = client.post(
            "/api/v1/users/register",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self):
        """Test endpoints with missing required fields"""
        # Registration without email
        response = client.post("/api/v1/users/register", json={"password": "test123"})
        assert response.status_code == 422
        
        # Login without password
        response = client.post("/api/v1/users/login", json={"email": "test@example.com"})
        assert response.status_code == 422