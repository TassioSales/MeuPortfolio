"""
Amadeus Flight Search Service

This module provides an interface to the Amadeus Self-Service API for flight search and booking.
It handles authentication, request formatting, response parsing, and error handling.
"""
import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

import httpx
from loguru import logger
from pydantic import ValidationError

from config.settings import settings
from schemas.flight import FlightItinerary, FlightSegment, FlightSearchResponse, CabinClass
from schemas.search import FlightSearchQuery, SortBy
from utils.helpers import retry_with_backoff

# Configure logger
logger = logger.bind(module="amadeus_service")

# Amadeus API endpoints
AMADEUS_BASE_URL = "https://test.api.amadeus.com"
TOKEN_URL = f"{AMADEUS_BASE_URL}/v1/security/oauth2/token"
FLIGHT_OFFERS_URL = f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers"
FLIGHT_OFFERS_PRICING_URL = f"{AMADEUS_BASE_URL}/v1/shopping/flight-offers/pricing"
AIRPORT_AUTOCOMPLETE_URL = f"{AMADEUS_BASE_URL}/v1/reference-data/locations"

class AmadeusAPIError(Exception):
    """Custom exception for Amadeus API errors."""
    def __init__(self, message: str, status_code: int = None, errors: List[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(self.message)

class AmadeusService:
    """Service for interacting with the Amadeus Self-Service API."""
    
    def __init__(self):
        """Initialize the Amadeus service with API credentials."""
        self.client_id = settings.AMADEUS_API_KEY
        self.client_secret = settings.AMADEUS_API_SECRET
        self.access_token = None
        self.token_expires_at = None
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
    
    async def _get_access_token(self) -> str:
        """Get an access token from the Amadeus API."""
        # Check if we have a valid token
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at - timedelta(minutes=5):
            return self.access_token
        
        logger.info("Requesting new access token from Amadeus API")
        
        try:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(TOKEN_URL, data=data, headers=headers)
                response.raise_for_status()
                token_data = response.json()
                
                self.access_token = token_data["access_token"]
                # Set token expiration (default to 30 minutes if not specified)
                expires_in = token_data.get("expires_in", 1800)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                return self.access_token
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get access token: {e.response.text}")
            raise AmadeusAPIError("Failed to authenticate with Amadeus API", 
                                status_code=e.response.status_code)
        except Exception as e:
            logger.error(f"Unexpected error getting access token: {str(e)}")
            raise AmadeusAPIError(f"Failed to get access token: {str(e)}")
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict:
        """Make an authenticated request to the Amadeus API."""
        # Ensure we have a valid access token
        token = await self._get_access_token()
        
        # Set default headers
        headers = kwargs.pop('headers', {})
        headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        
        # Make the request with retry logic
        @retry_with_backoff(max_retries=3, backoff_in_seconds=1)
        async def _request():
            try:
                response = await self.client.request(
                    method, url, headers=headers, **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_data = {}
                try:
                    error_data = e.response.json()
                except:
                    pass
                
                if e.response.status_code == 401:  # Unauthorized
                    # Token might be expired, clear it to force refresh
                    self.access_token = None
                    logger.warning("Token expired, will refresh on next request")
                
                raise AmadeusAPIError(
                    message=error_data.get("detail", "Amadeus API error"),
                    status_code=e.response.status_code,
                    errors=error_data.get("errors", [])
                )
            except Exception as e:
                logger.error(f"Request to {url} failed: {str(e)}")
                raise AmadeusAPIError(f"Request failed: {str(e)}")
        
        return await _request()
    
    async def search_flights(self, query: FlightSearchQuery) -> FlightSearchResponse:
        """Search for flights using the Amadeus Flight Offers Search API.
        
        Args:
            query: Flight search query parameters
            
        Returns:
            FlightSearchResponse with matching flight itineraries
            
        Raises:
            AmadeusAPIError: If the API request fails
            ValidationError: If the response cannot be parsed
        """
        logger.info(f"Searching flights with query: {query.dict()}")
        
        # Build request payload
        payload = self._build_flight_search_payload(query)
        
        try:
            # Make the API request
            response = await self._make_request("POST", FLIGHT_OFFERS_URL, json=payload)
            
            # Parse and validate the response
            return self._parse_flight_search_response(response, query)
            
        except ValidationError as e:
            logger.error(f"Failed to validate flight search response: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Flight search failed: {str(e)}")
            if not isinstance(e, AmadeusAPIError):
                raise AmadeusAPIError(f"Flight search failed: {str(e)}")
            raise
    
    def _build_flight_search_payload(self, query: FlightSearchQuery) -> Dict[str, Any]:
        """Build the request payload for the flight search API."""
        payload = {
            "currencyCode": query.currency.upper(),
            "sources": ["GDS"],
            "searchCriteria": {
                "maxFlightOffers": query.limit or 10,
                "flightFilters": {
                    "cabinRestrictions": [{
                        "cabin": query.cabin_class.value.upper(),
                        "coverage": "MOST_SEGMENTS",
                        "originDestinationIds": ["1"]  # Applies to all segments
                    }]
                }
            },
            "travelerPricings": []
        }
        
        # Add origin/destination segments
        payload["originDestinations"] = [{
            "id": "1",
            "originLocationCode": query.origin,
            "destinationLocationCode": query.destination,
            "departureDateTimeRange": {
                "date": query.departure_date.strftime("%Y-%m-%d"),
                "time": "00:00:00"
            }
        }]
        
        # Add return segment if provided
        if query.return_date:
            payload["originDestinations"].append({
                "id": "2",
                "originLocationCode": query.destination,
                "destinationLocationCode": query.origin,
                "departureDateTimeRange": {
                    "date": query.return_date.strftime("%Y-%m-%d"),
                    "time": "00:00:00"
                }
            })
        
        # Add travelers
        travelers = []
        traveler_id = 1
        
        # Add adults
        for _ in range(query.adults or 1):
            travelers.append({
                "id": str(traveler_id),
                "travelerType": "ADULT",
                "fareOptions": ["STANDARD"]
            })
            traveler_id += 1
        
        # Add children
        for _ in range(query.children or 0):
            travelers.append({
                "id": str(traveler_id),
                "travelerType": "CHILD",
                "fareOptions": ["STANDARD"]
            })
            traveler_id += 1
        
        # Add infants
        for _ in range(query.infants or 0):
            travelers.append({
                "id": str(traveler_id),
                "travelerType": "HELD_INFANT",
                "associatedAdultId": str(traveler_id - 1)  # Associate with the previous adult
            })
            traveler_id += 1
        
        payload["travelerPricings"] = travelers
        
        # Add filters
        if query.max_price:
            payload["searchCriteria"]["flightFilters"] = {
                "priceRange": {
                    "max": query.max_price,
                    "currency": query.currency.upper()
                }
            }
        
        if query.max_stops is not None:
            if "flightFilters" not in payload["searchCriteria"]:
                payload["searchCriteria"]["flightFilters"] = {}
            payload["searchCriteria"]["flightFilters"]["connectionRestriction"] = {
                "maxNumberOfConnections": query.max_stops
            }
        
        # Add sorting
        if query.sort_by == SortBy.PRICE:
            payload["sort"] = "price"
        elif query.sort_by == SortBy.DURATION:
            payload["sort"] = "duration"
        elif query.sort_by == SortBy.DEPARTURE_TIME:
            payload["sort"] = "departure"
        
        return payload
    
    def _parse_flight_search_response(self, response: Dict, query: FlightSearchQuery) -> FlightSearchResponse:
        """Parse the flight search response from Amadeus API."""
        itineraries = []
        
        for offer in response.get("data", []):
            try:
                itinerary = self._parse_flight_offer(offer, query)
                if itinerary:
                    itineraries.append(itinerary)
            except Exception as e:
                logger.warning(f"Failed to parse flight offer: {str(e)}")
                continue
        
        # Sort itineraries based on the query
        if query.sort_by == SortBy.PRICE:
            itineraries.sort(key=lambda x: x.price)
        elif query.sort_by == SortBy.DURATION:
            itineraries.sort(key=lambda x: sum(s.duration_minutes for s in x.segments))
        elif query.sort_by == SortBy.DEPARTURE_TIME:
            itineraries.sort(key=lambda x: x.segments[0].departure_time if x.segments else 0)
        
        return FlightSearchResponse(
            data=itineraries,
            meta={
                "count": len(itineraries),
                "origin": query.origin,
                "destination": query.destination,
                "departure_date": query.departure_date.isoformat(),
                "return_date": query.return_date.isoformat() if query.return_date else None,
                "adults": query.adults or 1,
                "children": query.children or 0,
                "infants": query.infants or 0,
                "cabin_class": query.cabin_class.value,
                "max_stops": query.max_stops,
                "sort_by": query.sort_by.value if query.sort_by else None
            },
            links={
                "self": f"{settings.API_BASE_URL}/flights?origin={query.origin}&destination={query.destination}&departure_date={query.departure_date.strftime('%Y-%m-%d')}"
            }
        )
    
    def _parse_flight_offer(self, offer: Dict, query: FlightSearchQuery) -> Optional[FlightItinerary]:
        """Parse a single flight offer from the Amadeus API."""
        try:
            # Extract pricing information
            price_data = offer.get("price", {})
            
            # Extract segments
            segments = []
            for segment in offer.get("itineraries", [{}])[0].get("segments", []):
                segments.append(
                    FlightSegment(
                        departure_airport=segment.get("departure", {}).get("iataCode"),
                        arrival_airport=segment.get("arrival", {}).get("iataCode"),
                        departure_time=datetime.fromisoformat(segment.get("departure", {}).get("at").replace('Z', '+00:00')),
                        arrival_time=datetime.fromisoformat(segment.get("arrival", {}).get("at").replace('Z', '+00:00')),
                        airline=segment.get("carrierCode", ""),
                        flight_number=f"{segment.get('carrierCode', '')}{segment.get('number', '')}",
                        aircraft=segment.get("aircraft", {}).get("code"),
                        duration_minutes=int(segment.get("duration", "PT0M").replace("PT", "").replace("H", "h ").replace("M", "m").split()[0]),
                        cabin_class=query.cabin_class.value,
                        booking_code=segment.get("number", ""),
                        operating_airline=segment.get("operating", {}).get("carrierCode"),
                        operating_flight_number=segment.get("number", ""),
                        distance_miles=0,  # Not provided in the response
                        equipment=segment.get("aircraft", {}).get("code"),
                        seats_remaining=segment.get("numberOfStops", 0),
                        fare_basis=segment.get("numberOfStops", ""),
                        baggage_allowance="1 x 23kg"  # Default, can be overridden with pricing info
                    )
                )
            
            # Create the itinerary
            return FlightItinerary(
                id=offer.get("id", ""),
                price=float(price_data.get("grandTotal", 0)),
                currency=price_data.get("currency", "USD"),
                segments=segments,
                booking_url="",  # Will be set by the frontend
                provider="amadeus",
                last_ticketing_datetime=datetime.utcnow() + timedelta(days=7),  # Default
                number_of_bookable_seats=offer.get("numberOfBookableSeats", 1),
                pricing_options={
                    "fare_type": "PUBLIC",
                    "included_checked_bags": price_data.get("numberOfBookableSeats", 1),
                    "is_refundable": any("REFUNDABLE" in p.get("fareType", []) for p in offer.get("pricingOptions", [])),
                    "is_partial_refundable": any("PARTIALLY_REFUNDABLE" in p.get("fareType", []) for p in offer.get("pricingOptions", [])),
                    "cancellation_deadline": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                    "change_deadline": (datetime.utcnow() + timedelta(days=1)).isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing flight offer: {str(e)}")
            logger.error(f"Offer data: {json.dumps(offer, indent=2)}")
            return None
    
    async def get_airport_autocomplete(self, keyword: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search for airports and cities using the Amadeus Location API."""
        if not keyword or len(keyword) < 2:
            return []
        
        try:
            params = {
                "subType": "AIRPORT,CITY",
                "keyword": keyword,
                "max": max_results
            }
            
            response = await self._make_request("GET", AIRPORT_AUTOCOMPLETE_URL, params=params)
            
            results = []
            for location in response.get("data", []):
                if location.get("subType") == "AIRPORT":
                    results.append({
                        "type": "airport",
                        "code": location.get("iataCode"),
                        "name": location.get("name"),
                        "city": location.get("address", {}).get("cityName"),
                        "country": location.get("address", {}).get("countryName"),
                        "full_name": f"{location.get('name')} ({location.get('iataCode')})"
                    })
                elif location.get("subType") == "CITY":
                    results.append({
                        "type": "city",
                        "code": location.get("iataCode"),
                        "name": location.get("name"),
                        "city": location.get("name"),
                        "country": location.get("address", {}).get("countryName"),
                        "full_name": f"{location.get('name')}, {location.get('address', {}).get('countryCode')}"
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Airport autocomplete failed: {str(e)}")
            return []

# Singleton instance
amadeus_service = AmadeusService()

# Example usage
if __name__ == "__main__":
    import asyncio
    from datetime import datetime, timedelta
    from schemas.search import FlightSearchQuery, CabinClass, SortBy
    
    async def test_flight_search():
        async with AmadeusService() as service:
            # Test flight search
            query = FlightSearchQuery(
                origin="JFK",
                destination="LAX",
                departure_date=datetime.now() + timedelta(days=30),
                return_date=datetime.now() + timedelta(days=37),
                adults=1,
                cabin_class=CabinClass.ECONOMY,
                sort_by=SortBy.PRICE,
                max_stops=1,
                limit=5
            )
            
            try:
                result = await service.search_flights(query)
                print(f"Found {len(result.data)} flights")
                for flight in result.data[:3]:  # Print first 3 flights
                    print(f"${flight.price} - {flight.segments[0].airline}{flight.segments[0].flight_number}")
            except Exception as e:
                print(f"Error: {str(e)}")
    
    async def test_airport_autocomplete():
        async with AmadeusService() as service:
            results = await service.get_airport_autocomplete("new york")
            print("Airport autocomplete results:")
            for loc in results:
                print(f"- {loc['full_name']} ({loc['type']})")
    
    # Run the tests
    asyncio.run(test_airport_autocomplete())
    # asyncio.run(test_flight_search())
