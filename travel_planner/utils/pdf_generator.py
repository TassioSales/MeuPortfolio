"""PDF Generation Utilities for Travel Planner.

This module provides functionality to generate PDF documents for travel itineraries,
flight confirmations, and other travel-related documents.
"""
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any, BinaryIO

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image, UnidentifiedImageError

from config.settings import settings
from config.log_config import get_logger
from schemas.flight import FlightItinerary, FlightSegment
from schemas.itinerary import TravelItinerary, DailyPlan, Activity
from utils.helpers import format_currency, format_date, human_readable_size, ensure_directory_exists

# Initialize logger
logger = get_logger(__name__)

# Type aliases
RGBColor = Tuple[int, int, int]

# Color scheme
COLORS = {
    'primary': (41, 128, 185),    # Blue
    'secondary': (52, 152, 219),  # Lighter Blue
    'success': (39, 174, 96),     # Green
    'warning': (241, 196, 15),    # Yellow
    'danger': (231, 76, 60),      # Red
    'dark': (44, 62, 80),         # Dark Blue-Gray
    'light': (236, 240, 241),     # Light Gray
    'white': (255, 255, 255),     # White
    'black': (0, 0, 0),           # Black
    'gray': (149, 165, 166),      # Gray
    'light_gray': (236, 240, 241) # Light Gray
}

# Fonts
FONTS = {
    'regular': 'helvetica',
    'bold': 'helveticab',
    'italic': 'helveticai',
    'bold_italic': 'helveticabi',
    'mono': 'courier'
}

