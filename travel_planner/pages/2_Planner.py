"""
Travel Planner Page - Part 1: Basic Structure

This module provides an interactive interface for users to create and manage
travel itineraries with AI-powered suggestions.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import streamlit as st

from config.log_config import get_logger
from schemas.itinerary import TravelItinerary, DailyPlan, Activity
from services.gemini_service import gemini_service
from services.unsplash_service import unsplash_service
from utils.helpers import format_date

# Initialize logger
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Trip Planner | Travel Planner",
    page_icon="🗺️",
    layout="wide"
)

def init_session_state():
    """Initialize session state variables."""
    if 'itinerary' not in st.session_state:
        st.session_state.itinerary = create_new_itinerary()
    if 'destination_images' not in st.session_state:
        st.session_state.destination_images = {}
    if 'ai_suggestions' not in st.session_state:
        st.session_state.ai_suggestions = {}
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "itinerary"

def create_new_itinerary() -> TravelItinerary:
    """Create a new empty itinerary."""
    today = datetime.now().date()
    return TravelItinerary(
        title="My Trip",
        destination="",
        start_date=today,
        end_date=today + timedelta(days=3),
        daily_plans=[],
        notes=[],
        budget=0.0,
        currency="USD"
    )

def display_header():
    """Display the page header."""
    st.title("✈️ Travel Itinerary Planner")
    st.markdown("Plan your perfect trip with AI-powered suggestions")
    st.markdown("---")

# Initialize session state
init_session_state()

# Basic CSS
st.markdown("""
    <style>
    .itinerary-day {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        background-color: #f9f9f9;
    }
    .activity-card {
        background-color: white;
        border-left: 4px solid #4CAF50;
        padding: 10px 15px;
        margin: 10px 0;
        border-radius: 0 5px 5px 0;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 10px 20px;
    }
    </style>
""", unsafe_allow_html=True)

def display_itinerary_editor():
    """Display the itinerary editor form."""
    itinerary = st.session_state.itinerary
    
    # Basic trip info
    col1, col2 = st.columns(2)
    
    with col1:
        itinerary.title = st.text_input("Trip Title", value=itinerary.title)
    
    with col2:
        itinerary.destination = st.text_input("Destination", value=itinerary.destination or "")
    
    # Date range
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input("Start Date", value=itinerary.start_date)
        if start_date != itinerary.start_date:
            itinerary.start_date = start_date
            # Update end date if it's before start date
            if itinerary.end_date < start_date:
                itinerary.end_date = start_date + timedelta(days=1)
    
    with col2:
        min_end_date = itinerary.start_date + timedelta(days=1)
        end_date = st.date_input(
            "End Date",
            value=itinerary.end_date,
            min_value=min_end_date
        )
        if end_date != itinerary.end_date:
            itinerary.end_date = end_date
    
    # Update days based on date range
    num_days = (itinerary.end_date - itinerary.start_date).days + 1
    
    # Initialize or update daily plans
    if not itinerary.daily_plans or len(itinerary.daily_plans) != num_days:
        itinerary.daily_plans = []
        for i in range(num_days):
            day_date = itinerary.start_date + timedelta(days=i)
            itinerary.daily_plans.append(DailyPlan(
                day_number=i + 1,
                date=day_date,
                activities=[]
            ))
    
    # Display daily plans
    st.subheader("📅 Daily Plans")
    
    # Create tabs for each day
    day_tabs = st.tabs([f"Day {i+1}" for i in range(num_days)])
    
    for i, day_tab in enumerate(day_tabs):
        with day_tab:
            day = itinerary.daily_plans[i]
            st.markdown(f"### {day.date.strftime('%A, %B %d, %Y')}")
            
            # Add new activity
            with st.expander("➕ Add Activity", expanded=False):
                with st.form(key=f"add_activity_{i}"):
                    activity_time = st.time_input("Time", value=datetime.strptime("12:00", "%H:%M").time(), key=f"time_{i}")
                    activity_title = st.text_input("Title", key=f"title_{i}")
                    activity_location = st.text_input("Location", key=f"location_{i}")
                    activity_notes = st.text_area("Notes", key=f"notes_{i}")
                    
                    if st.form_submit_button("Add Activity"):
                        if activity_title:
                            new_activity = Activity(
                                title=activity_title,
                                time=activity_time.strftime("%H:%M"),
                                location=activity_location,
                                notes=[note for note in activity_notes.split('\n') if note.strip()]
                            )
                            day.activities.append(new_activity)
                            st.rerun()
            
            # Display activities for the day
            if day.activities:
                # Sort activities by time
                day.activities.sort(key=lambda x: x.time)
                
                for j, activity in enumerate(day.activities):
                    with st.container():
                        st.markdown(f"""
                            <div class="activity-card">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <strong>{activity.time}</strong> • {activity.title}
                                        {f'<br><span style="color: #666;">📍 {activity.location}</span>' if activity.location else ''}
                                    </div>
                                    <div>
                                        <button onclick="window.deleteActivity({i}, {j})" style="background: none; border: none; cursor: pointer;">
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                                {"<div class="activity-notes">" + "<br>".join([f"• {note}" for note in activity.notes]) + "</div>" if activity.notes else ""}
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No activities planned for this day. Add some activities using the form above.")
    
    # Add JavaScript for activity deletion
    st.markdown(
        """
        <script>
        function deleteActivity(dayIndex, activityIndex) {
            const data = {
                type: 'delete_activity',
                dayIndex: dayIndex,
                activityIndex: activityIndex
            };
            window.parent.postMessage(data, '*');
        }
        
        // Listen for messages from the parent window
        window.addEventListener('message', function(event) {
            if (event.data.type === 'delete_activity') {
                const {dayIndex, activityIndex} = event.data;
                // This will be handled in the main Streamlit app
                window.parent.document.dispatchEvent(new CustomEvent('deleteActivity', {detail: {dayIndex, activityIndex}}));
            }
        });
        </script>
        """,
        unsafe_allow_html=True
    )

