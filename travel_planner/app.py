"""
Travel Planner - Main Application

This is the main entry point for the Travel Planner Streamlit application.
"""
import asyncio
import datetime
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import streamlit as st
from loguru import logger

from config.settings import settings
from config.log_config import setup_logging
from schemas.search import FlightSearchQuery, LocationSearchResponse
from schemas.flight import FlightSegment, FlightItinerary, FlightSearchResponse

# Setup logging
setup_logging()
logger = logger.bind(module=__name__)

# Set page config
st.set_page_config(
    page_title="Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css():
    """Load custom CSS styles."""
    css_file = settings.BASE_DIR / "static" / "css" / "styles.css"
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        # Fallback to basic styles if CSS file is missing
        st.markdown("""
        <style>
            .main { padding: 2rem; }
            .stButton>button { width: 100%; }
            .flight-card { 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 1rem; 
                margin-bottom: 1rem;
            }
            .flight-card:hover { 
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                transition: box-shadow 0.3s ease;
            }
        </style>
        """, unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables."""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(hash(st.session_state.get('_id', id(st))))
        logger.info(f"New session started: {st.session_state.session_id}")
    
    # Initialize search state
    if 'search_query' not in st.session_state:
        st.session_state.search_query = None
    if 'search_results' not in st.session_state:
        st.session_state.search_results = None
    if 'selected_flight' not in st.session_state:
        st.session_state.selected_flight = None

def show_flight_search():
    """Display the flight search form and handle submissions."""
    st.header("✈️ Search Flights")
    
    with st.form("flight_search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            origin = st.text_input(
                "From (City or Airport)",
                value=st.session_state.search_query.origin if st.session_state.search_query else "",
                help="Enter the city or airport code of your departure location"
            )
            
            destination = st.text_input(
                "To (City or Airport)",
                value=st.session_state.search_query.destination if st.session_state.search_query else "",
                help="Enter the city or airport code of your destination"
            )
        
        with col2:
            today = datetime.date.today()
            min_date = today
            max_date = today + datetime.timedelta(days=365)
            
            departure_date = st.date_input(
                "Departure",
                value=st.session_state.search_query.departure_date if st.session_state.search_query else today + datetime.timedelta(days=7),
                min_value=min_date,
                max_value=max_date,
                help="Select your departure date"
            )
            
            return_date = st.date_input(
                "Return (optional)",
                value=st.session_state.search_query.return_date if (st.session_state.search_query and hasattr(st.session_state.search_query, 'return_date')) else None,
                min_value=departure_date if departure_date else min_date,
                max_value=max_date,
                help="Select your return date (leave empty for one-way)"
            )
        
        # Advanced options
        with st.expander("Advanced Options"):
            adv_col1, adv_col2 = st.columns(2)
            with adv_col1:
                adults = st.number_input("Adults (12+)", min_value=1, max_value=9, value=1)
                children = st.number_input("Children (2-11)", min_value=0, max_value=8, value=0)
                infants = st.number_input("Infants (under 2)", min_value=0, max_value=5, value=0)
            
            with adv_col2:
                cabin_class = st.selectbox(
                    "Cabin Class",
                    ["Economy", "Premium Economy", "Business", "First"],
                    index=0
                )
                
                max_stops = st.selectbox(
                    "Max Stops",
                    ["Non-stop only", "Up to 1 stop", "Up to 2 stops", "Any number of stops"],
                    index=0
                )
        
        # Search button
        if st.form_submit_button("Search Flights", type="primary"):
            try:
                # Validate inputs
                if not all([origin, destination, departure_date]):
                    st.error("Please fill in all required fields.")
                    return
                
                if origin.lower() == destination.lower():
                    st.error("Origin and destination cannot be the same.")
                    return
                
                if return_date and return_date < departure_date:
                    st.error("Return date cannot be before departure date.")
                    return
                
                # Create search query
                search_query = FlightSearchQuery(
                    origin=origin.strip(),
                    destination=destination.strip(),
                    departure_date=departure_date,
                    return_date=return_date if return_date else None,
                    adults=adults,
                    children=children,
                    infants=infants,
                    cabin_class=cabin_class.lower().replace(" ", "_"),
                    max_stops={
                        "Non-stop only": 0,
                        "Up to 1 stop": 1,
                        "Up to 2 stops": 2,
                        "Any number of stops": None
                    }[max_stops]
                )
                
                # Store search query in session state
                st.session_state.search_query = search_query
                
                # Simulate API call (replace with actual API call)
                with st.spinner("Searching for flights..."):
                    try:
                        # Create mock response
                        departure_time = datetime.datetime.combine(departure_date, datetime.time(10, 0))
                        arrival_time = departure_time + datetime.timedelta(hours=2)
                        
                        mock_segment = FlightSegment(
                            departure_airport=origin.upper(),
                            arrival_airport=destination.upper(),
                            departure_time=departure_time,
                            arrival_time=arrival_time,
                            airline="XX",
                            flight_number="123",
                            aircraft="A320",
                            cabin_class="economy"
                        )
                        
                        mock_itinerary = FlightItinerary(
                            id="ITIN123",
                            price=299.99,
                            currency="USD",
                            segments=[mock_segment],
                            provider="amadeus"
                        )
                        
                        mock_response = FlightSearchResponse(
                            request_id="MOCK_REQ_123",
                            data=[mock_itinerary],
                            meta={"count": 1, "test": True}
                        )
                        
                        st.session_state.search_results = mock_response
                        st.rerun()
                        
                    except Exception as e:
                        logger.error(f"Error during flight search: {str(e)}", exc_info=True)
                        st.error("An error occurred while searching for flights. Please try again.")
            
            except Exception as e:
                logger.error(f"Error processing search form: {str(e)}", exc_info=True)
                st.error("An error occurred. Please check your inputs and try again.")

def show_flight_results():
    """Display flight search results."""
    if 'search_results' not in st.session_state or not st.session_state.search_results:
        st.warning("No search results available. Please perform a search first.")
        return
    
    st.header("✈️ Flight Results")
    
    # Display search summary
    query = st.session_state.search_query
    st.write(f"**From:** {query.origin.upper()}")
    st.write(f"**To:** {query.destination.upper()}")
    st.write(f"**Departure:** {query.departure_date.strftime('%A, %B %d, %Y')}")
    if query.return_date:
        st.write(f"**Return:** {query.return_date.strftime('%A, %B %d, %Y')}")
    
    st.divider()
    
    # Display results
    for itinerary in st.session_state.search_results.data:
        with st.container():
            airline_code = itinerary.segments[0].airline if itinerary.segments else "Unknown"
            st.subheader(f"{airline_code} Flight {itinerary.id}")
            
            # Display flight segments
            st.write("**Itinerary:**")
            for i, segment in enumerate(itinerary.segments, 1):
                st.write(f"**Segment {i}:** {segment.departure_airport} → {segment.arrival_airport}")
                st.write(f"Depart: {segment.departure_time.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"Arrive: {segment.arrival_time.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"Airline: {segment.airline} {segment.flight_number}")
                st.write(f"Duration: {segment.duration_formatted}")
                st.write(f"Aircraft: {segment.aircraft or 'Not specified'}")
                st.write(f"Class: {segment.cabin_class.value.title()}")
                st.write("---")
            
            st.write(f"\n**Total Price:** ${itinerary.price:.2f} {itinerary.currency}")
            
            if st.button(f"Select Flight {itinerary.id}"):
                st.session_state.selected_flight = itinerary.dict()
                st.success(f"Flight {itinerary.id} selected!")
                st.rerun()
            
            st.divider()

def show_itinerary():
    """Display the user's selected flight itinerary."""
    st.header("📋 My Itinerary")
    
    if 'selected_flight' not in st.session_state or not st.session_state.selected_flight:
        st.info("You haven't selected any flights yet. Search for flights to get started!")
        return
    
    itinerary = st.session_state.selected_flight
    st.subheader("Your Flight Details")
    
    st.json(itinerary)  # For now, just show the raw data
    
    if st.button("Clear Itinerary"):
        st.session_state.selected_flight = None
        st.rerun()

async def main():
    """Main application function."""
    try:
        # Initialize session state
        initialize_session_state()
        
        # Load CSS
        load_css()
        
        # Sidebar navigation
        st.sidebar.title("Travel Planner ✈️")
        page = st.sidebar.radio(
            "Navigation",
            ["Search Flights", "My Itinerary"],
            index=0
        )
        
        # Display the selected page
        if page == "Search Flights":
            if 'search_results' in st.session_state and st.session_state.search_results:
                show_flight_results()
            else:
                show_flight_search()
        elif page == "My Itinerary":
            show_itinerary()
    
    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}", exc_info=True)
        st.error("An unexpected error occurred. Please refresh the page and try again.")
        if settings.DEBUG:
            st.exception(e)

if __name__ == "__main__":
    asyncio.run(main())
