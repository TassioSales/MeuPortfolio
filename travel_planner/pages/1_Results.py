"""
Flight Search Results Page

This module displays the search results for flight queries, including flight options,
pricing, and filters. It allows users to sort, filter, and select flights.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

import streamlit as st

from config import settings
from config.log_config import get_logger
from schemas.flight import FlightItinerary, FlightSegment, CabinClass
from schemas.search import FlightSearchQuery, SortBy
from services.amadeus_service import amadeus_service
from services.gemini_service import gemini_service
from services.unsplash_service import unsplash_service
from utils.helpers import format_currency, format_duration, format_date, format_time

# Initialize logger
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Flight Search Results | Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'selected_flights' not in st.session_state:
    st.session_state.selected_flights = {}
if 'search_params' not in st.session_state:
    st.session_state.search_params = {}
if 'itinerary' not in st.session_state:
    st.session_state.itinerary = None
if 'show_itinerary_modal' not in st.session_state:
    st.session_state.show_itinerary_modal = False

# Custom CSS for better UI
st.markdown("""
    <style>
    .flight-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    .flight-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .selected-flight {
        border: 2px solid #4CAF50 !important;
        background-color: #f0f9f0;
    }
    .airline-logo {
        max-width: 40px;
        max-height: 40px;
        margin-right: 10px;
    }
    .price-tag {
        font-size: 1.5em;
        font-weight: bold;
        color: #2196F3;
    }
    .duration-badge {
        background-color: #e3f2fd;
        color: #1565C0;
        padding: 3px 8px;
        border-radius: 10px;
        font-size: 0.8em;
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
    }
    .itinerary-modal {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        padding: 20px;
        border-radius: 10px;
        z-index: 1000;
        width: 80%;
        max-width: 800px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0,0,0,0.5);
        z-index: 999;
    }
    </style>
""", unsafe_allow_html=True)

def display_flight_segment(segment: FlightSegment) -> None:
    """Display a single flight segment."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown(f"**{segment.departure_time.strftime('%H:%M')}**")
        st.caption(segment.departure_airport)
        st.caption(segment.departure_time.strftime('%a, %b %d'))
    
    with col2:
        duration = segment.duration_minutes
        hours, minutes = divmod(duration, 60)
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        st.progress(0.5)
        st.markdown(f"<div style='text-align: center;'>{duration_str} • {segment.airline} {segment.flight_number}</div>", 
                   unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"**{segment.arrival_time.strftime('%H:%M')}**")
        st.caption(segment.arrival_airport)
        st.caption(segment.arrival_time.strftime('%a, %b %d'))
    
    st.markdown("---")

def display_flight_card(flight: FlightItinerary, index: int) -> None:
    """Display a flight card with details."""
    # Check if this flight is selected
    is_selected = st.session_state.selected_flights.get(flight.id, False)
    
    # Card container
    card_class = "flight-card" + (" selected-flight" if is_selected else "")
    st.markdown(f"<div class='{card_class}'>", unsafe_allow_html=True)
    
    # Flight header with airline and price
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Airline and flight number
        airline = flight.segments[0].airline if flight.segments else "Unknown"
        st.markdown(f"**{airline}** • {flight.segments[0].flight_number if flight.segments else ''}")
        
        # Stops information
        stops = len(flight.segments) - 1
        if stops == 0:
            stops_text = "Direct"
        else:
            stops_text = f"{stops} stop{'s' if stops > 1 else ''}"
        
        st.caption(f"✈️ {stops_text} • {flight.segments[0].cabin_class if flight.segments else 'Economy'}")
    
    with col2:
        # Price
        st.markdown(f"<div class='price-tag'>{format_currency(flight.price, flight.currency)}</div>", 
                   unsafe_allow_html=True)
        st.caption("per passenger")
    
    # Flight segments
    for i, segment in enumerate(flight.segments):
        if i > 0:
            # Show layover time
            prev_arrival = flight.segments[i-1].arrival_time
            layover = (segment.departure_time - prev_arrival).total_seconds() / 60  # in minutes
            
            if layover > 0:
                hours, minutes = divmod(int(layover), 60)
                layover_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                st.markdown(
                    f"<div style='text-align: center; margin: 5px 0;'>"
                    f"Layover: {layover_str} at {segment.departure_airport}"
                    "</div>",
                    unsafe_allow_html=True
                )
        
        display_flight_segment(segment)
    
    # Flight details and select button
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Baggage and other info
        baggage = flight.segments[0].baggage_allowance if flight.segments else "1 x 23kg"
        st.caption(f"🎒 {baggage} • ✈️ {flight.aircraft if hasattr(flight, 'aircraft') else 'Boeing 737'}")
        
        # Cancellation policy
        if hasattr(flight, 'refundable') and flight.refundable:
            st.caption("🔄 Free cancellation available")
    
    with col2:
        # Select button
        if is_selected:
            if st.button("Selected", key=f"selected_{index}", disabled=True):
                pass
        else:
            if st.button("Select", key=f"select_{index}"):
                # Toggle selection
                st.session_state.selected_flights[flight.id] = not st.session_state.selected_flights.get(flight.id, False)
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def display_search_filters() -> Dict[str, Any]:
    """Display and handle search filters in the sidebar."""
    st.sidebar.header("🔍 Filters")
    
    # Price range
    price_range = st.sidebar.slider(
        "Price Range",
        0, 5000, (0, 2000),
        step=50,
        format="$%d"
    )
    
    # Stops
    stops = st.sidebar.multiselect(
        "Stops",
        ["Direct", "1 Stop", "2+ Stops"],
        ["Direct", "1 Stop"]
    )
    
    # Airlines
    airlines = st.sidebar.multiselect(
        "Airlines",
        ["Delta", "United", "American", "Southwest", "JetBlue", "Spirit", "Frontier"],
        []
    )
    
    # Departure time
    departure_times = st.sidebar.multiselect(
        "Departure Time",
        ["Morning (6AM-12PM)", "Afternoon (12PM-5PM)", "Evening (5PM-10PM)", "Night (10PM-6AM)"],
        []
    )
    
    # Cabin class
    cabin_class = st.sidebar.selectbox(
        "Cabin Class",
        ["Economy", "Premium Economy", "Business", "First Class"],
        index=0
    )
    
    # Sort by
    sort_by = st.sidebar.selectbox(
        "Sort By",
        ["Best", "Price (Low to High)", "Price (High to Low)", "Duration (Shortest)", "Departure (Earliest)"],
        index=0
    )
    
    return {
        "price_range": price_range,
        "stops": stops,
        "airlines": airlines,
        "departure_times": departure_times,
        "cabin_class": cabin_class,
        "sort_by": sort_by
    }

