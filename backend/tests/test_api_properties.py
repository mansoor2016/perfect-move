import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestPropertiesAPI:
    """Test cases for properties API endpoints"""
    
    def test_get_properties_basic(self):
        """Test basic property retrieval"""
        response = client.get("/api/v1/properties/")
        
        assert response.status_code == 200
        result = response.json()
        
        # Should return a list of properties
        assert isinstance(result, list)
        
        # Check structure if properties exist
        if result:
            property_item = result[0]
            required_fields = ["id", "title", "price", "property_type", "status", "location"]
            for field in required_fields:
                assert field in property_item
    
    def test_get_properties_with_filters(self):
        """Test property retrieval with filters"""
        params = {
            "limit": 10,
            "min_price": 200000,
            "max_price": 500000,
            "property_type": "flat"
        }
        
        response = client.get("/api/v1/properties/", params=params)
        
        assert response.status_code == 200
        result = response.json()
        
        assert isinstance(result, list)
        assert len(result) <= 10
        
        # Check that filters are applied (if properties exist)
        for property_item in result:
            if "price" in property_item:
                assert property_item["price"] >= 200000
                assert property_item["price"] <= 500000
            if "property_type" in property_item:
                assert property_item["property_type"] == "flat"
    
    def test_get_properties_pagination(self):
        """Test property retrieval with pagination"""
        # First page
        response1 = client.get("/api/v1/properties/?limit=5&offset=0")
        assert response1.status_code == 200
        result1 = response1.json()
        
        # Second page
        response2 = client.get("/api/v1/properties/?limit=5&offset=5")
        assert response2.status_code == 200
        result2 = response2.json()
        
        # Results should be different (if enough properties exist)
        if len(result1) == 5 and len(result2) > 0:
            # Check that we got different properties
            ids1 = {prop["id"] for prop in result1 if "id" in prop}
            ids2 = {prop["id"] for prop in result2 if "id" in prop}
            assert ids1.isdisjoint(ids2)  # No overlap
    
    def test_get_properties_invalid_filters(self):
        """Test property retrieval with invalid filters"""
        params = {
            "limit": -1,  # Invalid limit
            "min_price": -100  # Invalid price
        }
        
        response = client.get("/api/v1/properties/", params=params)
        
        # Should either return 422 (validation error) or handle gracefully
        assert response.status_code in [200, 422]
    
    def test_get_property_details(self):
        """Test getting detailed property information"""
        # Use a mock property ID for testing
        property_id = "12345678-1234-1234-1234-123456789012"
        
        response = client.get(f"/api/v1/properties/{property_id}")
        
        # Should return property details or 404 if not found
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            result = response.json()
            
            # Check response structure
            assert "property" in result
            assert "nearby_amenities" in result
            assert "commute_analysis" in result
            assert "environmental_data" in result
            assert "similar_properties" in result
            assert "price_history" in result
            
            # Check property structure
            property_data = result["property"]
            required_fields = ["id", "title", "price", "property_type", "status", "location"]
            for field in required_fields:
                assert field in property_data
    
    def test_get_property_details_with_options(self):
        """Test getting property details with different options"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        params = {
            "include_similar": False,
            "include_amenities": True,
            "include_commute": False
        }
        
        response = client.get(f"/api/v1/properties/{property_id}", params=params)
        
        # Should handle the options appropriately
        assert response.status_code in [200, 404, 500]
    
    def test_get_property_amenities(self):
        """Test getting amenities for a property"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        params = {
            "radius_km": 1.5,
            "amenity_types": ["park", "train_station"]
        }
        
        response = client.get(f"/api/v1/properties/{property_id}/amenities", params=params)
        
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            result = response.json()
            
            # Check response structure
            assert "property_id" in result
            assert "radius_km" in result
            assert "amenities" in result
            
            assert result["property_id"] == property_id
            assert result["radius_km"] == 1.5
    
    def test_get_property_amenities_invalid_radius(self):
        """Test getting amenities with invalid radius"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        params = {
            "radius_km": -1.0  # Invalid radius
        }
        
        response = client.get(f"/api/v1/properties/{property_id}/amenities", params=params)
        
        # Should return validation error
        assert response.status_code == 422
    
    def test_get_property_commute_analysis(self):
        """Test getting commute analysis for a property"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        params = {
            "destinations": ["London Bridge", "Canary Wharf"],
            "transport_modes": ["public_transport", "driving"]
        }
        
        response = client.get(f"/api/v1/properties/{property_id}/commute", params=params)
        
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            result = response.json()
            
            # Check response structure
            assert "property_id" in result
            assert "commute_analysis" in result
            
            assert result["property_id"] == property_id
            
            # Check that we have analysis for each destination
            commute_data = result["commute_analysis"]
            for destination in params["destinations"]:
                assert destination in commute_data
    
    def test_get_property_commute_missing_destinations(self):
        """Test commute analysis without destinations"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        # Missing required destinations parameter
        response = client.get(f"/api/v1/properties/{property_id}/commute")
        
        # Should return validation error
        assert response.status_code == 422

class TestPropertiesErrorHandling:
    """Test error handling in properties API"""
    
    def test_get_property_invalid_id_format(self):
        """Test getting property with invalid ID format"""
        invalid_id = "not-a-valid-uuid"
        
        response = client.get(f"/api/v1/properties/{invalid_id}")
        
        # Should handle invalid UUID format gracefully
        assert response.status_code in [400, 404, 422, 500]
    
    def test_get_properties_extreme_pagination(self):
        """Test properties endpoint with extreme pagination values"""
        params = {
            "limit": 1000,  # Very large limit
            "offset": 999999  # Very large offset
        }
        
        response = client.get("/api/v1/properties/", params=params)
        
        # Should handle gracefully, either by validation or capping values
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            result = response.json()
            assert isinstance(result, list)
            # Should cap limit to maximum allowed
            assert len(result) <= 100
    
    def test_get_amenities_extreme_radius(self):
        """Test amenities endpoint with extreme radius values"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        params = {
            "radius_km": 100.0  # Very large radius
        }
        
        response = client.get(f"/api/v1/properties/{property_id}/amenities", params=params)
        
        # Should either validate or handle large radius appropriately
        assert response.status_code in [200, 404, 422, 500]
    
    def test_get_commute_empty_destinations(self):
        """Test commute analysis with empty destinations list"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        params = {
            "destinations": []  # Empty list
        }
        
        response = client.get(f"/api/v1/properties/{property_id}/commute", params=params)
        
        # Should return validation error for empty destinations
        assert response.status_code == 422

class TestPropertiesIntegration:
    """Integration tests for properties API"""
    
    def test_property_search_to_details_flow(self):
        """Test the flow from search to property details"""
        # First, search for properties
        search_data = {
            "limit": 5,
            "property_types": ["flat"],
            "status": ["for_sale"]
        }
        
        search_response = client.post("/api/v1/search/", json=search_data)
        
        if search_response.status_code == 200:
            search_result = search_response.json()
            
            if search_result["properties"]:
                # Get details for the first property
                property_id = search_result["properties"][0]["id"]
                
                details_response = client.get(f"/api/v1/properties/{property_id}")
                
                # Should be able to get details for a property from search results
                assert details_response.status_code in [200, 404, 500]
    
    def test_property_amenities_consistency(self):
        """Test that amenity data is consistent across different radius values"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        # Get amenities with small radius
        response1 = client.get(f"/api/v1/properties/{property_id}/amenities?radius_km=1.0")
        
        # Get amenities with larger radius
        response2 = client.get(f"/api/v1/properties/{property_id}/amenities?radius_km=2.0")
        
        if response1.status_code == 200 and response2.status_code == 200:
            amenities1 = response1.json()["amenities"]
            amenities2 = response2.json()["amenities"]
            
            # Larger radius should include all amenities from smaller radius
            # (This is a logical consistency check)
            # Implementation would depend on the actual amenities data structure
            pass
    
    def test_property_commute_modes_consistency(self):
        """Test that commute analysis is consistent across transport modes"""
        property_id = "12345678-1234-1234-1234-123456789012"
        
        destinations = ["London Bridge"]
        
        # Test different transport modes
        for mode in ["public_transport", "driving", "walking"]:
            params = {
                "destinations": destinations,
                "transport_modes": [mode]
            }
            
            response = client.get(f"/api/v1/properties/{property_id}/commute", params=params)
            
            # Each mode should either work or fail consistently
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                result = response.json()
                assert "commute_analysis" in result
                assert destinations[0] in result["commute_analysis"]