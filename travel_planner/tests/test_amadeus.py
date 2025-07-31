import os
import json
from dotenv import load_dotenv
from pathlib import Path
import sys
import requests
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from .env file
load_dotenv()

# Configure the Amadeus API credentials
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
    raise ValueError("Amadeus API credentials not found in environment variables")

# Amadeus API endpoints
TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
FLIGHT_OFFERS_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

class AmadeusClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expiry = None
    
    def _get_auth_token(self):
        """Get an access token from Amadeus API."""
        # If we have a valid token, return it
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
            
        # Otherwise, get a new token
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        # Set token expiry 5 minutes before actual expiry to be safe
        self.token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'] - 300)
        
        return self.access_token
    
    def search_flights(self, origin, destination, departure_date, return_date=None, adults=1):
        """Search for flight offers."""
        headers = {
            'Authorization': f'Bearer {self._get_auth_token()}'
        }
        
        params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': adults,
            'max': 5  # Limit to 5 results
        }
        
        if return_date:
            params['returnDate'] = return_date
        
        response = requests.get(FLIGHT_OFFERS_URL, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()

def test_amadeus_flight_search():
    """Test function to search for flights using Amadeus API."""
    try:
        client = AmadeusClient(AMADEUS_API_KEY, AMADEUS_API_SECRET)
        
        # Set up test parameters
        origin = "NYC"  # New York
        destination = "LAX"  # Los Angeles
        departure_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        print(f"Searching for flights from {origin} to {destination} on {departure_date}...")
        
        # Make the API request
        results = client.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            adults=1
        )
        
        # Print the results in a readable format
        print("\nFlight Search Results:")
        print("=" * 50)
        
        if 'data' in results and results['data']:
            for i, offer in enumerate(results['data'], 1):
                print(f"\nOffer {i}:")
                print(f"Price: {offer['price']['total']} {offer['price']['currency']}")
                
                # Print itinerary details
                for segment in offer['itineraries'][0]['segments']:
                    departure = segment['departure']['at']
                    arrival = segment['arrival']['at']
                    print(f"{segment['departure']['iataCode']} -> {segment['arrival']['iataCode']}")
                    print(f"  Departure: {departure}")
                    print(f"  Arrival: {arrival}")
                    print(f"  Airline: {segment.get('carrierCode', 'N/A')} {segment.get('number', '')}")
                    print("-" * 40)
        else:
            print("No flight offers found.")
            if 'warnings' in results:
                print("\nWarnings:")
                for warning in results['warnings']:
                    print(f"- {warning['title']}: {warning['detail']}")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    test_amadeus_flight_search()