def handle_custom_events():
    """Handle custom JavaScript events."""
    if 'delete_activity' in st.query_params:
        try:
            day_index = int(st.query_params['day_index'])
            activity_index = int(st.query_params['activity_index'])
            
            if 0 <= day_index < len(st.session_state.itinerary.daily_plans):
                day = st.session_state.itinerary.daily_plans[day_index]
                if 0 <= activity_index < len(day.activities):
                    del day.activities[activity_index]
                    st.rerun()
        except (ValueError, KeyError):
            pass

# Main layout
display_header()

# Handle custom events
handle_custom_events()

# Create tabs
tab1, tab2 = st.tabs(["📝 Itinerary", "🔍 AI Suggestions"])

with tab1:
    display_itinerary_editor()

def display_ai_suggestions():
    """Display AI-powered suggestions for the trip."""
    itinerary = st.session_state.itinerary
    
    if not itinerary.destination:
        st.warning("Please enter a destination in the Itinerary tab first.")
        return
    
    # Check if we already have suggestions for this destination
    if itinerary.destination in st.session_state.ai_suggestions:
        suggestions = st.session_state.ai_suggestions[itinerary.destination]
    else:
        suggestions = None
    
    # Button to generate new suggestions
    if st.button("✨ Generate New Suggestions") or not suggestions:
        with st.spinner("Generating AI-powered suggestions..."):
            try:
                # Generate destination images if not already cached
                if itinerary.destination not in st.session_state.destination_images:
                    images = asyncio.run(unsplash_service.search_photos(
                        query=itinerary.destination,
                        per_page=6,
                        orientation="landscape"
                    ))
                    st.session_state.destination_images[itinerary.destination] = images.get("results", [])
                
                # Get travel tips and recommendations
                travel_tips = asyncio.run(gemini_service.get_travel_tips(
                    destination=itinerary.destination,
                    travel_dates={
                        "start_date": itinerary.start_date.isoformat(),
                        "end_date": itinerary.end_date.isoformat()
                    },
                    interests=["sightseeing", "food", "culture"],
                    group_type="solo"  # Could be made configurable
                ))
                
                # Get recommended activities
                recommended_activities = asyncio.run(gemini_service.generate_itinerary(
                    destination=itinerary.destination,
                    start_date=itinerary.start_date.isoformat(),
                    end_date=itinerary.end_date.isoformat(),
                    interests=["sightseeing", "food", "culture"],
                    budget="medium",  # Could be made configurable
                    group_type="solo"
                ))
                
                # Save to session state
                st.session_state.ai_suggestions[itinerary.destination] = {
                    "travel_tips": travel_tips,
                    "recommended_activities": recommended_activities
                }
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Failed to generate suggestions: {str(e)}")
                return
    
    # Display suggestions if available
    if suggestions:
        # Display destination images
        if itinerary.destination in st.session_state.destination_images:
            images = st.session_state.destination_images[itinerary.destination]
            if images:
                st.subheader(f"📷 Images of {itinerary.destination}")
                
                # Display images in a grid
                cols = st.columns(3)
                for i, image in enumerate(images[:6]):  # Show max 6 images
                    with cols[i % 3]:
                        st.image(
                            image.urls.get("regular"),
                            use_column_width=True,
                            caption=image.description or f"Photo by {image.user.get('name', 'Unknown')} on Unsplash"
                        )
                
                st.markdown("---")
        
        # Display travel tips
        if "travel_tips" in suggestions and suggestions["travel_tips"]:
            st.subheader("💡 Travel Tips")
            
            tips = suggestions["travel_tips"]
            
            if "best_time_to_visit" in tips:
                with st.expander("⏰ Best Time to Visit", expanded=True):
                    st.write(tips["best_time_to_visit"])
            
            if "local_customs" in tips:
                with st.expander("👥 Local Customs & Etiquette", expanded=False):
                    st.write(tips["local_customs"])
            
            if "safety_tips" in tips:
                with st.expander("🔒 Safety Tips", expanded=False):
                    st.write(tips["safety_tips"])
            
            if "money_saving_tips" in tips:
                with st.expander("💰 Money-Saving Tips", expanded=False):
                    st.write(tips["money_saving_tips"])
            
            st.markdown("---")
        
        # Display recommended activities
        if "recommended_activities" in suggestions and suggestions["recommended_activities"]:
            st.subheader("🏞️ Recommended Activities")
            
            activities = suggestions["recommended_activities"]
            
            if "days" in activities and activities["days"]:
                for day in activities["days"]:
                    if "activities" in day and day["activities"]:
                        with st.expander(f"Day {day.get('day_number', '?')}: {day.get('day_title', 'Activities')}", 
                                      expanded=True if day.get('day_number', 1) == 1 else False):
                            for activity in day["activities"]:
                                st.markdown(f"""
                                    <div class="activity-card">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <div>
                                                <strong>{activity.get('time', '')}</strong> • {activity.get('title', '')}
                                                {f'<br><span style="color: #666;">📍 {activity.get("location", "")}</span>' if activity.get("location") else ''}
                                            </div>
                                            {f'<a href="{activity.get("booking_link", "#")}" target="_blank" style="text-decoration: none;">
                                                <button style="background: #4CAF50; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer;">
                                                    Book Now
                                                </button>
                                            </a>' if activity.get("booking_link") else ''}
                                        </div>
                                        {"<div class=\"activity-notes\">" + activity.get("description", "") + "</div>" if activity.get("description") else ""}
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                # Add to itinerary button
                                if st.button(f"Add to Itinerary: {activity.get('title', '')}", 
                                           key=f"add_{activity.get('id', '')}"):
                                    # Find the corresponding day in the itinerary
                                    day_index = day.get('day_number', 1) - 1
                                    if 0 <= day_index < len(st.session_state.itinerary.daily_plans):
                                        # Create a new activity
                                        new_activity = Activity(
                                            title=activity.get('title', 'Activity'),
                                            time=activity.get('time', '12:00'),
                                            location=activity.get('location', ''),
                                            notes=[activity.get('description', '')] if activity.get('description') else []
                                        )
                                        # Add to the day's activities
                                        st.session_state.itinerary.daily_plans[day_index].activities.append(new_activity)
                                        st.success(f"Added {activity.get('title', 'activity')} to your itinerary!")
                                        st.rerun()
                                    else:
                                        st.error("Could not add activity to itinerary: Invalid day number")
                            
                            st.markdown("---")
        
        # Display additional recommendations
        if "recommended_activities" in suggestions and "additional_recommendations" in suggestions["recommended_activities"]:
            with st.expander("🌟 More Recommendations", expanded=False):
                for rec_type, items in suggestions["recommended_activities"]["additional_recommendations"].items():
                    if items:
                        st.subheader(rec_type.replace("_", " ").title())
                        if isinstance(items, list):
                            for item in items:
                                st.markdown(f"- {item}")
                        elif isinstance(items, dict):
                            for key, value in items.items():
                                st.markdown(f"**{key}**: {value}")
                        st.markdown("")

# Main layout
display_header()

# Handle custom events
handle_custom_events()

# Create tabs
tab1, tab2 = st.tabs(["📝 Itinerary", "🔍 AI Suggestions"])

with tab1:
    display_itinerary_editor()

with tab2:
    display_ai_suggestions()
