from typing import Optional, Dict, Any, List
import httpx
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from geoalchemy2.functions import ST_DWithin, ST_GeogFromText
from app.models.geospatial import Location, EnvironmentalData
from app.db.models import EnvironmentalData as EnvironmentalDataDB
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EnvironmentalDataService:
    """Service for fetching and managing environmental data"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache_duration_hours = 24  # Cache environmental data for 24 hours
    
    async def get_air_quality_data(self, location: Location) -> Optional[Dict[str, Any]]:
        """
        Fetch air quality data for a location
        Uses UK Air Quality API or similar service
        """
        try:
            # Example using UK Air Quality API (replace with actual API)
            url = "https://api.erg.ic.ac.uk/AirQuality/Hourly/MonitoringIndex/GroupName=London/Json"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Find closest monitoring station
                    closest_station = self._find_closest_air_quality_station(
                        data.get('HourlyAirQualityIndex', {}).get('LocalAuthority', []),
                        location
                    )
                    
                    if closest_station:
                        return {
                            'air_quality_index': closest_station.get('@AirQualityIndex'),
                            'air_quality_band': closest_station.get('@AirQualityBand'),
                            'measurement_time': closest_station.get('@IndexSource'),
                            'location': location,
                            'source': 'uk_air_quality_api'
                        }
                        
        except Exception as e:
            logger.error(f"Error fetching air quality data: {e}")
        
        return None
    
    def _find_closest_air_quality_station(self, stations: List[Dict], location: Location) -> Optional[Dict]:
        """Find the closest air quality monitoring station to the given location"""
        # This is a simplified implementation
        # In practice, you'd calculate distances to each station
        if stations:
            return stations[0]  # Return first station for now
        return None
    
    async def get_flood_risk_data(self, location: Location) -> Optional[Dict[str, Any]]:
        """
        Fetch flood risk data for a location
        Uses Environment Agency flood risk API
        """
        try:
            # Example using Environment Agency API
            url = f"https://environment.data.gov.uk/flood-monitoring/id/floodAreas"
            params = {
                'lat': location.latitude,
                'long': location.longitude,
                'dist': 5000  # 5km radius
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    flood_areas = data.get('items', [])
                    
                    if flood_areas:
                        # Determine risk level based on flood areas
                        risk_level = self._calculate_flood_risk_level(flood_areas)
                        return {
                            'flood_risk_level': risk_level,
                            'flood_areas_count': len(flood_areas),
                            'location': location,
                            'source': 'environment_agency'
                        }
                    else:
                        return {
                            'flood_risk_level': 'low',
                            'flood_areas_count': 0,
                            'location': location,
                            'source': 'environment_agency'
                        }
                        
        except Exception as e:
            logger.error(f"Error fetching flood risk data: {e}")
        
        return None
    
    def _calculate_flood_risk_level(self, flood_areas: List[Dict]) -> str:
        """Calculate flood risk level based on nearby flood areas"""
        if len(flood_areas) >= 3:
            return 'high'
        elif len(flood_areas) >= 1:
            return 'medium'
        else:
            return 'low'
    
    async def get_crime_statistics(self, location: Location) -> Optional[Dict[str, Any]]:
        """
        Fetch crime statistics for a location
        Uses Police API or similar service
        """
        try:
            # Example using UK Police API
            url = "https://data.police.uk/api/crimes-street/all-crime"
            params = {
                'lat': location.latitude,
                'lng': location.longitude,
                'date': datetime.now().strftime('%Y-%m')  # Current month
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                
                if response.status_code == 200:
                    crimes = response.json()
                    
                    # Calculate crime rate per 1000 residents (simplified)
                    crime_count = len(crimes)
                    estimated_population = 1000  # This should be actual population data
                    crime_rate = (crime_count / estimated_population) * 1000
                    
                    return {
                        'crime_rate': round(crime_rate, 2),
                        'crime_count': crime_count,
                        'location': location,
                        'period': datetime.now().strftime('%Y-%m'),
                        'source': 'police_api'
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching crime statistics: {e}")
        
        return None
    
    async def get_comprehensive_environmental_data(self, location: Location) -> Dict[str, Any]:
        """
        Fetch comprehensive environmental data for a location
        Combines air quality, flood risk, and crime statistics
        """
        # Fetch all environmental data concurrently
        air_quality_task = self.get_air_quality_data(location)
        flood_risk_task = self.get_flood_risk_data(location)
        crime_stats_task = self.get_crime_statistics(location)
        
        air_quality, flood_risk, crime_stats = await asyncio.gather(
            air_quality_task,
            flood_risk_task,
            crime_stats_task,
            return_exceptions=True
        )
        
        # Combine results
        environmental_data = {
            'location': location,
            'timestamp': datetime.now().isoformat(),
            'air_quality': air_quality if not isinstance(air_quality, Exception) else None,
            'flood_risk': flood_risk if not isinstance(flood_risk, Exception) else None,
            'crime_statistics': crime_stats if not isinstance(crime_stats, Exception) else None
        }
        
        # Cache the data
        await self._cache_environmental_data(environmental_data)
        
        return environmental_data
    
    async def _cache_environmental_data(self, data: Dict[str, Any]) -> None:
        """Cache environmental data in the database"""
        try:
            location = data['location']
            
            # Create environmental data record
            env_data = EnvironmentalDataDB(
                location=func.ST_GeogFromText(f'POINT({location.longitude} {location.latitude})'),
                area_name=location.address,
                air_quality_index=data.get('air_quality', {}).get('air_quality_index'),
                flood_risk=data.get('flood_risk', {}).get('flood_risk_level'),
                crime_rate=data.get('crime_statistics', {}).get('crime_rate'),
                data_source='comprehensive_fetch',
                measurement_date=datetime.now()
            )
            
            self.db.add(env_data)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error caching environmental data: {e}")
            self.db.rollback()
    
    def get_cached_environmental_data(self, location: Location, radius_km: float = 1.0) -> Optional[EnvironmentalData]:
        """
        Get cached environmental data for a location
        Returns cached data if available and fresh (within cache duration)
        """
        try:
            radius_meters = radius_km * 1000
            search_point = func.ST_GeogFromText(f'POINT({location.longitude} {location.latitude})')
            cutoff_time = datetime.now() - timedelta(hours=self.cache_duration_hours)
            
            # Find recent environmental data within radius
            result = self.db.query(EnvironmentalDataDB).filter(
                ST_DWithin(EnvironmentalDataDB.location, search_point, radius_meters),
                EnvironmentalDataDB.measurement_date >= cutoff_time
            ).order_by(
                EnvironmentalDataDB.measurement_date.desc()
            ).first()
            
            if result:
                # Extract coordinates
                coords_result = self.db.execute(
                    text("SELECT ST_Y(location::geometry) as lat, ST_X(location::geometry) as lng FROM environmental_data WHERE id = :id"),
                    {'id': str(result.id)}
                ).fetchone()
                
                if coords_result:
                    return EnvironmentalData(
                        location=Location(
                            latitude=coords_result.lat,
                            longitude=coords_result.lng,
                            address=result.area_name
                        ),
                        air_quality_index=result.air_quality_index,
                        flood_risk_level=result.flood_risk,
                        crime_rate=result.crime_rate
                    )
                    
        except Exception as e:
            logger.error(f"Error retrieving cached environmental data: {e}")
        
        return None
    
    async def refresh_environmental_data_if_stale(self, location: Location) -> Dict[str, Any]:
        """
        Check if cached data is stale and refresh if necessary
        """
        cached_data = self.get_cached_environmental_data(location)
        
        if cached_data is None:
            # No cached data, fetch fresh
            return await self.get_comprehensive_environmental_data(location)
        else:
            # Return cached data (it's fresh enough)
            return {
                'location': location,
                'timestamp': datetime.now().isoformat(),
                'air_quality': {'air_quality_index': cached_data.air_quality_index} if cached_data.air_quality_index else None,
                'flood_risk': {'flood_risk_level': cached_data.flood_risk_level} if cached_data.flood_risk_level else None,
                'crime_statistics': {'crime_rate': cached_data.crime_rate} if cached_data.crime_rate else None,
                'source': 'cached'
            }