def filter_flights(flights: List[FlightItinerary], filters: Dict[str, Any]) -> List[FlightItinerary]:
    """Filter flights based on user-selected filters."""
    filtered = flights.copy()
    
    # Filter by price range
    min_price, max_price = filters["price_range"]
    filtered = [f for f in filtered if min_price <= f.price <= max_price]
    
    # Filter by stops
    if filters["stops"]:
        max_stops = 2  # Default to 2+ stops if any option is selected
        if "Direct" in filters["stops"] and len(filters["stops"]) == 1:
            max_stops = 0
        elif "1 Stop" in filters["stops"] and len(filters["stops"]) == 1:
            max_stops = 1
        
        filtered = [f for f in filtered if (len(f.segments) - 1) <= max_stops]
    
    # Filter by airlines
    if filters["airlines"]:
        filtered = [f for f in filtered if any(airline in f.segments[0].airline for airline in filters["airlines"])]
    
    # Filter by departure time
    if filters["departure_times"]:
        time_filtered = []
        for flight in filtered:
            if not flight.segments:
                continue
                
            dep_time = flight.segments[0].departure_time.hour
            time_match = False
            
            if "Morning (6AM-12PM)" in filters["departure_times"] and 6 <= dep_time < 12:
                time_match = True
            if "Afternoon (12PM-5PM)" in filters["departure_times"] and 12 <= dep_time < 17:
                time_match = True
            if "Evening (5PM-10PM)" in filters["departure_times"] and 17 <= dep_time < 22:
                time_match = True
            if "Night (10PM-6AM)" in filters["departure_times"] and (22 <= dep_time or dep_time < 6):
                time_match = True
                
            if time_match:
                time_filtered.append(flight)
        
        filtered = time_filtered
    
    # Sort the results
    if filters["sort_by"] == "Price (Low to High)":
        filtered.sort(key=lambda x: x.price)
    elif filters["sort_by"] == "Price (High to Low)":
        filtered.sort(key=lambda x: -x.price)
    elif filters["sort_by"] == "Duration (Shortest)":
        filtered.sort(key=lambda x: sum(s.duration_minutes for s in x.segments))
    elif filters["sort_by"] == "Departure (Earliest)":
        filtered.sort(key=lambda x: x.segments[0].departure_time if x.segments else datetime.max)
    
    return filtered

