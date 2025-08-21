#!/usr/bin/env python3
"""
Demo script to show ingestion functionality
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.modules.ingestion.service import IngestionService
from app.modules.ingestion.tasks import schedule_location_sync, get_task_status


async def demo_sync_ingestion():
    """Demo synchronous ingestion"""
    print("=== Demo: Synchronous Property Ingestion ===")
    
    service = IngestionService()
    
    # Sync properties for London
    print("Fetching properties for London...")
    properties = await service.sync_properties_for_location("London", radius_km=5, max_results=10)
    
    print(f"Found {len(properties)} unique properties after deduplication")
    
    # Show sample properties
    for i, prop in enumerate(properties[:3]):
        print(f"\nProperty {i+1}:")
        print(f"  Source: {prop.get('source')}")
        print(f"  Address: {prop.get('address')}")
        print(f"  Price: £{prop.get('price'):,}" if prop.get('price') else "  Price: Not available")
        print(f"  Bedrooms: {prop.get('bedrooms')}")
        print(f"  Reliability Score: {prop.get('reliability_score', 'N/A')}")


def demo_async_ingestion():
    """Demo asynchronous ingestion with Celery"""
    print("\n=== Demo: Asynchronous Property Ingestion ===")
    
    # Schedule a background task
    print("Scheduling background ingestion task for Manchester...")
    task = schedule_location_sync("Manchester", radius_km=5, max_results=10)
    
    print(f"Task scheduled with ID: {task.id}")
    print("In a real application, this would run in the background")
    
    # Check task status
    status = get_task_status(task.id)
    print(f"Task status: {status}")


def demo_data_quality():
    """Demo data quality validation"""
    print("\n=== Demo: Data Quality Validation ===")
    
    from app.modules.ingestion.data_quality import DataQualityValidator
    
    validator = DataQualityValidator()
    
    # Sample properties with various quality issues
    sample_properties = [
        {
            'source': 'rightmove',
            'source_id': 'rm_good',
            'address': '123 Perfect Street, London SW1 1AA',
            'price': 450000,
            'bedrooms': 3,
            'bathrooms': 2,
            'property_type': 'house',
            'latitude': 51.5074,
            'longitude': -0.1278
        },
        {
            'source': 'zoopla',
            'source_id': 'zp_issues',
            'address': 'Bad St',  # Too short
            'price': -100,  # Invalid
            'bedrooms': 50,  # Suspicious
            'latitude': 0.0,  # Invalid coordinates
            'longitude': 0.0
        }
    ]
    
    # Run validation
    report = validator.validate_batch(sample_properties)
    
    print(f"Validated {report.total_properties} properties")
    print(f"Valid properties: {report.valid_properties}")
    print(f"Overall quality score: {report.overall_score:.2f}")
    print(f"Issues found: {len(report.issues)}")
    
    # Show issues
    for issue in report.issues[:5]:  # Show first 5 issues
        print(f"  - {issue.severity.value.upper()}: {issue.description}")


async def main():
    """Main demo function"""
    print("Property Ingestion System Demo")
    print("=" * 40)
    
    try:
        # Demo sync ingestion
        await demo_sync_ingestion()
        
        # Demo async ingestion (requires Redis/Celery setup)
        try:
            demo_async_ingestion()
        except Exception as e:
            print(f"\nAsync demo skipped (requires Redis/Celery): {e}")
        
        # Demo data quality
        demo_data_quality()
        
        print("\n=== Demo Complete ===")
        print("The ingestion system is ready for production use!")
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())