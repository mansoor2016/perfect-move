from typing import List, Tuple, Optional, Dict, Any
import math
import httpx
import asyncio
from datetime import datetime
from geopy.distance import geodesic
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_GeogFromText, ST_AsText
from app.models.geospatial import Location, Amenity, CommuteInfo, EnvironmentalData, TransportLink
from app.db.models import Amenity as AmenityDB, Property as PropertyDB
from app.core.config import settings
from .environmental_service import EnvironmentalDataService
from .transport_service import TransportDataService
import logging

logger = logging.getLogger(__name__)


class GeospatialService:
    """Service for geospatial operations and location-based queries"""
    
    def __init__(self, db: Session):
        self.db = db
        self.mapbox_api_key = getattr(settings, 'MAPBOX_API_KEY', None)
        self.environmental_service = EnvironmentalDataService(db)
        self.transport_service = TransportDataService(db)
        
    def calculate_distance(self, point1: Location, point2: Location) -> float:
        """
        Calculate straight-line distance between two points using geodesic calculation
        Returns distance in kilometers
        """
        try:
            coord1 = (point1.latitude, point1.longitude)
            coord2 = (point2.latitude, point2.longitude)
            distance = geodesic(coord1, coord2).kilometers
            return round(distance, 3)
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return 0.0
    
    def calculate_distance_postgis(self, point1: Location, point2: Location) -> float:
        """
        Calculate straight-line distance using PostGIS ST_Distance
        Returns distance in meters, converted to kilometers
        """
        try:
            query = text("""
                SELECT ST_Distance(
                    ST_GeogFromText('POINT(:lon1 :lat1)'),
                    ST_GeogFromText('POINT(:lon2 :lat2)')
                ) as distance
            """)
            
            result = self.db.execute(query, {
                'lat1': point1.latitude,
                'lon1': point1.longitude,
                'lat2': point2.latitude,
                'lon2': point2.longitude
            }).fetchone()
            
            if result:
                # Convert meters to kilometers
                return round(result.distance / 1000, 3)
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating PostGIS distance: {e}")
            return 0.0
    
    async def calculate_walking_distance(self, point1: Location, point2: Location) -> Optional[CommuteInfo]:
        """
        Calculate walking distance and time using Mapbox Directions API
        Returns CommuteInfo with duration and distance, or None if API unavailable
        """
        if not self.mapbox_api_key:
            logger.warning("Mapbox API key not configured, falling back to straight-line distance")
            straight_distance = self.calculate_distance(point1, point2)
            # Estimate walking time: average 5 km/h walking speed
            estimated_minutes = int((straight_distance / 5) * 60)
            return CommuteInfo(
                origin=point1,
                destination=point2,
                duration_minutes=estimated_minutes,
                distance_km=straight_distance,
                transport_mode="walking_estimated"
            )
        
        try:
            url = f"https://api.mapbox.com/directions/v5/mapbox/walking/{point1.longitude},{point1.latitude};{point2.longitude},{point2.latitude}"
            params = {
                'access_token': self.mapbox_api_key,
                'geometries': 'geojson',
                'overview': 'simplified'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('routes'):
                        route = data['routes'][0]
                        duration_seconds = route['duration']
                        distance_meters = route['distance']
                        
                        return CommuteInfo(
                            origin=point1,
                            destination=point2,
                            duration_minutes=int(duration_seconds / 60),
                            distance_km=round(distance_meters / 1000, 3),
                            transport_mode="walking",
                            route_details={
                                'geometry': route.get('geometry'),
                                'legs': route.get('legs', [])
                            }
                        )
                else:
                    logger.warning(f"Mapbox API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error calculating walking distance: {e}")
        
        # Fallback to straight-line distance
        return await self._fallback_walking_estimate(point1, point2)
    
    async def _fallback_walking_estimate(self, point1: Location, point2: Location) -> CommuteInfo:
        """Fallback walking estimate when API is unavailable"""
        straight_distance = self.calculate_distance(point1, point2)
        # Estimate walking time with 1.3x factor for actual walking routes
        estimated_distance = straight_distance * 1.3
        estimated_minutes = int((estimated_distance / 5) * 60)  # 5 km/h average
        
        return CommuteInfo(
            origin=point1,
            destination=point2,
            duration_minutes=estimated_minutes,
            distance_km=estimated_distance,
            transport_mode="walking_estimated"
        )
    
    def find_nearby_amenities(
        self, 
        location: Location, 
        amenity_category: str, 
        radius_km: float,
        limit: int = 50
    ) -> List[Amenity]:
        """
        Find amenities within radius of location using PostGIS spatial queries
        """
        try:
            # Convert radius from km to meters for PostGIS
            radius_meters = radius_km * 1000
            
            # Create point geometry for the search location
            search_point = func.ST_GeogFromText(f'POINT({location.longitude} {location.latitude})')
            
            # Query amenities within radius
            query = self.db.query(AmenityDB).filter(
                AmenityDB.category == amenity_category,
                ST_DWithin(AmenityDB.location, search_point, radius_meters)
            ).order_by(
                ST_Distance(AmenityDB.location, search_point)
            ).limit(limit)
            
            amenities = []
            for amenity_db in query.all():
                # Extract coordinates from PostGIS geometry
                coords_result = self.db.execute(
                    text("SELECT ST_Y(location::geometry) as lat, ST_X(location::geometry) as lng FROM amenities WHERE id = :id"),
                    {'id': str(amenity_db.id)}
                ).fetchone()
                
                if coords_result:
                    amenity_location = Location(
                        latitude=coords_result.lat,
                        longitude=coords_result.lng,
                        address=amenity_db.address
                    )
                    
                    amenity = Amenity(
                        id=str(amenity_db.id),
                        name=amenity_db.name,
                        category=amenity_db.category,
                        location=amenity_location,
                        opening_hours=amenity_db.opening_hours or {},
                        contact_info={
                            'website': amenity_db.website,
                            'phone': amenity_db.phone
                        } if amenity_db.website or amenity_db.phone else {}
                    )
                    amenities.append(amenity)
            
            return amenities
            
        except Exception as e:
            logger.error(f"Error finding nearby amenities: {e}")
            return []
    
    def find_properties_within_radius(
        self, 
        location: Location, 
        radius_km: float,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find properties within radius of location
        Returns list of property data with distances
        """
        try:
            radius_meters = radius_km * 1000
            search_point = func.ST_GeogFromText(f'POINT({location.longitude} {location.latitude})')
            
            # Query properties within radius with distance calculation
            query = self.db.query(
                PropertyDB,
                ST_Distance(PropertyDB.location, search_point).label('distance_meters')
            ).filter(
                ST_DWithin(PropertyDB.location, search_point, radius_meters)
            ).order_by(
                ST_Distance(PropertyDB.location, search_point)
            ).limit(limit)
            
            properties = []
            for property_db, distance_meters in query.all():
                # Extract coordinates
                coords_result = self.db.execute(
                    text("SELECT ST_Y(location::geometry) as lat, ST_X(location::geometry) as lng FROM properties WHERE id = :id"),
                    {'id': str(property_db.id)}
                ).fetchone()
                
                if coords_result:
                    property_data = {
                        'id': str(property_db.id),
                        'title': property_db.title,
                        'price': property_db.price,
                        'bedrooms': property_db.bedrooms,
                        'property_type': property_db.property_type,
                        'address': property_db.address,
                        'location': {
                            'latitude': coords_result.lat,
                            'longitude': coords_result.lng
                        },
                        'distance_km': round(distance_meters / 1000, 3)
                    }
                    properties.append(property_data)
            
            return properties
            
        except Exception as e:
            logger.error(f"Error finding properties within radius: {e}")
            return []
    
    async def get_commute_isochrone(
        self, 
        location: Location, 
        max_minutes: int,
        transport_mode: str = "walking"
    ) -> Optional[Dict[str, Any]]:
        """
        Get commute isochrone data using Mapbox Isochrone API
        Returns GeoJSON polygon representing reachable area
        """
        if not self.mapbox_api_key:
            logger.warning("Mapbox API key not configured for isochrone calculation")
            return None
        
        try:
            # Convert minutes to seconds
            max_seconds = max_minutes * 60
            
            url = f"https://api.mapbox.com/isochrone/v1/mapbox/{transport_mode}/{location.longitude},{location.latitude}"
            params = {
                'contours_minutes': max_minutes,
                'polygons': 'true',
                'access_token': self.mapbox_api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'type': 'isochrone',
                        'transport_mode': transport_mode,
                        'max_minutes': max_minutes,
                        'center': {
                            'latitude': location.latitude,
                            'longitude': location.longitude
                        },
                        'geojson': data
                    }
                else:
                    logger.warning(f"Mapbox Isochrone API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error getting commute isochrone: {e}")
        
        return None
    
    def get_amenity_density(self, location: Location, radius_km: float = 1.0) -> Dict[str, int]:
        """
        Calculate amenity density around a location
        Returns count of amenities by category within radius
        """
        try:
            radius_meters = radius_km * 1000
            search_point = func.ST_GeogFromText(f'POINT({location.longitude} {location.latitude})')
            
            # Query amenity counts by category
            query = self.db.query(
                AmenityDB.category,
                func.count(AmenityDB.id).label('count')
            ).filter(
                ST_DWithin(AmenityDB.location, search_point, radius_meters)
            ).group_by(AmenityDB.category)
            
            density = {}
            for category, count in query.all():
                density[category] = count
            
            return density
            
        except Exception as e:
            logger.error(f"Error calculating amenity density: {e}")
            return {}
    
    async def get_location_insights(self, location: Location) -> Dict[str, Any]:
        """
        Get comprehensive location insights including environmental and transport data
        """
        try:
            # Fetch all data concurrently
            environmental_data_task = self.environmental_service.refresh_environmental_data_if_stale(location)
            transport_score_task = self.transport_service.calculate_transport_score(location)
            amenity_density_task = self.get_amenity_density(location, radius_km=1.0)
            nearby_transport_task = self.transport_service.get_nearby_transport_links(location, radius_meters=500)
            
            environmental_data, transport_score, amenity_density, nearby_transport = await asyncio.gather(
                environmental_data_task,
                transport_score_task,
                amenity_density_task,
                nearby_transport_task,
                return_exceptions=True
            )
            
            # Compile insights
            insights = {
                'location': location,
                'timestamp': datetime.now().isoformat(),
                'environmental_data': environmental_data if not isinstance(environmental_data, Exception) else None,
                'transport_score': transport_score if not isinstance(transport_score, Exception) else None,
                'amenity_density': amenity_density if not isinstance(amenity_density, Exception) else {},
                'nearby_transport': nearby_transport if not isinstance(nearby_transport, Exception) else [],
                'overall_score': self._calculate_overall_location_score(
                    environmental_data, transport_score, amenity_density
                )
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting location insights: {e}")
            return {
                'location': location,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _calculate_overall_location_score(
        self, 
        environmental_data: Dict[str, Any], 
        transport_score: Dict[str, Any], 
        amenity_density: Dict[str, int]
    ) -> Dict[str, Any]:
        """Calculate an overall location desirability score"""
        try:
            scores = {
                'transport': 0,
                'environmental': 0,
                'amenities': 0,
                'overall': 0
            }
            
            # Transport score (0-100)
            if transport_score and 'transport_score' in transport_score:
                scores['transport'] = transport_score['transport_score']
            
            # Environmental score (0-100)
            env_score = 50  # Default neutral score
            if environmental_data and not isinstance(environmental_data, Exception):
                # Air quality (lower AQI is better)
                air_quality = environmental_data.get('air_quality', {})
                if air_quality and 'air_quality_index' in air_quality:
                    aqi = air_quality['air_quality_index']
                    if aqi <= 50:
                        env_score += 20
                    elif aqi <= 100:
                        env_score += 10
                    elif aqi > 150:
                        env_score -= 20
                
                # Flood risk
                flood_risk = environmental_data.get('flood_risk', {})
                if flood_risk and 'flood_risk_level' in flood_risk:
                    risk_level = flood_risk['flood_risk_level']
                    if risk_level == 'low':
                        env_score += 15
                    elif risk_level == 'high':
                        env_score -= 25
                
                # Crime rate (lower is better)
                crime_stats = environmental_data.get('crime_statistics', {})
                if crime_stats and 'crime_rate' in crime_stats:
                    crime_rate = crime_stats['crime_rate']
                    if crime_rate < 20:
                        env_score += 15
                    elif crime_rate > 50:
                        env_score -= 20
            
            scores['environmental'] = max(0, min(100, env_score))
            
            # Amenities score (0-100)
            total_amenities = sum(amenity_density.values()) if amenity_density else 0
            amenity_score = min(100, total_amenities * 2)  # Scale amenity count
            scores['amenities'] = amenity_score
            
            # Overall score (weighted average)
            scores['overall'] = int(
                scores['transport'] * 0.4 +
                scores['environmental'] * 0.35 +
                scores['amenities'] * 0.25
            )
            
            return scores
            
        except Exception as e:
            logger.error(f"Error calculating overall location score: {e}")
            return {'overall': 0, 'error': str(e)}
    
    async def get_environmental_data(self, location: Location) -> Optional[Dict[str, Any]]:
        """Get environmental data for a location"""
        return await self.environmental_service.refresh_environmental_data_if_stale(location)
    
    async def get_transport_data(self, location: Location) -> Dict[str, Any]:
        """Get transport connectivity data for a location"""
        return await self.transport_service.calculate_transport_score(location)
    
    async def get_nearby_transport_links(self, location: Location, radius_meters: int = 500) -> List[TransportLink]:
        """Get nearby transport links"""
        return await self.transport_service.get_nearby_transport_links(location, radius_meters)
    
    async def plan_journey(self, origin: Location, destination: Location) -> Optional[CommuteInfo]:
        """Plan a journey using public transport"""
        return await self.transport_service.get_journey_planner_data(origin, destination)