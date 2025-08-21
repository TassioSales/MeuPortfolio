"""Search models for flight queries in the Travel Planner application."""
from datetime import date, datetime, time
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, HttpUrl


class TimeWindow(str, Enum):
    """Time windows for flight searches."""
    MORNING = "morning"  # 06:00 - 11:59
    AFTERNOON = "afternoon"  # 12:00 - 17:59
    EVENING = "evening"  # 18:00 - 23:59
    NIGHT = "night"  # 00:00 - 05:59
    ANY = "any"  # Any time


class SortBy(str, Enum):
    """Sorting options for search results."""
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    DURATION_ASC = "duration_asc"
    DURATION_DESC = "duration_desc"
    DEPARTURE_ASC = "departure_asc"
    DEPARTURE_DESC = "departure_desc"


class FlightSearchQuery(BaseModel):
    """Model for flight search queries."""
    # Required fields
    origin: str = Field(..., description="Origin IATA code or location query")
    destination: str = Field(..., description="Destination IATA code or location query")
    departure_date: date = Field(..., description="Departure date (YYYY-MM-DD)")
    
    # Optional fields
    return_date: Optional[date] = Field(None, description="Return date for round trips")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=8, description="Number of child passengers")
    infants: int = Field(0, ge=0, le=5, description="Number of infant passengers")
    
    # Cabin class and preferences
    cabin_class: str = Field("economy", description="Cabin class (economy, premium_economy, business, first)")
    preferred_airlines: List[str] = Field(
        default_factory=list,
        description="Preferred airline IATA codes"
    )
    
    # Filters
    max_stops: Optional[int] = Field(None, ge=0, le=3, description="Maximum number of stops")
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price per passenger")
    currency: str = Field("USD", description="Currency code for prices")
    
    # Time preferences
    departure_time_window: Optional[TimeWindow] = Field(
        TimeWindow.ANY,
        description="Preferred departure time window"
    )
    return_time_window: Optional[TimeWindow] = Field(
        TimeWindow.ANY,
        description="Preferred return time window (for round trips)"
    )
    
    # Sorting and pagination
    sort_by: SortBy = Field(
        SortBy.PRICE_ASC,
        description="Sorting criteria for results"
    )
    limit: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum number of results to return"
    )
    
    # Metadata
    include_viable_only: bool = Field(
        True,
        description="Whether to include only bookable flights"
    )
    include_airlines: Optional[List[str]] = Field(
        None,
        description="Specific airlines to include (IATA codes)"
    )
    exclude_airlines: Optional[List[str]] = Field(
        None,
        description="Airlines to exclude (IATA codes)"
    )
    
    class Config:
        json_encoders = {
            date: lambda d: d.isoformat(),
            datetime: lambda d: d.isoformat(),
        }
    
    @validator('return_date')
    def validate_return_date(cls, v, values):
        if v is not None and 'departure_date' in values and v < values['departure_date']:
            raise ValueError('return_date must be after or equal to departure_date')
        return v
    
    @validator('cabin_class')
    def validate_cabin_class(cls, v):
        valid_classes = ["economy", "premium_economy", "business", "first"]
        if v.lower() not in valid_classes:
            raise ValueError(f"cabin_class must be one of {valid_classes}")
        return v.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API requests."""
        return self.dict(exclude_none=True, by_alias=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlightSearchQuery':
        """Create from dictionary."""
        return cls(**data)


class LocationSuggestion(BaseModel):
    """Location suggestion from search."""
    id: str = Field(..., description="Unique identifier for the location")
    name: str = Field(..., description="Display name of the location")
    iata_code: Optional[str] = Field(None, description="IATA code if available")
    type: str = Field(..., description="Type of location (airport, city, country)")
    city: Optional[str] = Field(None, description="City name")
    country: Optional[str] = Field(None, description="Country name")
    country_code: Optional[str] = Field(None, description="ISO country code")
    coordinates: Optional[Dict[str, float]] = Field(
        None,
        description="Geographic coordinates (lat, lon)"
    )
    
    @property
    def display_name(self) -> str:
        """Get a user-friendly display name for the location."""
        if self.type == "airport" and self.iata_code:
            return f"{self.name} ({self.iata_code})"
        return self.name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.dict(exclude_none=True, by_alias=True)


class LocationSearchResponse(BaseModel):
    """Response model for location search."""
    data: List[LocationSuggestion] = Field(
        default_factory=list,
        description="List of location suggestions"
    )
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the search results"
    )
