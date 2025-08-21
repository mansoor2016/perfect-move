"""
Unit tests for the NLP service functionality.

Tests cover:
- Natural language parsing accuracy
- Entity extraction
- Autocomplete suggestions
- Query intent detection
"""

import pytest
from app.modules.search.nlp_service import NLPService, QueryIntent, ParsedEntity, SearchSuggestion
from app.models.search import SearchCriteria, AmenityType, PropertyType, DistanceUnit, TransportMode


class TestNLPService:
    """Test suite for NLP service functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.nlp_service = NLPService()
    
    def test_parse_simple_price_query(self):
        """Test parsing simple price-based queries"""
        query = "houses under £500k"
        criteria, entities = self.nlp_service.parse_query(query)
        
        assert criteria.max_price == 500000
        assert len(entities) >= 1
        
        # Check that price entity was extracted
        price_entities = [e for e in entities if e.entity_type == 'max_price']
        assert len(price_entities) == 1
        assert price_entities[0].value == 500000
        assert price_entities[0].confidence > 0.8
    
    def test_parse_price_range_query(self):
        """Test parsing price range queries"""
        query = "flats between £300k and £600k"
        criteria, entities = self.nlp_service.parse_query(query)
        
        assert criteria.min_price == 300000
        assert criteria.max_price == 600000
        
        # Check price range entity
        price_entities = [e for e in entities if e.entity_type == 'price_range']
        assert len(price_entities) == 1
        assert price_entities[0].value == (300000, 600000)
    
    def test_parse_bedroom_query(self):
        """Test parsing bedroom requirements"""
        test_cases = [
            ("2 bedroom flat", 2),
            ("3 bed house", 3),
            ("4br property", 4),
            ("1 bedroom apartment", 1)
        ]
        
        for query, expected_bedrooms in test_cases:
            criteria, entities = self.nlp_service.parse_query(query)
            
            assert criteria.min_bedrooms == expected_bedrooms
            assert criteria.max_bedrooms == expected_bedrooms
            
            bedroom_entities = [e for e in entities if e.entity_type == 'bedrooms']
            assert len(bedroom_entities) == 1
            assert bedroom_entities[0].value == expected_bedrooms
    
    def test_parse_amenity_query(self):
        """Test parsing amenity-based queries"""
        query = "house near train station"
        criteria, entities = self.nlp_service.parse_query(query)
        
        assert len(criteria.amenity_filters) == 1
        amenity_filter = criteria.amenity_filters[0]
        assert amenity_filter.amenity_type == AmenityType.TRAIN_STATION
        assert amenity_filter.required == True
        
        # Check extracted entities
        amenity_entities = [e for e in entities if e.entity_type == 'amenity']
        assert len(amenity_entities) == 1
        assert amenity_entities[0].value['amenity_type'] == AmenityType.TRAIN_STATION
    
    def test_parse_walking_distance_query(self):
        """Test parsing walking distance requirements"""
        query = "flat within 10 minutes walk of tube station"
        criteria, entities = self.nlp_service.parse_query(query)
        
        assert len(criteria.amenity_filters) == 1
        amenity_filter = criteria.amenity_filters[0]
        assert amenity_filter.amenity_type == AmenityType.UNDERGROUND_STATION
        assert amenity_filter.walking_distance == True
        # 10 minutes walk ≈ 0.83 km (5 km/h walking speed)
        assert abs(amenity_filter.max_distance - 0.83) < 0.1
    
    def test_parse_property_type_query(self):
        """Test parsing property type requirements"""
        test_cases = [
            ("detached house", PropertyType.HOUSE),
            ("semi-detached property", PropertyType.HOUSE),
            ("flat in London", PropertyType.FLAT),
            ("terraced house", PropertyType.HOUSE),
            ("bungalow for sale", PropertyType.BUNGALOW),
            ("maisonette", PropertyType.MAISONETTE)
        ]
        
        for query, expected_type in test_cases:
            criteria, entities = self.nlp_service.parse_query(query)
            
            assert expected_type in criteria.property_types
            
            property_entities = [e for e in entities if e.entity_type == 'property_type']
            assert len(property_entities) >= 1
            assert any(e.value == expected_type for e in property_entities)
    
    def test_parse_commute_query(self):
        """Test parsing commute-based requirements"""
        query = "house 30 minutes to Central London"
        criteria, entities = self.nlp_service.parse_query(query)
        
        assert len(criteria.commute_filters) == 1
        commute_filter = criteria.commute_filters[0]
        assert commute_filter.max_commute_minutes == 30
        assert commute_filter.destination_address == "Central London"
        assert TransportMode.PUBLIC_TRANSPORT in commute_filter.transport_modes
    
    def test_parse_complex_query(self):
        """Test parsing complex multi-criteria queries"""
        query = "2 bedroom flat near park under £400k within 20 minutes to work"
        criteria, entities = self.nlp_service.parse_query(query)
        
        # Should extract multiple entities
        assert len(entities) >= 4
        
        # Check individual criteria
        assert criteria.min_bedrooms == 2
        assert criteria.max_bedrooms == 2
        assert criteria.max_price == 400000
        assert PropertyType.FLAT in criteria.property_types
        assert len(criteria.amenity_filters) >= 1
        
        # Check that park amenity was detected
        park_filters = [f for f in criteria.amenity_filters 
                       if f.amenity_type == AmenityType.PARK]
        assert len(park_filters) == 1
    
    def test_autocomplete_suggestions_empty_query(self):
        """Test autocomplete suggestions for empty query"""
        suggestions = self.nlp_service.get_autocomplete_suggestions("", limit=5)
        
        assert len(suggestions) == 5
        assert all(isinstance(s, SearchSuggestion) for s in suggestions)
        assert all(s.confidence > 0 for s in suggestions)
    
    def test_autocomplete_suggestions_partial_match(self):
        """Test autocomplete suggestions for partial queries"""
        suggestions = self.nlp_service.get_autocomplete_suggestions("near train", limit=10)
        
        # Should return suggestions related to train stations
        assert len(suggestions) > 0
        train_suggestions = [s for s in suggestions if 'train' in s.text.lower()]
        assert len(train_suggestions) > 0
        
        # Check that suggestions are sorted by confidence
        confidences = [s.confidence for s in suggestions]
        assert confidences == sorted(confidences, reverse=True)
    
    def test_autocomplete_suggestions_price_query(self):
        """Test autocomplete suggestions for price-related queries"""
        suggestions = self.nlp_service.get_autocomplete_suggestions("under £", limit=10)
        
        price_suggestions = [s for s in suggestions if '£' in s.text]
        assert len(price_suggestions) > 0
        
        # Check that price suggestions have appropriate filters
        for suggestion in price_suggestions:
            if suggestion.filters and 'max_price' in suggestion.filters:
                assert isinstance(suggestion.filters['max_price'], int)
                assert suggestion.filters['max_price'] > 0
    
    def test_query_intent_detection(self):
        """Test detection of query intents"""
        test_cases = [
            ("houses in London", QueryIntent.LOCATION_SEARCH),
            ("near train station", QueryIntent.AMENITY_PROXIMITY),
            ("under £500k", QueryIntent.PRICE_RANGE),
            ("2 bedroom flat", QueryIntent.PROPERTY_TYPE),
            ("30 minutes to work", QueryIntent.COMMUTE_BASED),
            ("2 bed flat near park under £400k in London", QueryIntent.MIXED)
        ]
        
        for query, expected_intent in test_cases:
            intent = self.nlp_service.detect_query_intent(query)
            assert intent == expected_intent
    
    def test_search_examples(self):
        """Test that search examples are provided"""
        examples = self.nlp_service.get_search_examples()
        
        assert len(examples) > 0
        assert all(isinstance(example, str) for example in examples)
        assert all(len(example) > 0 for example in examples)
    
    def test_entity_extraction_confidence_scores(self):
        """Test that entity extraction includes appropriate confidence scores"""
        query = "3 bedroom house near gym under £600k"
        criteria, entities = self.nlp_service.parse_query(query)
        
        assert len(entities) >= 3
        
        # All entities should have confidence scores
        for entity in entities:
            assert hasattr(entity, 'confidence')
            assert 0.0 <= entity.confidence <= 1.0
        
        # High-confidence entities (exact matches)
        bedroom_entities = [e for e in entities if e.entity_type == 'bedrooms']
        if bedroom_entities:
            assert bedroom_entities[0].confidence >= 0.9
        
        price_entities = [e for e in entities if e.entity_type == 'max_price']
        if price_entities:
            assert price_entities[0].confidence >= 0.8
    
    def test_entity_position_tracking(self):
        """Test that entities track their position in the original text"""
        query = "2 bedroom flat under £400k"
        criteria, entities = self.nlp_service.parse_query(query)
        
        for entity in entities:
            assert hasattr(entity, 'start_pos')
            assert hasattr(entity, 'end_pos')
            assert hasattr(entity, 'original_text')
            assert 0 <= entity.start_pos < entity.end_pos <= len(query)
            
            # Check that the original text matches the query substring
            extracted_text = query[entity.start_pos:entity.end_pos].lower()
            assert entity.original_text.lower() in extracted_text or extracted_text in entity.original_text.lower()
    
    def test_price_parsing_edge_cases(self):
        """Test edge cases in price parsing"""
        test_cases = [
            ("£500,000", 500000),
            ("500k", 500000),
            ("1.5k", 1500),
            ("£1,200,000", 1200000),
            ("2.5K", 2500)
        ]
        
        for price_str, expected_value in test_cases:
            parsed_value = self.nlp_service._parse_price_value(price_str.replace('£', ''))
            assert parsed_value == expected_value
    
    def test_amenity_distance_extraction(self):
        """Test extraction of distance information for amenities"""
        test_cases = [
            ("gym within 1km", 1.0, False),
            ("park within 500 meters", 0.5, False),
            ("train station within 5 minutes walk", 0.42, True),  # ~5 min walk at 5km/h
            ("school within 2 miles", 3.218, False)  # 2 miles to km
        ]
        
        for query, expected_distance, expected_walking in test_cases:
            criteria, entities = self.nlp_service.parse_query(query)
            
            if criteria.amenity_filters:
                amenity_filter = criteria.amenity_filters[0]
                assert abs(amenity_filter.max_distance - expected_distance) < 0.1
                assert amenity_filter.walking_distance == expected_walking
    
    def test_suggestion_filtering_and_scoring(self):
        """Test that suggestions are properly filtered and scored"""
        # Test with a specific query that should match certain suggestions
        suggestions = self.nlp_service.get_autocomplete_suggestions("train station", limit=5)
        
        # Should return suggestions related to train stations
        relevant_suggestions = [s for s in suggestions if 'train' in s.text.lower()]
        assert len(relevant_suggestions) > 0
        
        # Test scoring function directly
        test_suggestion = SearchSuggestion(
            text="within 10 minutes walk of a train station",
            description="Properties close to public transport",
            category="transport"
        )
        
        score = self.nlp_service._calculate_suggestion_score("train station", test_suggestion)
        assert score > 0.5  # Should have good relevance score
        
        score_partial = self.nlp_service._calculate_suggestion_score("train", test_suggestion)
        assert score_partial > 0.3  # Should have some relevance
        
        score_irrelevant = self.nlp_service._calculate_suggestion_score("garden", test_suggestion)
        assert score_irrelevant == 0.0  # Should have no relevance


class TestNLPServiceIntegration:
    """Integration tests for NLP service with SearchCriteria validation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.nlp_service = NLPService()
    
    def test_parsed_criteria_validation(self):
        """Test that parsed criteria pass SearchCriteria validation"""
        valid_queries = [
            "2 bedroom flat under £500k",
            "house near park",
            "property between £300k and £600k",
            "3 bed house within 30 minutes to Central London"
        ]
        
        for query in valid_queries:
            criteria, entities = self.nlp_service.parse_query(query)
            
            # Should be able to create a valid SearchCriteria object
            assert isinstance(criteria, SearchCriteria)
            
            # Should be serializable
            criteria_dict = criteria.model_dump()
            assert isinstance(criteria_dict, dict)
    
    def test_invalid_query_handling(self):
        """Test handling of queries that might produce invalid criteria"""
        problematic_queries = [
            "",  # Empty query
            "xyz abc def",  # Nonsense query
            "£0 to £-100",  # Invalid price range
            "0 bedroom house"  # Edge case
        ]
        
        for query in problematic_queries:
            # Should not raise exceptions
            criteria, entities = self.nlp_service.parse_query(query)
            assert isinstance(criteria, SearchCriteria)
    
    def test_suggestion_filter_generation(self):
        """Test that suggestions generate valid filter dictionaries"""
        suggestions = self.nlp_service.get_autocomplete_suggestions("", limit=10)
        
        for suggestion in suggestions:
            if suggestion.filters:
                # Should be able to create SearchCriteria from suggestion filters
                try:
                    criteria = SearchCriteria(**suggestion.filters)
                    assert isinstance(criteria, SearchCriteria)
                except Exception as e:
                    pytest.fail(f"Suggestion '{suggestion.text}' has invalid filters: {e}")


if __name__ == "__main__":
    pytest.main([__file__])