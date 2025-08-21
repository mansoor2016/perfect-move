"""
Celery tasks for property data ingestion
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from celery import Task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.db.models import Property as PropertyModel
from .service import IngestionService
from .data_quality import DataQualityValidator

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task class that provides database session management"""
    
    def __call__(self, *args, **kwargs):
        with SessionLocal() as db:
            try:
                return self.run(db, *args, **kwargs)
            except Exception as e:
                db.rollback()
                logger.error(f"Task {self.name} failed: {str(e)}")
                raise
            finally:
                db.close()
    
    def run(self, db: Session, *args, **kwargs):
        """Override this method in subclasses"""
        raise NotImplementedError


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3, default_retry_delay=300)
def sync_properties_for_location(self, db: Session, location: str, 
                               radius_km: float = 5, max_results: int = 100) -> Dict[str, Any]:
    """
    Background task to sync properties from all sources for a location
    """
    import asyncio
    
    try:
        logger.info(f"Starting property sync for {location} (radius: {radius_km}km, max: {max_results})")
        
        # Initialize ingestion service
        ingestion_service = IngestionService()
        
        # Sync properties from all sources (run async function in sync context)
        properties = asyncio.run(ingestion_service.sync_properties_for_location(
            location, radius_km, max_results
        ))
        
        # Save to database
        saved_properties = ingestion_service.save_properties_to_db(properties, db)
        
        # Run data quality validation
        validator = DataQualityValidator()
        quality_report = validator.validate_batch(properties)
        
        result = {
            'location': location,
            'properties_fetched': len(properties),
            'properties_saved': len(saved_properties),
            'quality_score': quality_report.get('overall_score', 0.0),
            'sync_time': datetime.now().isoformat(),
            'issues': quality_report.get('issues', [])
        }
        
        logger.info(f"Completed property sync for {location}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in sync_properties_for_location: {str(e)}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3)
def sync_rightmove_properties(self, db: Session, location: str, 
                            radius_km: float = 5, max_results: int = 100) -> Dict[str, Any]:
    """Background task to sync properties from Rightmove only"""
    import asyncio
    
    try:
        logger.info(f"Starting Rightmove sync for {location}")
        
        ingestion_service = IngestionService()
        properties = asyncio.run(ingestion_service.sync_rightmove_properties(
            location, radius_km, max_results
        ))
        
        saved_properties = ingestion_service.save_properties_to_db(properties, db)
        
        return {
            'source': 'rightmove',
            'location': location,
            'properties_fetched': len(properties),
            'properties_saved': len(saved_properties),
            'sync_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in sync_rightmove_properties: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, base=DatabaseTask, max_retries=3)
def sync_zoopla_properties(self, db: Session, location: str, 
                         radius_km: float = 5, max_results: int = 100) -> Dict[str, Any]:
    """Background task to sync properties from Zoopla only"""
    import asyncio
    
    try:
        logger.info(f"Starting Zoopla sync for {location}")
        
        ingestion_service = IngestionService()
        properties = asyncio.run(ingestion_service.sync_zoopla_properties(
            location, radius_km, max_results
        ))
        
        saved_properties = ingestion_service.save_properties_to_db(properties, db)
        
        return {
            'source': 'zoopla',
            'location': location,
            'properties_fetched': len(properties),
            'properties_saved': len(saved_properties),
            'sync_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in sync_zoopla_properties: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, base=DatabaseTask)
def incremental_sync_properties(self, db: Session, location: str, 
                              last_sync_time: Optional[str] = None) -> Dict[str, Any]:
    """
    Incremental sync that only processes properties changed since last sync
    """
    try:
        logger.info(f"Starting incremental sync for {location}")
        
        # Parse last sync time
        since_time = None
        if last_sync_time:
            since_time = datetime.fromisoformat(last_sync_time)
        else:
            # Default to last 24 hours if no time provided
            since_time = datetime.now() - timedelta(hours=24)
        
        import asyncio
        
        ingestion_service = IngestionService()
        
        # Get all properties for location
        all_properties = asyncio.run(ingestion_service.sync_properties_for_location(location))
        
        # Filter for new/updated properties
        new_or_updated = []
        for prop in all_properties:
            # Check if property exists in database
            existing = db.query(PropertyModel).filter(
                PropertyModel.source == prop.get('source'),
                PropertyModel.source_id == prop.get('source_id')
            ).first()
            
            if not existing:
                # New property
                new_or_updated.append(prop)
            elif existing.last_updated < since_time:
                # Property might have been updated
                new_or_updated.append(prop)
        
        # Save only new/updated properties
        saved_properties = ingestion_service.save_properties_to_db(new_or_updated, db)
        
        return {
            'location': location,
            'since_time': since_time.isoformat(),
            'total_properties_checked': len(all_properties),
            'new_or_updated': len(new_or_updated),
            'properties_saved': len(saved_properties),
            'sync_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in incremental_sync_properties: {str(e)}")
        raise


@celery_app.task(bind=True, base=DatabaseTask)
def cleanup_old_properties(self, db: Session, days_old: int = 30) -> Dict[str, Any]:
    """Remove properties that haven't been updated in specified days"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Find old properties
        old_properties = db.query(PropertyModel).filter(
            PropertyModel.last_updated < cutoff_date
        ).all()
        
        # Delete old properties
        deleted_count = 0
        for prop in old_properties:
            db.delete(prop)
            deleted_count += 1
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_count} properties older than {days_old} days")
        
        return {
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'cleanup_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_properties: {str(e)}")
        db.rollback()
        raise


@celery_app.task(bind=True, base=DatabaseTask)
def validate_property_data_quality(self, db: Session, batch_size: int = 1000) -> Dict[str, Any]:
    """Run data quality validation on existing properties"""
    try:
        logger.info("Starting data quality validation")
        
        validator = DataQualityValidator()
        
        # Process properties in batches
        offset = 0
        total_processed = 0
        total_issues = 0
        
        while True:
            properties = db.query(PropertyModel).offset(offset).limit(batch_size).all()
            
            if not properties:
                break
            
            # Convert to dict format for validation
            property_dicts = []
            for prop in properties:
                prop_dict = {
                    'id': str(prop.id),
                    'source': prop.source,
                    'source_id': prop.source_id,
                    'price': prop.price,
                    'address': prop.address,
                    'bedrooms': prop.bedrooms,
                    'bathrooms': prop.bathrooms,
                    'property_type': prop.property_type,
                    'latitude': prop.location.latitude if prop.location else None,
                    'longitude': prop.location.longitude if prop.location else None,
                    'reliability_score': prop.reliability_score
                }
                property_dicts.append(prop_dict)
            
            # Validate batch
            batch_report = validator.validate_batch(property_dicts)
            total_issues += len(batch_report.get('issues', []))
            
            total_processed += len(properties)
            offset += batch_size
        
        return {
            'total_properties_validated': total_processed,
            'total_issues_found': total_issues,
            'validation_time': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in validate_property_data_quality: {str(e)}")
        raise


@celery_app.task(bind=True)
def sync_property_details(self, source: str, property_id: str) -> Dict[str, Any]:
    """Fetch detailed information for a specific property"""
    import asyncio
    
    try:
        logger.info(f"Fetching details for {source} property {property_id}")
        
        ingestion_service = IngestionService()
        property_details = asyncio.run(ingestion_service.get_property_details(source, property_id))
        
        if property_details:
            # Save to database
            with SessionLocal() as db:
                saved_properties = ingestion_service.save_properties_to_db([property_details], db)
                
            return {
                'source': source,
                'property_id': property_id,
                'details_fetched': property_details is not None,
                'saved': len(saved_properties) > 0,
                'fetch_time': datetime.now().isoformat()
            }
        else:
            return {
                'source': source,
                'property_id': property_id,
                'details_fetched': False,
                'error': 'Property not found or fetch failed'
            }
            
    except Exception as e:
        logger.error(f"Error fetching property details: {str(e)}")
        raise self.retry(exc=e, countdown=60)


# Utility functions for task management
def schedule_location_sync(location: str, radius_km: float = 5, max_results: int = 100):
    """Schedule a property sync for a specific location"""
    return sync_properties_for_location.delay(location, radius_km, max_results)


def schedule_incremental_sync(location: str, last_sync_time: Optional[str] = None):
    """Schedule an incremental sync for a location"""
    return incremental_sync_properties.delay(location, last_sync_time)


def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get the status of a Celery task"""
    result = celery_app.AsyncResult(task_id)
    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None,
        'traceback': result.traceback if result.failed() else None
    }