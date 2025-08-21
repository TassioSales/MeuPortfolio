"""
Google Gemini Integration Service

This module provides an interface to Google's Gemini API for generating
AI-powered travel recommendations, analyzing flight options, and providing
personalized travel advice.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

import google.generativeai as genai
from loguru import logger
from pydantic import BaseModel, Field

from config.settings import settings
from schemas.flight import FlightItinerary, FlightSegment
from schemas.itinerary import TravelItinerary, DailyPlan, Activity

# Configure logger
logger = logger.bind(module="gemini_service")

# Configure the Gemini API
try:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    logger.info("Google Gemini API configured successfully")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {str(e)}")
    raise

class GeminiService:
    """Service for interacting with Google's Gemini API."""
    
    def __init__(self, model_name: str = "gemini-pro"):
        """Initialize the Gemini service.
        
        Args:
            model_name: Name of the Gemini model to use
        """
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        self.chat_sessions = {}  # Store chat sessions by session_id
    
    async def generate_travel_recommendations(
        self,
        destination: str,
        travel_dates: Dict[str, str],
        interests: List[str],
        budget: str = "medium",
        group_type: str = "solo",
        previous_trips: List[Dict] = None,
        additional_context: str = ""
    ) -> Dict[str, Any]:
        """Generate personalized travel recommendations using Gemini.
        
        Args:
            destination: Destination city or country
            travel_dates: Dict with 'start_date' and 'end_date' (YYYY-MM-DD)
            interests: List of interests (e.g., ["history", "food", "adventure"])
            budget: Budget level (low, medium, high, luxury)
            group_type: Type of travel group (solo, couple, family, friends, business)
            previous_trips: List of previous trips for personalization
            additional_context: Any additional context or preferences
            
        Returns:
            Dict containing travel recommendations
        """
        prompt = self._build_travel_recommendation_prompt(
            destination, travel_dates, interests, budget, 
            group_type, previous_trips, additional_context
        )
        
        try:
            response = await self._generate_text(prompt)
            return self._parse_travel_recommendations(response)
        except Exception as e:
            logger.error(f"Failed to generate travel recommendations: {str(e)}")
            raise
    
    async def analyze_flight_options(
        self,
        itineraries: List[FlightItinerary],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze flight options and provide recommendations.
        
        Args:
            itineraries: List of FlightItinerary objects
            user_preferences: User preferences for flight selection
            
        Returns:
            Dict with analysis and recommendations
        """
        prompt = self._build_flight_analysis_prompt(itineraries, user_preferences)
        
        try:
            response = await self._generate_text(prompt)
            return self._parse_flight_analysis(response)
        except Exception as e:
            logger.error(f"Failed to analyze flight options: {str(e)}")
            raise
    
    async def generate_itinerary(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        interests: List[str],
        budget: str = "medium",
        group_type: str = "solo",
        additional_notes: str = ""
    ) -> TravelItinerary:
        """Generate a detailed travel itinerary using Gemini.
        
        Args:
            destination: Destination city or country
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            interests: List of interests (e.g., ["history", "food", "adventure"])
            budget: Budget level (low, medium, high, luxury)
            group_type: Type of travel group (solo, couple, family, friends, business)
            additional_notes: Any additional notes or preferences
            
        Returns:
            TravelItinerary object with daily plans
        """
        prompt = self._build_itinerary_prompt(
            destination, start_date, end_date, interests, 
            budget, group_type, additional_notes
        )
        
        try:
            response = await self._generate_text(prompt)
            return self._parse_itinerary_response(response, destination, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to generate itinerary: {str(e)}")
            raise
    
    async def get_travel_tips(
        self,
        destination: str,
        travel_dates: Dict[str, str],
        interests: List[str],
        group_type: str = "solo"
    ) -> Dict[str, Any]:
        """Get travel tips and advice for a destination.
        
        Args:
            destination: Destination city or country
            travel_dates: Dict with 'start_date' and 'end_date' (YYYY-MM-DD)
            interests: List of interests
            group_type: Type of travel group
            
        Returns:
            Dict with travel tips and advice
        """
        prompt = self._build_travel_tips_prompt(destination, travel_dates, interests, group_type)
        
        try:
            response = await self._generate_text(prompt)
            return self._parse_travel_tips(response)
        except Exception as e:
            logger.error(f"Failed to get travel tips: {str(e)}")
            raise
    
    async def start_chat_session(self, session_id: str, system_prompt: str = "") -> None:
        """Start a new chat session.
        
        Args:
            session_id: Unique session ID
            system_prompt: Initial system prompt to set the context
        """
        if session_id in self.chat_sessions:
            logger.warning(f"Chat session {session_id} already exists, resetting...")
        
        # Start a new chat session
        chat = self.model.start_chat(history=[])
        
        # Set the system prompt if provided
        if system_prompt:
            chat.send_message(system_prompt)
        
        self.chat_sessions[session_id] = chat
    
    async def chat(self, session_id: str, message: str) -> str:
        """Send a message in an existing chat session.
        
        Args:
            session_id: Session ID
            message: User message
            
        Returns:
            Assistant's response
            
        Raises:
            ValueError: If session_id doesn't exist
        """
        if session_id not in self.chat_sessions:
            raise ValueError(f"Chat session {session_id} not found")
        
        chat = self.chat_sessions[session_id]
        response = await chat.send_message_async(message)
        return response.text
    
    async def end_chat_session(self, session_id: str) -> None:
        """End a chat session.
        
        Args:
            session_id: Session ID to end
        """
        if session_id in self.chat_sessions:
            del self.chat_sessions[session_id]
    
    async def _generate_text(self, prompt: str) -> str:
        """Generate text using the Gemini model.
        
        Args:
            prompt: The prompt to send to the model
            
        Returns:
            Generated text response
        """
        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Text generation failed: {str(e)}")
            raise
    
    def _build_travel_recommendation_prompt(
        self,
        destination: str,
        travel_dates: Dict[str, str],
        interests: List[str],
        budget: str,
        group_type: str,
        previous_trips: List[Dict],
        additional_context: str
    ) -> str:
        """Build the prompt for travel recommendations."""
        prompt = f"""You are a knowledgeable travel assistant helping plan a trip. 
        Provide detailed recommendations for the following trip:
        
        Destination: {destination}
        Travel Dates: {travel_dates.get('start_date')} to {travel_dates.get('end_date')}
        Interests: {', '.join(interests) if interests else 'Not specified'}
        Budget: {budget}
        Group Type: {group_type}
        """
        
        if previous_trips:
            prompt += "\nPrevious Trips:"
            for trip in previous_trips:
                prompt += f"\n- {trip.get('destination')} ({trip.get('date')}): {trip.get('highlights', '')}"
        
        if additional_context:
            prompt += f"\nAdditional Context: {additional_context}"
        
        prompt += """
        
        Provide recommendations in the following JSON format:
        {
            "destination_overview": "Brief overview of the destination",
            "best_time_to_visit": "Best times to visit and why",
            "top_attractions": [
                {
                    "name": "Attraction name",
                    "description": "Brief description",
                    "cost": "Estimated cost or if it's free",
                    "best_time_to_visit": "Best time of day or season",
                    "accessibility": "Accessibility information"
                }
            ],
            "dining_recommendations": [
                {
                    "name": "Restaurant name",
                    "cuisine": "Type of cuisine",
                    "price_range": "$ - $$$$",
                    "special_dietary_options": ["vegetarian", "vegan", "gluten-free"],
                    "description": "What makes it special"
                }
            ],
            "accommodation_recommendations": [
                {
                    "name": "Hotel name",
                    "type": "hotel/hostel/vacation rental",
                    "price_range": "$ - $$$$",
                    "amenities": ["pool", "gym", "free breakfast"],
                    "proximity": "Proximity to attractions/transport"
                }
            ],
            "local_tips": [
                "Tip 1",
                "Tip 2"
            ],
            "safety_advice": "General safety advice for the destination"
        }
        """
        
        return prompt
    
    def _build_flight_analysis_prompt(
        self, 
        itineraries: List[FlightItinerary],
        user_preferences: Dict[str, Any]
    ) -> str:
        """Build the prompt for flight analysis."""
        flights_info = []
        for i, itin in enumerate(itineraries[:5]):  # Limit to top 5 for token efficiency
            flight_info = {
                "option": i + 1,
                "airlines": list({s.airline for s in itin.segments}),
                "total_duration_minutes": sum(s.duration_minutes for s in itin.segments),
                "total_price": itin.price,
                "currency": itin.currency,
                "stops": len(itin.segments) - 1,
                "departure_time": itin.segments[0].departure_time.isoformat(),
                "arrival_time": itin.segments[-1].arrival_time.isoformat(),
                "baggage_allowance": itin.segments[0].baggage_allowance if itin.segments else "Not specified"
            }
            flights_info.append(flight_info)
        
        prompt = f"""You are a flight booking assistant. Analyze these flight options and provide recommendations.
        
        User Preferences:
        - Budget: {user_preferences.get('budget', 'Not specified')}
        - Preferred Airlines: {', '.join(user_preferences.get('preferred_airlines', [])) or 'None specified'}
        - Cabin Class: {user_preferences.get('cabin_class', 'Economy')}
        - Max Stops: {user_preferences.get('max_stops', 'No preference')}
        - Travel Time: {user_preferences.get('travel_time', 'No preference')}
        - Other Preferences: {user_preferences.get('other_preferences', 'None')}
        
        Flight Options (in JSON format):
        {json.dumps(flights_info, indent=2)}
        
        Please analyze these options and provide:
        1. The best overall option and why
        2. The best value option (price vs. convenience)
        3. Any red flags or things to watch out for
        4. Additional tips for this route
        
        Format your response as a JSON object with these keys:
        {{
            "best_overall": {{"option": 1, "reason": "..."}},
            "best_value": {{"option": 2, "reason": "..."}},
            "red_flags": ["...", "..."],
            "additional_tips": ["...", "..."]
        }}
        """
        
        return prompt
    
    def _build_itinerary_prompt(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        interests: List[str],
        budget: str,
        group_type: str,
        additional_notes: str
    ) -> str:
        """Build the prompt for itinerary generation."""
        prompt = f"""You are a professional travel planner. Create a detailed daily itinerary for the following trip:
        
        Destination: {destination}
        Travel Dates: {start_date} to {end_date}
        Interests: {', '.join(interests) if interests else 'Not specified'}
        Budget: {budget}
        Group Type: {group_type}
        Additional Notes: {additional_notes or 'None'}
        
        Create a day-by-day itinerary with the following structure for each day:
        - Morning: Activities, places to visit
        - Afternoon: Lunch suggestions and activities
        - Evening: Dinner suggestions and evening activities
        
        Include practical information like:
        - Estimated costs where applicable
        - Transportation options between locations
        - Time required for each activity
        - Any necessary reservations or tickets
        - Local tips or tricks
        
        Format your response as a JSON object with this structure:
        {{
            "destination": "...",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "trip_duration_days": N,
            "daily_itinerary": [
                {{
                    "day": 1,
                    "date": "YYYY-MM-DD",
                    "activities": [
                        {{
                            "time": "Morning/Afternoon/Evening",
                            "title": "Activity/Place name",
                            "description": "Detailed description",
                            "location": "Address or area",
                            "duration_minutes": 120,
                            "cost": "Free/$$/$$$/$$$$",
                            "booking_required": true/false,
                            "booking_url": "...",
                            "tips": ["...", "..."]
                        }}
                    ]
                }}
            ],
            "estimated_total_cost": {{
                "budget_level": "low/medium/high/luxury",
                "range": "$ - $$$$",
                "cost_breakdown": {{
                    "accommodation": "...",
                    "food": "...",
                    "activities": "...",
                    "transportation": "...",
                    "miscellaneous": "..."
                }}
            }},
            "packing_suggestions": ["...", "..."],
            "local_customs_tips": ["...", "..."],
            "emergency_contacts": ["...", "..."]
        }}
        """
        
        return prompt
    
    def _build_travel_tips_prompt(
        self,
        destination: str,
        travel_dates: Dict[str, str],
        interests: List[str],
        group_type: str
    ) -> str:
        """Build the prompt for travel tips."""
        return f"""You are a knowledgeable travel expert. Provide useful travel tips for the following trip:
        
        Destination: {destination}
        Travel Dates: {travel_dates.get('start_date')} to {travel_dates.get('end_date')}
        Interests: {', '.join(interests) if interests else 'Not specified'}
        Group Type: {group_type}
        
        Provide a comprehensive list of travel tips including:
        1. Best ways to get around the destination
        2. Local customs and etiquette
        3. Money-saving tips
        4. Safety advice
        5. Must-try local foods
        6. Off-the-beaten-path recommendations
        7. Packing suggestions
        8. Any seasonal considerations
        
        Format your response as a JSON object with these keys:
        {{
            "transportation_tips": ["...", "..."],
            "local_customs": ["...", "..."],
            "money_saving_tips": ["...", "..."],
            "safety_advice": ["...", "..."],
            "food_recommendations": ["...", "..."],
            "hidden_gems": ["...", "..."],
            "packing_suggestions": ["...", "..."],
            "seasonal_considerations": ["...", "..."]
        }}
        """
    
    def _parse_travel_recommendations(self, response: str) -> Dict[str, Any]:
        """Parse the travel recommendations response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the response
            try:
                # Look for JSON-like content in the response
                start = response.find('{')
                end = response.rfind('}') + 1
                if start >= 0 and end > start:
                    return json.loads(response[start:end])
                raise
            except:
                logger.error("Failed to parse travel recommendations")
                return {
                    "error": "Failed to parse recommendations",
                    "raw_response": response
                }
    
    def _parse_flight_analysis(self, response: str) -> Dict[str, Any]:
        """Parse the flight analysis response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse flight analysis",
                "raw_response": response
            }
    
    def _parse_itinerary_response(self, response: str, destination: str, start_date: str, end_date: str) -> TravelItinerary:
        """Parse the itinerary response into a TravelItinerary object."""
        try:
            data = json.loads(response)
            
            # Create daily plans
            daily_plans = []
            for day_data in data.get("daily_itinerary", []):
                activities = []
                for act_data in day_data.get("activities", []):
                    activity = Activity(
                        title=act_data.get("title", ""),
                        description=act_data.get("description", ""),
                        location=act_data.get("location", ""),
                        start_time=datetime.strptime(f"{day_data['date']} {act_data.get('time', '12:00').split('-')[0].strip()}", 
                                                   "%Y-%m-%d %H:%M"),
                        duration_minutes=act_data.get("duration_minutes", 60),
                        cost=act_data.get("cost", ""),
                        booking_required=act_data.get("booking_required", False),
                        booking_url=act_data.get("booking_url", ""),
                        notes=", ".join(act_data.get("tips", []))
                    )
                    activities.append(activity)
                
                daily_plan = DailyPlan(
                    date=datetime.strptime(day_data["date"], "%Y-%m-%d").date(),
                    activities=activities
                )
                daily_plans.append(daily_plan)
            
            # Create the itinerary
            itinerary = TravelItinerary(
                title=f"{destination} Itinerary",
                destination=destination,
                start_date=datetime.strptime(start_date, "%Y-%m-%d").date(),
                end_date=datetime.strptime(end_date, "%Y-%m-%d").date(),
                daily_plans=daily_plans,
                estimated_budget=data.get("estimated_total_cost", {}).get("range", "$"),
                notes=[
                    f"Budget Level: {data.get('estimated_total_cost', {}).get('budget_level', 'medium')}",
                    "Packing Suggestions: " + ", ".join(data.get("packing_suggestions", [])),
                    "Local Customs: " + ", ".join(data.get("local_customs_tips", []))
                ]
            )
            
            return itinerary
            
        except Exception as e:
            logger.error(f"Failed to parse itinerary: {str(e)}")
            # Return a basic itinerary with the error
            return TravelItinerary(
                title=f"{destination} Itinerary",
                destination=destination,
                start_date=datetime.strptime(start_date, "%Y-%m-%d").date(),
                end_date=datetime.strptime(end_date, "%Y-%m-%d").date(),
                daily_plans=[],
                notes=[f"Error generating itinerary: {str(e)}"]
            )
    
    def _parse_travel_tips(self, response: str) -> Dict[str, Any]:
        """Parse the travel tips response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse travel tips",
                "raw_response": response
            }

