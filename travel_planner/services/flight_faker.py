"""
Flight Faker Service

This module provides mock flight data for development and testing purposes.
It generates realistic-looking flight data that mimics real flight information.
"""
import random
import string
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from faker import Faker

from config.log_config import get_logger
from schemas.flight import FlightSegment, FlightItinerary, FlightSearchResponse
from schemas.search import LocationSuggestion
from utils.helpers import format_currency, format_duration

# Initialize logger
logger = get_logger(__name__)

# Initialize Faker
fake = Faker()
Faker.seed(42)  # For consistent results

# Common airline codes and names
AIRLINES = [
    ("AA", "American Airlines"),
    ("DL", "Delta Air Lines"),
    ("UA", "United Airlines"),
    ("WN", "Southwest Airlines"),
    ("B6", "JetBlue Airways"),
    ("AS", "Alaska Airlines"),
    ("NK", "Spirit Airlines"),
    ("F9", "Frontier Airlines"),
    ("HA", "Hawaiian Airlines"),
    ("G4", "Allegiant Air"),
]

# Aircraft types with typical seat capacities
AIRCRAFT_TYPES = [
    ("B737", "Boeing 737-800", 160, 1800),
    ("A320", "Airbus A320", 150, 3300),
    ("B787", "Boeing 787-9", 290, 14140),
    ("A350", "Airbus A350-900", 315, 15000),
    ("E190", "Embraer E190", 100, 4260),
    ("CRJ9", "Bombardier CRJ-900", 76, 2870),
]

# Common booking classes
CABIN_CLASSES = ["Y", "B", "M", "H", "Q", "K", "L", "U", "T", "X", "V", "N", "R", "O", "S"]

@dataclass
class Route:
    """Represents a flight route between two airports."""
    origin: str
    destination: str
    distance: int  # in miles
    duration: int  # in minutes
    typical_airlines: List[str]  # List of airline IATA codes
    
    def get_random_airline(self) -> Tuple[str, str]:
        """Get a random airline that operates this route."""
        # First try to get one of the typical airlines
        if self.typical_airlines and random.random() < 0.8:  # 80% chance
            airline_code = random.choice(self.typical_airlines)
            for code, name in AIRLINES:
                if code == airline_code:
                    return (code, name)
        
        # Fall back to any airline
        return random.choice(AIRLINES)

# Common routes with realistic distances and typical airlines
COMMON_ROUTES = [
    Route("JFK", "LAX", 2475, 320, ["AA", "DL", "B6"]),
    Route("LAX", "ORD", 1740, 245, ["AA", "UA", "WN"]),
    Route("ORD", "DFW", 801, 135, ["AA", "WN"]),
    Route("DFW", "DEN", 641, 105, ["WN", "UA", "F9"]),
    Route("DEN", "SFO", 966, 165, ["UA", "WN"]),
    Route("SFO", "SEA", 679, 130, ["AS", "UA"]),
    Route("SEA", "JFK", 2416, 300, ["DL", "AS"]),
    Route("MIA", "JFK", 1090, 175, ["AA", "B6", "DL"]),
    Route("ATL", "LAX", 1946, 255, ["DL", "WN"]),
    Route("LAS", "JFK", 2245, 290, ["B6", "DL", "WN"]),
]

