"""Flight data models for the Travel Planner application."""
from datetime import datetime, time
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class CabinClass(str, Enum):
    """Cabin class types for flights."""
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class FlightSegment(BaseModel):
    """A single flight segment between two airports."""
    departure_airport: str = Field(..., description="IATA code of departure airport")
    arrival_airport: str = Field(..., description="IATA code of arrival airport")
    departure_time: datetime = Field(..., description="Scheduled departure time")
    arrival_time: datetime = Field(..., description="Scheduled arrival time")
    airline: str = Field(..., description="Airline IATA code")
    flight_number: str = Field(..., description="Flight number")
    aircraft: Optional[str] = Field(None, description="Aircraft type")
    cabin_class: CabinClass = Field(..., description="Cabin class")
    booking_code: Optional[str] = Field(None, description="Booking/class code")

    @property
    def duration_minutes(self) -> int:
        """Calculate flight duration in minutes."""
        return int((self.arrival_time - self.departure_time).total_seconds() / 60)

    @property
    def duration_formatted(self) -> str:
        """Format duration as HHh MMm."""
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        return f"{hours}h {minutes}m"


class FlightItinerary(BaseModel):
    """A complete flight itinerary, potentially with connections."""
    id: str = Field(..., description="Unique identifier for this itinerary")
    price: float = Field(..., description="Total price in USD")
    currency: str = Field("USD", description="Currency code")
    segments: List[FlightSegment] = Field(..., description="List of flight segments")
    booking_url: Optional[str] = Field(None, description="URL to book this flight")
    provider: str = Field("amadeus", description="Provider of this flight data")
    last_ticketing_datetime: Optional[datetime] = Field(
        None, description="Last ticketing datetime"
    )
    number_of_bookable_seats: Optional[int] = Field(
        None, description="Number of bookable seats"
    )
    pricing_options: Optional[Dict[str, Any]] = Field(
        None, description="Additional pricing options"
    )

    @property
    def is_direct(self) -> bool:
        """Check if this is a direct flight (no connections)."""
        return len(self.segments) == 1

    @property
    def total_duration_minutes(self) -> int:
        """Calculate total travel time in minutes."""
        if not self.segments:
            return 0
        return int((self.segments[-1].arrival_time - self.segments[0].departure_time).total_seconds() / 60)

    @property
    def total_duration_formatted(self) -> str:
        """Format total duration as Xh Ym."""
        hours = self.total_duration_minutes // 60
        minutes = self.total_duration_minutes % 60
        return f"{hours}h {minutes}m"

    @property
    def departure_airport(self) -> str:
        """Get the departure airport IATA code."""
        return self.segments[0].departure_airport if self.segments else ""

    @property
    def arrival_airport(self) -> str:
        """Get the final arrival airport IATA code."""
        return self.segments[-1].arrival_airport if self.segments else ""

    @property
    def departure_time(self) -> datetime:
        """Get the departure time of the first segment."""
        return self.segments[0].departure_time if self.segments else None

    @property
    def arrival_time(self) -> datetime:
        """Get the arrival time of the last segment."""
        return self.segments[-1].arrival_time if self.segments else None

    @property
    def airlines(self) -> List[str]:
        """Get list of unique airline codes in this itinerary."""
        return list({segment.airline for segment in self.segments})

    @property
    def stop_count(self) -> int:
        """Get the number of stops (0 for direct flights)."""
        return max(0, len(self.segments) - 1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.dict(by_alias=True, exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlightItinerary':
        """Create from dictionary."""
        return cls(**data)


class FlightSearchResponse(BaseModel):
    """Response model for flight search results."""
    data: List[FlightItinerary] = Field(..., description="List of flight itineraries")
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the search results"
    )
    links: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pagination links"
    )