# Singleton instance
gemini_service = GeminiService()

# Example usage
if __name__ == "__main__":
    import asyncio
    from datetime import datetime, timedelta
    
    async def test_travel_recommendations():
        service = GeminiService()
        
        # Test travel recommendations
        recommendations = await service.generate_travel_recommendations(
            destination="Kyoto, Japan",
            travel_dates={
                "start_date": "2024-11-15",
                "end_date": "2024-11-25"
            },
            interests=["history", "food", "nature"],
            budget="medium",
            group_type="couple"
        )
        
        print("Travel Recommendations:")
        print(json.dumps(recommendations, indent=2))
    
    async def test_itinerary_generation():
        service = GeminiService()
        
        # Test itinerary generation
        itinerary = await service.generate_itinerary(
            destination="Barcelona, Spain",
            start_date="2024-09-10",
            end_date="2024-09-17",
            interests=["architecture", "beaches", "food"],
            budget="medium",
            group_type="friends",
            additional_notes="We love trying local foods and exploring hidden gems."
        )
        
        print("\nGenerated Itinerary:")
        print(f"Destination: {itinerary.destination}")
        print(f"Duration: {itinerary.start_date} to {itinerary.end_date}")
        print(f"Estimated Budget: {itinerary.estimated_budget}")
        
        for day in itinerary.daily_plans:
            print(f"\nDay {day.date}:")
            for activity in day.activities:
                print(f"- {activity.time}: {activity.title} ({activity.duration} min)")
    
    # Run the tests
    # asyncio.run(test_travel_recommendations())
    # asyncio.run(test_itinerary_generation())
