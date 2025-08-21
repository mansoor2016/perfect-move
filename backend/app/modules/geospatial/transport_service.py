from typing import Optional, Dict, Any, List
import httpx
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from geoalchemy2.functions import ST_DWithin, ST_GeogFromText
from app.models.geospatial import Location, TransportLink, CommuteInfo
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class TransportDataService:
    """Service for fetching and managing transport data, particularly TfL integration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tfl_api_key = getattr(settings, 'TFL_API_KEY', None)
        self.cache_duration_hours = 6  # Cache transport data for 6 hours
    
    async def get_nearby_transport_links(
        self, 
        location: Location, 
        radius_meters: int = 500,
        transport_types: Optional[List[str]] = None
    ) -> List[TransportLink]:
        """
        Get nearby transport links (stations, bus stops) using TfL API
        """
        if not self.tfl_api_key:
            logger.warning("TfL API key not configured")
            return []
        
        if transport_types is None:
            transport_types = ['tube', 'bus', 'rail', 'dlr', 'overground']
        
        try:
            # TfL StopPoint API to find nearby stops
            url = "https://api.tfl.gov.uk/StopPoint"
            params = {
                'lat': location.latitude,
                'lon': location.longitude,
                'radius': radius_meters,
                'stopTypes': ','.join(transport_types),
                'app_key': self.tfl_api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                
                if response.status_code == 200:
                    data = response.json()
                    transport_links = []
                    
                    for stop in data.get('stopPoints', []):
                        transport_link = TransportLink(
                            id=stop.get('id', ''),
                            name=stop.get('commonName', ''),
                            transport_type=self._map_tfl_mode_to_type(stop.get('modes', [])),
                            location=Location(
                                latitude=stop.get('lat', 0),
                                longitude=stop.get('lon', 0),
                                address=stop.get('commonName', '')
                            ),
                            lines=self._extract_lines_from_stop(stop),
                            zones=self._extract_zones_from_stop(stop)
                        )
                        transport_links.append(transport_link)
                    
                    return transport_links
                else:
                    logger.warning(f"TfL API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error fetching nearby transport links: {e}")
        
        return []
    
    def _map_tfl_mode_to_type(self, modes: List[Dict]) -> str:
        """Map TfL mode to our transport type"""
        if not modes:
            return "unknown"
        
        mode_mapping = {
            'tube': 'tube',
            'bus': 'bus',
            'national-rail': 'train',
            'dlr': 'dlr',
            'overground': 'overground',
            'tram': 'tram'
        }
        
        # Return the first recognized mode
        for mode in modes:
            mode_name = mode.get('modeName', '').lower()
            if mode_name in mode_mapping:
                return mode_mapping[mode_name]
        
        return modes[0].get('modeName', 'unknown')
    
    def _extract_lines_from_stop(self, stop: Dict) -> List[str]:
        """Extract line names from TfL stop data"""
        lines = []
        for line in stop.get('lines', []):
            line_name = line.get('name', '')
            if line_name:
                lines.append(line_name)
        return lines
    
    def _extract_zones_from_stop(self, stop: Dict) -> List[str]:
        """Extract zone information from TfL stop data"""
        zones = []
        additional_properties = stop.get('additionalProperties', [])
        
        for prop in additional_properties:
            if prop.get('key') == 'Zone':
                zone_value = prop.get('value', '')
                if zone_value:
                    zones.append(zone_value)
        
        return zones
    
    async def get_journey_planner_data(
        self, 
        origin: Location, 
        destination: Location,
        journey_preference: str = "LeastTime"
    ) -> Optional[CommuteInfo]:
        """
        Get journey planning data using TfL Journey Planner API
        """
        if not self.tfl_api_key:
            logger.warning("TfL API key not configured for journey planning")
            return None
        
        try:
            # TfL Journey Planner API
            from_point = f"{origin.latitude},{origin.longitude}"
            to_point = f"{destination.latitude},{destination.longitude}"
            
            url = f"https://api.tfl.gov.uk/Journey/JourneyResults/{from_point}/to/{to_point}"
            params = {
                'journeyPreference': journey_preference,
                'app_key': self.tfl_api_key
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=20.0)
                
                if response.status_code == 200:
                    data = response.json()
                    journeys = data.get('journeys', [])
                    
                    if journeys:
                        # Take the first (best) journey
                        best_journey = journeys[0]
                        
                        return CommuteInfo(
                            origin=origin,
                            destination=destination,
                            duration_minutes=best_journey.get('duration', 0),
                            distance_km=0,  # TfL doesn't always provide distance
                            transport_mode="public_transport",
                            route_details={
                                'legs': self._extract_journey_legs(best_journey),
                                'fare': self._extract_fare_info(best_journey),
                                'accessibility': best_journey.get('accessibility', {}),
                                'journey_preference': journey_preference
                            }
                        )
                else:
                    logger.warning(f"TfL Journey Planner API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error fetching journey planner data: {e}")
        
        return None
    
    def _extract_journey_legs(self, journey: Dict) -> List[Dict]:
        """Extract journey legs from TfL journey data"""
        legs = []
        for leg in journey.get('legs', []):
            leg_info = {
                'mode': leg.get('mode', {}).get('name', ''),
                'duration': leg.get('duration', 0),
                'instruction': leg.get('instruction', {}).get('summary', ''),
                'departure_point': leg.get('departurePoint', {}).get('commonName', ''),
                'arrival_point': leg.get('arrivalPoint', {}).get('commonName', ''),
                'line_name': leg.get('routeOptions', [{}])[0].get('name', '') if leg.get('routeOptions') else ''
            }
            legs.append(leg_info)
        return legs
    
    def _extract_fare_info(self, journey: Dict) -> Dict[str, Any]:
        """Extract fare information from TfL journey data"""
        fare_info = {}
        if 'fare' in journey:
            fare_data = journey['fare']
            fare_info = {
                'total_cost': fare_data.get('totalCost', 0),
                'peak_cost': fare_data.get('peakCost', 0),
                'off_peak_cost': fare_data.get('offPeakCost', 0)
            }
        return fare_info
    
    async def get_line_status_updates(self, line_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get current line status updates from TfL
        """
        if not self.tfl_api_key:
            logger.warning("TfL API key not configured for line status")
            return {}
        
        try:
            if line_ids:
                # Get status for specific lines
                line_ids_str = ','.join(line_ids)
                url = f"https://api.tfl.gov.uk/Line/{line_ids_str}/Status"
            else:
                # Get status for all lines
                url = "https://api.tfl.gov.uk/Line/Mode/tube,bus,dlr,overground,tram/Status"
            
            params = {'app_key': self.tfl_api_key}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    status_updates = {}
                    
                    for line in data:
                        line_id = line.get('id', '')
                        line_name = line.get('name', '')
                        line_statuses = line.get('lineStatuses', [])
                        
                        if line_statuses:
                            status = line_statuses[0]
                            status_updates[line_id] = {
                                'name': line_name,
                                'status': status.get('statusSeverityDescription', ''),
                                'reason': status.get('reason', ''),
                                'disruption': status.get('disruption', {}),
                                'last_updated': datetime.now().isoformat()
                            }
                    
                    return status_updates
                else:
                    logger.warning(f"TfL Line Status API error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error fetching line status updates: {e}")
        
        return {}
    
    async def get_transport_accessibility_info(
        self, 
        location: Location, 
        radius_meters: int = 1000
    ) -> Dict[str, Any]:
        """
        Get transport accessibility information for a location
        """
        transport_links = await self.get_nearby_transport_links(
            location, 
            radius_meters, 
            ['tube', 'rail', 'dlr', 'overground']
        )
        
        accessibility_info = {
            'location': location,
            'transport_links_count': len(transport_links),
            'transport_types': list(set(link.transport_type for link in transport_links)),
            'zones': [],
            'lines': [],
            'step_free_access': []
        }
        
        # Aggregate information
        all_zones = set()
        all_lines = set()
        
        for link in transport_links:
            all_zones.update(link.zones)
            all_lines.update(link.lines)
        
        accessibility_info['zones'] = sorted(list(all_zones))
        accessibility_info['lines'] = sorted(list(all_lines))
        
        # Get step-free access information if available
        if self.tfl_api_key:
            step_free_info = await self._get_step_free_access_info(transport_links)
            accessibility_info['step_free_access'] = step_free_info
        
        return accessibility_info
    
    async def _get_step_free_access_info(self, transport_links: List[TransportLink]) -> List[Dict]:
        """Get step-free access information for transport links"""
        step_free_info = []
        
        try:
            for link in transport_links[:5]:  # Limit to first 5 to avoid too many API calls
                url = f"https://api.tfl.gov.uk/StopPoint/{link.id}"
                params = {'app_key': self.tfl_api_key}
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=5.0)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Check for accessibility information
                        additional_properties = data.get('additionalProperties', [])
                        for prop in additional_properties:
                            if 'accessibility' in prop.get('key', '').lower():
                                step_free_info.append({
                                    'stop_name': link.name,
                                    'stop_id': link.id,
                                    'accessibility_info': prop.get('value', '')
                                })
                                break
                        
                        # Small delay to be respectful to the API
                        await asyncio.sleep(0.1)
                        
        except Exception as e:
            logger.error(f"Error fetching step-free access info: {e}")
        
        return step_free_info
    
    async def calculate_transport_score(self, location: Location) -> Dict[str, Any]:
        """
        Calculate a transport connectivity score for a location
        """
        try:
            # Get transport links within different radii
            nearby_500m = await self.get_nearby_transport_links(location, 500)
            nearby_1km = await self.get_nearby_transport_links(location, 1000)
            
            # Calculate scores
            tube_stations_500m = len([link for link in nearby_500m if link.transport_type == 'tube'])
            bus_stops_500m = len([link for link in nearby_500m if link.transport_type == 'bus'])
            rail_stations_1km = len([link for link in nearby_1km if link.transport_type in ['train', 'dlr', 'overground']])
            
            # Simple scoring algorithm
            transport_score = min(100, (
                tube_stations_500m * 20 +  # Tube stations are highly valued
                bus_stops_500m * 5 +       # Bus stops are good
                rail_stations_1km * 15     # Rail stations are valuable
            ))
            
            # Get unique zones
            all_zones = set()
            for link in nearby_1km:
                all_zones.update(link.zones)
            
            return {
                'location': location,
                'transport_score': transport_score,
                'breakdown': {
                    'tube_stations_500m': tube_stations_500m,
                    'bus_stops_500m': bus_stops_500m,
                    'rail_stations_1km': rail_stations_1km,
                    'total_links_1km': len(nearby_1km)
                },
                'zones': sorted(list(all_zones)),
                'score_explanation': self._get_score_explanation(transport_score)
            }
            
        except Exception as e:
            logger.error(f"Error calculating transport score: {e}")
            return {
                'location': location,
                'transport_score': 0,
                'error': str(e)
            }
    
    def _get_score_explanation(self, score: int) -> str:
        """Get human-readable explanation of transport score"""
        if score >= 80:
            return "Excellent transport connectivity"
        elif score >= 60:
            return "Very good transport connectivity"
        elif score >= 40:
            return "Good transport connectivity"
        elif score >= 20:
            return "Fair transport connectivity"
        else:
            return "Limited transport connectivity"