class TravelPDF(FPDF):
    """Custom PDF generator for travel documents."""
    
    def __init__(self, title: str = "Travel Itinerary", author: str = "Travel Planner"):
        super().__init__()
        self.title = title
        self.author = author
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(15, 15, 15)
        self.set_author(author)
        self.set_title(title)
        self.set_display_mode("fullwidth")
        self.set_compression(True)
        self._toc = []
    
    def header(self):
        """Add a header to each page."""
        self.set_fill_color(*COLORS['primary'])
        self.rect(0, 0, self.w, 25, 'F')
        self.set_xy(15, 10)
        self.set_font(FONTS['bold'], 'B', 16)
        self.set_text_color(*COLORS['white'])
        self.cell(0, 10, self.title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_draw_color(*COLORS['secondary'])
        self.set_line_width(0.5)
        self.line(15, 25, self.w - 15, 25)
        self.set_y(30)
    
    def footer(self):
        """Add a footer to each page."""
        self.set_y(-15)
        self.set_draw_color(*COLORS['light_gray'])
        self.line(15, self.get_y(), self.w - 15, self.get_y())
        self.set_font(FONTS['regular'], 'I', 8)
        self.set_text_color(*COLORS['gray'])
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
        self.set_x(15)
        self.cell(0, 10, self.title, 0, 0, 'L')

    def add_section(self, title: str, level: int = 1):
        """Add a section title to the document."""
        self.ln(5 if level > 1 else 10)
        if level == 1:
            self.set_font(FONTS['bold'], 'B', 16)
            self.set_text_color(*COLORS['primary'])
            self.set_fill_color(*COLORS['light_gray'])
            self.cell(0, 10, title, 0, 1, 'L', fill=True)
        elif level == 2:
            self.set_font(FONTS['bold'], 'B', 14)
            self.set_text_color(*COLORS['dark'])
            self.cell(0, 8, title, 0, 1, 'L')
            self.set_draw_color(*COLORS['secondary'])
            self.set_line_width(0.3)
            self.line(self.get_x(), self.get_y(), self.get_x() + 50, self.get_y())
            self.ln(2)
        else:
            self.set_font(FONTS['bold'], 'B', 12)
            self.set_text_color(*COLORS['dark'])
            self.cell(0, 6, title, 0, 1, 'L')
        
        self.set_font(FONTS['regular'], '', 10)
        self.set_text_color(*COLORS['black'])

def generate_flight_itinerary_pdf(itinerary: FlightItinerary, 
                                output_path: Optional[Union[str, Path]] = None) -> Optional[bytes]:
    """Generate a PDF for a flight itinerary."""
    pdf = TravelPDF(title="Flight Itinerary")
    pdf.add_page()
    
    # Header
    pdf.set_font(FONTS['bold'], 'B', 20)
    pdf.cell(0, 10, "Flight Itinerary", 0, 1, 'C')
    pdf.ln(10)
    
    # Booking reference
    if hasattr(itinerary, 'booking_reference') and itinerary.booking_reference:
        pdf.set_font(FONTS['bold'], 'B', 12)
        pdf.cell(0, 8, f"Booking Reference: {itinerary.booking_reference}", 0, 1, 'L')
    
    # Price
    if hasattr(itinerary, 'price') and itinerary.price is not None:
        price_str = format_currency(itinerary.price, getattr(itinerary, 'currency', 'USD'))
        pdf.set_font(FONTS['bold'], 'B', 14)
        pdf.set_text_color(*COLORS['success'])
        pdf.cell(0, 8, f"Total Price: {price_str}", 0, 1, 'L')
    
    pdf.ln(5)
    
    # Flight segments
    for i, segment in enumerate(itinerary.segments):
        pdf.add_section(f"Flight {i+1}", 2)
        
        # Flight details
        dep_time = segment.departure_time.strftime('%a, %b %d, %Y %H:%M')
        arr_time = segment.arrival_time.strftime('%a, %b %d, %Y %H:%M')
        
        pdf.set_font(FONTS['bold'], 'B', 12)
        pdf.cell(0, 8, f"{segment.airline}{segment.flight_number}", 0, 1, 'L')
        
        pdf.set_font(FONTS['regular'], '', 10)
        pdf.cell(30, 6, "Departure:", 0, 0, 'L')
        pdf.cell(0, 6, f"{segment.departure_airport} at {dep_time}", 0, 1, 'L')
        
        pdf.cell(30, 6, "Arrival:", 0, 0, 'L')
        pdf.cell(0, 6, f"{segment.arrival_airport} at {arr_time}", 0, 1, 'L')
        
        duration = f"{segment.duration_minutes // 60}h {segment.duration_minutes % 60}m"
        pdf.cell(30, 6, "Duration:", 0, 0, 'L')
        pdf.cell(0, 6, duration, 0, 1, 'L')
        
        if hasattr(segment, 'aircraft'):
            pdf.cell(30, 6, "Aircraft:", 0, 0, 'L')
            pdf.cell(0, 6, segment.aircraft, 0, 1, 'L')
        
        if hasattr(segment, 'baggage_allowance'):
            pdf.cell(30, 6, "Baggage:", 0, 0, 'L')
            pdf.cell(0, 6, segment.baggage_allowance, 0, 1, 'L')
        
        pdf.ln(5)
    
    # Booking info
    if hasattr(itinerary, 'booking_url') and itinerary.booking_url:
        pdf.add_section("Booking Information", 2)
        pdf.set_font(FONTS['regular'], 'U', 10)
        pdf.set_text_color(*COLORS['secondary'])
        pdf.cell(0, 6, itinerary.booking_url, link=itinerary.booking_url)
        pdf.ln(10)
    
    # Terms and conditions
    pdf.add_section("Terms & Conditions", 2)
    pdf.set_font(FONTS['regular'], '', 8)
    pdf.set_text_color(*COLORS['gray'])
    pdf.multi_cell(0, 4, 
        "This is an automatically generated itinerary. Please verify all details with the airline. "
        "Flight times are subject to change."
    )
    
    # Save or return the PDF
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(output_path)
        return None
    else:
        return pdf.output(dest='S').encode('latin1')

# Example usage
if __name__ == "__main__":
    from datetime import datetime, timedelta
    from schemas.flight import FlightSegment, FlightItinerary
    
    # Create a sample flight itinerary
    departure = datetime.now() + timedelta(days=30)
    arrival = departure + timedelta(hours=5, minutes=30)
    
    segment = FlightSegment(
        departure_airport="JFK",
        arrival_airport="LAX",
        departure_time=departure,
        arrival_time=arrival,
        airline="AA",
        flight_number="123",
        aircraft="Boeing 777",
        equipment="B777",
        cabin_class="economy",
        booking_code="Y",
        duration_minutes=330,
        operating_airline="AA",
        operating_flight_number="123",
        distance_miles=2475,
        seats_remaining=5,
        fare_basis="Y123",
        baggage_allowance="1 x 23kg"
    )
    
    itinerary = FlightItinerary(
        id="ITIN123456",
        price=299.99,
        currency="USD",
        segments=[segment],
        booking_url="https://example.com/book/ITIN123456",
        provider="mock",
        last_ticketing_datetime=departure - timedelta(days=7),
        number_of_bookable_seats=3,
        pricing_options={
            "fare_type": "PUBLIC",
            "included_checked_bags": 1,
            "is_refundable": False,
            "is_partial_refundable": True,
            "cancellation_deadline": (departure - timedelta(days=2)).isoformat(),
            "change_deadline": (departure - timedelta(days=1)).isoformat()
        }
    )
    
    # Generate and save the flight itinerary PDF
    generate_flight_itinerary_pdf(itinerary, "flight_itinerary.pdf")