class FlightFaker:
    """
    A service that generates realistic flight data for testing and development.
    """
    
    def __init__(self):
        self.routes = COMMON_ROUTES
        self.aircraft_types = AIRCRAFT_TYPES
        self.airlines = AIRLINES
        
    def _generate_flight_number(self, airline_code: str) -> str:
        """
        Generate a realistic flight number.
        
        Args:
            airline_code: The IATA airline code (e.g., 'AA', 'DL')
            
        Returns:
            str: A flight number string (e.g., 'AA1234')
        """
        try:
            if not isinstance(airline_code, str) or len(airline_code) != 2:
                airline_code = "AA"  # Default to American Airlines if invalid
                
            # Major airlines typically use 1-4 digits
            if airline_code in ["AA", "UA", "DL"]:
                return f"{airline_code}{random.randint(1, 2000):04d}"
            # Low-cost carriers often use 3-4 digits
            elif airline_code in ["WN", "B6", "NK", "F9", "G4"]:
                return f"{airline_code}{random.randint(100, 5000)}"
            # Default case
            return f"{airline_code}{random.randint(100, 9999)}"
        except Exception as e:
            logger.error(f"Error generating flight number: {e}")
            return f"AA{random.randint(1000, 9999)}"  # Fallback flight number
    
    def _generate_booking_reference(self) -> str:
        """
        Generate a random booking reference (PNR).
        
        Returns:
            str: A 6-character alphanumeric booking reference
        """
        try:
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        except Exception as e:
            logger.error(f"Error generating booking reference: {e}")
            # Fallback to a predictable but unique reference based on timestamp
            return f"REF{int(datetime.now().timestamp() % 1000000):06d}"
    
    def _generate_aircraft(self) -> Tuple[str, str, int, int]:
        """
        Generate a random aircraft type.
        
        Returns:
            Tuple[str, str, int, int]: A tuple containing (aircraft_code, aircraft_name, seats, range_miles)
        """
        try:
            return random.choice(self.aircraft_types)
        except Exception as e:
            logger.error(f"Error generating aircraft: {e}")
            # Return a default aircraft if there's an error
            return ("B737", "Boeing 737-800", 160, 1800)
    
    def _generate_cabin_class(self) -> str:
        """
        Generate a random cabin class.
        
        Returns:
            str: One of 'economy', 'premium_economy', 'business', or 'first'
        """
        try:
            return random.choice(["economy", "premium_economy", "business", "first"])
        except Exception as e:
            logger.error(f"Error generating cabin class: {e}")
            return "economy"  # Default to economy class
    
    def _generate_booking_class(self) -> str:
        """
        Generate a random booking class.
        
        Returns:
            str: A single character representing the booking class
        """
        try:
            return random.choice(CABIN_CLASSES)
        except Exception as e:
            logger.error(f"Error generating booking class: {e}")
            return "Y"  # Default to economy class
    
    def _generate_seat(self) -> str:
        """
        Generate a random seat number.
        
        Returns:
            str: A string representing a seat (e.g., '12A', '24F')
        """
        try:
            row = random.randint(1, 40)
            seat = random.choice(['A', 'B', 'C', 'D', 'E', 'F'])
            return f"{row}{seat}"
        except Exception as e:
            logger.error(f"Error generating seat: {e}")
            # Return a default seat if there's an error
            return "12A"
    
    def _generate_segments(self, route: Route, departure_time: datetime) -> List[FlightSegment]:
        """
        Generate flight segments for a route, either as a direct flight or with connections.
        
        Args:
            route: The route for which to generate segments
            departure_time: Scheduled departure time for the first segment
            
        Returns:
            List[FlightSegment]: A list of flight segments making up the journey
        """
        try:
            segments = []
            
            # For non-stop flights (80% of the time or short routes)
            if not route or not hasattr(route, 'distance') or random.random() < 0.8 or route.distance < 1000:
                return [self._create_segment(route.origin, route.destination, departure_time, route)]
            
            # For connecting flights (20% of the time for longer routes)
            # Find a reasonable connecting point
            possible_connections = [r for r in self.routes 
                                  if r and hasattr(r, 'origin') and hasattr(r, 'destination')
                                  and (r.origin == route.origin or r.destination == route.destination)]
            
            if not possible_connections:
                return [self._create_segment(route.origin, route.destination, departure_time, route)]
            
            connection = random.choice(possible_connections)
            layover = connection.destination if connection.origin == route.origin else connection.origin
            
            # Create segments with a layover
            first_leg = self._create_segment(route.origin, layover, departure_time, route)
            
            # Add a layover (1-4 hours)
            layover_duration = random.randint(60, 240)  # minutes
            second_departure = first_leg.arrival_time + timedelta(minutes=layover_duration)
            
            second_leg = self._create_segment(layover, route.destination, second_departure, route)
            
            return [first_leg, second_leg]
            
        except Exception as e:
            logger.error(f"Error generating segments: {e}")
            # Fallback to a simple direct flight
            if route and hasattr(route, 'origin') and hasattr(route, 'destination'):
                return [self._create_segment(route.origin, route.destination, departure_time, route)]
            return []
    
    def _create_segment(self, origin: str, destination: str, 
                       departure_time: datetime, route: Optional[Route] = None) -> FlightSegment:
        """
        Create a single flight segment.
        
        Args:
            origin: Departure airport code
            destination: Arrival airport code
            departure_time: Scheduled departure time
            route: Optional Route object with route details
            
        Returns:
            FlightSegment: A configured flight segment
        """
        try:
            # Validate inputs
            if not all(isinstance(x, str) and len(x) == 3 for x in [origin, destination]):
                raise ValueError("Origin and destination must be 3-letter airport codes")
                
            if not isinstance(departure_time, datetime):
                raise ValueError("departure_time must be a datetime object")
            
            # Handle missing or invalid route
            if route is None or not hasattr(route, 'distance') or not hasattr(route, 'duration'):
                # Find an existing route
                route = next((r for r in self.routes 
                             if r and hasattr(r, 'origin') and hasattr(r, 'destination')
                             and ((r.origin == origin and r.destination == destination) or
                                 (r.origin == destination and r.destination == origin))), None)
                
                if route is None:
                    # Create a synthetic route
                    distance = random.randint(200, 5000)
                    duration = max(60, int(distance / 500 * 60))  # Rough estimate: 500 mph
                    route = Route(origin, destination, distance, duration, [])
            
            # Get airline and flight details
            airline_code, airline_name = route.get_random_airline()
            flight_number = self._generate_flight_number(airline_code)
            aircraft_code, aircraft_name, _, _ = self._generate_aircraft()
            
            # Calculate arrival time based on distance and a bit of randomness
            flight_duration = route.duration * random.uniform(0.9, 1.1)  # ±10% variation
            arrival_time = departure_time + timedelta(minutes=flight_duration)
            
            # Create and return the flight segment
            return FlightSegment(
                departure_airport=origin,
                arrival_airport=destination,
                departure_time=departure_time,
                arrival_time=arrival_time,
                airline=airline_code,
                flight_number=flight_number,
                aircraft=aircraft_name,
                cabin_class=self._generate_cabin_class(),
                booking_code=self._generate_booking_class(),
                duration_minutes=int(flight_duration),
                operating_airline=airline_code,
                operating_flight_number=flight_number,
                distance_miles=route.distance,
                equipment=aircraft_code,
                seats_remaining=random.randint(0, 30),
            )
            
        except Exception as e:
            logger.error(f"Error creating flight segment from {origin} to {destination}: {e}")
            # Create a minimal valid segment in case of errors
            return FlightSegment(
                departure_airport=origin or "XXX",
                arrival_airport=destination or "YYY",
                departure_time=departure_time or datetime.now(),
                arrival_time=(departure_time or datetime.now()) + timedelta(hours=2),
                airline="AA",
                flight_number="AA1234",
                aircraft="Boeing 737-800",
                cabin_class="economy",
                booking_code="Y",
                duration_minutes=120,
                operating_airline="AA",
                operating_flight_number="AA1234",
                distance_miles=500,
                equipment="B737",
                seats_remaining=10,
            fare_basis=self._generate_booking_class() + str(random.randint(1, 9)),
            baggage_allowance="1 x 23kg" if random.random() > 0.3 else "1 x 10kg"
        )
    
    def generate_flight_itinerary(self, origin: str, destination: str, 
                                departure_date: datetime) -> FlightItinerary:
        """Generate a single flight itinerary."""
        # Find a matching route or create one
        route = next((r for r in self.routes 
                     if r.origin == origin and r.destination == destination), None)
        
        if route is None:
            # Create a synthetic route
            distance = random.randint(200, 5000)
            duration = max(60, int(distance / 500 * 60))  # Rough estimate: 500 mph
            route = Route(origin, destination, distance, duration, [])
        
        # Generate a random departure time (between 6 AM and 10 PM)
        departure_hour = random.randint(6, 22)
        departure_minute = random.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
        departure_time = departure_date.replace(
            hour=departure_hour,
            minute=departure_minute,
            second=0,
            microsecond=0
        )
        
        # Generate segments
        segments = self._generate_segments(route, departure_time)
        
        # Calculate total price based on distance, cabin class, and demand
        base_price = route.distance * random.uniform(0.10, 0.25)  # $0.10-$0.25 per mile
        
        # Adjust price based on cabin class
        cabin_class = segments[0].cabin_class
        if cabin_class == "premium_economy":
            base_price *= 1.8
        elif cabin_class == "business":
            base_price *= 3.5
        elif cabin_class == "first":
            base_price *= 6.0
        
        # Add some random variation
        price = base_price * random.uniform(0.8, 1.5)
        
        # Round to nearest $10
        price = round(price / 10) * 10
        
        # Create the itinerary
        itinerary_id = f"ITIN{random.randint(100000, 999999)}"
        
        return FlightItinerary(
            id=itinerary_id,
            price=price,
            currency="USD",
            segments=segments,
            booking_url=f"https://example.com/book/{itinerary_id}",
            provider="mock",
            last_ticketing_datetime=departure_date - timedelta(days=random.randint(1, 7)),
            number_of_bookable_seats=random.randint(1, 9),
            pricing_options={
                "fare_type": random.choice(["PUBLIC", "PRIVATE", "NEGOTIATED"]),
                "included_checked_bags": random.randint(0, 2),
                "is_refundable": random.random() > 0.7,
                "is_partial_refundable": random.random() > 0.5,
                "cancellation_deadline": (departure_date - timedelta(days=random.randint(1, 7))).isoformat(),
                "change_deadline": (departure_date - timedelta(days=random.randint(1, 3))).isoformat()
            }
        )
    
    def search_flights(self, origin: str, destination: str, 
                      departure_date: datetime, return_date: Optional[datetime] = None,
                      adults: int = 1, children: int = 0, infants: int = 0,
                      cabin_class: str = "economy", max_stops: Optional[int] = None,
                      limit: int = 10) -> FlightSearchResponse:
        """Search for flights between two locations."""
        # Generate outbound flights
        outbound_flights = []
        for _ in range(limit):
            try:
                itinerary = self.generate_flight_itinerary(origin, destination, departure_date)
                
                # Apply filters
                if max_stops is not None and len(itinerary.segments) - 1 > max_stops:
                    continue
                    
                if cabin_class and itinerary.segments[0].cabin_class != cabin_class:
                    continue
                
                outbound_flights.append(itinerary)
            except Exception as e:
                logger.warning(f"Error generating flight: {e}")
        
        # Sort by price
        outbound_flights.sort(key=lambda x: x.price)
        
        # Generate return flights if requested
        return_flights = []
        if return_date:
            for _ in range(min(limit, len(outbound_flights))):
                try:
                    itinerary = self.generate_flight_itinerary(destination, origin, return_date)
                    
                    # Apply filters
                    if max_stops is not None and len(itinerary.segments) - 1 > max_stops:
                        continue
                        
                    if cabin_class and itinerary.segments[0].cabin_class != cabin_class:
                        continue
                    
                    return_flights.append(itinerary)
                except Exception as e:
                    logger.warning(f"Error generating return flight: {e}")
            
            # Sort by price
            return_flights.sort(key=lambda x: x.price)
        
        # Combine results
        all_flights = outbound_flights
        
        # If we have return flights, pair them with outbound flights
        if return_flights:
            paired_flights = []
            for i, outbound in enumerate(outbound_flights):
                if i < len(return_flights):
                    # Create a round-trip itinerary
                    return_flight = return_flights[i]
                    total_price = outbound.price + return_flight.price
                    
                    # Create a new itinerary ID for the round-trip
                    itinerary_id = f"RT{random.randint(100000, 999999)}"
                    
                    # Combine segments
                    combined_segments = outbound.segments + return_flight.segments
                    
                    # Create the round-trip itinerary
                    round_trip = FlightItinerary(
                        id=itinerary_id,
                        price=total_price,
                        currency=outbound.currency,
                        segments=combined_segments,
                        booking_url=f"https://example.com/book/{itinerary_id}",
                        provider="mock",
                        last_ticketing_datetime=min(outbound.last_ticketing_datetime, 
                                                 return_flight.last_ticketing_datetime),
                        number_of_bookable_seats=min(outbound.number_of_bookable_seats,
                                                   return_flight.number_of_bookable_seats),
                        pricing_options={
                            **outbound.pricing_options,
                            "is_round_trip": True,
                            "outbound_price": outbound.price,
                            "return_price": return_flight.price
                        }
                    )
                    
                    paired_flights.append(round_trip)
            
            all_flights = paired_flights
        
        return FlightSearchResponse(
            data=all_flights,
            meta={
                "count": len(all_flights),
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date.isoformat(),
                "return_date": return_date.isoformat() if return_date else None,
                "adults": adults,
                "children": children,
                "infants": infants,
                "cabin_class": cabin_class,
                "max_stops": max_stops
            },
            links={
                "self": f"https://api.example.com/flights?origin={origin}&destination={destination}&departure_date={departure_date.date()}"
            }
        )