def display_itinerary_modal():
    """Display a modal for viewing the full travel itinerary."""
    if st.session_state.show_itinerary_modal and st.session_state.itinerary:
        st.markdown("<div class='modal-backdrop' onclick='window.itineraryModalClose()'></div>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<div class='itinerary-modal'>", unsafe_allow_html=True)
            
            # Modal header
            st.markdown("### ✈️ Your Travel Itinerary")
            st.markdown(f"**Destination:** {st.session_state.itinerary.destination}")
            st.markdown(f"**Dates:** {st.session_state.itinerary.start_date} to {st.session_state.itinerary.end_date}")
            st.markdown("---")
            
            # Daily plans
            for day in st.session_state.itinerary.daily_plans:
                st.markdown(f"#### 📅 Day {day.day_number}: {day.date.strftime('%A, %B %d')}")
                
                for activity in day.activities:
                    with st.expander(f"🕒 {activity.time}: {activity.title}"):
                        st.markdown(f"**Location:** {activity.location}")
                        st.markdown(f"**Duration:** {activity.duration}")
                        st.markdown(f"**Cost:** {activity.cost}")
                        
                        if activity.notes:
                            st.markdown("**Notes:**")
                            for note in activity.notes:
                                st.markdown(f"- {note}")
                
                st.markdown("---")
            
            # Close button
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("Close Itinerary"):
                    st.session_state.show_itinerary_modal = False
                    st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Add JavaScript to close modal when clicking outside
        st.markdown("""
            <script>
            window.itineraryModalClose = function() {
                const event = new CustomEvent('closeItineraryModal');
                window.dispatchEvent(event);
            }
            
            // Close modal when clicking outside
            document.addEventListener('click', function(event) {
                const modal = document.querySelector('.itinerary-modal');
                const backdrop = document.querySelector('.modal-backdrop');
                
                if (event.target === backdrop) {
                    window.itineraryModalClose();
                }
            });
            
            // Listen for close event from Streamlit
            window.addEventListener('closeItineraryModal', function() {
                const data = {type: 'close_modal'};
                window.parent.postMessage(data, '*');
            });
            </script>
        """, unsafe_allow_html=True)

def main():
    """Main function to render the results page."""
    # Page header
    st.title("✈️ Flight Search Results")
    
    # Display search summary
    if 'search_params' in st.session_state and st.session_state.search_params:
        params = st.session_state.search_params
        st.markdown(f"""
            <div style='background-color: #f0f8ff; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <h3>{params.get('origin', '')} → {params.get('destination', '')}</h3>
                        <p>{params.get('departure_date', '')} • {params.get('return_date', 'One way')} • 
                        {params.get('passengers', 1)} {'passenger' if int(params.get('passengers', 1)) == 1 else 'passengers'}</p>
                    </div>
                    <div>
                        <button class='css-1x8cf1d edgvbvh10' style='background-color: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 20px; cursor: pointer;'>
                            Modify Search
                        </button>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    # Display filters in sidebar
    filters = display_search_filters()
    
    # Display search results
    if st.session_state.search_results:
        # Apply filters
        filtered_flights = filter_flights(st.session_state.search_results, filters)
        
        # Show result count
        st.markdown(f"**{len(filtered_flights)} flights found**")
        
        # Display each flight
        for i, flight in enumerate(filtered_flights):
            display_flight_card(flight, i)
            
        # Show a message if no flights match the filters
        if not filtered_flights:
            st.warning("No flights match your current filters. Try adjusting your search criteria.")
            
            # Button to reset filters
            if st.button("Reset Filters"):
                # Reset filters to default
                st.rerun()
    else:
        # No search results yet
        st.info("Use the search form to find flights. No search results to display yet.")
        
        # Add a button to go back to search
        if st.button("← Back to Search"):
            st.switch_page("app.py")
    
    # Display itinerary modal if needed
    display_itinerary_modal()
    
    # Add JavaScript for handling modal close
    st.markdown("""
        <script>
        // Listen for messages from parent window
        window.addEventListener('message', function(event) {
            if (event.data.type === 'close_modal') {
                // Rerun the app to close the modal
                window.parent.document.dispatchEvent(new CustomEvent('streamlit:setFrameHeight', {detail: document.body.scrollHeight}));
            }
        });
        </script>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    # Mock data for testing
    if not st.session_state.search_results:
        from services.flight_faker import flight_faker
        from datetime import datetime, timedelta
        
        # Generate some fake flights using search_flights
        departure_date = datetime.now() + timedelta(days=30)
        return_date = datetime.now() + timedelta(days=37)
        search_results = flight_faker.search_flights(
            origin="JFK",
            destination="LAX",
            departure_date=departure_date,
            return_date=return_date,
            limit=5
        )
        st.session_state.search_results = search_results.data
        
        # Set search params
        st.session_state.search_params = {
            "origin": "New York (JFK)",
            "destination": "Los Angeles (LAX)",
            "departure_date": (datetime.now() + timedelta(days=30)).strftime("%a, %b %d, %Y"),
            "return_date": (datetime.now() + timedelta(days=37)).strftime("%a, %b %d, %Y"),
            "passengers": 1,
            "cabin_class": "Economy"
        }
    
    main()
