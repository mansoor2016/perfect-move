"""
Demonstration of the NLP service functionality for natural language property search.
"""

from app.modules.search.nlp_service import NLPService

def demo_nlp_functionality():
    """Demonstrate the NLP service capabilities"""
    nlp_service = NLPService()
    
    print("🏠 Advanced Property Search - Natural Language Processing Demo")
    print("=" * 60)
    
    # Test queries that demonstrate different capabilities
    test_queries = [
        "2 bedroom flat under £400k",
        "house near train station within 10 minutes walk",
        "3 bed house between £300k and £600k",
        "flat near park and gym under £500k",
        "property 30 minutes to Central London",
        "quiet bungalow with garden near school",
        "2 bedroom apartment within 500 meters of tube station"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: \"{query}\"")
        print("-" * 40)
        
        # Parse the query
        criteria, entities = nlp_service.parse_query(query)
        
        # Show extracted entities
        print("🔍 Extracted entities:")
        for entity in entities:
            print(f"  • {entity.entity_type}: {entity.value} (confidence: {entity.confidence:.2f})")
        
        # Show parsed criteria summary
        print("📋 Parsed search criteria:")
        if criteria.min_price or criteria.max_price:
            price_range = f"£{criteria.min_price or 0:,} - £{criteria.max_price or '∞'}"
            print(f"  • Price range: {price_range}")
        
        if criteria.min_bedrooms or criteria.max_bedrooms:
            bedrooms = f"{criteria.min_bedrooms or 0} - {criteria.max_bedrooms or '∞'}"
            print(f"  • Bedrooms: {bedrooms}")
        
        if criteria.property_types:
            print(f"  • Property types: {', '.join([pt.value for pt in criteria.property_types])}")
        
        if criteria.amenity_filters:
            print("  • Amenity requirements:")
            for amenity in criteria.amenity_filters:
                distance_desc = f"{amenity.max_distance:.1f}km"
                if amenity.walking_distance:
                    distance_desc += " (walking)"
                print(f"    - {amenity.amenity_type.value} within {distance_desc}")
        
        if criteria.commute_filters:
            print("  • Commute requirements:")
            for commute in criteria.commute_filters:
                print(f"    - {commute.max_commute_minutes} min to {commute.destination_address}")
        
        # Show query intent
        intent = nlp_service.detect_query_intent(query)
        print(f"🎯 Query intent: {intent.value}")
    
    print("\n" + "=" * 60)
    print("🔮 Autocomplete Suggestions Demo")
    print("=" * 60)
    
    # Test autocomplete functionality
    partial_queries = [
        "near train",
        "under £",
        "2 bed",
        "quiet area"
    ]
    
    for partial in partial_queries:
        print(f"\n💭 Partial query: \"{partial}\"")
        suggestions = nlp_service.get_autocomplete_suggestions(partial, limit=3)
        
        print("💡 Suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.text}")
            print(f"     {suggestion.description} (confidence: {suggestion.confidence:.2f})")
    
    print("\n" + "=" * 60)
    print("📚 Example Queries")
    print("=" * 60)
    
    examples = nlp_service.get_search_examples()
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example}")
    
    print("\n✅ NLP Service demonstration complete!")

if __name__ == "__main__":
    demo_nlp_functionality()