# Singleton instance
flight_faker = FlightFaker()

# Example usage
if __name__ == "__main__":
    from datetime import datetime, timedelta
    
    # Create a flight faker instance
    faker = FlightFaker()
    
    # Generate a one-way flight
    departure_date = datetime.now() + timedelta(days=30)
    results = faker.search_flights("JFK", "LAX", departure_date, limit=3)
    
    print(f"Found {len(results.data)} flights from JFK to LAX on {departure_date.strftime('%Y-%m-%d')}:")
    for flight in results.data:
        print(f"- {flight.segments[0].airline}{flight.segments[0].flight_number}: "
              f"{flight.segments[0].departure_time.strftime('%H:%M')} → {flight.segments[-1].arrival_time.strftime('%H:%M')} "
              f"({len(flight.segments)-1} stops) - ${flight.price}")
    
    # Generate a round-trip flight
    return_date = departure_date + timedelta(days=7)
    results = faker.search_flights("JFK", "LAX", departure_date, return_date, limit=3)
    
    print(f"\nFound {len(results.data)} round-trip flights from JFK to LAX:")
    for flight in results.data:
        outbound = next(s for s in flight.segments if s.departure_airport == "JFK")
        return_leg = next(s for s in flight.segments if s.departure_airport == "LAX")
        
        print(f"- Outbound: {outbound.airline}{outbound.flight_number} at {outbound.departure_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Return: {return_leg.airline}{return_leg.flight_number} at {return_leg.departure_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  Total price: ${flight.price}")
        print()
