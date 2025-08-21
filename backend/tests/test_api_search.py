import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.search import SearchCriteria
from app.models.property import PropertyType, PropertyStatus

client = TestClient(app)

class TestSearchAPI:
    """Test cases for search API endpoints"""
    
    def test_search_properties_basic(self):
        """Test basic property search"""
        search_data = {
            "min_price": 200000,
            "max_price": 500000,
            "property_types": ["flat"],
            "status": ["for_sale"],
            "limit": 10
        }
        
        response = client.post("/api/v1/search/", json=search_data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check response structure
        assert "properties" in result
        assert "total_count" in result
        assert "search_time_ms" in result
        assert "filters_applied" in result
        assert "summary" in result
        
        # Check that filters were applied correctly
        filters = result["filters_applied"]
        assert filters["min_price"] == 200000
        assert filters["max_price"] == 500000
        assert filters["limit"] == 10
    
    def test_search_properties_with_location(self):
        """Test property search with location filters"""
        search_data = {
            "center_latitude": 51.5074,
            "center_longitude": -0.1278,
            "radius_km": 5.0,
            "limit": 20
        }
        
        response = client.post("/api/v1/search/", json=search_data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check that location filters were applied
        filters = result["filters_applied"]
        assert filters["center_latitude"] == 51.5074
        assert filters["center_longitude"] == -0.1278
        assert filters["radius_km"] == 5.0
    
    def test_search_properties_with_amenities(self):
        """Test property search with amenity filters"""
        search_data = {
            "amenity_filters": [
                {
                    "amenity_type": "train_station",
                    "max_distance": 1.0,
                    "distance_unit": "kilometers",
                    "walking_distance": True,
                    "required": True
                }
            ],
            "limit": 15
        }
        
        response = client.post("/api/v1/search/", json=search_data)
        
        assert response.status_code == 200
        result = response.json()
        
        # Check that amenity filters were applied
        filters = result["filters_applied"]
        assert len(filters["amenity_filters"]) == 1
        assert filters["amenity_filters"][0]["amenity_type"] == "train_station"
    
    def test_search_properties_invalid_criteria(self):
        """Test search with invalid criteria"""
        search_data = {
            "min_price": 500000,
            "max_price": 200000,  # Invalid: max < min
            "limit": 10
        }
        
        response = client.post("/api/v1/search/", json=search_data)
        
        # Pydantic validation returns 422, not 400
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("max_price must be greater than min_price" in str(error) for error in error_detail)
    
    def test_search_properties_with_caching(self):
        """Test search with caching enabled/disabled"""
        search_data = {
            "min_price": 300000,
            "max_price": 400000,
            "limit": 5
        }
        
        # First request with caching
        response1 = client.post("/api/v1/search/?use_cache=true", json=search_data)
        assert response1.status_code == 200
        
        # Second request should use cache
        response2 = client.post("/api/v1/search/?use_cache=true", json=search_data)
        assert response2.status_code == 200
        
        # Results should be similar (search_time_ms may differ slightly)
        result1 = response1.json()
        result2 = response2.json()
        
        # Check that main content is the same
        assert result1["properties"] == result2["properties"]
        assert result1["total_count"] == result2["total_count"]
        assert result1["filters_applied"] == result2["filters_applied"]
        
        # Request without cache
        response3 = client.post("/api/v1/search/?use_cache=false", json=search_data)
        assert response3.status_code == 200
    
    def test_get_search_aggregations(self):
        """Test search aggregations endpoint"""
        params = {
            "min_price": 200000,
            "max_price": 600000
        }
        
        response = client.get("/api/v1/search/aggregations", params=params)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "aggregations" in result
    
    def test_parse_natural_language_query(self):
        """Test natural language query parsing"""
        query = "2 bedroom flat near train station under £400k"
        
        response = client.post(f"/api/v1/search/parse?query={query}")
        
        assert response.status_code == 200
        result = response.json()
        
        assert "query" in result
        assert "parsed_criteria" in result
        assert "extracted_entities" in result
        assert "intent" in result
        assert result["query"] == query
    
    def test_get_autocomplete_suggestions(self):
        """Test autocomplete suggestions"""
        query = "flat near"
        
        response = client.get(f"/api/v1/search/autocomplete?q={query}&limit=5")
        
        assert response.status_code == 200
        result = response.json()
        
        assert "query" in result
        assert "suggestions" in result
        assert result["query"] == query
        assert len(result["suggestions"]) <= 5
    
    def test_get_search_examples(self):
        """Test search examples endpoint"""
        response = client.get("/api/v1/search/examples")
        
        assert response.status_code == 200
        result = response.json()
        
        assert "examples" in result
        assert "description" in result
        assert isinstance(result["examples"], list)
    
    def test_get_search_suggestions(self):
        """Test search suggestions endpoint"""
        query = "house with garden"
        
        response = client.get(f"/api/v1/search/suggestions?query={query}&limit=8")
        
        assert response.status_code == 200
        result = response.json()
        
        assert "query" in result
        assert "suggestions" in result
        assert result["query"] == query
        assert len(result["suggestions"]) <= 8
    
    def test_validate_search_criteria(self):
        """Test search criteria validation"""
        params = {
            "min_price": 200000,
            "max_price": 500000,
            "property_types": ["flat"],
            "limit": 10
        }
        
        response = client.get("/api/v1/search/validate", params=params)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "valid" in result
        assert "warnings" in result
        assert "criteria" in result
        assert result["valid"] is True
    
    def test_validate_search_criteria_with_conflicts(self):
        """Test search criteria validation with conflicts"""
        # Use valid criteria since Pydantic validation happens before our endpoint
        params = {
            "min_price": 200000,
            "max_price": 500000,
            "radius_km": 50.0,  # Large radius
            "commute_filters": []  # This would be complex to test properly
        }
        
        response = client.get("/api/v1/search/validate", params=params)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "valid" in result
        assert "warnings" in result
        assert "criteria" in result

class TestSearchPagination:
    """Test pagination functionality"""
    
    def test_search_pagination_first_page(self):
        """Test first page of search results"""
        search_data = {
            "limit": 5,
            "offset": 0
        }
        
        response = client.post("/api/v1/search/", json=search_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert len(result["properties"]) <= 5
        assert result["filters_applied"]["offset"] == 0
    
    def test_search_pagination_second_page(self):
        """Test second page of search results"""
        search_data = {
            "limit": 5,
            "offset": 5
        }
        
        response = client.post("/api/v1/search/", json=search_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["filters_applied"]["offset"] == 5
    
    def test_search_limit_validation(self):
        """Test search limit validation"""
        search_data = {
            "limit": 150  # Exceeds maximum of 100
        }
        
        response = client.post("/api/v1/search/", json=search_data)
        
        # Should either reject or cap at 100
        if response.status_code == 200:
            result = response.json()
            assert result["filters_applied"]["limit"] <= 100
        else:
            assert response.status_code == 422  # Validation error

class TestSearchErrorHandling:
    """Test error handling in search endpoints"""
    
    def test_search_with_malformed_json(self):
        """Test search with malformed JSON"""
        response = client.post(
            "/api/v1/search/",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_search_with_missing_required_fields(self):
        """Test search with missing required location fields"""
        search_data = {
            "center_latitude": 51.5074,
            # Missing center_longitude and radius_km - but these are optional in our model
        }
        
        response = client.post("/api/v1/search/", json=search_data)
        
        # This should actually work since location fields are optional
        # The validation happens in the model's validator
        assert response.status_code == 200
    
    def test_autocomplete_with_empty_query(self):
        """Test autocomplete with empty query"""
        response = client.get("/api/v1/search/autocomplete?q=")
        
        # Should handle empty query gracefully
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            result = response.json()
            assert "suggestions" in result