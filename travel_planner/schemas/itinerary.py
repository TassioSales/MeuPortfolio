"""Itinerary data models for the Travel Planner application."""
from datetime import date, time, datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator


class ActivityType(str, Enum):
    """Types of activities in an itinerary."""
    SIGHTSEEING = "sightseeing"
    DINING = "dining"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    ACTIVITY = "activity"
    SHOPPING = "shopping"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


class Activity(BaseModel):
    """A single activity in a daily plan."""
    id: str = Field(..., description="Unique identifier for the activity")
    type: ActivityType = Field(..., description="Type of activity")
    name: str = Field(..., description="Name of the activity")
    description: Optional[str] = Field(None, description="Detailed description")
    start_time: time = Field(..., description="Start time of the activity")
    end_time: time = Field(..., description="End time of the activity")
    location: Optional[str] = Field(None, description="Location name or address")
    location_url: Optional[HttpUrl] = Field(None, description="Google Maps URL or similar")
    cost_estimate: Optional[float] = Field(None, description="Estimated cost in local currency")
    currency: str = Field("USD", description="Currency code for cost_estimate")
    notes: Optional[str] = Field(None, description="Additional notes or tips")
    image_url: Optional[HttpUrl] = Field(None, description="URL to an image of the activity")
    booking_required: bool = Field(False, description="Whether booking is required")
    booking_url: Optional[HttpUrl] = Field(None, description="URL to book this activity")

    class Config:
        json_encoders = {
            time: lambda t: t.strftime("%H:%M"),
            HttpUrl: lambda u: str(u)
        }

    @validator('end_time')
    def validate_times(cls, v, values):
        if 'start_time' in values and v < values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class DailyPlan(BaseModel):
    """A single day's plan in an itinerary."""
    date: date = Field(..., description="Date of the plan")
    activities: List[Activity] = Field(
        default_factory=list,
        description="List of activities for this day"
    )
    notes: Optional[str] = Field(None, description="General notes for the day")

    @property
    def is_empty(self) -> bool:
        """Check if the day has no activities."""
        return len(self.activities) == 0

    def add_activity(self, activity: Activity) -> None:
        """Add an activity to the day's plan."""
        self.activities.append(activity)
        # Sort activities by start time
        self.activities.sort(key=lambda x: x.start_time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.dict(by_alias=True, exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DailyPlan':
        """Create from dictionary."""
        return cls(**data)


class TravelItinerary(BaseModel):
    """A complete travel itinerary with multiple days of activities."""
    id: str = Field(..., description="Unique identifier for the itinerary")
    title: str = Field(..., description="Title of the itinerary")
    destination: str = Field(..., description="Destination city and country")
    start_date: date = Field(..., description="Start date of the trip")
    end_date: date = Field(..., description="End date of the trip")
    days: List[DailyPlan] = Field(
        default_factory=list,
        description="List of daily plans"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the itinerary was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the itinerary was last updated"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization (e.g., 'romantic', 'family', 'adventure')"
    )
    budget_level: Optional[str] = Field(
        None,
        description="Budget level (budget, midrange, luxury)"
    )
    cover_image_url: Optional[HttpUrl] = Field(
        None,
        description="URL to a cover image for the itinerary"
    )
    notes: Optional[str] = Field(
        None,
        description="General notes about the itinerary"
    )

    class Config:
        json_encoders = {
            date: lambda d: d.isoformat(),
            datetime: lambda d: d.isoformat(),
            HttpUrl: lambda u: str(u)
        }

    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after or equal to start_date')
        return v

    @property
    def duration_days(self) -> int:
        """Calculate the duration of the trip in days."""
        return (self.end_date - self.start_date).days + 1

    def get_daily_plan(self, date: date) -> Optional[DailyPlan]:
        """Get the daily plan for a specific date, if it exists."""
        for day in self.days:
            if day.date == date:
                return day
        return None

    def add_daily_plan(self, daily_plan: DailyPlan) -> None:
        """Add a daily plan to the itinerary."""
        # Check if a plan for this date already exists
        existing = self.get_daily_plan(daily_plan.date)
        if existing:
            # Merge activities
            for activity in daily_plan.activities:
                existing.add_activity(activity)
            if daily_plan.notes:
                existing.notes = (existing.notes + "\n" + daily_plan.notes).strip()
        else:
            self.days.append(daily_plan)
            # Sort days by date
            self.days.sort(key=lambda x: x.date)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.dict(by_alias=True, exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TravelItinerary':
        """Create from dictionary."""
        return cls(**data)
