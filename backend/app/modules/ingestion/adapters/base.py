"""
Base adapter class for property listing APIs with rate limiting and retry logic
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class RawPropertyData(BaseModel):
    """Raw property data from external APIs before normalization"""
    source: str
    source_id: str
    raw_data: Dict[str, Any]
    fetched_at: datetime
    url: Optional[str] = None


class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    async def acquire(self):
        """Wait if necessary to respect rate limits"""
        now = datetime.now()
        # Remove calls outside the time window
        self.calls = [call_time for call_time in self.calls 
                     if now - call_time < timedelta(seconds=self.time_window)]
        
        if len(self.calls) >= self.max_calls:
            # Calculate how long to wait
            oldest_call = min(self.calls)
            wait_time = self.time_window - (now - oldest_call).total_seconds()
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        self.calls.append(now)


class BasePropertyAdapter(ABC):
    """Base class for property listing API adapters"""
    
    def __init__(self, api_key: Optional[str] = None, rate_limit_calls: int = 100, 
                 rate_limit_window: int = 3600):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(rate_limit_calls, rate_limit_window)
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self.source_name = self.__class__.__name__.lower().replace('adapter', '')
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def _make_request(self, url: str, params: Optional[Dict] = None, 
                           headers: Optional[Dict] = None) -> httpx.Response:
        """Make HTTP request with retry logic and rate limiting"""
        await self.rate_limiter.acquire()
        
        try:
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {url}: {str(e)}")
            raise
    
    @abstractmethod
    async def search_properties(self, location: str, radius_km: float = 5, 
                              max_results: int = 100) -> List[RawPropertyData]:
        """Search for properties in a given location"""
        pass
    
    @abstractmethod
    async def get_property_details(self, property_id: str) -> Optional[RawPropertyData]:
        """Get detailed information for a specific property"""
        pass
    
    @abstractmethod
    def normalize_property_data(self, raw_data: RawPropertyData) -> Dict[str, Any]:
        """Convert raw API data to normalized property format"""
        pass
    
    def calculate_reliability_score(self, raw_data: RawPropertyData) -> float:
        """Calculate reliability score based on data completeness and source"""
        score = 1.0
        data = raw_data.raw_data
        
        # Reduce score for missing critical fields
        critical_fields = ['price', 'address', 'bedrooms']
        missing_critical = sum(1 for field in critical_fields if not data.get(field))
        score -= missing_critical * 0.2
        
        # Reduce score for missing optional fields
        optional_fields = ['description', 'bathrooms', 'property_type', 'images']
        missing_optional = sum(1 for field in optional_fields if not data.get(field))
        score -= missing_optional * 0.1
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    def add_lineage_data(self, normalized_data: Dict[str, Any], 
                        raw_data: RawPropertyData) -> Dict[str, Any]:
        """Add lineage tracking information to normalized data"""
        normalized_data.update({
            'source': self.source_name,
            'source_id': raw_data.source_id,
            'last_updated': raw_data.fetched_at,
            'reliability_score': self.calculate_reliability_score(raw_data)
        })
        return normalized_data