"""Airport data loading and search functionality.

This module provides utilities for loading airport data from a CSV file and
performing efficient searches by IATA code, city name, or country.
"""
import csv
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
import re

import pandas as pd
from aiocache import cached, Cache
from aiocache.serializers import JsonSerializer

from config.settings import settings
from schemas.search import LocationSuggestion, LocationSearchResponse
from config.log_config import get_logger

logger = get_logger(__name__)

# Define the expected columns in the airports.csv file
AIRPORT_COLUMNS = [
    'iata_code', 'name', 'city', 'country', 'iata_country_code',
    'latitude', 'longitude', 'timezone', 'type'
]

# Type aliases
IATACode = str

@dataclass
class Airport:
    """Data class representing an airport."""
    iata_code: str
    name: str
    city: str
    country: str
    iata_country_code: str
    latitude: float
    longitude: float
    timezone: str
    type: str
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Airport':
        """Create an Airport instance from a dictionary."""
        return cls(
            iata_code=data.get('iata_code', '').upper(),
            name=data.get('name', '').strip(),
            city=data.get('city', '').strip(),
            country=data.get('country', '').strip(),
            iata_country_code=data.get('iata_country_code', '').upper(),
            latitude=float(data.get('latitude', 0)),
            longitude=float(data.get('longitude', 0)),
            timezone=data.get('timezone', '').strip(),
            type=data.get('type', 'airport').lower()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the Airport instance to a dictionary."""
        return asdict(self)
    
    def to_location_suggestion(self) -> LocationSuggestion:
        """Convert to LocationSuggestion for API responses."""
        return LocationSuggestion(
            id=f"airport_{self.iata_code}",
            name=f"{self.name} ({self.iata_code})",
            iata_code=self.iata_code,
            type="airport",
            city=self.city,
            country=self.country,
            country_code=self.iata_country_code,
            coordinates={"lat": self.latitude, "lon": self.longitude}
        )


class AirportDatabase:
    """In-memory database for airport data with search capabilities."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the airport database.
        
        Args:
            data_dir: Directory containing the airports.csv file.
                     If None, uses the default from settings.
        """
        self.data_dir = data_dir or settings.DATA_DIR
        self.airports: Dict[IATACode, Airport] = {}
        self.city_index: Dict[str, Set[IATACode]] = {}
        self.country_index: Dict[str, Set[IATACode]] = {}
        self.loaded = False
    
    async def load_data(self) -> None:
        """Load airport data from the CSV file."""
        if self.loaded:
            return
            
        csv_path = settings.airports_data_path
        if not csv_path.exists():
            logger.error(f"Airport data file not found: {csv_path}")
            raise FileNotFoundError(f"Airport data file not found: {csv_path}")
        
        logger.info(f"Loading airport data from {csv_path}")
        
        try:
            # Read the CSV file
            df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
            
            # Ensure all required columns are present
            missing_cols = set(AIRPORT_COLUMNS) - set(df.columns)
            if missing_cols:
                logger.warning(f"Missing columns in airport data: {missing_cols}")
            
            # Process each row
            for _, row in df.iterrows():
                try:
                    airport = Airport.from_dict(row.to_dict())
                    
                    # Skip if missing required fields
                    if not all([airport.iata_code, airport.name, airport.city, airport.country]):
                        continue
                    
                    # Add to main index
                    self.airports[airport.iata_code] = airport
                    
                    # Add to city index
                    city_key = self._normalize_text(airport.city)
                    if city_key not in self.city_index:
                        self.city_index[city_key] = set()
                    self.city_index[city_key].add(airport.iata_code)
                    
                    # Add to country index
                    country_key = self._normalize_text(airport.country)
                    if country_key not in self.country_index:
                        self.country_index[country_key] = set()
                    self.country_index[country_key].add(airport.iata_code)
                    
                except Exception as e:
                    logger.warning(f"Error processing airport data for row {_}: {e}")
            
            self.loaded = True
            logger.info(f"Loaded {len(self.airports)} airports")
            
        except Exception as e:
            logger.error(f"Failed to load airport data: {e}")
            raise
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for case-insensitive comparison."""
        return text.lower().strip()
    
    async def search_by_iata(self, code: str) -> Optional[Airport]:
        """Search for an airport by IATA code.
        
        Args:
            code: IATA code (e.g., 'GRU', 'JFK')
            
        Returns:
            Airport object if found, None otherwise
        """
        if not self.loaded:
            await self.load_data()
        
        code = code.upper().strip()
        return self.airports.get(code)
    
    async def search_by_city(self, city: str) -> List[Airport]:
        """Search for airports by city name.
        
        Args:
            city: City name (case-insensitive)
            
        Returns:
            List of matching Airport objects
        """
        if not self.loaded:
            await self.load_data()
        
        city_key = self._normalize_text(city)
        matching_codes = set()
        
        # Exact match
        if city_key in self.city_index:
            matching_codes.update(self.city_index[city_key])
        
        # Partial match
        for city_name, codes in self.city_index.items():
            if city_key in city_name or city_name in city_key:
                matching_codes.update(codes)
        
        return [self.airports[code] for code in matching_codes if code in self.airports]
    
    async def search_by_country(self, country: str) -> List[Airport]:
        """Search for airports by country name.
        
        Args:
            country: Country name (case-insensitive)
            
        Returns:
            List of matching Airport objects
        """
        if not self.loaded:
            await self.load_data()
        
        country_key = self._normalize_text(country)
        matching_codes = set()
        
        # Exact match
        if country_key in self.country_index:
            matching_codes.update(self.country_index[country_key])
        
        # Partial match
        for country_name, codes in self.country_index.items():
            if country_key in country_name or country_name in country_key:
                matching_codes.update(codes)
        
        return [self.airports[code] for code in matching_codes if code in self.airports]
    
    async def search(self, query: str) -> List[Airport]:
        """Search for airports by IATA code, city, or country.
        
        Args:
            query: Search query (IATA code, city name, or country name)
            
        Returns:
            List of matching Airport objects
        """
        if not query:
            return []
        
        query = query.strip()
        
        # Try IATA code search (exact match only)
        if re.match(r'^[A-Za-z]{3}$', query):
            airport = await self.search_by_iata(query)
            return [airport] if airport else []
        
        # Try city search
        city_results = await self.search_by_city(query)
        if city_results:
            return city_results
        
        # Try country search
        return await self.search_by_country(query)


# Global instance
_airport_db = None

@cached(ttl=3600 * 24, key_builder=lambda f, *args, **kwargs: f"airport_search:{args[1].lower()}")
async def search_airports(query: str) -> LocationSearchResponse:
    """Search for airports by IATA code, city, or country.
    
    This function is cached for 24 hours to improve performance.
    
    Args:
        query: Search query (IATA code, city name, or country name)
        
    Returns:
        LocationSearchResponse with matching locations
    """
    global _airport_db
    
    if _airport_db is None:
        _airport_db = AirportDatabase()
    
    try:
        airports = await _airport_db.search(query)
        suggestions = [airport.to_location_suggestion() for airport in airports]
        
        return LocationSearchResponse(
            data=suggestions,
            meta={"query": query, "count": len(suggestions)}
        )
    except Exception as e:
        logger.error(f"Error searching airports: {e}")
        return LocationSearchResponse(data=[], meta={"error": str(e), "query": query})


async def get_airport_by_iata(iata_code: str) -> Optional[LocationSuggestion]:
    """Get airport details by IATA code.
    
    Args:
        iata_code: IATA code (e.g., 'GRU', 'JFK')
        
    Returns:
        LocationSuggestion if found, None otherwise
    """
    global _airport_db
    
    if _airport_db is None:
        _airport_db = AirportDatabase()
    
    try:
        airport = await _airport_db.search_by_iata(iata_code)
        if airport:
            return airport.to_location_suggestion()
        return None
    except Exception as e:
        logger.error(f"Error getting airport {iata_code}: {e}")
        return None
